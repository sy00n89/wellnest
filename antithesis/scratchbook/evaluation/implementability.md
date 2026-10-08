---
sut_path: /home/exedev/wellnest
commit: 9e9e52f1a8f7948ebfc911fe95571579a1ff37c5
updated: 2026-10-05
external_references:
  - path: https://github.com/sy00n89/wellnest
    why: Upstream repo named by the user as the outside source; checked for issues, PRs, and wiki (no issues, no wiki, one merged PR #1 "local dev").
---

# Evaluation — Lens 3: Implementability

## Summary

Most properties can be observed from the workload because the API returns
everything needed: ids, server `timestamp`, `check_ins`, `frequency`, and the
error string in 500 bodies. The main implementability risks are: (1) count-equality
invariants that false-positive once unknown-outcome requests exist; (2) how the
workload's model is shared across `parallel_driver_` processes; (3) the
concurrency-restoring topology change, where a lighter and more faithful option
exists than the one recommended; (4) timeouts. boto3 and urllib waits (60 s) are
longer than any sensible workload timeout, which turns many requests into unknown
outcomes and, on the committed shim, stalls the whole API.

## Catalog-wide findings

### I-1 — Unknown outcomes are under-modelled; several invariants use equality where only a bound is sound

The catalog models only timeouts as "maybe stored". From the code:

- `POST /entries` can return **500 with the entry stored**: `put_item` reaches
  dynamodb, the response is lost, and botocore's retries (legacy mode, DynamoDB
  `max_attempts: 10`, read timeout 60 s) run out. `update_plant` swallows its own
  errors, so after a stored put, the only 500 source is this. The model must treat a
  create 500 as unknown, not as failed.
- `POST /patterns` can likewise be applied with a 500 or timeout returned.

Invariants affected:

| Slug | As written | Sound form |
|---|---|---|
| `concurrent-creates-all-retained` | `len(new_ids_listed) == acked_count` | `acked_ids ⊆ listed_ids` (unknown-outcome creates add extra items, so a count can be larger without any bug). Matching by id also avoids needing to know which listed ids are "new". |
| `pattern-increments-not-lost` | `freq == F + K` | `Always(freq >= F + K)` (lost update) and, separately, `Always(freq <= F + K + U)` where U = pattern POSTs with unknown outcome. |
| `acked-entry-is-listed` | timeouts = maybe | also 500s and connection resets on create = maybe. |
| `entry-fields-round-trip` | compare each listed item with the record "for that id" | skip ids with no record (unknown-outcome creates return no id to the workload). |

Suggested action: add a short "outcome model" note at catalog level (201 = stored;
4xx = not stored; 5xx / timeout / reset = unknown) and fix the three invariants above.

### I-2 — How the model is shared across `parallel_driver_` processes is unspecified

`deployment-topology.md` says parallelism comes from Antithesis running several
`parallel_driver_` commands at once. Those are separate processes. Properties that
compare server state with a model (`acked-entry-is-listed`,
`deleted-entry-stays-gone`, `pattern-increments-not-lost`,
`concurrent-creates-all-retained`) need that model to include every write to the
user being checked. Options the catalog should pick:

1. **User ownership per driver process** (recommended). Each driver invocation uses
   fresh user ids it alone writes. Overlap comes from threads inside the driver
   (as `overlapping-same-user-writes-occur` already assumes). The model stays
   in-process, and quiescent checks run at the end of the driver for its own users.
2. A shared model file with locking, needed only if cross-process same-user overlap
   is wanted.

`plant-checkins-match-entry-count` and `pattern-frequency-matches-entries` compare
server against server (plant vs list, patterns vs list), so they need no model, only
quiescence for the user. F-FIT-5 (resurrection) needs one driver to delete ids
learned from a list while another thread's create is still in flight, which
option 1 supports with threads.

### I-3 — A lighter, more faithful way to restore concurrency: `uvicorn --workers N`

The catalog and topology recommend `run_in_threadpool` in `server.py`, a SUT code
change. Two implementability concerns:

- **No code change needed with workers.** Overriding the api command in the
  Antithesis compose to `... exec uvicorn server:app --host 0.0.0.0 --port 8080 --workers 4`
  gives process-level concurrency with the committed `server.py`. Each worker still
  runs one request at a time on its event loop, which is **exactly the Lambda
  model** (one request per instance, separate memory, many instances). Same-ms
  collisions and RMW races happen across workers.
- **Thread-pool dispatch shares one `boto3.resource` across threads.** Each handler
  module creates a module-level `boto3.resource('dynamodb')` and `Table`. boto3's
  documentation says resource objects are not thread-safe and should not be shared
  across threads. Lambda never shares them. Thread-pool dispatch could therefore
  produce failures that are artifacts of the harness, and those would be reported
  against the SUT. I did not observe this. It is a documented risk, and the
  experiment in `sut-analysis.md` did not show which mechanism caused the 4–5
  lost entries (for example by checking for duplicate timestamps).

Suggested action: present `--workers N` as the first option to the human. Also
present it as a command override, not a code change, which removes the "needs the
owner's agreement because it changes the shim" objection. If thread-pool stays,
confirm the lost entries had colliding timestamps.

### I-4 — Timeouts: the workload must allow for 60 s server-side waits, and the committed shim stalls on them

- boto3 waits up to 60 s per attempt on dropped packets. `call_anthropic` waits up to
  60 s. On the committed shim the handler runs on the event loop, so **one** stalled
  dynamodb or Anthropic call blocks **every** request for that time. A workload with
  a 10 s timeout then sees bursts of unknown outcomes across all routes during any
  api↔dynamodb or api↔mock fault. That is a harness behaviour to plan for, not a
  SUT property.
