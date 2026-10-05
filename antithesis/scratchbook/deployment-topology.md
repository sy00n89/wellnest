---
sut_path: /home/exedev/wellnest
commit: 9e9e52f1a8f7948ebfc911fe95571579a1ff37c5
updated: 2026-10-05
external_references:
  - path: https://github.com/sy00n89/wellnest
    why: Upstream repo named by the user as the outside source; checked for documented topology (none found beyond the repo's own template.yaml and docker-compose.yaml).
---

# Deployment Topology

## Summary

Four containers: one dependency (dynamodb), one service (api), one mock dependency
(anthropic-mock), one client (workload). The frontend is left out.

```
+---------------------+        +---------------------+        +---------------------+
| workload            | -----> | api                 | -----> | dynamodb            |
| (client, Python SDK)|  HTTP  | uvicorn + handlers  |  HTTP  | amazon/dynamodb-    |
|  test template      | <----- | (SUT)               | <----- | local               |
+---------------------+        +----------+----------+        +---------------------+
                                          |
                                          | HTTP POST /v1/messages
                                          v
                               +---------------------+
                               | anthropic-mock      |
                               | (mock dependency)   |
                               +---------------------+
```

Every link is between separate containers, so Antithesis can independently delay,
drop, or partition: workload↔api, api↔dynamodb, api↔anthropic-mock.

## Components

| Container | Image source | Role | Runs | Talks to | Replicas |
|---|---|---|---|---|---|
| `dynamodb` | Official `amazon/dynamodb-local` | Dependency | DynamoDB-compatible engine on :8000 | — | 1 |
| `api` | Existing `backend/Dockerfile` (needs SDK added for SUT-side assertions) | Service (SUT) | `create_tables.py` then `uvicorn server:app --workers 4` on :8080 | dynamodb, anthropic-mock | 1 container, 4 worker processes |
| `anthropic-mock` | Existing `mocks/anthropic/Dockerfile` | Dependency (mock) | FastAPI `POST /v1/messages` on :8080 | — | 1 |
| `workload` | **New** `antithesis/` Dockerfile (Python 3.12 + `antithesis` SDK + test template at `/opt/antithesis/test/v1/wellnest/`) | Client | Emits `setup_complete` once api answers, then sleeps; Antithesis runs its test commands | api | 1 |

### Why the frontend is excluded

There is no browser in Antithesis, and nginx only serves static files and forwards
`/api/` unchanged. Including it adds a container and a network hop without adding
SUT logic. The workload replicates the browser's behavior that *does* matter: the
separate, sequential `POST /patterns` calls after each `POST /entries`.

## Concurrency (important)

The committed `server.py` runs each handler on the asyncio event loop, which
serializes all requests in a process. Lambda runs requests in parallel, one per
instance.

**Decision recommended: run the api with `uvicorn ... --workers 4`** via a compose
`command:` override in `antithesis/config/docker-compose.yaml`. No code change. Each
worker is a separate process (like a Lambda instance) with its own boto3 objects.

Verified 2026-10-05, 50 concurrent requests:

| api mode | pattern frequency (of 50) | entries listed (of 50 acked) |
|---|---|---|
| committed (1 process, serialized) | 50 | 50 |
| `--workers 4` | 21, 20, 19 | 48, 49, 48 |
| thread-pool dispatch (not recommended) | 12, 11 | 46, 45 |

Thread-pool dispatch was rejected after evaluation: it shares module-level
`boto3.resource` objects across threads, which boto3 documents as not thread-safe,
so some failures could be harness artifacts.

## Persistence

dynamodb-local defaults to `-inMemory`. If node-termination faults are enabled for
the tenant, killing `dynamodb` erases every table, so the api would serve 500s until
the tables are recreated, which only happens at api startup. Options:

- Leave in-memory and keep node termination off for `dynamodb` (default fault config
  has node termination disabled).
- Or run `-sharedDb -dbPath /data` with a volume so restarts test recovery.

Recorded as an open question; the default is in-memory with node termination off.

## Mock changes needed (setup task)

The current `anthropic-mock` always answers instantly with HTTP 200, so the insights
failure paths (`insights-never-500`) can't be exercised by the mock itself. Add
occasional misbehavior, ideally chosen with the Antithesis SDK's random source:

- stall for more than 60 s (reaches the `TimeoutError` → 500 path in `call_anthropic`), and sometimes 29–60 s (exercises the gateway-limit property only)
- close the connection mid-response
- return HTTP 429 or 500
- return invalid JSON

Network faults on api↔anthropic-mock also cover some of this.

## Client conventions

- Workload HTTP timeout: **29 s** for every request, matching API Gateway's
  integration limit, so outcomes match what a production client sees.
- Outcome model: 2xx = acked, 4xx = failed-clean, 5xx/timeout/reset = unknown.

## SDK selection

- **Workload:** Antithesis Python SDK (`antithesis` on PyPI; Python ≥ 3.9). Needed
  for `setup_complete`, `always`, `sometimes`, `reachable`, and `random`.
- **api (SUT):** Python SDK for a small number of SUT-side assertions (for example,
  the swallowed `update_plant` failure, and the insights fallback/timeout paths).
  Python coverage instrumentation is not required for a first run.
- **anthropic-mock, dynamodb:** none.

## Readiness

The workload container emits `setup_complete` after it gets a successful
`GET /plant` from the api. That confirms dynamodb is up, the tables exist, and
uvicorn is serving. Compose `depends_on` with healthchecks should also gate the api
on dynamodb.

## Assumptions

- The workload calls `http://api:8080` directly.
- One workload container is enough; parallelism comes from Antithesis running
  multiple `parallel_driver_` commands concurrently.

## Open Questions

- Confirm running the api with `--workers 4` in the Antithesis compose. Recommended and verified. `(needs human input)`
- In-memory vs. persistent dynamodb, which depends on node-termination availability. `(needs human input)`
- Lower botocore retries/timeouts (`AWS_MAX_ATTEMPTS`, connect/read timeouts) in the api env so dynamodb faults surface within fault windows? `(needs human input)`
