---
sut_path: /home/exedev/wellnest
commit: 9e9e52f1a8f7948ebfc911fe95571579a1ff37c5
updated: 2026-10-05
external_references:
  - path: https://github.com/sy00n89/wellnest
    why: Upstream repo named by the user as the outside source; checked for issues, PRs, and wiki (no issues, no wiki, one merged PR #1 "local dev").
---

# Evaluation — Lens 1: Antithesis Fit

## Summary

The catalog's top tier (`acked-entry-is-listed`, `concurrent-creates-all-retained`,
`pattern-increments-not-lost`, `plant-checkins-match-entry-count`) sits squarely in
Antithesis territory: lost updates and key collisions that need overlapping requests
and partial failures. Below that tier, about a third of the catalog cannot fail
against the current code under any timing or fault, or fails deterministically
without faults. Two things work the other way: clock faults and boto3's
automatic retries open real failure paths that the catalog either leaves out or
says cannot happen.

Verification done for this lens (code read at commit 9e9e52f, plus local Python
3.12.3 experiments and the botocore 1.43.106 sources in `backend/.venv`):

- `urllib` exception types for a stalled or closed Anthropic connection (experiment, see F-FIT-6).
- botocore defaults: `connect_timeout = read_timeout = 60` (`botocore/endpoint.py`
  `DEFAULT_TIMEOUT = 60`); retry mode `legacy` (`NEW_RETRIES_ENABLED` resolves False);
  DynamoDB legacy policy `max_attempts: 10`, exponential backoff base 0.05 s, growth 2
  (`botocore/data/_retry.json`); `ReadTimeoutError` and `EndpointConnectionError` are
  retried (`retryhandler.py`).

## Catalog-wide findings

### F-FIT-1 — About a third of the catalog cannot fail against this code (unit-test territory)

Affected: `entry-ids-unique-in-list`, `user-entries-isolated`, `plant-stage-matches-checkins`,
`entry-fields-round-trip`, `delete-removes-only-target` (as specified), `insights-normal-reply-parsed`.

| Slug | Why no fault or interleaving can break it today |
|---|---|
| `entry-ids-unique-in-list` | `id = str(uuid.uuid4())` server-side in `create_entry`; client ids are ignored. Two items with the same `id` need two puts with the same uuid under different keys. Nothing does that. (Its evidence file says so.) |
| `user-entries-isolated` | Every read is `Key('user_id').eq(user_id)` on the hash key. The query cannot return another hash key. Also, `user_id` is a client-supplied query parameter with no auth, so "isolation" does not exist as a guarantee: any caller can read any user by passing their id. The check is a tautology about DynamoDB. |
| `plant-stage-matches-checkins` | `stage` and `check_ins` are computed from the same `total` and written in one `put_item` (`entries.update_plant`). `GET /plant`'s default is `sprout`/0, also consistent. Only `POST`/`PUT /plant` can break it, and the workload excludes those. |
| `entry-fields-round-trip` | Under a same-ms overwrite the surviving item keeps *its own* id and content together, because they arrive in one `put_item`. The catalog's angle ("id stays but content changes, or vice versa") does not have a mechanism. |
| `delete-removes-only-target` | See F-FIT-3. Under the serial context the invariant requires, it cannot fail. |
| `insights-normal-reply-parsed` | The mock returns `GOOD_REPLY` 80% of the time with HTTP 200 and no delay. The `Sometimes` is satisfied by the first or second call of almost any timeline. It tests the mock. |

These are cheap as workload-side side checks, so search budget is not the main cost.
The cost is implementation effort and false signal in the report: six green
properties that could never have been red. Suggested action: keep at most
`entry-ids-unique-in-list` and `entry-fields-round-trip` as unlisted side checks
inside the `acked-entry-is-listed` read path (no separate catalog entries). Drop or
mark the others as non-Antithesis regression guards. If `user-entries-isolated`
stays, its Why It Matters should say there is no isolation guarantee today.

### F-FIT-2 — Two properties fail by construction, not through exploration

Affected: `pattern-frequency-matches-entries`, `data-survives-dynamodb-restart`.

