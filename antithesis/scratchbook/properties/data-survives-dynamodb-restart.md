> **INVALIDATED 2026-10-05** (evaluation): tests dynamodb-local in-memory mode rather than Wellnest, and is vacuous with default faults (node termination off). Recovery covered by `api-recovers-after-faults`.

# data-survives-dynamodb-restart

## Evidence trail
dynamodb-local image default CMD `-jar DynamoDBLocal.jar -inMemory` (verified). Compose sets no command override and no volume.

## Failure scenario
Any dynamodb container restart loses all data.

## Key observations
Vacuous unless node termination is enabled. With `-sharedDb -dbPath /data` + volume it tests real recovery. Antithesis notes restarted containers "may lose non-durable filesystem state", so a volume is required.

## Instrumentation
Workload `Always` after recovery. Missing today.

## Open questions
- Node termination enabled for the tenant? `(needs human input)`
- Persist dynamodb-local to disk in the Antithesis topology? `(needs human input)`

### Investigation Log

#### Node termination enabled? / Persist dynamodb-local?
- Examined: research `faults.md` reference, compose file, image config.
- Found: node termination is disabled by default; no persistence configured.
- Not found: tenant settings.
- Conclusion: both `(needs human input)`.
