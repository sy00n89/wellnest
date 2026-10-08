---
sut_path: /home/exedev/wellnest
commit: 9e9e52f1a8f7948ebfc911fe95571579a1ff37c5
updated: 2026-10-05
external_references:
  - path: https://github.com/sy00n89/wellnest
    why: Upstream repo named by the user as the outside source; checked for issues, PRs, and wiki (no issues, no wiki, one merged PR #1 "local dev").
---

# Wellnest — SUT Analysis

## Summary

Wellnest is a stress and wellbeing check-in journal. A user records check-ins (mood,
stress 1–10, triggers, physical signs, notes, optional cognitive-appraisal answers,
vulnerability factors). The app shows history, trends, a "plant" that grows with
engagement, trigger patterns, and AI-generated insights.

It was built as a grad-school prototype to demonstrate psychology frameworks, then
adapted (this branch) to run without AWS. There is one hardcoded user (`default`),
no authentication, and no existing Antithesis instrumentation.

The most important finding of this analysis, confirmed by experiment, is in
[Concurrency model](#concurrency-model): **the handlers have real lost-update and
key-collision bugs under concurrent requests, but the local HTTP shim
(`backend/server.py`) runs one request at a time, which hides them.** On AWS Lambda,
concurrent requests run in parallel and the bugs are live.

## Architecture and data flow

### Production shape (AWS, `backend/template.yaml`)

```
browser (React SPA) ──HTTPS──▶ API Gateway ──event──▶ Lambda ×4 ──▶ DynamoDB ×3
browser ─────────────────────────────────────────────────────────▶ (no direct 3rd-party calls since ab4949a)
Lambda wellnest-insights ──HTTPS──▶ api.anthropic.com
```

### Local / Antithesis shape (`docker-compose.yaml`)

```
frontend (nginx :80) ──/api/──▶ api (uvicorn :8080, server.py) ──▶ dynamodb (dynamodb-local :8000, in-memory)
                                                              └──▶ anthropic-mock (:8080)
```

### Components

| Component | Code | Role |
|---|---|---|
| React SPA | `src/App.jsx` (~1,650 lines, one file) | All UI. Derives every display (history, trends, plant stage, top triggers) from the `entries` list in the browser. |
| HTTP shim | `backend/server.py` | Replaces API Gateway + Lambda: builds the API Gateway event dict, dispatches by first path segment, returns the handler's response. |
| Entries handler | `backend/handlers/entries.py` | `GET /entries`, `POST /entries`, `DELETE /entries/{id}`. Calls `update_plant` after create and (since 3558b2c) after delete. |
| Plant handler | `backend/handlers/plant.py` | `GET /plant`, `POST`/`PUT /plant` (overwrite plant row with client-supplied values). |
| Patterns handler | `backend/handlers/patterns.py` | `GET /patterns`, `POST /patterns` (increment frequency for one trigger, blend severity). |
| Insights handler | `backend/handlers/insights.py` | `POST /insights`: reads last 14 entries, builds prompt, calls Anthropic Messages API at `ANTHROPIC_BASE_URL`, returns `{"text": ...}`. |
| Table bootstrap | `backend/create_tables.py` | Creates the three tables if missing; refuses to run without `DYNAMODB_ENDPOINT`. Runs in the api container's CMD before uvicorn. |
| Anthropic mock | `mocks/anthropic/server.py` | `POST /v1/messages` returns a canned five-section insight; 20% of replies are malformed (empty text or no section labels). Always HTTP 200, instant. |

### Request paths

**Check-in (the critical write path)** — `App.jsx` `handleSubmitEntry`:

1. `POST /entries` with the entry plus `user_id`. Server assigns `id = uuid4()` and
   `timestamp = int(time.time()*1000)`; `put_item`; then `update_plant(user_id)`
   which queries all entries, counts them, and `put_item`s the plant row. Returns 201.
2. **Browser then sends one `POST /patterns` per trigger**, sequentially. Each does
   `get_item(user_id, trigger)` → compute → `put_item`.
3. `GET /entries` + `GET /plant` to refresh.

The browser never checks `response.ok`; `fetch` only throws on network failure. A
500 from step 1 still proceeds to step 2, so patterns can be incremented for an entry
that was never stored.

**Delete** — `DELETE /entries/{id}?user_id=`: query all of the user's entries, find
the one whose `id` matches, `delete_item` by `(user_id, timestamp)`, then
`update_plant`. Patterns are never decremented.

**Insights** — `POST /insights {user_id}`: query entries, sort by timestamp desc,
take 14, build prompt, `urllib` POST to `{ANTHROPIC_BASE_URL}/v1/messages` with a
60 s timeout. `URLError`/`JSONDecodeError` → fallback text. Other exceptions bubble
to the handler's catch-all → 500.

## State management and persistence

| Table | Key | Written by | Read by |
|---|---|---|---|
| `wellnest-entries` | `user_id` (HASH) + `timestamp` number, ms (RANGE) | `POST /entries`, `DELETE /entries/{id}` | `GET /entries`, `update_plant`, delete lookup, insights |
| `wellnest-plant` | `user_id` | `entries.update_plant` (count-derived), `POST`/`PUT /plant` (client-supplied) | `GET /plant` — **but the UI ignores it** and recomputes a different stage client-side |
| `wellnest-patterns` | `user_id` + `trigger` | `POST /patterns` (from browser, after entry) | `GET /patterns` — **no UI reads it**; the UI computes top triggers from entries |

Key observations:

- **Entry identity is `(user_id, timestamp_ms)`, not `id`.** The UUID `id` is a
  plain attribute. `put_item` has no `ConditionExpression`, so two creates for the
  same user in the same millisecond silently overwrite one another.
- **Derived state is stored in two tables and recomputed in the browser** with a
  different algorithm. Server stage: count thresholds 3/8/14/20 (`entries.py`
  `update_plant`). Client stage: `engagementScore` thresholds 5/…/22/35 over
  behavioral metrics (`App.jsx` `PlantScreen`). The two disagree by design; the
  plant table is effectively write-only.
- **Three writers for the plant row:** `entries.update_plant` (writes `stage`,
  `check_ins`, drops `days_active`), and `plant.update_plant` via `POST`/`PUT /plant`
  (writes arbitrary client values). The frontend never calls `POST`/`PUT /plant`.
- **No transactions.** Entry + plant are two separate `put_item`s; entry + patterns
  are separate HTTP requests from the browser.
- **No pagination.** Every `table.query` reads only the first page (≤1 MB) and
  ignores `LastEvaluatedKey`. Affects list, delete lookup, plant count, insights.
- **dynamodb-local runs `-inMemory`** (image default `CMD -jar DynamoDBLocal.jar -inMemory`,
  verified with `docker inspect`). A dynamodb container restart loses all data and
  all tables. The api only creates tables at its own startup.
- **Consistency differs between environments.** dynamodb-local is a single process
  and reads are effectively strongly consistent. Real DynamoDB `Query` is eventually
  consistent unless `ConsistentRead=True`, which no handler sets. `update_plant`'s
  count immediately after `put_item` could miss the new entry on AWS. Antithesis
  cannot reproduce this with dynamodb-local.

## Concurrency model

**Production (Lambda):** each concurrent request runs in its own Lambda instance.
Handlers execute fully in parallel. Every read-modify-write in the handlers is a race.

**Local shim (`server.py`):** a single uvicorn process with one asyncio event loop.
`dispatch` is `async def` and calls the synchronous `handler.lambda_handler(...)`
directly, so the handler runs **on the event loop thread and blocks it**. Requests
are therefore processed strictly one at a time.

**Experiment (2026-10-05), 50 concurrent requests from 20 threads:**

| Shim mode | `POST /patterns` same trigger ×50 → frequency | `POST /entries` ×50 (all 201) → entries listed |
|---|---|---|
| As committed (handler on event loop) | 50 | 50 (50 distinct timestamps) |
| Handler in a thread pool (`run_in_threadpool`; shares boto3 objects across threads) | **12** and **11** | **46** and **45** |
| `uvicorn --workers 4` (separate processes, Lambda-like; added after evaluation) | **21, 20, 19** | **48, 49, 48** |

So with real concurrency, most pattern increments were lost (read-modify-write race
in `patterns.upsert_pattern`), and acknowledged entries vanished (same-millisecond
`timestamp` key collisions in `entries.create_entry`). With the committed shim,
neither happened in this experiment, because each handler takes several ms and
requests never overlap.

**Implication for Antithesis:** the committed shim is *less concurrent than
production*. The recommended topology runs the api with `--workers 4` (see
`deployment-topology.md`). Without it, the lost-update race cannot occur, and key
collisions can only occur through clock jitter: a backward clock step reuses
milliseconds that already hold entries, even with serialized requests. (Correction
after evaluation: an earlier draft said Antithesis could not find these bugs at all
on the committed shim; that is false if clock jitter is enabled.)

Thread-pool dispatch is not recommended for the harness: handlers share
module-level `boto3.resource` objects, which boto3 documents as not thread-safe.

Other races present once handlers overlap:

- `update_plant`: query-count-then-put. Two overlapping creates can each count
  before the other's write lands; the last writer wins with a stale count.
- Delete vs create: delete's `update_plant` and a concurrent create's `update_plant`
  race the same way.
- Patterns severity blend `(old + new) / 2` is order-dependent, so concurrent
  updates also produce nondeterministic severity.

## Safety guarantees (claimed or implied)

The code and UI make no formal guarantees. Implied ones, to be tested, not assumed:

- A check-in the API acknowledged with 201 appears in History until the user deletes it.
- Deleting removes exactly the chosen entry.
- The plant's check-in count reflects the number of check-ins (the `update_plant`
  docstring says "Update plant stage based on total entries").
- A trigger's pattern frequency counts how often it was logged (the frontend comment
  "Save triggers as patterns"; `upsert_pattern` comment "increment frequency").
