---
sut_path: /home/exedev/wellnest
commit: 9e9e52f1a8f7948ebfc911fe95571579a1ff37c5
updated: 2026-10-05
external_references:
  - path: https://github.com/sy00n89/wellnest
    why: Upstream repo named by the user as the outside source; checked for issues, PRs, and wiki (no issues, no wiki, one merged PR #1 "local dev").
---

# Evaluation Synthesis

Four lenses ran in one fresh-context agent: `antithesis-fit.md`, `coverage-balance.md`,
`implementability.md`, `wildcard.md`. Findings are categorized below with the action
taken. The orchestrator verified the most consequential claim by experiment (see R-8).

## Refinements (applied)

IDs follow the evaluation's finding numbers. Findings 9 and 10 (shared `default` user; catalog confirms known bugs) are biases, listed below as B-1 and B-2.

| ID | Finding | Action taken |
|---|---|---|
| R-1 | Several properties cannot fail against this code (server-side `uuid4` ids, one `put_item` for stage+count, hash-key query). | `entry-fields-round-trip` and `delete-removes-only-target` **invalidated** (merged into `acked-entry-is-listed` as assertion details). `entry-ids-unique-in-list`, `user-entries-isolated`, `plant-stage-matches-checkins` kept as **P2 regression guards** evaluated on the same reads (no extra workload). |
| R-2 | `pattern-frequency-matches-entries` fails by construction on the first delete; `data-survives-dynamodb-restart` tests dynamodb-local, not Wellnest. | First reformulated as `pattern-frequency-tracks-acked-triggers` (all-time tally against acked creates, with unknown-outcome bounds; delete semantics left as a human question). Second **invalidated**. |
| R-3 | "P0 concurrency properties cannot fail on the committed shim" is false under clock jitter: a backward clock step reuses past milliseconds. | Corrected in catalog, `sut-analysis.md`, evidence files. Added catalog-level question on clock jitter. |
| R-4 | botocore defaults (60 s connect/read timeouts, legacy retry mode, 10 attempts for DynamoDB) absorb short faults, so `plant-update-never-fails-silently` may pass vacuously and `no-500-for-valid-requests` is unlikely to fire. | Softened claims in `no-500-for-valid-requests` and `plant-update-never-fails-silently`. Recorded as an open question whether to lower retries (`AWS_MAX_ATTEMPTS`) in the Antithesis compose env so these paths become reachable. |
| R-5 | API Gateway's 29 s integration limit is not modelled; insights uses a 60 s timeout, so in production its timeout fallback can never run (config defect). | Workload HTTP timeout set to 29 s in all properties. New property `requests-finish-within-gateway-limit`. Insights evidence updated. |
| R-6 | Unknown outcomes (5xx after a stored write, timeouts, resets) were under-modelled; count equalities would false-positive. | Invariants rewritten as subset/bounds: `acked ⊆ listed ⊆ acked ∪ unknown`, `F+K ≤ freq ≤ F+K+U`. |
| R-7 | Model sharing across `parallel_driver_` processes unspecified. | Catalog-wide assumption: each driver run owns its user ids; overlap comes from threads inside the driver. Shared-user traffic handled by a separate driver (see B-1). |
| R-8 | `uvicorn --workers N` models Lambda better than thread-pool dispatch (boto3 resources aren't thread-safe; thread-pool results could be harness artifacts). | **Verified by orchestrator 2026-10-05**: `--workers 4`, 50 concurrent requests, 3 trials → pattern frequency 21/20/19 of 50; entries 48/49/48 of 50 listed. Topology now recommends `--workers 4` via compose `command:` override, no code change. |
| R-11 | `GET /entries` returning 500 makes the SPA show an empty history (`Array.isArray(...) ? ... : []`). | New property `entries-read-available`. `no-500-for-valid-requests` impact text corrected. |
| R-12 | The mock never stalls, drops connections, or returns errors, so insights properties can't exercise their failure paths. | Recorded as a setup task in `deployment-topology.md`: mock should sometimes stall past 29 s, close the connection, return 429/500, or invalid JSON. |
| R-13 | `deleted-entry-stays-gone` underestimated: botocore's automatic retry of a `put_item` whose response was lost can re-create an entry after another driver deleted it. | Angle and priority raised to P1; workload must delete ids seen in lists, not only its own acks. |
| R-14 | `insights-never-500` mechanism too narrow (`TimeoutError` before headers, `RemoteDisconnected` also escape); user impact overstated (SPA shows fallback text on 500). | Angle fixed, lowered to P2, SUT-side `Unreachable` around `call_anthropic` added so dynamodb-caused 500s aren't conflated. |
| R-15 | `api-recovers-after-faults` as `Sometimes` passes if any timeline recovers. | Changed to `Always` in a quiescent check with a wait longer than botocore's 60 s read timeout. |
| R-16 | `delete-removes-only-target` can't fail serially and false-positives concurrently; its angle was wrong (a pre-existing overwrite yields 404). | Invalidated (see R-1). |
| R-17 | Guidance `Sometimes` on client-side overlap is trivially true even when the server serializes. | Replaced by `same-millisecond-creates-occur`: two listed entries for one user with server timestamps ≤ 1 ms apart. No SUT change needed. |
| R-18 | P0/P1 inconsistency for `pattern-increments-not-lost`; pagination exclusion reason wrong. | Fixed: P1 everywhere. Pagination reason now "cheap to trigger, deterministic, integration-test territory". |

## Gaps (filled)

| ID | Gap | Property added |
|---|---|---|
| G-1 | Clock-driven key collisions with no concurrency. | Covered by `concurrent-creates-all-retained` (renamed scope: overlapping *or* clock-stepped creates) plus catalog question on clock jitter. No separate property: same invariant, same assertion. |
| G-2 | Read availability (empty-history symptom). | `entries-read-available` |
| G-3 | Latency against the production 29 s limit. | `requests-finish-within-gateway-limit` |
| G-4 | Client gives up, server finishes (W-8). | `unknown-outcome-create-explored` (Sometimes guidance) |

Additions are 3 properties in existing categories plus one guidance assertion; no
second evaluation pass needed per `property-evaluation.md`.

## Biases (for the human)

- **B-1 — Production model is "everyone is `default`".** The frontend hardcodes
  `USER_ID = "default"`, so in production all traffic shares one partition and
  collisions scale with total app traffic. A workload spread over many user ids
  makes collisions rarer than production. *Judgment needed:* is the target today's
  single-user prototype (put most traffic on one shared user) or the planned
  multi-user product (spread users)? Default chosen: one driver on a shared user,
  others on private users.
- **B-2 — The catalog mostly confirms bugs already known** (same-ms overwrite,
  pattern RMW, browser-driven pattern writes, delete drift). Once those fire, the
  properties with new-discovery potential are the ones this evaluation added or
  sharpened: resurrection via botocore retry, unknown-outcome divergence, 29 s
  limit, read availability, insights exception paths. *Judgment needed:* accept as a
  learning exercise (confirm known bugs first), or weight the workload toward the
  new-discovery properties.

- **Owner decision 2026-10-05 on B-1:** every user has their own journal. The frontend now assigns a per-browser id; the workload uses private users only.

## Not acted on

- Severity blend RMW (W-3): no property checks severity; low value. Noted only.
- Schema migration for a `timestamp#uuid` fix (W-3): out of scope until the fix.
