# plant-checkins-match-entry-count

## Evidence trail
- `entries.update_plant`: `table.query(...)` → `total = len(Items)` → `plant_table.put_item({'user_id', 'stage', 'check_ins': total})`. Called after create and (since commit 3558b2c) after delete.
- `update_plant` wraps everything in `try/except Exception: print(...)`.
- `plant.update_plant` (`POST`/`PUT /plant`) overwrites the row with client values.
- pytest `test_delete_updates_plant` covers the sequential delete case.

## Failure scenarios
1. Lost update: create X and create Y overlap. X's `update_plant` queries (sees n+1), Y's queries (sees n+2), Y writes n+2, X writes n+1 last. Count is one short.
2. Partial failure: entry `put_item` succeeds, plant `put_item` fails (network fault). Error swallowed, 201 returned, count stale until the next write.
3. External overwrite via `POST /plant` (excluded from workload).

## Key observations
Only meaningful at quiescence. Check in a `finally_`/`eventually_` command or in a serial section after all writes for the user complete.

## Instrumentation
Workload `Always` at quiescence. SUT-side: see `plant-update-never-fails-silently`. Missing today.

## Open questions
- Workload must not call `POST`/`PUT /plant` `(needs human input)`

### Investigation Log

#### Workload must not call POST/PUT /plant
- Examined: `src/App.jsx` (all `fetch` calls), `backend/handlers/plant.py`.
- Found: the frontend only calls `GET /plant`. `POST`/`PUT /plant` accept arbitrary `check_ins`, so any call breaks the invariant by construction.
- Not found: any documented consumer of `POST`/`PUT /plant`.
- Conclusion: recommend excluding them from the workload; the owner should confirm the endpoints are not meant to be used. `(needs human input)`
