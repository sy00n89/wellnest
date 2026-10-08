> **INVALIDATED 2026-10-05** (evaluation): cannot fail in the required serial context and false-positives concurrently. Correction: an entry overwritten before the delete makes the lookup miss and return 404; it does not delete the wrong item. Covered by `acked-entry-is-listed`.

# delete-removes-only-target

## Evidence trail
`delete_entry` looks up the entry by `id` to get its `timestamp`, then deletes by `(user_id, timestamp)`. If two different ids ever shared a key slot (same-ms overwrite), the slot holds only the surviving item, so delete-by-key removes whatever is in the slot.

## Failure scenario
1. Create A at ms T (201, id a). 2. Create B at ms T (201, id b) overwrites A. 3. Delete a → lookup finds no `a` → 404 (so A's deletion "fails"). Alternatively, a concurrent create landing in the same ms as the looked-up timestamp between lookup and delete gets deleted instead.

## Key observations
Needs a per-user serial window to check precisely: read list, delete, read list, with no other writers for that user in between.

## Instrumentation
Workload `Always` in a serial section or a dedicated user. Missing today.

## Open questions
- Requires per-user serialization in the workload to avoid false positives. Workload design choice.
