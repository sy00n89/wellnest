---
sut_path: /home/exedev/wellnest
commit: 9e9e52f1a8f7948ebfc911fe95571579a1ff37c5
updated: 2026-10-05
external_references:
  - path: https://github.com/sy00n89/wellnest
    why: Upstream repo named by the user as the outside source; checked for issues, PRs, and wiki (no issues, no wiki, one merged PR #1 "local dev").
---

# Evaluation — Lens 4: Wildcard

Other lenses: Lens 1 Antithesis Fit (sweet spot vs unit-test territory), Lens 2
Coverage Balance (risk areas vs property set), Lens 3 Implementability (observability,
topology, preconditions). This pass looks for what those frames miss.

## W-1 — The production user model is "everyone is `default`", and the workload plan dilutes it

`App.jsx`: `const USER_ID = "default";` is used for every request, and the deployed
SPA points at the real API Gateway URL. So **every person using the production app
shares one `user_id`**. Consequences the catalog doesn't draw out:

- Same-ms collisions in production depend on **total app traffic**, not one
  person's typing speed. The catalog frames concurrency as "one user, overlapping
  requests". In production that overlap is any two people checking in within the
  same millisecond.
- Per-"user" reads (`GET /entries`, `update_plant`'s count, the delete lookup,
  insights) query the whole app's data. The 1 MB pagination limit is hit by combined
  usage, which makes pagination more relevant than the catalog treats it.
- `plant`'s `check_ins` and patterns' `frequency` are app-wide tallies.
- `user-entries-isolated` ("users only see their own entries") describes a property
  production doesn't have at all.

The catalog says "the workload uses a few user ids". Spreading writes across users
**lowers** collision and race probability compared with production. Suggested action:
make a single shared user id the dominant workload pattern (with per-driver users
only where model ownership needs them, see implementability I-2). Record the
"everyone is `default`" fact in the catalog so priorities reflect it. This is
a framing question for the human: is the target the deployed prototype as it is
(one shared user) or the intended multi-user product (Phase 5)?

## W-2 — Bias: the catalog is built to confirm four known bugs, and has little left to find once they fire

`docs/LEARNING_PLAN.md` lists "Leave for Antithesis to find": same-ms overwrite,
non-atomic patterns, plant drift and dual stage algorithms, delete not updating
plant/patterns. The P0/P1 safety properties map one-to-one onto those rows. They
will fire early (two fire deterministically or nearly so). After that, the
catalog's remaining properties mostly cannot fail (antithesis-fit F-FIT-1), so
continued runs mostly re-report the same four.

The paths this evaluation found that were *not* in the learning plan are the ones
that show what Antithesis is for:

- Delete resurrection through botocore's automatic `put_item` retry (antithesis-fit F-FIT-5).
- Insights 500 through header-wait timeout or `RemoteDisconnected`, not only body stalls (F-FIT-6).
- Same-ms collision with **no concurrency** under clock jitter (F-FIT-3).
- `urlopen(timeout=60)` longer than the 30 s Lambda timeout, so production's
  fallback can never run (coverage G-1).

Judgment needed from the human: is the run's goal to confirm the planted bugs
(teaching value, already met by about 5 properties), or to find unknown ones? If the
latter, rebalance budget away from the guard properties toward these mechanisms.

## W-3 — Properties should survive the planned fixes

The learning plan says "After the first run finds them, we fix them." The fixes named
in the evidence files are `timestamp#uuid` as the sort key (or
`ConditionExpression attribute_not_exists` plus retry), and `update_item ADD
frequency`. Two observations:

- The fix-agnostic properties (`acked-entry-is-listed`, `pattern-increments-not-lost`
  in its bound form, `plant-checkins-match-entry-count`) stay useful after the fix.
  Attribution details that assume a numeric ms key (for example "missing entry
  shares a timestamp") should stay in assertion *details*, not in the condition.
- A conditional-put-plus-retry fix brings a new failure mode the catalog should
  expect. Under a backward clock step the retry can collide repeatedly. With
  botocore's own retry of a conditional put whose first attempt landed, the retry
  fails with `ConditionalCheckFailedException` even though the item was written,
  so the create returns an error for a stored entry. `acked-entry-is-listed` with
  the unknown-outcome model (implementability I-1) catches the consequences.
  Worth a note in its evidence file so the post-fix run is read correctly.
- Changing the sort key type (`N` to `S` for `timestamp#uuid`) is a schema migration
  of existing data. It is the only lifecycle transition on the horizon and no
  property spans it. Probably out of scope. Flag for the human.
- The patterns severity blend `(old + new) / 2` can't be expressed with `ADD`, so a
  fix that keeps a read for severity leaves an RMW race there. `pattern-increments-not-lost`
  won't see it, and nothing checks severity.

## W-4 — Make the workload's outcome model match a production client: 29 s

This combines fit F-FIT-4, coverage G-1 and implementability I-4. The shim's lack
of a deadline is what makes boto3's 60 s / 10-attempt behaviour turn faults into
long successes locally, where production would give a 5xx and a possibly half-done
check-in. A minimal, harness-only change brings the semantics back: **the workload
uses a 29 s HTTP timeout on every request** (API Gateway's integration limit) and
treats a timeout as "unknown outcome", exactly what a production browser would
experience. Then:

- `insights-never-500` can be reformulated as "insights returns 200 with text within
  29 s", which fails whenever Anthropic stalls for more than 29 s. That is far more
  reachable than more than 60 s, and it encodes the real production defect
  (60 s urllib timeout > 30 s Lambda timeout).
- The "entry stored, plant not updated, client saw an error" path stays reachable
  as a quiescent `plant-checkins-match-entry-count` failure without needing botocore
  to exhaust its retries. The server thread finishes later, but the client has
  already given up, which is the production outcome.

Caveat: unlike Lambda, the shim does not kill the handler, so a late
`update_plant` still runs. The model gives the right client-visible outcome but
not identical server state. Record this as an assumption.

## W-5 — Cross-lens: `insights-never-500` is high-fit but hard to observe; another formulation captures the risk

Fit says it is reachable by more paths. Implementability says the workload can't
separate "dynamodb unavailable" 500s from "Anthropic exception escaped" 500s without
parsing error strings. Coverage says the mock never produces the triggering
behaviour. One formulation fixes all three:

1. SUT-side `unreachable("insights: non-fallback exception from call_anthropic", {type})`
   around `call_anthropic` (a precise anchor, no body heuristics).
2. The mock draws rare misbehaviours (long stall, abrupt close, non-JSON, non-list
   `content`), preferably through the Antithesis SDK random source so Antithesis can
   steer them.
3. Workload-side assertion reduced to the 29 s latency form (W-4).

Also correct the impact: the SPA shows the same fallback text on a 500
(`data.text || "Unable to generate insight..."`), so users don't see these 500s
today.

## W-6 — The concurrency fix itself has a fidelity gap pointing the other way

Everyone has treated thread-pool dispatch as "Lambda-like". It isn't, quite: it
shares module-level `boto3.resource` / `Table` objects across threads, which boto3
documents as not thread-safe, and Lambda never does that. `uvicorn --workers N`
(compose command override, no code change) is the faithful model: serial per
instance, many instances. See implementability I-3. This matters for trusting
results. A failure that only reproduces under thread-pool dispatch might be a
harness artifact.

## W-7 — Odd things in the catalog and analysis

- The SUT analysis says Antithesis "cannot find the two highest-impact bugs, no
  matter how it schedules requests" on the committed shim. False under clock
  jitter (F-FIT-3). The catalog repeats it as "cannot fail".
- `deleted-entry-stays-gone`'s evidence says nothing rewrites a deleted key with the
  same id. botocore does (F-FIT-5). This is the one "guard" property with a live
  mechanism, and it is ranked "low expected yield".
- `delete-removes-only-target`'s Antithesis Angle describes behaviour the code
  doesn't have (a pre-existing overwrite gives a 404, not a wrong delete).
- `no-500-for-valid-requests` is "expected to fire under partitions", but botocore's
  retries make that unlikely within any workload timeout. The catalog's own
  expectation about its most generic property is probably wrong.
- Intro text calls `pattern-increments-not-lost` P0. The table says P1.
- A `GET /entries` 500 empties the user's whole history in the SPA
  (`Array.isArray(...) ? ... : []`). That is the most alarming user-visible symptom
  the API can produce, and the catalog never mentions it (coverage G-2).

## W-8 — A scenario nobody modelled: the client gives up, the server finishes

Every client in this system (SPA, API Gateway at 29 s, the Antithesis workload) can
abandon a request the server then completes. The SPA's sequential flow (create →
N pattern POSTs → reload) means an abandoned create, or one that only looks
abandoned, still gets its pattern POSTs, and a create that returned 500 may be
stored. The catalog treats "unknown outcome" as a caveat for modelling. It is
actually the main real-world way the tables diverge, and it combines with
concurrency to produce resurrection (F-FIT-5) and patterns counting entries that
don't exist. A guidance assertion
`Sometimes("create outcome unknown to client but entry later listed")` would show the
run actually explored it.

## Uncertainties

- Whether the deployed production app is really used by more than one person (if
  it's a single-user prototype, W-1's traffic argument weakens, but the "a few user
  ids" workload still under-weights the single shared key space).
- Whether the owner considers the 30 s Lambda deadline in scope for a local-shim test
  at all.
