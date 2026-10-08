# concurrent-creates-all-retained

## Evidence trail
Same mechanism as `acked-entry-is-listed`: `int(time.time()*1000)` as the sort key with unconditional `put_item` in `backend/handlers/entries.py` `create_entry`.

Experiment: thread-pool dispatch, 50 concurrent creates → 45–46 retained. Committed shim → 50 retained, because `server.py` `dispatch` (an `async def`) calls the sync handler on the event loop and serializes requests.

## Failure scenario
A `parallel_driver_` fires several creates for one user at once. Two land in the same ms. One is silently overwritten.

## Key observations
- (Superseded, see Evaluation update) Cannot fail against the committed shim unless clock jitter is on; needs parallel request handling (`--workers 4`).
- Clock jitter backward (if enabled) can also reuse a past millisecond.
- Fix options (for later): add the uuid to the sort key (`timestamp#uuid`), or `ConditionExpression='attribute_not_exists(#ts)'` plus retry.

## Instrumentation
Workload-side `Always`. SUT-side option for exploration guidance: `Reachable` when `put_item` replaces an existing item (would need `ReturnValues='ALL_OLD'` to detect). Missing today.

## Open questions (superseded — see "Open questions (current)" below)

## Evaluation update (2026-10-05)
- Correction: the earlier claim "cannot fail on the committed shim" is false if clock jitter is enabled. A backward clock step reuses past milliseconds with no concurrency.
- Recommended topology is `uvicorn --workers 4` rather than thread-pool dispatch: separate processes like Lambda instances, and no shared non-thread-safe `boto3.resource`. Verified to reproduce collisions (48–49 of 50 listed).
- Invariant uses subset form (`burst_acked_ids ⊆ listed_ids`), not a count, so unknown outcomes don't false-positive.

## Open questions (current)
- Is clock jitter enabled for the tenant? If yes, collisions also occur without concurrency, and the property is exercised even if worker concurrency were missing. `(needs human input)`

### Investigation Log

#### Is clock jitter enabled for the tenant?
- Examined: research `faults.md` reference (clock faults commonly disabled by default), `snouty` CLI availability, repo config.
- Found: no tenant configuration in the repo; defaults suggest off.
- Not found: the tenant's actual fault settings.
- Conclusion: `(needs human input)`.
