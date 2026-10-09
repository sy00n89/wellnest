# Wellnest: Learning and Execution Plan

A plan for taking Wellnest from a grad-school prototype to a containerized service running under Antithesis, and for learning why each change matters along the way.

## How we work together

Claude is both teacher and development agent on this project. The split is deliberate:

- **Siwoo owns understanding.** Every step starts with a short "why". Siwoo writes the prompts, reviews every diff, runs the commands, and explains each change back in their own words before it is committed. The rule is simple: never commit a diff you cannot explain.
- **Claude owns boilerplate.** Dockerfiles, config plumbing, test scaffolding, repetitive edits. Anything where the learning is in reading it, not typing it.
- **Siwoo hand-writes the conceptual core of each step.** These are marked "Siwoo writes" below. They are small on purpose, usually under forty lines, and they are the part where the concept clicks.
- **One step, one commit, one note.** After each step Siwoo writes three to five sentences in `docs/NOTES.md`: what changed, what broke, what surprised them. Those notes become the onboarding doc.

Working with an agent is a skill in itself. Good prompts name the file, the constraint, and the reason. Ask for a plan before a diff when the change touches more than one file. Ask "what could this break?" before accepting. Push back when the agent over-reaches; it will.

## Where we are starting

Wellnest today is a React single-page app, three Python Lambda handlers behind API Gateway, and three DynamoDB tables. It works, and it was built to demonstrate psychology frameworks, not engineering practice. Known debts, in the order we care:

| Debt | Why it matters | When we fix it |
|---|---|---|
| Anthropic API key compiled into the browser bundle | Anyone can read it and spend on your account | Phase 2 |
| API URL hardcoded in the frontend | Same build cannot run in two places | Phase 2 |
| No HTTP status checks in the frontend | Server errors look like success | Phase 2 |
| DynamoDB queries read one page only | Old entries silently vanish past ~1MB | Phase 2 |
| Build artifacts committed (`.aws-sam/`, `dist.zip`) | Repo is not the source of truth | Phase 0 |
| Plant table written but never read; two disagreeing stage algorithms | Data drift | Leave for Antithesis to find |
| Patterns updated from the browser, non-atomically with the entry | Tables disagree after a crash | Leave for Antithesis to find |
| Same-millisecond writes overwrite each other | Lost entries under load | Leave for Antithesis to find |
| Delete does not update plant or patterns | Drift | Leave for Antithesis to find |
| Everyone is user `default` | No isolation | Phase 5 |

The "leave for Antithesis" rows are a teaching choice. We know they are there. Letting the platform find them, with a reproducible trace, teaches more than a code review would. After the first run finds them, we fix them.

---

## Phase 0: Make the repo a source of truth

**Why.** Everything downstream assumes that checking out the repo and running one command gives you a working system. Committed build output, missing README, and untracked secrets all break that assumption.

**Steps**

0.1 Remove `backend/.aws-sam/` and `dist.zip` from git and add them to `.gitignore`. *Claude does it, Siwoo explains why `git rm --cached` differs from `rm`.*

0.2 Replace the Vite template README with a real one: what the app is, how to run the frontend and backend, what the three tables hold. *Siwoo writes the first draft from memory; Claude checks it against the code.*

0.3 Add `.env.example` listing every environment variable the app will need by the end of this plan, with comments. It starts nearly empty and grows. *Claude does it.*

**Done when** a fresh clone plus `npm install && npm run dev` produces the welcome screen, and `git status` is clean after a build.

---

## Phase 1: Make the backend run anywhere

**Why.** Lambda and DynamoDB are Amazon's machines. Antithesis has no internet and no Amazon. But the handler code does not actually depend on Lambda; it depends on receiving a dictionary and returning a dictionary. This phase makes that explicit.

**Step 1.1: Configurable DynamoDB endpoint**

*Why.* boto3 defaults to the real AWS endpoint. One optional environment variable lets the same code talk to a local container. This is the twelve-factor principle: config lives in the environment, code stays identical across environments.

