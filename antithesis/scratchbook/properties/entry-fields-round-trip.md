> **INVALIDATED 2026-10-05** (evaluation): cannot fail independently of `acked-entry-is-listed`; field comparison moved into that property's assertion details.

# entry-fields-round-trip

## Evidence trail
`create_entry` copies `mood`, `stress_level` (as `Decimal(str(...))`), `triggers`, `physical_signs`, `notes`, `appraisal_*`, `vulnerability_factors`, client `date`/`time`. `DecimalEncoder` returns numbers as floats.

## Failure scenario
Same-ms overwrite where the surviving item's content belongs to a different request than the id the workload is tracking (only if ids and contents ever separate). Mostly a cheap consistency side check.

## Instrumentation
Workload `Always`. Compare `stress_level` numerically. Missing today.

## Open questions
- Numeric comparison for `stress_level` (float on read). Implementation note, resolved by design.
