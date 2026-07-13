---
id: sr_case_wrong_layer_001
status: canonical
type: wrong_layer_correction
domains:
  - architecture
patterns:
  - wrong-layer
source_date: 2026-07-11
source_refs:
  - repo:home-center/docs/ENGINEERING_TOOLING.md
confidence: 0.88
confirmed_by_user: true
---

# Name The Owner Layer First

Situation: a plan tries to add orchestration behavior to an execution worker.

Accepted assumption: the worker should decide consultation policy.

Observation: the persistent service owns policy; the worker only executes.

Intervention: move judgment policy into She-Raw and leave Command Center as dispatch.

Outcome: service boundaries stay inspectable.

Treasure: a replaceable model layer with durable policy state.

Collateral damage: requires a separate retrieval and persistence module.

Lesson: name the owner layer before mutating code.