- One user's entries are not visible to another `user_id` (implied by the key schema
  and query parameter, though the frontend only ever uses `default`).

## Liveness guarantees (implied)

- After transient failures (dynamodb slow or restarted, network faults), the API
  serves requests again without manual intervention.
- `POST /insights` returns an answer (possibly the fallback text) rather than hanging
  or erroring when Anthropic is slow, down, or returns garbage.

## Bug history

- GitHub `sy00n89/wellnest`: no issues, no wiki. Only PR #1 (this learning project's
  local-dev work, merged 2026-10-01).
- Git history: commit `3a72e76` "Fix date/time to use local timezone instead of UTC"
  — the client now sends `date`/`time`; the server falls back to UTC only if absent.
  Display ordering uses client `date`/`time`, storage ordering uses server
  `timestamp`; these can disagree.
- Fixed in this project: delete did not update the plant (commit `3558b2c`, with
  pytest `test_delete_updates_plant`). A regression target.
- `docs/LEARNING_PLAN.md` lists known debts. Treated as leads; each one used below
  was confirmed against the code or by experiment.

## Existing test strategy

- `backend/tests/` (pytest, 3 tests): create→list, plant count after 3 creates,
  delete updates plant. Sequential, single-threaded, against dynamodb-local with
  `test-*` tables. No concurrency, no faults, no patterns or insights tests.
