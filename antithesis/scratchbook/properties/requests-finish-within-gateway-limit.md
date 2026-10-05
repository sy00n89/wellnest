# requests-finish-within-gateway-limit

## Evidence trail
- `backend/template.yaml` Globals `Timeout: 30` (InsightsFunction 60). API Gateway REST integrations time out at 29 s regardless.
- botocore defaults: 60 s connect/read timeouts, up to 10 attempts for DynamoDB.
- `insights.call_anthropic`: `urlopen(timeout=60)`.
- The local shim has no request deadline.

## Failure scenario
dynamodb or anthropic-mock latency/hang makes a request take > 29 s. In production the client gets a 504 while the Lambda may still complete the write (unknown outcome); insights' 60 s timeout fallback never runs.

## Instrumentation
Workload `Always(elapsed < 29 s)` per route; client timeout 29 s. Missing today.

## Open questions
- None.
