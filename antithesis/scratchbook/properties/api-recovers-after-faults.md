# api-recovers-after-faults

## Evidence trail
- api CMD: `python create_tables.py && exec uvicorn ...`. No compose `restart:` policy.
- boto3 default client; connection reuse across partitions untested.
- dynamodb `-inMemory`: a dynamodb restart wipes tables; `create_tables.py` only runs at api start.

## Failure scenarios
1. Partition heals but requests keep failing (unlikely with boto3, worth confirming).
2. api restarted while dynamodb is down → `create_tables.py` exhausts retries → api exits and stays down.
3. dynamodb restarted (in-memory) → tables gone → every request 500 (`ResourceNotFoundException`) until api restarts.

## Instrumentation
Workload `Sometimes(recovered)` in an `eventually_` command or after `ANTITHESIS_STOP_FAULTS`. Missing today.

## Open questions
- Is dynamodb node termination with `-inMemory` in scope? `(needs human input)`

### Investigation Log

#### Is dynamodb node termination with -inMemory in scope?
- Examined: `docker inspect amazon/dynamodb-local` (CMD `-jar DynamoDBLocal.jar -inMemory`), `create_tables.py`, `backend/Dockerfile` CMD, Antithesis faults reference (node termination disabled by default).
- Found: scenario 3 is guaranteed if dynamodb is killed.
- Not found: tenant fault configuration.
- Conclusion: `(needs human input)`.

## Evaluation update (2026-10-05)
Changed from `Sometimes` to `Always` in an `eventually_` check: `Sometimes` passes if any one timeline recovers, hiding a stuck one. Poll window must exceed botocore's 60 s read timeout (~90 s).