*Do.* In each handler, change `boto3.resource('dynamodb')` to read `DYNAMODB_ENDPOINT` from the environment and pass it as `endpoint_url` when set. Three files, one line each. Also move the shared `DecimalEncoder` and `cors_headers` into a `common.py` since they are copy-pasted three times.

*Siwoo writes* the endpoint change in one handler, Claude mirrors it to the other two.

**Step 1.2: Run DynamoDB locally**

*Why.* Amazon publishes `amazon/dynamodb-local`, a real DynamoDB engine in a jar. LocalStack is the alternative the Antithesis docs recommend for AWS generally; we start with dynamodb-local because it is one process and persists to disk. Either speaks the same wire protocol boto3 already uses.

*Do.* `docker run -p 8000:8000 amazon/dynamodb-local`. Then write `backend/create_tables.py`, a boto3 script that creates the three tables from the SAM template's key schemas and is safe to run twice. Verify with `aws dynamodb list-tables --endpoint-url http://localhost:8000`.

*Siwoo writes* `create_tables.py` by reading `template.yaml` and translating each table block. This is infrastructure-as-code made literal: the YAML was always just a description of these API calls.

**Step 1.3: Replace API Gateway and Lambda with an HTTP shim**

*Why.* API Gateway turns an HTTP request into an event dictionary. Lambda calls `lambda_handler(event, context)`. Then API Gateway turns the returned dictionary back into an HTTP response. That is the whole job. A FastAPI app of about forty lines does the same thing, and the handlers do not change. Serverless is a deployment shape, not a programming model.

*Do.* Create `backend/server.py`. One catch-all route builds the event dict with `httpMethod`, `path`, `pathParameters`, `queryStringParameters`, and `body`, dispatches to the right handler by path prefix, and converts the result. Run with `uvicorn`. Curl every route.

*Siwoo writes* the function that converts a FastAPI request into the event dictionary. Claude writes the routing table and the uvicorn wiring. Compare the event Siwoo builds against a real API Gateway event sample side by side.

**Step 1.4: First tests**

*Why.* We are about to refactor. Tests written now define "still works." They also become the seed of the Antithesis workload later: the same assertions, run against a hostile environment.

*Do.* `pytest` with `httpx` hitting the running shim: create an entry, list entries, delete, check plant updates. Fixture that empties the tables between tests.

*Siwoo writes* the test for "create then list returns the entry." Claude writes the fixtures and the rest.

**Done when** the frontend, pointed at `http://localhost:8080` by hand, can complete a full check-in with no AWS credentials on the machine.

---

## Phase 2: Pay down the debts that matter

**Why.** These are the practices that separate a prototype from software other people can run. Each one is small. Together they change what the system is.

**Step 2.1: Move the Anthropic call server-side**

*Why.* A secret in a browser bundle is public. Anyone who opens the page can extract the key and bill your account. The rule is that clients never hold credentials for third-party services; they call your server, and your server holds the secret. A second benefit shows up immediately: the server call can be pointed at a mock with one environment variable, which is exactly what Antithesis needs.

*Do.* Add `backend/handlers/insights.py` with a `POST /insights` route. It receives `user_id`, reads the last 14 entries itself, builds the same prompt the frontend builds today, calls the Anthropic Messages API with `ANTHROPIC_API_KEY` and `ANTHROPIC_BASE_URL` from the environment, and returns the parsed sections as JSON. Frontend now calls `/insights` and renders the sections. Remove the key from the Vite config.

*Siwoo writes* the prompt-building function by moving it from `App.jsx` to Python. Claude writes the HTTP plumbing and the frontend change. Discuss: why should the server build the prompt rather than accepting one from the client?

**Step 2.2: Runtime configuration for the frontend**

*Why.* A static bundle cannot read environment variables at runtime; they are baked in when Vite builds. The standard fix is a tiny `config.js` the web server serves alongside the bundle, generated from the environment at container start. Same image, any API URL.

*Do.* `public/config.js` sets `window.WELLNEST_CONFIG = { apiBase: ... }`. `App.jsx` reads it instead of the constant. The nginx container's entrypoint writes the file from `API_BASE_URL`.

*Claude does it*, Siwoo explains why a Vite `import.meta.env` value would not have worked here.

**Step 2.3: Handle errors honestly**

