# insights-fallback-exercised

## Evidence trail
Two fallback returns in `call_anthropic`: the `except` branch and `content[0].get('text') or FALLBACK_TEXT` (empty text). The mock returns empty text in ~10% of calls (`BAD_REPLIES[0]`, chosen half the time within the 20% bad branch).

## Instrumentation (SUT-side, missing)
`reachable("insights fallback: anthropic call failed", {"error": ...})` in the except; `reachable("insights fallback: empty text", {})` at the empty-text return. Distinct messages per callsite.

## Open questions
- None.

## Evaluation update (2026-10-05)
Connection-failure fallback also needs the mock to misbehave at the transport level or network faults on api↔anthropic-mock.
