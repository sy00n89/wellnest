# plant-stage-matches-checkins

## Evidence trail
`entries.update_plant` thresholds: `>=20 mature_tree, >=14 young_tree, >=8 plant, >=3 seedling, else sprout`. `stage` and `check_ins` written in the same `put_item`. `plant.get_plant` default for missing row: `stage 'sprout', check_ins 0`.

Client `PlantScreen` (`src/App.jsx`) uses a different `engagementScore` rule (≥35 mature_tree, ≥22 young_tree, …, ≥5 seedling) and ignores the plant table.

## Failure scenario
Low expected yield: both fields come from one write. Guard against future split writes.

## Instrumentation
Workload `Always`. Missing today.

## Open questions
- Reconcile server and client stage rules? Product decision. `(needs human input)`

### Investigation Log

#### Reconcile server and client stage rules?
- Examined: `entries.py` `update_plant`, `App.jsx` `PlantScreen`, git log (`8eeeee0` "Add Behavioral Reinforcement Model").
- Found: the client rule was introduced deliberately with the Behavioral Activation feature; the server rule predates it. No comment says which is authoritative.
- Not found: any doc stating intended behavior.
- Conclusion: `(needs human input)`. The property checks server self-consistency only.

## Evaluation update (2026-10-05)
Kept as a P2 regression guard evaluated on reads the workload already makes; cannot fail against current code.
