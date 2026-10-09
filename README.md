# Wellnest

A stress and wellbeing journal. You check in with your mood, stress level, triggers, and notes; the app shows your history, trigger patterns, AI-generated insights, and a plant that grows every 20 check-ins. Each browser keeps its own journal.

## How it fits together

```
Browser → frontend (React, served by nginx) → /api → API (Python) → DynamoDB
                                                         └────────→ Anthropic API (insights)
```

- `src/`: the React app
- `backend/`: the API (`server.py` + `handlers/`) and its tests (`backend/tests/`)
- `mocks/anthropic/`: a stand-in for the Anthropic API, used locally and in Antithesis
- `antithesis/`: the Antithesis test harness, workload, and research notes
- `.github/workflows/ci.yml`: CI (lint, build, pytest on every pull request)

The plant and trigger counts are computed from a user's entries on every read, and deleted entries are kept as tombstones (`deleted = true`) so a late retried save cannot bring them back. When DynamoDB is unreachable the API answers `503` quickly instead of waiting past API Gateway's 29 s limit.

## Run it

Everything runs in Docker:

```
docker compose up -d --build     # app on http://localhost (and :8081)
docker compose down              # stop (add -v only to delete all data)
```

For frontend development with hot reload, keep the compose stack running for the API and run `npm install && npm run dev`.

## Test it

```
cd backend
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt -r requirements-dev.txt
docker run -d -p 8001:8000 amazon/dynamodb-local    # tests use a local DynamoDB on :8001
.venv/bin/python -m pytest tests
```

## Antithesis

The harness lives in `antithesis/`. Build the images, validate, then launch:

```
docker compose -f antithesis/config/docker-compose.yaml build
snouty validate antithesis/config
snouty launch --webhook basic_test --config antithesis/config --duration 30
```

What is tested, every run, every bug found, and every decision made is recorded in `antithesis/scratchbook/property-catalog.md`. The original plan is in `docs/LEARNING_PLAN.md`.
