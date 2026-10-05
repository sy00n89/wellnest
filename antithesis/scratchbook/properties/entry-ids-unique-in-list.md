# entry-ids-unique-in-list

## Evidence trail
`get_entries` returns `response['Items']` sorted by timestamp. Duplicate ids would require two items with the same `id` attribute under different keys. Today `id` is always a fresh `uuid4()`, so this is a guard against future retry/duplicate paths rather than a known bug.

## Failure scenario
A future client retry that resends the same `id` (the server currently ignores client ids) or a migration that copies items.

## Instrumentation
Workload `Always` on every list response. Missing today.

## Open questions
- None.

## Evaluation update (2026-10-05)
Kept as a P2 regression guard evaluated on reads the workload already makes; cannot fail against current code.
