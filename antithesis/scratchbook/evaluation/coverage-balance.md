---
sut_path: /home/exedev/wellnest
commit: 9e9e52f1a8f7948ebfc911fe95571579a1ff37c5
updated: 2026-10-05
external_references:
  - path: https://github.com/sy00n89/wellnest
    why: Upstream repo named by the user as the outside source; checked for issues, PRs, and wiki (no issues, no wiki, one merged PR #1 "local dev").
---

# Evaluation — Lens 2: Coverage Balance

## Summary

The catalog's coverage follows the four "Leave for Antithesis to find" rows in
`docs/LEARNING_PLAN.md` closely: same-ms overwrite, browser-driven patterns, plant
drift, delete not updating plant/patterns. It covers those well. Coverage is thin
where the SUT analysis itself points at risk outside those rows: the
production-vs-shim fidelity gaps (timeouts as well as concurrency), the read path
under failure (a 500 on `GET /entries` empties the user's history), clock behaviour,
and the anthropic-mock as a fault source. Weight is spread unevenly. Entry
integrity has seven properties, three of which cannot fail. The dependency-failure
area has four, and their mechanisms are partly mis-described.

## Risk area → property map (from `sut-analysis.md`)

| SUT-analysis risk area | Risk | Catalog properties | Assessment |
|---|---|---|---|
| Same-ms key collision (`create_entry`) | High | acked-entry-is-listed, concurrent-creates-all-retained, delete-removes-only-target, entry-fields-round-trip, overlapping-same-user-writes-occur | Over-covered by count. Two of five cannot fail (see antithesis-fit F-FIT-1/F-FIT-8). The clock-backward trigger is missing (gap G-3). |
| Patterns RMW lost update | High | pattern-increments-not-lost, pattern-frequency-matches-entries | Adequate. |
| Plant RMW + swallowed error | Medium | plant-checkins-match-entry-count, plant-update-never-fails-silently, plant-stage-matches-checkins, plant-reaches-later-stage | Adequate count. `plant-stage-matches-checkins` cannot fail. |
| Non-atomic check-in (entry + plant + N pattern POSTs) | Medium | plant-checkins-match-entry-count, pattern-frequency-matches-entries | Covered. The "500 with entry stored" outcome is not modelled (see implementability). |
| Catch-all 500 / frontend ignores status | Medium | no-500-for-valid-requests | Covers only the write side. Read-side impact missing (gap G-2). |
| Insights timeout path | Medium | insights-never-500, insights-fallback-exercised, insights-normal-reply-parsed | Three properties, but the mechanism is incomplete and the impact overstated (antithesis-fit F-FIT-6). The mock never produces the stalls the property needs (gap G-4). |
| Startup ordering (`create_tables.py` exits, no restart policy) | Medium | api-recovers-after-faults (only with node termination) | Thin. Only exercised if api node termination is on. |
| dynamodb in-memory restart | Low (harness config) | data-survives-dynamodb-restart, api-recovers-after-faults | Over-invested. One property tests dynamodb-local, not Wellnest. |
| Pagination (≥1 MB per user) | Medium (lists, delete lookup, plant count, insights all affected) | none (deferred) | Exclusion is defensible, but the stated reason is wrong (see G-5). |
| Display ordering (client `date`/`time` vs server `timestamp`) | Low | none | Fine to omit, except under clock jitter (G-3). |
| Eventual consistency on real DynamoDB | n/a in Antithesis | none | Correctly omitted. dynamodb-local cannot reproduce it. |
| Lambda/API Gateway timeouts (30 s / 29 s) | Not identified by SUT analysis | none | Gap G-1. |

## Catalog-wide findings

### G-1 — Second fidelity gap not covered: production has a 30 s per-invocation deadline, the shim has none

`backend/template.yaml` `Globals.Function.Timeout: 30` (API Gateway's integration
limit is 29 s). The shim has no deadline. Two consequences no property models:

- In production, a slow dynamodb call (boto3 waits up to 60 s per attempt) gets
  the Lambda **killed mid-handler**, for example after the entry `put_item` and
  before `update_plant`. No exception, no swallowed error, and the client gets a 5xx
  while the entry is stored. That is the main production path to plant drift and
  to "unknown outcome" creates. Locally the same fault produces a slow 201 instead.
- `insights.call_anthropic` uses `urlopen(timeout=60)`, longer than the 30 s Lambda
  timeout. In production the timeout-fallback logic can never run on a slow
  Anthropic call. The Lambda is killed first. That is a real configuration defect,
  visible by reading, which no property states.

Suggested direction for gap-filling: a latency property such as "every request
returns within 29 s when its dependencies are reachable", and a workload HTTP
timeout of 29 s so that the workload's outcome model (201 / error / unknown) matches
what a production client would see. The concurrency fidelity gap is handled at the
catalog level. This one is not mentioned anywhere.

### G-2 — Read-path failure impact is missing; the catalog only weighs write-side 500s

`App.jsx` `loadData`: `setEntries(Array.isArray(entriesData) ? entriesData : [])`.
A 500 on `GET /entries` returns `{"error": ...}`, so the user sees an **empty
history**, and every client-derived display (trends, client plant stage, top
triggers) goes blank. For a journal, "all my check-ins are gone" is the most
alarming user-visible failure, even if it is transient. `no-500-for-valid-requests`
Why It Matters mentions only that a 500 "looks like success". No property
distinguishes read 500s or asserts that `GET /entries` keeps serving under faults
(for example a `Sometimes(GET /entries == 200 during an active fault)` or a
read-specific liveness check). Suggested action: split read-route coverage out of
`no-500-for-valid-requests`, or add a read-availability liveness property, and
update Why It Matters.

### G-3 — Clock behaviour has no coverage and no human question

The catalog leaves clock-specific properties out because "clock faults are off by
default". Clock jitter alone (no concurrency) can cause same-ms key collisions by
re-walking past milliseconds (antithesis-fit F-FIT-3). It also reorders storage
(`timestamp`) relative to display (`date`/`time` from the client), and `GET /entries`
sorts by `timestamp`. That makes clock jitter the only way to find the P0 bug on the
committed shim. Suggested action: add a catalog-level open question "Is clock
jitter enabled for the tenant?" and a gap-fill pass on clock-driven collision.

### G-4 — The anthropic-mock is a fault source the catalog doesn't use

The mock is harness-owned (`mocks/anthropic/server.py`) and today always replies
instantly with 200. Every insights 500 path (stall ≥60 s before headers or mid-body,
connection closed mid-request; see antithesis-fit F-FIT-6) depends on an
Antithesis fault lasting 60 s or more, or on node termination. Coverage of the
insights area therefore rests on a fault duration nobody has confirmed. Because the
mock is a test double, it could legitimately inject these behaviours itself: a rare
long sleep, an abrupt connection close, a non-JSON body, a `content` that isn't a
list (the `data.get('content') or [{}]` → `content[0].get(...)` path raises on a
non-dict element). Suggested action: record in the catalog (or deployment topology)
that the mock should draw these misbehaviours, ideally via the Antithesis SDK random
source, so the insights properties can be reached.

### G-5 — Pagination exclusion: right decision, wrong reason

The catalog defers pagination because "the workload would need very large notes,
which competes with search budget". DynamoDB items can be up to 400 KB, so three or
four entries with notes of about 300 KB cross the 1 MB query page. That is cheap.
The better reason to leave it out of Antithesis is that it fails **deterministically
with sequential requests**, so it is integration-test territory. `docs/LEARNING_PLAN.md`
also schedules it as a Phase 2 fix. One non-obvious effect worth recording for that
test: the query returns ascending by sort key, so the first page holds the user's
**oldest** entries. `insights` then sorts that page descending and takes 14, so past
1 MB the "recent" insight is built from the oldest data. Suggested action: correct
the stated rationale. No Antithesis property needed.

### G-6 — Assertion-type balance: guidance assertions don't point at the interesting states

Counts: 15 `Always`/`Unreachable`, 1 `Reachable`, 5 `Sometimes`. The mix is fine on
paper. But the five `Sometimes` and the one `Reachable` are almost all reached by
any workload without faults: delete returns 200, plant reaches stage, overlapping
client requests, a good mock reply, the mock's 10% empty text satisfying
`insights-fallback-exercised`. None of them confirms that the run reached a state
the safety properties depend on. Missing guidance states:

- Server-side near-collision: two acknowledged entries for one user with server
  `timestamp`s 1 ms or less apart (observable from `GET /entries`; see implementability).
- A create still in flight when a delete of its id is issued (antithesis-fit F-FIT-5).
- A request served successfully *during* an active api↔dynamodb fault (degraded-but-working).
- The insights fallback reached through the `except` branch, specifically, not the
  empty-text branch the mock reaches 10% of the time.

### G-7 — Component distribution

Properties sit almost entirely on api↔dynamodb. The api↔anthropic-mock link has
three properties, but their reachability depends on G-4. The workload↔api link
(request lost after the server acted, the source of unknown outcomes) is treated only
as a modelling caveat, never as a target. A `Sometimes("create outcome unknown but
entry later listed")` would show that the run exercised lost responses. That is the
exact precondition for F-FIT-5 and for model correctness in
`acked-entry-is-listed`.

## Property-specific findings

- `pattern-frequency-matches-entries` and `plant-checkins-match-entry-count` both
  claim the non-atomic check-in. Only the plant side has a server-side claim of
  consistency (`update_plant` docstring). The patterns side is browser-driven, with
  no reconciliation by design, so it is a design-gap report, not a coverage
  property. This weighs the derived-state category toward a known gap.
- Category "Lifecycle and recovery" has two properties. One is vacuous by default
  (`data-survives-dynamodb-restart`). The other uses `Sometimes`, which cannot
  detect a non-recovering timeline (antithesis-fit F-FIT-7). Effective lifecycle
  coverage is close to zero under default fault settings.
- Inconsistency: the catalog intro says "P0 concurrency properties
  (`concurrent-creates-all-retained`, `pattern-increments-not-lost`)", but the table
  lists `pattern-increments-not-lost` as P1. `acked-entry-is-listed` (P0) is equally
  vacuous on the committed shim (its main mechanism is the collision), and the intro
  doesn't say so.

## Passes

- Safety, liveness, and reachability are all represented.
- Every high-risk item in the SUT analysis "Concurrency model" section has at least
  one property with a correct mechanism.
- The fix for 3558b2c (delete updates plant; commit present in history as the
  second parent of PR #1) is correctly covered as a regression target by
  `plant-checkins-match-entry-count`.
- Leaving out `POST`/`PUT /plant` and eventual consistency is justified.

## Uncertainties

- Whether dynamodb-local enforces the 1 MB query page limit exactly as DynamoDB does
  (affects G-5's "cheap" claim, not its conclusion).
- Whether the owner treats insights as a user-facing feature with an SLA, which
  sets how much weight G-4 deserves.
