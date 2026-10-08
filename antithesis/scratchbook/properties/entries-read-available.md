# entries-read-available

## Evidence trail
`src/App.jsx` `loadData`: `setEntries(Array.isArray(entriesData) ? entriesData : [])`. A 500 from `GET /entries` returns `{"error": ...}`, so the SPA shows an empty history. `entries.get_entries` errors (boto3 exceptions) go to the catch-all 500.

## Failure scenario
dynamodb slow or partially partitioned long enough to exhaust botocore retries; or an api worker restarting.

## Key observations
Evaluate only when neighbouring api requests succeed, so a total api outage isn't counted (that's `api-recovers-after-faults`).

## Instrumentation
Workload `Always`. Missing today.

## Open questions
- None.