*Why.* `fetch` only throws on network failure. A 500 from the server resolves normally, and today the app then reloads data as if the write succeeded. Checking `response.ok` and surfacing a message is the minimum. Under Antithesis, every swallowed error is a bug the platform cannot see.

*Do.* A small `api.js` wrapper in the frontend that checks status and throws. Visible error banner in the UI. On the backend, log every 500 with the exception and return a stable error shape.

*Siwoo writes* the wrapper. Claude replaces the call sites.

**Step 2.4: Paginate DynamoDB queries**

*Why.* A DynamoDB query returns at most 1MB and a `LastEvaluatedKey` if there is more. Every handler ignores that key. Past roughly a few thousand entries, old ones disappear from the list and become impossible to delete. This is the classic "works in the demo" bug.

*Do.* A `query_all` helper in `common.py` that loops on `LastEvaluatedKey`. Use it everywhere. Add a test that writes enough entries to cross a page boundary.

*Siwoo writes* `query_all`. Claude writes the boundary test, which needs to generate large notes to hit 1MB quickly.

**Done when** the frontend bundle contains no secrets (`grep -r sk-ant dist/` is empty), the same bundle runs against two different API URLs, and the pagination test passes.

---

## Phase 3: Containerize

**Why.** A container is a process with its filesystem, network, and configuration pinned down so it runs the same everywhere. Antithesis requires it. Every step here surfaces a concept that a project born in Docker would have hidden.

**Step 3.1: Frontend image, twice**

*Do.* First a single-stage Dockerfile from `node:20` that installs, builds, and serves with `vite preview`. Note the image size. Then a two-stage build: Node builds, `nginx:alpine` serves the `dist/` folder. Note the size again.

*Siwoo writes* the single-stage version. Claude writes the multi-stage version. The size difference is the lesson: ship the runtime, not the toolchain.

**Step 3.2: API image**

*Do.* `python:3.11-slim`, copy `backend/`, install `requirements.txt`, run `create_tables.py` then `uvicorn` from an entrypoint script. Pin every dependency version.

*Claude does it.* Siwoo explains why the entrypoint creates tables rather than assuming they exist.

**Step 3.3: Compose the system**

*Why.* Containers find each other by service name on a private network. They also start in whatever order they like, and the API will crash if DynamoDB is not ready. The first run will fail. That failure is the lesson.

*Do.* `docker-compose.yaml` with `frontend`, `api`, `dynamodb`. Run it. Watch `api` crash. Add a healthcheck to `dynamodb` and `depends_on: condition: service_healthy` to `api`. Then discuss why a retry loop in `create_tables.py` is the more durable fix, and add that too.

*Siwoo writes* the compose file from a skeleton. Claude writes the healthcheck and retry.

**Step 3.4: Persist state, then lose it on purpose**

*Do.* Create entries. `docker compose down`. `docker compose up`. Entries gone. Add a named volume for dynamodb-local's data directory. Repeat. Entries survive. `docker compose down -v`. Gone again.

*Siwoo runs* the whole experiment. Stateless containers plus explicit volumes is the mental model that makes "restart this container" a meaningful fault later.

**Step 3.5: Mock the Anthropic API**

*Why.* No internet inside Antithesis. The insights route needs somewhere to call. A stub that returns a canned five-section response is enough to exercise the parsing. Make it occasionally return malformed text so the parser's fallback path runs.

*Do.* `mocks/anthropic/` with a small FastAPI app implementing `POST /v1/messages`. Add to compose. Point `ANTHROPIC_BASE_URL` at it.

*Claude writes the mock.* Siwoo writes the three canned responses, including one broken one.

**Done when** `docker compose up` from a clean checkout gives a working app at `localhost:3000`, and `docker compose down -v && docker compose up` gives an empty one.

---

## Phase 4: Test in Antithesis

**Why.** Antithesis runs the compose file in a deterministic simulation, injects faults, drives it with your workload, and checks your assertions. The planted bugs from the table above are the targets. Finding them with a reproducible trace, rather than by reading the code, is the point of the platform and of this exercise.

**Step 4.1: Research and property catalog**

