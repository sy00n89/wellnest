# no-500-for-valid-requests

## Evidence trail
Every `lambda_handler` (`entries.py`, `plant.py`, `patterns.py`, `insights.py`) wraps dispatch in `except Exception as e: return 500 {'error': str(e)}`. boto3 errors (endpoint unreachable, timeouts) therefore become 500. Malformed input also becomes 500 (e.g. `json.loads(None)` when the body is empty; `Decimal('abc')`), but the workload sends only well-formed requests.

## Failure scenario
Partition between api and dynamodb → boto3 `EndpointConnectionError` after retries → 500.

## Key observations
Expected to fire under partitions; the open question is whether that's acceptable. A useful framing for the report: which routes 500, and whether they recover (`api-recovers-after-faults`).

## Instrumentation
Workload `Always(status != 500)` with route in details. Missing today.

## Open questions
- Is a 500 acceptable during a full api↔dynamodb partition? `(needs human input)`

### Investigation Log

#### Is a 500 acceptable during a full partition?
- Examined: all handlers' error paths, `App.jsx` callers.
- Found: no retry or 503 distinction; the frontend ignores status codes, so the user can't tell.
- Not found: an SLO or error-handling spec.
- Conclusion: `(needs human input)`. Suggest narrowing to "no 500 when dynamodb reachable" or reporting it as degradation.

## Evaluation update (2026-10-05) — lowered to P2
Earlier "expected to fire under partitions" is unlikely: botocore retries absorb faults shorter than ~60 s × attempts. The user-visible read case moved to `entries-read-available`. Impact correction: a 500 on `GET /entries` empties the SPA history (`Array.isArray(...) ? ... : []` in `loadData`).