- CI (`.github/workflows/ci.yml`): lint + build + those tests.
- No frontend tests, no end-to-end tests, no load or chaos tests.

Antithesis adds value exactly where these stop: overlapping requests, partial
failures between the two writes of a check-in, dependency restarts, slow or broken
Anthropic.

## Failure and degradation modes

- **Catch-all 500.** Each `lambda_handler` wraps everything in `except Exception`
  and returns 500 with `str(e)`. Malformed JSON, a missing body (`json.loads(None)`
  in `create_entry` when the body is empty), non-numeric `stress_level`
  (`Decimal('abc')`), and dynamodb errors all become 500.
- **IAM gap (fixed 2026-10-05).** `template.yaml` gave the entries Lambda access to the entries table only, so on AWS `update_plant`'s write to the plant table would be denied and swallowed on every create. Now granted plant and patterns access.
- **Swallowed plant failure.** `entries.update_plant` catches every exception and
  only `print`s. The create still returns 201, leaving the plant stale. Nothing
  signals it.
- **Insights timeout path.** `call_anthropic` catches `URLError` (which includes
  `HTTPError`) and `JSONDecodeError`. A timeout before headers or during the body
  raises `TimeoutError`, and a dropped connection raises `RemoteDisconnected`;
  neither is a `URLError` (verified in Python 3.12), so both bubble to the catch-all
  and return **500**. Connection refused is a `URLError` and returns the fallback.
- **botocore defaults absorb short faults.** No handler configures boto3. botocore
  1.43.106 defaults: 60 s connect and read timeouts, legacy retry mode, up to 10
  attempts for DynamoDB. Faults shorter than that become slow successes rather than
  errors; a write whose response is lost is retried, which can re-create an item
  deleted in between.