- `pattern-frequency-matches-entries`: the catalog says itself that it "fails
  deterministically once any delete of an entry with triggers happens". `delete_entry`
  never touches the patterns table, which the code shows and `docs/LEARNING_PLAN.md`
  lists. The second failure path ("the workload fails before sending pattern posts")
  is the workload's own choice. The workload decides whether to send the pattern
  POSTs and knows if they failed, so Antithesis finds nothing there that the
  workload author didn't put in. Only the lost-update path is a real exploration
  result, and `pattern-increments-not-lost` already isolates it. As written, the
  property goes red within the first few minutes of every run and stays red.
  Suggested action: either (a) reformulate as an all-time tally,
  `freq_T == count of acked creates containing T whose pattern POSTs the workload sent`
  (which then mostly duplicates `pattern-increments-not-lost`), or (b) keep it as
  a known-failing design gap that is reported once, not as an Antithesis property.
  This depends on the existing human question about delete semantics.
- `data-survives-dynamodb-restart`: dynamodb-local `-inMemory` loses everything on
  restart, so this fails on the first restart. With `-sharedDb -dbPath` it tests
  dynamodb-local's durability, not Wellnest code. Wellnest has no durability logic
  to test. With default faults (node termination off) it never runs. Suggested
  action: drop it. Keep the Wellnest-relevant half (does the api serve again after a
  dynamodb restart) in `api-recovers-after-faults`.

### F-FIT-3 — The catalog says the P0 concurrency properties "cannot fail" on the committed shim. That holds only without clock faults.

Affected: `concurrent-creates-all-retained`, `acked-entry-is-listed`, catalog-level
"Relevant to all properties" note and the Assumptions bullet about clock jitter.

The entry key is `(user_id, int(time.time()*1000))`. If the clock steps **backward**
by more than a few ms (Antithesis clock jitter, see `faults.md`), later creates
re-walk milliseconds that already hold this user's entries. Each new create
overwrites an older acknowledged entry when its ms matches exactly. On the
serialized shim a create takes a few ms, so existing entries are dense in that
window. The chance per create is roughly (entries in the window) / (window ms),
which is far from negligible for a busy user. That is a key collision **with no
concurrency at all**, so it also works on the committed shim. The catalog lists clock
jitter only as something that "widens the window" and leaves clock-specific
properties out because clock faults are "off by default". `faults.md` says they are
*commonly* disabled and that the tenant setting must be confirmed. Suggested
action: make "enable clock jitter" a catalog-level human question next to node
termination, and note in `concurrent-creates-all-retained` / `acked-entry-is-listed`
that clock jitter alone can trigger the collision.

### F-FIT-4 — boto3's 60 s timeouts and 10 attempts change which fault-driven paths are reachable

Affected: `plant-update-never-fails-silently`, `no-500-for-valid-requests`,
`plant-checkins-match-entry-count` (partial-failure path),
`api-recovers-after-faults`; catalog-wide framing of "network faults → boto3 exceptions → 500".

Every handler uses a default `boto3.resource('dynamodb')`. With botocore 1.43.106
defaults, a dynamodb call whose packets are dropped waits up to 60 s
(`read_timeout`), then retries, up to 10 attempts. That is about 10 minutes before
an exception if packets keep dropping. With connection refused (only when dynamodb
is down), the backoff sum is about 25 s before an exception. Antithesis partitions
and bad-node faults mostly drop or hold packets. So typical faults lasting a few
seconds to tens of seconds show up as **slow requests that succeed**, not as
exceptions. Consequences:

- `plant-update-never-fails-silently` (`Unreachable`): the `except` branch needs a
  minutes-long api↔dynamodb disruption, or dynamodb down for about 25 s or more
  (node termination, which is off by default). It is likely never reached, so it
  passes for the wrong reason.
- `no-500-for-valid-requests`: the catalog says it is "expected to fire under
  api↔dynamodb partitions". Likely false for entries/plant/patterns. The workload's
  own HTTP timeout fires first. The 500s it does see will mostly come from
  `/insights` (F-FIT-6), which duplicates `insights-never-500`.
