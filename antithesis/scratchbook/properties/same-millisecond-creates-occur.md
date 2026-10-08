# same-millisecond-creates-occur

(Replaces `overlapping-same-user-writes-occur` after evaluation.)

## Why replaced
The original counted client-side in-flight requests, which is true even when the committed shim serializes requests on the server, so it was trivially satisfied and could hide a non-concurrent topology.

## Evidence trail
Server timestamps (`int(time.time()*1000)` in `entries.create_entry`) are returned by `GET /entries`. Two listed entries for one user ≤ 1 ms apart prove the server processed creates nearly simultaneously. A burst ack missing from the list with another item at its timestamp also proves a collision. Committed shim: 50 concurrent creates gave 50 distinct timestamps. `--workers 4`: collisions occurred.

## Instrumentation
Workload `Sometimes`, no SUT change. Missing today.

## Open questions
- None.