- **Production deadline the shim lacks.** API Gateway cuts requests at 29 s
  (`template.yaml` Lambda `Timeout: 30`, insights 60). The insights Anthropic timeout
  is 60 s, so its timeout fallback can never run in production, and a slow write
  becomes a 504 to the user while the Lambda may still complete it.
- **A read 500 empties the UI.** `App.jsx` `loadData` sets entries to `[]` when
  `GET /entries` returns a non-array, so one failed read shows an empty history.
- **Startup.** api CMD is `python create_tables.py && exec uvicorn ...`. If
  dynamodb isn't accepting connections, boto3's default retries usually cover it
  (observed 3/3 clean starts). If retries are exhausted, `create_tables.py` exits
  non-zero, uvicorn never starts, and with no compose `restart:` policy the api
  stays down.
- **Graceful shutdown.** Since de53f83, uvicorn is PID 1's exec target and handles
  SIGTERM. In-flight requests during a kill can leave an entry written without its
  plant update.

## External dependencies

| Dependency | Local stand-in | Failure handling |
|---|---|---|
| DynamoDB | `amazon/dynamodb-local` (in-memory) | None beyond boto3 default retries; errors become 500 |
| Anthropic Messages API | `mocks/anthropic` | Fallback text for connection/HTTP/JSON errors; read timeout → 500 |
| API Gateway + Lambda | `server.py` shim | n/a (fidelity gap: concurrency, see above) |
| Google Fonts (browser only) | none | Irrelevant to Antithesis (no browser) |

## Product context

The critical user workflow is: check in → see it in History → watch the plant and
insights reflect it. User-visible failures that matter most:

1. A check-in that said "saved" silently disappears (data loss, erodes trust in a
   wellbeing journal).
2. Stats that disagree with history (plant count, trigger frequency).
3. Insights button erroring.

## Unproven assumptions

- "Two requests from the same user never arrive in the same millisecond." The entry
  key depends on it. False under concurrency (experiment above), retries, or two
  devices.
- "The browser will always send the pattern updates after a successful entry." Tab
  close, network drop, or a 500 breaks this; nothing reconciles.
- "dynamodb is always up and keeps its data." In-memory mode violates the second half
  on any restart.
- "A query returns all of a user's items." True only below 1 MB per user.
- "Server clock only moves forward." `timestamp` ordering and key uniqueness both
  degrade if the clock steps backward (clock faults are off by default in Antithesis).

## Wildcard

- **The test shim is not the production runtime, and the gap points the wrong way.**
  Usually a test environment is harsher than production. Here the shim is gentler:
  it serializes what Lambda parallelizes, and it has no 29 s deadline. A green
  Antithesis run against the committed shim would create false confidence on exactly
  the properties that matter most.
- **Everyone was `default` in production.** The frontend hardcoded one user id, so all
  real traffic shared one partition. Owner decision 2026-10-05: each user has their
  own journal; the frontend now assigns a random per-browser id (localStorage).
- **Derived state with no reader.** The plant and patterns tables are maintained on
  every write but nothing user-visible reads them. Their correctness is still worth
  testing (the API exposes them and they are the obvious basis for future features),
  but the user-visible impact today is low. A human should decide how much search
  budget they deserve.
- **Client and server disagree on what "correct" is** for the plant stage. A property
  over the plant table can only check the server's own rule.

## Assumptions

- The Antithesis workload will call the api container directly, playing the role of
  the browser, including the browser's separate `POST /patterns` calls.
- The frontend container is out of scope for Antithesis (no browser, and nginx only
  forwards `/api/`).
- Only `user_id` values chosen by the workload exist; there is no auth to model.

## Open Questions

- Confirm running the api with `uvicorn --workers 4` in the Antithesis topology to
  restore Lambda-like concurrency (no code change; verified to reproduce both bugs).
  `(needs human input)`
- Is clock jitter enabled for the tenant? `(needs human input)`
- Should dynamodb-local persist to disk (`-sharedDb -dbPath` plus a volume) so
  node-termination faults test recovery rather than trivially wiping data? Depends on
  whether node termination is enabled for the tenant. `(needs human input)`
- Should the workload exercise `POST`/`PUT /plant`? The frontend never calls them, and
  doing so would make `plant-checkins-match-entry-count` fail by construction.
  Recommended no. `(needs human input)`
