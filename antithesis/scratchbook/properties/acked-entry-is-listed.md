# acked-entry-is-listed

## Evidence trail
- `backend/handlers/entries.py` `create_entry`: `timestamp = Decimal(str(int(now * 1000)))`, `table.put_item(Item=item)` with no `ConditionExpression`.
- `backend/template.yaml` / `backend/create_tables.py`: entries key is `user_id` (HASH) + `timestamp` (RANGE). The UUID `id` is not part of the key.
- Experiment 2026-10-05 (see `sut-analysis.md`): 50 concurrent `POST /entries` for one user, all returned 201. With the committed shim, 50 listed. With thread-pool dispatch, 46 and 45 listed in two trials.

## Failure scenario
Two creates for user U compute the same millisecond. Both `put_item` the same key; the second replaces the first. Both clients got 201 with different ids. `GET /entries` returns only the second id.

## Other paths that could violate it
- A network fault after `put_item` reached dynamodb but before the api replied: the workload sees an error or timeout though the entry exists. Not a violation (unknown outcome), but the model must allow it.
- dynamodb restart with `-inMemory` wipes all tables; out of scope unless node termination is enabled (see `api-recovers-after-faults`).

## Workload notes
Track `acked = {id: entry}` per user and `deleted = {id}`. On each list, assert `acked - deleted ⊆ listed_ids`. Treat timeouts as "maybe stored": don't add to `acked`, but don't flag if it appears.

## Instrumentation
Workload-side `Always`. Optional SUT-side: none needed; the workload observes it directly. Nothing exists today (`existing-assertions.md`).

## Open questions
- None (resolved by the outcome model; see Evaluation update).

## Evaluation update (2026-10-05)
- Outcome model: invariant is `acked_live_ids ⊆ listed_ids`; unknown-outcome creates (5xx, timeout, reset) may or may not be listed. A create can return 500 *after* the entry was stored (botocore retries exhausted on the response path).
- Absorbs `entry-fields-round-trip` (field mismatches in details) and `delete-removes-only-target`.
- Reproduced with `uvicorn --workers 4` (no code change): 50 acked → 48, 49, 48 listed.
- Not only concurrency: a backward clock step (clock jitter) can reuse a millisecond that already holds an entry.
- After a future conditional-put-plus-retry fix, botocore retrying a conditional put whose first attempt landed fails with `ConditionalCheckFailedException` for a stored entry. The unknown-outcome model handles it; read post-fix runs with that in mind.
