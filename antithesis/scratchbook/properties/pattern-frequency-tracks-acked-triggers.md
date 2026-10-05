# pattern-frequency-tracks-acked-triggers

(Renamed from `pattern-frequency-matches-entries` after evaluation.)

## Evidence trail
- `src/App.jsx` `handleSubmitEntry`: after `POST /entries`, loops `for (const trigger of entry.triggers) await fetch(POST /patterns)`. No `response.ok` checks; a failed entry still updates patterns.
- `entries.delete_entry` never touches patterns.
- `patterns.upsert_pattern` lost-update race (see `pattern-increments-not-lost`).

## Failure scenarios
1. Entry stored, workload/browser fails before sending the pattern posts (fault between requests).
2. Entry POST returns 500, pattern posts still sent (frequency counts an entry that doesn't exist).
3. Delete of an entry with triggers: entry count drops, frequency doesn't.
4. Concurrent increments lost.

## Key observations
Scenario 3 is deterministic: the first delete of an entry with triggers fails it. That will dominate the report; the owner should decide whether patterns are an all-time tally (then exclude deleted entries from the expected count).

## Instrumentation
Workload `Always` at quiescence. Missing today.

## Open questions
- Is "delete doesn't decrement patterns" intended (all-time tally)? `(needs human input)`

### Investigation Log

#### Is "delete doesn't decrement patterns" intended?
- Examined: `patterns.py`, `entries.py` `delete_entry`, `App.jsx` (no UI reads `/patterns`), `docs/LEARNING_PLAN.md` ("Delete does not update plant or patterns | Drift").
- Found: the learning plan lists it as drift, implying a bug. No code comment either way.
- Not found: a product spec.
- Conclusion: `(needs human input)`. Leaning bug per the learning plan.

## Evaluation update (2026-10-05) — reformulated
The original equality failed by construction on the first delete (patterns never decrement). Now an all-time tally with bounds: lower = acked creates containing T whose pattern POSTs were acked; upper = all create attempts containing T (acked, unknown, failed), because the browser posts patterns even after a failed entry POST. Whether delete should decrement remains a human question.
