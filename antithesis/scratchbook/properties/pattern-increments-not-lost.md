# pattern-increments-not-lost

## Evidence trail
`backend/handlers/patterns.py` `upsert_pattern`: `get_item` → `new_frequency = existing + 1` → `put_item` (no condition, no `UpdateExpression ADD`).

Experiment 2026-10-05: 50 concurrent `POST /patterns` (same user, same trigger), all 201:
- committed shim → frequency 50
- thread-pool dispatch → frequency 12, then 11

## Failure scenario
Two increments read frequency f, both write f+1. One increment lost. Severity blend `(old+new)/2` is also order-dependent.

## Key observations
- Requires thread-pool dispatch to fail.
- Fix (later): `update_item` with `ADD frequency :one`.

## Instrumentation
Workload `Always` at quiescence for a (user, trigger) pair the workload owns. Missing today.

## Open questions
- None.

## Evaluation update (2026-10-05)
- Recommended topology is `uvicorn --workers 4` (thread-pool dispatch rejected: shares non-thread-safe boto3 objects). Verified: 50 concurrent increments → frequency 21, 20, 19.
- "Requires thread-pool dispatch to fail" above is superseded: it requires parallel request handling, provided by `--workers 4`.
- Invariant now uses bounds `F+K ≤ freq ≤ F+K+U` to tolerate unknown outcomes.
