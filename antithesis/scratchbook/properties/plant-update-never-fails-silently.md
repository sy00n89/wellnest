# plant-update-never-fails-silently

## Evidence trail
`backend/handlers/entries.py` `update_plant`:
```python
try:
    ...
    plant_table.put_item(...)
except Exception as e:
    print(f"Plant update error: {e}")
```
`create_entry` returns 201 regardless.

## Failure scenario
api↔dynamodb partition or dynamodb hang after the entry `put_item` succeeds. The plant query or put raises; error printed and swallowed.

## Instrumentation (SUT-side, missing)
`antithesis.assertions.unreachable("update_plant failed after entry write", {"error": str(e)})` inside the `except`. Requires adding the Antithesis Python SDK (`antithesis` on PyPI) to `backend/requirements.txt`.

## Open questions (superseded — see "Open questions (current)" below)

## Evaluation update (2026-10-05)
botocore defaults verified in `backend/.venv` (botocore 1.43.106): 60 s connect and read timeouts, legacy retry mode, 10 max attempts for DynamoDB. Short faults appear as slow successes, so this `Unreachable` may pass without the path being exercised. Lowering `AWS_MAX_ATTEMPTS` and timeouts in the Antithesis compose would make it reachable (open question).

## Open questions (current)
- Lower `AWS_MAX_ATTEMPTS` and connect/read timeouts in the Antithesis compose so this path is reachable within fault durations? Trade-off: makes the harness less like production defaults but exposes the swallowed-error path. `(needs human input)`

### Investigation Log

#### Lower botocore retries/timeouts in the Antithesis env?
- Examined: `backend/handlers/*.py` (default `boto3.resource`, no `Config`), botocore 1.43.106 defaults in `backend/.venv` (via evaluation), Antithesis fault descriptions (durations not specified in docs we read).
- Found: no explicit retry/timeout configuration; defaults are 60 s timeouts, legacy mode, 10 attempts for DynamoDB.
- Not found: typical fault durations in Antithesis runs.
- Conclusion: `(needs human input)`.