- `plant-checkins-match-entry-count`: the "network fault between the two writes"
  path is reachable mainly as "boto3 eventually raised", which is rare as above, or
  as "put_item landed, response lost, retries exhausted → 500 with the entry
  stored". The lost-update race (needs concurrency) is the realistic path.

This does not make the properties wrong. It changes which ones Antithesis can
actually push to failure. Suggested action (for the implementability lens and the
human): either accept that these paths are rare, or set `AWS_RETRY_MODE=standard`
/ `AWS_MAX_ATTEMPTS` in the Antithesis compose env (env-only, no code change; botocore
`configprovider.py` honours both). Lowering the 60 s timeouts requires a
`botocore.config.Config` in code. Note that production Lambda caps this at the
30 s function timeout (`template.yaml` `Globals.Function.Timeout: 30`). See the
wildcard lens.

## Property-specific findings

### F-FIT-5 — `deleted-entry-stays-gone` is underestimated: boto3 put retry can resurrect a deleted entry

The evidence file says "nothing rewrites that key with the same id", which is wrong.
botocore retries `put_item` on `ReadTimeoutError`, resending the **same item**
(same uuid, same timestamp). Sequence under concurrency (thread-pool or multi-worker):

1. Create X: `put_item` reaches dynamodb and is stored. The response is dropped
   (api←dynamodb fault). boto3 waits up to 60 s.
2. Meanwhile another driver lists entries for the user, sees X, `DELETE /entries/X` → 200.
3. boto3 retries `put_item(X)` → X is back. Create returns 201.
4. X reappears in later lists after a successful delete. The property fires.

This is an Antithesis-shaped scenario (needs a fault on one direction of one link
plus an interleaving inside a 60 s window). It is also realistic: one user, two
devices. It needs the workload to delete ids it **observed in a list**, not only
ids it saw acknowledged. Suggested action: keep the property, rewrite its Antithesis
Angle and evidence around this mechanism, add the workload requirement, and pair it
with a `Sometimes("delete of an entry whose create is still in flight")` guidance
assertion. On the committed shim it cannot happen, because the create blocks the
event loop for the whole retry window.

### F-FIT-6 — `insights-never-500` is reachable by more paths than the catalog states, and its user impact is overstated

Experiment (Python 3.12.3, `urllib.request.urlopen(timeout=1)` against a raw socket server):

| Server behaviour | Exception | `isinstance(URLError)` | Wellnest result |
|---|---|---|---|
| Accepts, never sends headers | `TimeoutError` | False | 500 |
| Accepts, closes without a response | `http.client.RemoteDisconnected` | False | 500 |
| Sends partial body, closes | `ConnectionResetError` | False | 500 |
| RST while the request is being sent | `URLError` | True | fallback |

`urllib`'s `do_open` wraps only errors raised by `h.request()`. Errors from
`h.getresponse()` and `read()` propagate raw. So the 500 path covers any stall of
60 s or more **before headers** (not only "slow response bodies"), and any
connection closed by the mock mid-request (for example an anthropic-mock restart
under node termination). The catalog's description is too narrow.

Impact: `App.jsx` `generateInsight` does `const data = await response.json(); const text = data.text || "Unable to generate insight right now..."`.
A handler 500 has a JSON body `{"error": ...}`, so the user sees **exactly the
fallback text**. The catalog's "should show the fallback message, not an error" is
already what the user sees. This is an API-contract property with no visible
user impact today. Suggested action: correct the Antithesis Angle (header-wait
timeout, connection close), correct Why It Matters, and consider lowering from P1
to P2 unless API consumers other than the SPA matter.

### F-FIT-7 — `api-recovers-after-faults` uses `Sometimes`, which cannot catch a timeline that never recovers

