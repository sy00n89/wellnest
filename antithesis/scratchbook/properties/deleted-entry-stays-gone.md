# deleted-entry-stays-gone

## Evidence trail
`backend/handlers/entries.py` `delete_entry`: query all entries for the user, find `id`, `delete_item(Key={'user_id', 'timestamp'})`, then `update_plant`.

## Failure scenario
Low expected yield with current code: once deleted, nothing rewrites that key with the same id. Included as a guard for resurrect-on-retry behavior and to pair with `acked-entry-is-listed`.

## Instrumentation
Workload `Always`. Missing today.

## Open questions
- None.

## Evaluation update (2026-10-05) — priority raised to P1
Earlier text said nothing rewrites a deleted key. botocore does: if a `put_item` reaches dynamodb but its response is lost, botocore retries the same `put_item`. If another thread deleted that entry between the two attempts (after seeing it in a list), the retry re-creates it. Requirements: concurrency, network faults on api↔dynamodb, and a workload that deletes ids it saw in lists, not only its own acks.
