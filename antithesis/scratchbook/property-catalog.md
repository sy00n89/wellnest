---
sut_path: /home/exedev/wellnest
commit: f572ccda04d4136a71d8aea57b73211e9b4447df
updated: 2026-10-08
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
| `acked-entry-is-listed` | Safety | P0 | Always — **implemented** |
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

### Implementation status (2026-10-08)

Test commands in `antithesis/test/v1/wellnest/`: `parallel_driver_check_ins`, `parallel_driver_journal`, `parallel_driver_insights`, `eventually_api_recovers`, `finally_journals_consistent`; guard and production-limit checks live in `helper_api.py`.

| Slug | Status | Where | Result |
|---|---|---|---|
| `acked-entry-is-listed` | Implemented | check_ins, journal, finally | Found same-ms overwrite (run d58ab81e); fixed, green since 38440dda |
| `concurrent-creates-all-retained` | Implemented (via check_ins burst) | check_ins | Green after fix |
| `deleted-entry-stays-gone` | Implemented | journal, finally | Green |
| `entry-ids-unique-in-list` | Implemented (guard) | helper_api | Green |
| `user-entries-isolated` | Implemented (guard) | helper_api | Green |
| `plant-checkins-match-entry-count` | Implemented | journal, finally | Found recount race (fa7252e5) and double-counted retries (3b96068a); fixed by computing the plant from entries (6cb7fdb) |
| `plant-stage-matches-checkins` | Implemented (guard) | helper_api | Green |
| `pattern-increments-not-lost` | **Invalidated 2026-10-08** | — | Trigger counts are computed from entries; POST /patterns removed. Lost-update bug found locally and fixed before invalidation |
| `pattern-frequency-tracks-acked-triggers` | Implemented | journal | Found stale counts after deletes (local); fixed; green |
| `plant-update-never-fails-silently` | **Invalidated 2026-10-08** | — | No plant write path remains to fail |
| `entries-read-available` | Implemented | helper_api | Green |
| `no-500-for-valid-requests` | Implemented | helper_api | Green |
| `requests-finish-within-gateway-limit` | Implemented, refined; residual failures **accepted as environmental** (owner, 2026-10-08) | helper_api | Judges answered requests (3500a1b). Run cf988001: 1,793 answers after 29 s (e.g. POST /entries 201 after 31.6 s during ~32 s of back-to-back jammed/stopped faults). Wait-vs-fail-fast is an owner decision (see Open Questions) |
| `insights-never-500` | Implemented | insights | Found TimeoutError → 500 (local); fixed (20 s timeout, catch-all fallback); green |
| `insights-fallback-exercised` | Implemented | insights.py (SUT) | Both Reachable markers hit |
| `insights-normal-reply-parsed` | Implemented | insights | Hit |
| `api-recovers-after-faults` | Implemented | eventually_api_recovers | Green |
| `same-millisecond-creates-occur` | Implemented | check_ins | Hit |
| `unknown-outcome-create-explored` | Implemented | journal | Hit |
| `delete-of-existing-entry-occurs` | Implemented | journal | Hit |
| `plant-reaches-later-stage` | Implemented | journal | Hit (seedling) |

Later findings (2026-10-08, after the owner chose option B, fail fast):
- `deleted-entry-stays-gone` failed in run 88ee0399 (79): a save delayed in a jammed network and retried reached DynamoDB after the entry was deleted and recreated it. Fixed with tombstones (deletes set `deleted = true`; reads skip them; c970649). Green in 683c30eb and 0f208a0a.
- `requests-finish-within-gateway-limit` is now checked inside the API per handler (server.py), with DynamoDB fail-fast (2 s connect, 4 s read, 2 attempts, 503 when unreachable) and a 25 s insights deadline (8123d93). Latest run `0f208a0a494566f7cd9f8b80efb2b186-64-0`: 151 of 5,675 handlers over 29 s; the example examined overlapped repeated 5-10 s freezes of the whole API container (node-hang faults), which no in-process deadline can prevent. **Owner decision 2026-10-08: accepted as environmental.** Residual failures of this property under node-hang faults are expected and not treated as app bugs; budgets stay as they are. Only one of the 151 counterexamples was examined, so a new failure pattern (for example, without container freezes) should still be investigated.
- End-of-run plant check now uses the same double-read guard as the mid-run check (88857f4).

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
| **Implementation** | `antithesis/test/v1/wellnest/parallel_driver_check_ins.py` (2026-10-06): fresh private user per invocation, burst of 1–16 creates on 1–8 threads (SDK random), then list and `Always("acknowledged check-in is listed with the values sent")`. Reach claims: `Sometimes("check-in burst with 2+ acknowledged concurrent creates was verified")`, `Sometimes("two listed check-ins for one user were stored within 1 ms")`. Local run: 7 of 40 invocations lost acknowledged entries (e.g. 4 acked, 2 listed). Antithesis run `d58ab81e31ec42bc3e6f2a96a1c31598-64-0`: **failed 7,200×** (no faults active in the first counterexample: 5 concurrent creates, 4 listed). Fixed 2026-10-07 in `entries.put_new_entry` (conditional put, next ms on collision, own-write detection) with pytest `test_same_millisecond_check_ins_are_both_kept`; verified by run `38440ddaacec2974258a589869d8c061-64-0`: **57,200 passes, 0 failures**, same-ms reach claim fired 22,040×. Deletes are not yet exercised by this command. |

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
| **Property** | For a private user, at quiescence, each trigger's frequency reflects the user's *current* entries: at least the number of live acked entries that include it (pattern POSTs acked), and at most the number of create attempts that included it (acked, unknown, or failed) minus the deletes of entries that included it. |
| **Invariant** | Workload `Always(lower_T <= freq_T <= upper_T, "pattern frequency tracks triggers")`. Deletes reduce the expected value (owner decision 2026-10-05: trigger counts go down on delete). `entries.decrement_patterns` (added 2026-10-05, with pytest `test_delete_lowers_trigger_counts`) lowers each trigger on delete and removes rows that reach zero. The upper bound includes failed creates on purpose, because the browser posts patterns even when the entry POST fails; a separate `Sometimes` in the details reports when a pattern was counted for an entry that doesn't exist. |
| **Antithesis Angle** | Fails on the lower bound through lost increments, and through a fault between the entry POST and the pattern POSTs (the browser-driven second write never arrives). |
| **Why It Matters** | The two tables drift with no reconciliation. |

**Open Questions:**

- None. (Resolved 2026-10-05: owner decided trigger counts go down on delete.)

### plant-update-never-fails-silently — The swallowed plant-update error is never hit

| | |
|---|---|
| **Type** | Safety |
| **Property** | `entries.update_plant` never reaches its `except` branch after the entry write succeeded. |
| **Invariant** | SUT-side `Unreachable("update_plant failed after entry write", {error})` inside the `except` in `backend/handlers/entries.py`. Missing today. |
| **Antithesis Angle** | Requires a dynamodb fault that outlasts botocore's retries (60 s timeouts, up to 10 attempts by default) between the two writes. With defaults, short faults look like slow successes, so this may pass without being exercised. |
| **Why It Matters** | A swallowed error is invisible to every other check. On AWS this branch ran on *every* create until 2026-10-05: `template.yaml` gave the entries Lambda access to the entries table only, so its plant write was denied and silently swallowed (fixed by granting plant and patterns access). |

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
- Lower botocore retries/timeouts? Resolved 2026-10-08: owner chose fail fast (option B), now in `backend/handlers/aws.py` for all environments.
- Weight the workload toward confirming the known bugs, or toward the new-discovery properties (evaluation bias B-2)? `(needs human input)`