`Sometimes(recovered_within_timeout)` passes if **any** timeline recovers. A stuck
API on some branches (for example a dynamodb restart wiping in-memory tables, or a
api restart where `create_tables.py` exhausts retries) stays green as long as
another branch recovered. The guarantee "after faults stop, the API serves again"
must hold on every timeline. That is `Always(recovered_within_timeout)` evaluated in
the `eventually_` command (or after `ANTITHESIS_STOP_FAULTS`), optionally with a
separate `Sometimes`/`Reachable` to show the check ran. Suggested action: change
the assertion to `Always` in a quiescent check. The timeout must exceed the boto3
60 s read timeout for connections stuck from the fault period (F-FIT-4).

### F-FIT-8 — `delete-removes-only-target` cannot fail in the context it requires

Under the required serial section (no other writes for the user between the two
reads): `delete_entry` returns 200 only if the query found an item with `id` at key
`(U, T)`, and then deletes key `(U, T)`. That key holds only that item. If an
earlier same-ms overwrite replaced it, the lookup finds nothing and returns **404**,
not 200 (the evidence file's own scenario 1). The only path where delete removes a
different item is a concurrent same-ms create landing between the query and
`delete_item`, which the serial context excludes. In a concurrent context, the
invariant `listed_after == listed_before - {id}` gives false positives. Also the
catalog's Antithesis Angle ("If a same-ms create overwrote the slot, delete-by-key
removes the newer item instead") does not match the code. If the overwrite happened
before the lookup, the delete 404s. Suggested action: fold into
`acked-entry-is-listed`, which already catches "a delete removed some other acked
entry" because that entry vanishes. Add attribution details (missing entry's
timestamp equals a recently deleted entry's timestamp) to that assertion's details.

### F-FIT-9 — Guidance `Sometimes` assertions are mostly trivially true

- `delete-of-existing-entry-occurs`: `Sometimes(delete_status == 200)` is true for any
  workload that deletes known ids. More useful: `Sometimes(delete returned 200 while
  another write for the same user was in flight)`, which pushes toward the
  delete-vs-create race (F-FIT-5, F-FIT-8).
- `plant-reaches-later-stage`: 8 entries per user is trivial for any workload with a
  few users. Harmless, low information.
- `overlapping-same-user-writes-occur`: measures client-side overlap, which happens
  even when the shim serializes. It can be green while the concurrency properties
  are vacuous, which is the exact failure it is meant to guard against. See the
  implementability lens for a workload-observable server-side proxy.

### F-FIT-10 — `no-500-for-valid-requests` is a known-fail property with an unresolved definition of "fail"

The catalog's Open Question already asks whether a 500 during a partition is
acceptable. `Always` is a discrete commitment (`property-catalog.md`
"Honest Summaries"), and the catalog expects it to fire. It is not ready as
written. Given F-FIT-4, it will in practice mostly re-report `/insights` 500s.
Suggested action: scope it to `/entries`, `/plant`, `/patterns`, or classify by the
`{"error": str(e)}` body so a dynamodb-unavailable 500 is told apart from a code
defect.

## Underestimated properties

- `deleted-entry-stays-gone` (P1, "low expected yield"): real fault + interleaving path (F-FIT-5).
- `concurrent-creates-all-retained` / `acked-entry-is-listed`: reachable without
  concurrency under clock jitter (F-FIT-3).
- `insights-never-500`: more reachable than stated, but lower impact (F-FIT-6).

## Passes

- `acked-entry-is-listed`, `concurrent-creates-all-retained`, `pattern-increments-not-lost`:
  correct mechanism (verified in `entries.create_entry`, `patterns.upsert_pattern`),
  correct `Always` choice, and they need overlap plus scheduling that a deterministic
  test can't reliably produce.
- `plant-checkins-match-entry-count`: real query-count→put race in `entries.update_plant`
  and real non-atomic two-write path. The quiescent `Always` is the right shape.
- `insights-fallback-exercised` as `Reachable`: right type. See the coverage lens on
  which callsite is informative.

## Uncertainties

- How long Antithesis network faults and node hangs last in practice, which decides
  whether 60 s stalls (insights) and minutes-long boto3 retry exhaustion are reachable
  at all.
- Whether clock jitter steps are large enough (tens of ms or more) to re-walk this
  user's past milliseconds. Not stated in `faults.md`.
- I did not rerun the 50-request docker experiment (I was told not to run docker).