- `insights-never-500` needs a workload timeout over 60 s (noted in the catalog).
  `api-recovers-after-faults` needs its bounded wait to cover a request stuck from
  the fault period (≥60 s read timeout plus backoff). The catalog doesn't say this.
- Alternative (see wildcard): set the workload HTTP timeout to 29 s to mirror API
  Gateway, and treat a longer wait as a production-equivalent 504.

### I-5 — SUT-side instrumentation: what it needs and where it gets awkward

- All SUT-side assertions (`plant-update-never-fails-silently`,
  `insights-fallback-exercised`, optional overlap counter) need the `antithesis`
  package in `backend/requirements.txt` and an image rebuild. The api image runs as
  user `app`. The SDK writes to `$ANTITHESIS_OUTPUT_DIR`. Confirm that path is
  writable by a non-root user in the Antithesis environment.
- `insights-fallback-exercised`'s empty-text callsite is the expression
  `return content[0].get('text') or FALLBACK_TEXT`. A separate `reachable` there
  needs a small refactor (split the `or` into an `if`). Not hard, but the catalog
  says "at each fallback return" as if both returns were already separate statements.
- `insights-never-500`'s precondition ("whenever entries can be read") cannot be
  checked from the workload as written. An api↔dynamodb fault makes the insights
  `table.query` fail → 500, which the workload `Always(status == 200 and text)`
  would count as a violation. Feasible fixes: (a) classify by the 500 body
  (`{"error": str(e)}`; for example `TimeoutError` gives `"timed out"`,
  `RemoteDisconnected` gives `"Remote end closed connection without response"`, which
  differ from botocore messages), or (b) better, a SUT-side
  `unreachable("insights: anthropic call raised outside fallback", {type})` wrapping
  `call_anthropic`, which needs no body-parsing heuristics.

## Property-specific findings

### `overlapping-same-user-writes-occur` — make the server-side proxy the primary signal, with no SUT change

Client-side in-flight counting stays green on the serializing shim. `GET /entries`
returns each item's server `timestamp` (ms). Two acknowledged creates for one user
whose server timestamps are within ~1 ms of each other, or closer together than a
handler's minimum duration, can only happen if the handlers overlapped (or the
clock stepped). `Sometimes(min_ts_gap_ms <= 1, "server-side near-collision")` is
fully observable from the workload. It is the precondition `concurrent-creates-all-retained`
actually needs, and it is false on the committed shim. That gives a direct "this
run was vacuous" signal.

### `delete-removes-only-target` — infeasible as specified

Serial context: cannot fail (antithesis-fit F-FIT-8). Concurrent context: the
set-difference invariant has false positives from other writers. No setup gives a
meaningful signal. Fold into `acked-entry-is-listed` and attach the deleted entry's
timestamp to failure details for attribution.

### `plant-checkins-match-entry-count` — quiescence is achievable, but say where

With per-driver user ownership (I-2), the driver can check its own users after
joining its threads. That is a serial section with no other writers, so a
`finally_` command is not required. If the check stays in `finally_`/`eventually_`,
it must list every user the run touched. In that case the workload needs a
persistent registry of user ids (a file).

### `pattern-frequency-matches-entries` — needs the workload to mirror the browser, including after failed creates

To exercise scenario 2 (entry 500, pattern POSTs still sent), the workload must send
pattern POSTs regardless of the create status, as `App.jsx` `handleSubmitEntry`
does. Combined with I-1 (create 500 may mean stored), the expected count is
ambiguous whenever a create's outcome is unknown. The equality form will
false-positive. Same fix pattern as I-1: bounds, or exclude users with unknown
outcomes from the equality check.

### `api-recovers-after-faults` — feasibility of the node-termination paths

Scenario 2 (api restarted while dynamodb is down → `create_tables.py` exits → api
stays down) needs api node termination plus dynamodb unavailability at the same
time. With no compose `restart:` policy, a dead api container stays dead. Whether
Antithesis "restores" a crashed container whose main process exited non-zero after
restart is a platform question (see Uncertainties). The Antithesis compose should
probably add a healthcheck on dynamodb and `depends_on: condition: service_healthy`
so setup itself doesn't flake. Today compose `depends_on` has no condition, so api
can start before the dynamodb JVM listens. boto3 retries (about 25 s of backoff on
connection refused) usually cover this.

### `data-survives-dynamodb-restart` — vacuous by default, and fails by configuration otherwise

Needs node termination (off by default) and a volume-backed dynamodb-local. The
topology plans neither. Recommend dropping (antithesis-fit F-FIT-2).

## Passes

- `acked-entry-is-listed`, `deleted-entry-stays-gone`, `entry-ids-unique-in-list`,
  `entry-fields-round-trip`, `user-entries-isolated`, `plant-stage-matches-checkins`,
  `plant-reaches-later-stage`, `insights-normal-reply-parsed`: all observable from
  public API responses, with no SUT change.
- `stress_level` numeric comparison note is correct (`DecimalEncoder` returns float).
- Topology puts workload, api, dynamodb, anthropic-mock in separate containers, so
  every link the properties need to fault can be faulted on its own.
- `plant-update-never-fails-silently`'s SUT-side `unreachable` placement is
  straightforward (inside the existing `except` in `entries.update_plant`).

## Uncertainties

- Whether the Antithesis SDK output directory is writable by the non-root `app` user
  in the api image.
- Whether Antithesis re-runs a container whose entrypoint exited after a node
  termination restart (affects `api-recovers-after-faults` scenario 2).
- Whether the 4–5 lost entries in the thread-pool experiment were all same-ms
  collisions or partly boto3 resource sharing artifacts. Not checked, since I did not
  run docker.
