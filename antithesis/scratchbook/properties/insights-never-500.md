# insights-never-500

## Evidence trail
`backend/handlers/insights.py` `call_anthropic`: `urlopen(request, timeout=60)`, `except (urllib.error.URLError, json.JSONDecodeError)` → `FALLBACK_TEXT`.

Verified 2026-10-05 in Python 3.12: a server that sends headers then stalls the body makes `r.read()` raise `TimeoutError`, and `isinstance(e, URLError)` is False. `HTTPError` *is* a `URLError` subclass (fallback). So a slow body escapes to `lambda_handler`'s catch-all → 500.

## Failure scenario
Network delay or node hang on `anthropic-mock` mid-response for > 60 s. Also: `data.get('content')` returning a non-list or `content[0]` not a dict would raise (the current mock never does this).

## Key observations
(Superseded) The workload uses a 29 s timeout everywhere, so it cannot observe the 60 s timeout 500 directly; the SUT-side `Unreachable` covers it.

## Instrumentation
Workload `Always(status == 200 and text)`. Missing today.

## Open questions
- None. (Resolved after evaluation: the workload uses a 29 s timeout; the 60 s `TimeoutError` path is detected by the SUT-side `Unreachable`, not the workload.)

## Evaluation update (2026-10-05) — lowered to P2
- Also verified: a timeout *before headers* raises `TimeoutError`, and a dropped connection raises `http.client.RemoteDisconnected`; neither is a `URLError`, so both return 500.
- Impact correction: the SPA's `generateInsight` shows fallback text when the call fails, so users see little difference today.
- Add SUT-side `Unreachable("insights: anthropic call raised uncaught exception", {type})` around `call_anthropic` so dynamodb-caused 500s on this route aren't conflated with Anthropic handling.
- Production config defect: the Anthropic timeout is 60 s but API Gateway cuts requests at 29 s, so the timeout fallback can never run in production. See `requests-finish-within-gateway-limit`.
- Needs the mock to sometimes stall or drop connections (setup task in `deployment-topology.md`).