*Do.* Run the `antithesis-research` skill against the repo. Review its output together. The property catalog should include at least:

- No request ever returns 500.
- An entry that was created and not deleted is always returned by GET.
- `plant.check_ins` equals the number of entries for that user.
- For each trigger, `patterns.frequency` equals the count of entries containing it.
- Deleting an entry removes exactly that entry.
- Two entries created back to back are both retrievable.

*Siwoo writes* the catalog entries in plain English first. Claude formalizes them.

**Step 4.2: Harness setup**

*Do.* Run `antithesis-setup`. It produces the config image and adjusts compose for the platform. Run `snouty validate`. Fix what it flags.

*Claude does it.* Siwoo reads the resulting compose diff and explains each change.

**Step 4.3: Write the workload**

*Why.* The workload is a program that uses the API like a chaotic user: random check-ins, random deletes, occasional insight requests, and after every action it checks the properties. It is the pytest suite from step 1.4 with randomness and SDK assertions.

*Do.* `workload/` in Python using the Antithesis SDK. `setup_complete` after tables are ready. A loop of random operations. `always` assertions for the invariants. `sometimes` assertions proving coverage: a delete happened, an insight was generated, a high-stress entry triggered appraisal fields.

*Siwoo writes* the invariant checks. Claude writes the operation generators and SDK wiring. Run it locally against compose first; it should pass clean.

**Step 4.4: Launch, triage, fix**

*Do.* `antithesis-launch` for a short run. Use `antithesis-triage` on the report. Expect the plant-count and pattern-count properties to fail. Read the trace. Fix the root causes:

- Plant and pattern updates move into the entry handler, computed from a full query, so one write path owns them.
- Sort key becomes `timestamp#uuid` or the id becomes part of the key, so same-millisecond writes cannot collide.
- Delete updates plant and patterns.

Re-run. Green.

*Siwoo drives triage* with Claude explaining the report. Siwoo proposes each fix; Claude implements; Siwoo reviews.

**Step 4.5: Prove the tests can fail**

*Do.* Run `antithesis-mutation-testing`. It reintroduces a bug and checks the property catches it. Any property that does not fire is a property that was never really testing anything.

**Done when** a run comes back green, and a mutation run shows every safety property firing at least once.

---

## Phase 5: Add real dependencies

**Why.** The user asked for more to test. Adding dependencies that create real distributed-systems problems gives the workload something to bite on.

Pick in order of value:

5.1 **Users and authentication with Postgres.** Fixes "everyone is default." Adds a relational store next to DynamoDB. New invariant: no user can read another's entries. Teaches: two stores, cross-store consistency, sessions.

5.2 **Async pattern updates through a queue.** Move the pattern write to an SQS-compatible queue (LocalStack) with a worker. Now the non-atomic write is a real eventual-consistency problem, and the invariant becomes "eventually equal." Teaches: queues, idempotency, at-least-once delivery.

5.3 **A cache in front of GET /entries.** Redis with a short TTL. New bug class: stale reads after delete. Teaches: cache invalidation, the hard problem.

Each one repeats the Phase 4 loop: research, properties, workload, launch, triage.

---

## Reference

**Commands you will use constantly**

```
docker compose up --build
docker compose down -v
docker compose logs -f api
aws dynamodb scan --table-name wellnest-entries --endpoint-url http://localhost:8000
curl -s localhost:8080/entries?user_id=default | jq
pytest backend/tests
snouty validate
```

**Reading, one per phase**

- Phase 1: The Twelve-Factor App, sections III (Config) and IV (Backing services).
- Phase 2: OWASP on client-side secrets; DynamoDB docs on pagination.
- Phase 3: Docker docs, "Multi-stage builds" and "Compose startup order."
- Phase 4: Antithesis docs, "Properties and assertions" and "Handling external dependencies."
- Phase 5: Kleppmann, *Designing Data-Intensive Applications*, chapters on consistency.

**Antithesis skills installed in this environment**

`antithesis-research`, `antithesis-setup`, `antithesis-workload`, `antithesis-launch`, `antithesis-triage`, `antithesis-mutation-testing`, `antithesis-documentation`.
