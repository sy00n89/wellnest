---
sut_path: /home/exedev/wellnest
commit: 9e9e52f1a8f7948ebfc911fe95571579a1ff37c5
updated: 2026-10-05
external_references:
  - path: https://github.com/sy00n89/wellnest
    why: Upstream repo named by the user as the outside source; checked for issues, PRs, and wiki (no issues, no wiki, one merged PR #1 "local dev").
---

# Property Relationships

## Same-millisecond entry key collision
Properties: concurrent-creates-all-retained, acked-entry-is-listed, same-millisecond-creates-occur, entry-ids-unique-in-list
Notes: All rooted in `(user_id, timestamp_ms)` as the entry key with unconditional `put_item` (`entries.create_entry`). Triggered by parallel api workers or a backward clock step. `concurrent-creates-all-retained` is the most direct detector; `acked-entry-is-listed` dominates it in coverage (any lost ack) but reports less specifically. `same-millisecond-creates-occur` is the precondition: if it never fires, the others are vacuous.

## Read-modify-write lost updates
Properties: pattern-increments-not-lost, plant-checkins-match-entry-count, pattern-frequency-tracks-acked-triggers
Notes: `patterns.upsert_pattern` (get→put) and `entries.update_plant` (query-count→put) share the no-condition read-modify-write shape. `pattern-increments-not-lost` isolates the race; `pattern-frequency-tracks-acked-triggers` also catches the browser-driven second write never arriving, so it is broader. Its lower bound is implied by `pattern-increments-not-lost` holding plus all pattern POSTs arriving.

## Non-atomic multi-write check-in
Properties: plant-checkins-match-entry-count, plant-update-never-fails-silently, pattern-frequency-tracks-acked-triggers, unknown-outcome-create-explored, no-500-for-valid-requests
Notes: A check-in is entry put + plant put (server) + N pattern posts (client). Partial failure between them causes drift. `plant-update-never-fails-silently` is the SUT-side anchor for the server half (reachable only if dynamodb faults outlast botocore retries); the client half is visible via `pattern-frequency-tracks-acked-triggers`. `unknown-outcome-create-explored` shows the divergence path was exercised.

## Concurrency fidelity of the shim (precondition cluster)
Properties: concurrent-creates-all-retained, pattern-increments-not-lost, deleted-entry-stays-gone, same-millisecond-creates-occur
Notes: Need parallel request handling, which the committed `server.py` lacks. All depend on running the api with `uvicorn --workers 4` in the Antithesis compose (clock jitter is a second path for the collision properties only).

## Insights degradation
Properties: insights-never-500, insights-fallback-exercised, insights-normal-reply-parsed, requests-finish-within-gateway-limit
Notes: Safety plus both sides of coverage. `insights-fallback-exercised` should fire if `insights-never-500` is to mean anything.

## dynamodb availability, latency, and recovery
Properties: api-recovers-after-faults, entries-read-available, no-500-for-valid-requests, requests-finish-within-gateway-limit, plant-update-never-fails-silently
Notes: All shaped by botocore's defaults (60 s timeouts, up to 10 attempts): short faults become slow successes, so `requests-finish-within-gateway-limit` is the most likely of this cluster to fire, while `no-500-for-valid-requests` and `entries-read-available` need longer faults. In-memory dynamodb plus node termination would make `api-recovers-after-faults` fail because tables vanish.

## Resurrection and unknown outcomes
Properties: deleted-entry-stays-gone, unknown-outcome-create-explored, acked-entry-is-listed
Notes: botocore retrying a landed `put_item` after its response was lost is the shared mechanism; `unknown-outcome-create-explored` is the coverage precondition.

## Delete paths
Properties: deleted-entry-stays-gone, delete-of-existing-entry-occurs, plant-checkins-match-entry-count
Notes: `delete-of-existing-entry-occurs` is the coverage precondition. The plant property is the regression check for fix 3558b2c.

## Plant stage thresholds
Properties: plant-stage-matches-checkins, plant-reaches-later-stage
Notes: Same threshold logic in `entries.update_plant`. The guard only checks later stages once `plant-reaches-later-stage` fires.
