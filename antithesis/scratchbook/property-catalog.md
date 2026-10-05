---
sut_path: /home/exedev/wellnest
commit: 9e9e52f1a8f7948ebfc911fe95571579a1ff37c5
updated: 2026-10-05
external_references:
  - path: https://github.com/sy00n89/wellnest
    why: Upstream repo named by the user as the outside source; checked for issues, PRs, and wiki (no issues, no wiki, one merged PR #1 "local dev").
---

# Wellnest — Property Catalog

## Summary

21 active properties in 5 categories, revised after evaluation
(`evaluation/synthesis.md`). Priorities: **P0** = acknowledged data lost or wrong,
**P1** = derived-state drift, user-visible errors, or recovery, **P2** = cheap
guards and coverage guidance.

| Slug | Type | Pri | Assertion |
|---|---|---|---|
| `acked-entry-is-listed` | Safety | P0 | Always |
| `concurrent-creates-all-retained` | Safety | P0 | Always |
| `deleted-entry-stays-gone` | Safety | P1 | Always |
| `entry-ids-unique-in-list` | Safety | P2 | Always |
| `user-entries-isolated` | Safety | P2 | Always |
| `plant-checkins-match-entry-count` | Safety | P1 | Always (quiescent) |
| `plant-stage-matches-checkins` | Safety | P2 | Always |
| `pattern-increments-not-lost` | Safety | P1 | Always (quiescent, bounds) |
| `pattern-frequency-tracks-acked-triggers` | Safety | P1 | Always (quiescent, bounds) |
| `plant-update-never-fails-silently` | Safety | P1 | Unreachable (SUT) |
| `entries-read-available` | Safety | P1 | Always |
| `no-500-for-valid-requests` | Safety | P2 | Always |
| `requests-finish-within-gateway-limit` | Safety | P1 | Always |
| `insights-never-500` | Safety | P2 | Unreachable (SUT) + Always (workload) |
| `insights-fallback-exercised` | Reachability | P2 | Reachable (SUT) |
| `insights-normal-reply-parsed` | Liveness | P2 | Sometimes |
| `api-recovers-after-faults` | Liveness | P1 | Always (quiescent, after wait) |
| `same-millisecond-creates-occur` | Liveness | P1 | Sometimes |
| `unknown-outcome-create-explored` | Liveness | P2 | Sometimes |
| `delete-of-existing-entry-occurs` | Liveness | P2 | Sometimes |
| `plant-reaches-later-stage` | Liveness | P2 | Sometimes |

### Ground rules every property relies on

- **Concurrency must match production.** The committed `server.py` handles one request
  at a time; Lambda runs many in parallel. The Antithesis compose must run
  `uvicorn ... --workers 4` (verified to reproduce both concurrency bugs with no code
  change). Without it, the concurrency properties only fail if clock jitter is on.
- **The workload plays the browser:** `POST /entries`, then one `POST /patterns` per
  trigger (sequentially, regardless of the entry's status, as `App.jsx` does), then
  reads. It never calls `POST`/`PUT /plant`.
- **Outcome model.** Each write is *acked* (expected 2xx), *failed-clean* (4xx), or
  *unknown* (5xx, timeout, connection reset). Properties use bounds:
  `acked ⊆ listed ⊆ acked ∪ unknown`, and for counters `F + K ≤ value ≤ F + K + U`.
- **29 s client timeout** on every request, matching API Gateway's integration limit.
- **Users.** Every user has their own journal (owner decision 2026-10-05; the
  frontend now gives each browser its own id). Each `parallel_driver_` run owns
  private user ids and creates overlap with threads inside the run that share one
  in-process model. The workload never uses `default`.

## Category: Entry data integrity

What you saved is there, exactly once, until you delete it. The entry key
`(user_id, timestamp_ms)` with unconditional `put_item` is the main risk.

### acked-entry-is-listed — Acknowledged entry is listed

| | |
|---|---|
| **Type** | Safety |
| **Property** | An entry whose `POST /entries` returned 201 appears (by `id`, with the submitted field values) in `GET /entries` for its user until a `DELETE` of that `id` is attempted with any outcome other than failed-clean. |
| **Invariant** | Workload `Always(acked_live_ids ⊆ listed_ids, "acknowledged entry is listed")` on every list read, where the acked/deleted model is shared by every thread that writes or deletes for that user. Details carry the missing ids, any listed item at the same `timestamp`, and field mismatches (mood, stress as a number, triggers, notes, date, time) to attribute cause. `Always` because losing an acknowledged write is never acceptable. Absorbs the former `entry-fields-round-trip` and `delete-removes-only-target`. |
| **Antithesis Angle** | Two creates in one millisecond (parallel workers, or a backward clock step) overwrite each other. Network faults between api and dynamodb produce unknown outcomes that the bounds tolerate. |
| **Why It Matters** | Silent loss of a saved check-in. Reproduced: 50 acked creates → 48–49 listed with `--workers 4`, 45–46 with thread-pool dispatch. |

**Open Questions:**

- None.

### concurrent-creates-all-retained — Overlapping or clock-stepped creates are all retained

| | |
|---|---|
| **Type** | Safety |
| **Property** | After a burst of creates for one user (overlapping in time, or spanning a clock step), every acked id from the burst is listed. |
| **Invariant** | Workload `Always(burst_acked_ids ⊆ listed_ids, "all burst creates retained")` right after each burst. Separate from `acked-entry-is-listed` so the report points straight at key collisions. |
| **Antithesis Angle** | Parallel api workers plus Antithesis scheduling put two `int(time.time()*1000)` calls in the same ms. A backward clock jump reuses milliseconds that already hold entries, even without concurrency. |
| **Why It Matters** | The mechanism behind the same-millisecond overwrite known since onboarding. |

**Open Questions:**

- Is clock jitter enabled for the tenant? It adds a non-concurrent path to this failure. `(needs human input)`

### deleted-entry-stays-gone — Deleted entry does not come back

| | |
|---|---|
| **Type** | Safety |
| **Property** | After `DELETE /entries/{id}` returns 200, that `id` never appears in a later `GET /entries`. |
| **Invariant** | Workload `Always(id not in listed_ids, "deleted entry stays gone")` for each successfully deleted id. The workload must delete ids it saw in lists (including other threads' entries), not only its own acks. |
| **Antithesis Angle** | botocore retries a `put_item` whose first attempt landed but whose response was lost. If another thread deleted the entry in between, the retry re-creates it. Needs concurrency plus network faults on api↔dynamodb. |
| **Why It Matters** | A user deletes a sensitive note; it must stay deleted. |

**Open Questions:**

- None.

### entry-ids-unique-in-list — No duplicate ids in a list (guard)

| | |
|---|---|
| **Type** | Safety |
| **Property** | `GET /entries` never returns two items with the same `id`. |
| **Invariant** | Workload `Always(len(ids) == len(set(ids)), "entry ids unique in list")` on every list. No extra requests. |
| **Antithesis Angle** | Cannot fail with server-side `uuid4` ids today; a regression guard for future retry/idempotency changes (for example a client-supplied id). |
| **Why It Matters** | Duplicate history rows double-count every stat. |

**Open Questions:**

- None.

### user-entries-isolated — Users only see their own entries (guard)

| | |
|---|---|
| **Type** | Safety |
| **Property** | `GET /entries?user_id=U` returns only items whose `user_id` is U. |
| **Invariant** | Workload `Always(all(e.user_id == U), "entries isolated by user")` on every list. |
| **Antithesis Angle** | Cannot fail with a hash-key query today; a guard for the planned authentication work. |
| **Why It Matters** | Privacy of a wellbeing journal. |

**Open Questions:**

- None.

## Category: Derived state (plant and patterns)

Plant and patterns are maintained by writes that are not atomic with the entry
write. Nothing user-visible reads them today.

### plant-checkins-match-entry-count — Plant count equals entry count

| | |
|---|---|
| **Type** | Safety |
| **Property** | When no writes are in flight for a user, `GET /plant` `check_ins` equals the number of entries `GET /entries` returns for that user. |
| **Invariant** | Workload `Always(check_ins == len(entries), "plant count matches entries")` only at quiescent points (end of a driver's section for its private user, or `finally_`). Transient mismatch during writes is expected. |
| **Antithesis Angle** | `update_plant` is query-count-then-put: overlapping creates and deletes leave a stale last write. A fault between the entry put and the plant put leaves the count behind; `update_plant` swallows the error. |
| **Why It Matters** | Regression target for the delete fix in `3558b2c`, plus the remaining race and partial-failure paths. |

**Open Questions:**

- None. (Resolved 2026-10-05: owner decided the plant is only updated automatically; the workload never calls `POST`/`PUT /plant`.)

### plant-stage-matches-checkins — Plant stage follows the server rule (guard)

| | |
|---|---|
| **Type** | Safety |
| **Property** | `GET /plant` `stage` equals the server's threshold function of `check_ins`: one stage per 20 check-ins (≥80 mature_tree, ≥60 young_tree, ≥40 plant, ≥20 seedling, else sprout). |
| **Invariant** | Workload `Always(stage == expected_stage(check_ins), "plant stage matches count")` on every plant read. |
| **Antithesis Angle** | Cannot fail while stage and count come from one `put_item`; guards future split writes. |
| **Why It Matters** | The plant screen now displays the server's stage directly, so a wrong stage is user-visible. |

**Open Questions:**

- None. (Resolved 2026-10-05: owner chose 20 check-ins per stage; the frontend now shows the server's plant.)

### pattern-increments-not-lost — Concurrent pattern updates are not lost

| | |
|---|---|
| **Type** | Safety |
| **Property** | For a `(user, trigger)` pair owned by one driver run, starting at frequency F, after K acked and U unknown-outcome `POST /patterns`, the frequency is between F + K and F + K + U. |
| **Invariant** | Workload `Always(F+K <= freq <= F+K+U, "pattern increments not lost")` at quiescence for that pair. |
| **Antithesis Angle** | `get_item` → +1 → `put_item` with no condition is a lost update under overlap. Reproduced: 50 concurrent increments → 19–21 with `--workers 4`. |
| **Why It Matters** | Trigger frequencies undercount exactly when the user is most active. |

**Open Questions:**

- None.

### pattern-frequency-tracks-acked-triggers — Pattern frequency tracks logged triggers

| | |
|---|---|
| **Type** | Safety |
| **Property** | For a private user, at quiescence, each trigger's frequency is at least the number of acked creates that included it and whose pattern POSTs were acked, and at most the number of create attempts (acked, unknown, or failed) that included it. |
| **Invariant** | Workload `Always(lower_T <= freq_T <= upper_T, "pattern frequency tracks triggers")`. Counted as an all-time tally (deletes don't reduce the expected value), matching current code. The upper bound includes failed creates on purpose, because the browser posts patterns even when the entry POST fails; a separate `Sometimes` in the details reports when a pattern was counted for an entry that doesn't exist. |
| **Antithesis Angle** | Fails on the lower bound through lost increments, and through a fault between the entry POST and the pattern POSTs (the browser-driven second write never arrives). |
| **Why It Matters** | The two tables drift with no reconciliation. |

**Open Questions:**

- Should deleting an entry decrement its patterns (tally vs. current state)? If yes, the expected value subtracts deletes and the property fails today on the first delete. `(needs human input)`

### plant-update-never-fails-silently — The swallowed plant-update error is never hit

| | |
|---|---|
| **Type** | Safety |
| **Property** | `entries.update_plant` never reaches its `except` branch after the entry write succeeded. |
| **Invariant** | SUT-side `Unreachable("update_plant failed after entry write", {error})` inside the `except` in `backend/handlers/entries.py`. Missing today. |
| **Antithesis Angle** | Requires a dynamodb fault that outlasts botocore's retries (60 s timeouts, up to 10 attempts by default) between the two writes. With defaults, short faults look like slow successes, so this may pass without being exercised. |
| **Why It Matters** | A swallowed error is invisible to every other check. |

**Open Questions:**

- Lower `AWS_MAX_ATTEMPTS` (and connect/read timeouts) in the Antithesis compose so this path is reachable within fault durations? `(needs human input)`

## Category: Availability, latency, and error handling

### entries-read-available — History reads succeed

| | |
|---|---|
| **Type** | Safety |
| **Property** | `GET /entries` returns 200 with a JSON array whenever the api can reach dynamodb. |
| **Invariant** | Workload `Always(status == 200 and isinstance(body, list), "entries read available")`, evaluated only when the previous and next requests to the api succeed (excludes total api outages). |
| **Antithesis Angle** | dynamodb latency, partial partitions, and worker restarts. |
| **Why It Matters** | The SPA sets entries to `[]` on a non-array response, so a single 500 shows the user an empty history. |

**Open Questions:**

- None.

### no-500-for-valid-requests — Well-formed requests never get a 500

| | |
|---|---|
| **Type** | Safety |
| **Property** | A well-formed request never receives HTTP 500. |
| **Invariant** | Workload `Always(status != 500, "no 500 for valid request")` with the route in the details. Timeouts and resets are recorded as unknown, not counted. |
| **Antithesis Angle** | Only faults that outlast botocore's retries become 500s. Useful as a broad net; the specific user-visible case is `entries-read-available`. |
| **Why It Matters** | The SPA never checks `response.ok`: a failed write looks saved, and a failed read empties the history. |

**Open Questions:**

- Is a 500 acceptable during a full api↔dynamodb partition? `(needs human input)`

### requests-finish-within-gateway-limit — Requests finish within 29 s

| | |
|---|---|
| **Type** | Safety |
| **Property** | Every api request completes (any status) within 29 s, API Gateway's integration limit in production. |
| **Invariant** | Workload `Always(elapsed < 29 s, "request within gateway limit")` per route, recording the route and elapsed time. A request that hits the 29 s client timeout counts as a violation. |
| **Antithesis Angle** | botocore's 60 s read timeout and retries, and insights' 60 s Anthropic timeout, can each exceed 29 s under latency or hangs. In production the gateway would cut these off and the client would see a 504 with the server still working. |
| **Why It Matters** | Insights' timeout fallback can never run in production (60 s > 29 s), a real config defect; slow writes become unknown outcomes to the user. |

**Open Questions:**

- None.

### insights-never-500 — Insights degrade gracefully

| | |
|---|---|
| **Type** | Safety |
| **Property** | When entries can be read, `POST /insights` returns 200 with non-empty `text`, even if Anthropic is slow, drops the connection, or returns malformed content. |
| **Invariant** | SUT-side `Unreachable("insights: anthropic call raised uncaught exception", {type})` around `call_anthropic` in `backend/handlers/insights.py` (separates Anthropic failures from dynamodb ones), plus workload `Always(status == 200 and text)`. The workload check sees only fast failures (e.g. `RemoteDisconnected`); the 60 s `TimeoutError` path outlasts the workload's 29 s timeout (recorded as unknown) and is detected only by the SUT-side `Unreachable`. |
| **Antithesis Angle** | `call_anthropic` catches only `URLError` and `JSONDecodeError`. `TimeoutError` (Anthropic slower than 60 s) and `RemoteDisconnected` (dropped connection) escape and return 500. Needs a mock that stalls for more than 60 s or drops connections (setup task), or network faults on api↔anthropic-mock. |
| **Why It Matters** | Mostly a correctness gap today: the SPA already shows fallback text when the call fails. |

**Open Questions:**

- None.

### insights-fallback-exercised — Insights fallback path is reached

| | |
|---|---|
| **Type** | Reachability |
| **Property** | Each `FALLBACK_TEXT` return in `insights.call_anthropic` is reached. |
| **Invariant** | SUT-side `Reachable("insights fallback: anthropic call failed", {error})` in the `except`, and `Reachable("insights fallback: empty text", {})` at the empty-text return. Distinct messages per callsite. Missing today. |
| **Antithesis Angle** | Reached by the mock's empty replies (~10%) and by connection failures. |
| **Why It Matters** | Without it, a green `insights-never-500` could mean the failure path never ran. |

**Open Questions:**

- None.

### insights-normal-reply-parsed — A normal insight is produced

| | |
|---|---|
| **Type** | Liveness |
| **Property** | At least one `POST /insights` returns text containing all five section labels. |
| **Invariant** | Workload `Sometimes(all_five_labels_present, "insight with all sections returned")`. |
| **Antithesis Angle** | Near-certain with an 80%-good mock; kept as a cheap sanity pair to the fallback check. |
| **Why It Matters** | Confirms the happy path works amid faults. |

**Open Questions:**

- None.

## Category: Lifecycle and recovery

### api-recovers-after-faults — API serves again after faults stop

| | |
|---|---|
| **Type** | Liveness |
| **Property** | After faults stop, `GET /plant` and `POST /entries` succeed within a bounded wait. |
| **Invariant** | Workload `Always(recovered_within_wait, "api recovers after faults")` in an `eventually_` command (faults paused), polling for up to ~90 s (longer than botocore's 60 s read timeout). `Always` so that one stuck timeline fails the property; a `Sometimes` would pass if any timeline recovered. |
| **Antithesis Angle** | Connection reuse after partitions and hangs. With node termination on: an api restart racing dynamodb startup (`create_tables.py` exhausting retries leaves api down, no restart policy), or an in-memory dynamodb restart wiping the tables (api never recreates them). |
| **Why It Matters** | A stuck API needs manual intervention. |

**Open Questions:**

- Is node termination enabled, and is a dynamodb kill with `-inMemory` in scope? `(needs human input)`

## Category: Coverage guidance

These confirm the run reached the states the safety properties depend on.

### same-millisecond-creates-occur — Same-millisecond creates happen

| | |
|---|---|
| **Type** | Liveness |
| **Property** | At least once, two acked creates for one user get server timestamps ≤ 1 ms apart (or the same timestamp, where one is lost). |
| **Invariant** | Workload `Sometimes(close_pair_found, "same-millisecond creates occurred")`, computed from timestamps in `GET /entries` after a burst, plus burst acks missing from the list. Measures *server-side* closeness, so it stays false if the server is serializing. |
| **Antithesis Angle** | If this never fires, the collision properties were never really tested. |
| **Why It Matters** | Guards against a false-green run. |

**Open Questions:**

- None.

### unknown-outcome-create-explored — Unknown-outcome creates happen

| | |
|---|---|
| **Type** | Liveness |
| **Property** | At least once, a create whose outcome was unknown to the client (5xx, timeout, reset) is later found listed. |
| **Invariant** | Workload `Sometimes(unknown_create_later_listed, "unknown create later listed")`. |
| **Antithesis Angle** | The client-gives-up-server-finishes path (evaluation W-8): the main real-world way the tables diverge, and the precondition for resurrection after delete. |
| **Why It Matters** | Shows the outcome model was actually exercised. |

**Open Questions:**

- None.

### delete-of-existing-entry-occurs — A delete of an existing entry happens

| | |
|---|---|
| **Type** | Liveness |
| **Property** | At least one `DELETE` of a listed entry returns 200. |
| **Invariant** | Workload `Sometimes(delete_status == 200, "delete of existing entry")`. |
| **Antithesis Angle** | Ensures delete-related properties are exercised. |
| **Why It Matters** | Guards against a workload that only deletes unknown ids. |

**Open Questions:**

- None.

### plant-reaches-later-stage — Plant reaches a later stage

| | |
|---|---|
| **Type** | Liveness |
| **Property** | Some user's plant reaches `seedling` stage (≥20 check-ins) or later. |
| **Invariant** | Workload `Sometimes(stage != "sprout", "plant reaches later stage")`. With 20 check-ins per stage, the workload must create 20+ entries for at least one user. |
| **Antithesis Angle** | Ensures enough writes per user to cross stage thresholds under faults. |
| **Why It Matters** | Stage logic only runs when counts grow. |

**Open Questions:**

- None.

## Invalidated properties

- `entry-fields-round-trip`: cannot fail independently of `acked-entry-is-listed` (ids and content are written together). Field comparison moved into that property's details.
- `delete-removes-only-target`: cannot fail in the serial context it required and false-positives concurrently; its original angle was wrong (a pre-existing overwrite yields 404, not a wrong delete). Covered by `acked-entry-is-listed`.
- `data-survives-dynamodb-restart`: tests dynamodb-local's in-memory mode, not Wellnest; vacuous with default faults. Recovery is covered by `api-recovers-after-faults`.
- `pattern-frequency-matches-entries`: replaced by `pattern-frequency-tracks-acked-triggers` (failed by construction on the first delete).
- `overlapping-same-user-writes-occur`: replaced by `same-millisecond-creates-occur` (client-side overlap was trivially true even when the server serialized).

## Assumptions

- Antithesis compose runs the api with `--workers 4`.
- The workload mirrors the browser, uses a 29 s timeout, and never calls `POST`/`PUT /plant` (owner decision: plant updates are automatic only).
- Pagination (≥1 MB per user) is excluded: cheap to trigger and deterministic, so it belongs in an integration test, not the Antithesis search budget.
- Eventual consistency of real DynamoDB queries is not modelled (dynamodb-local can't reproduce it).

## Open Questions

- Is clock jitter enabled for the tenant? `(needs human input)`
- Is node termination enabled for the tenant? `(needs human input)`
- Lower botocore retries/timeouts in the Antithesis env so dynamodb faults surface within fault windows? `(needs human input)`
- Weight the workload toward confirming the known bugs, or toward the new-discovery properties (evaluation bias B-2)? `(needs human input)`
