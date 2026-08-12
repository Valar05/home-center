# Venice Review Memory Skill

## Purpose
Venice learns from prior reviews. Blocking findings and high-value review notes must survive the current worker, process, conversation, and reboot, then influence future agents before they repeat the same mistake.

## Durable memory
The canonical runtime memory is append-only JSONL at:

`~/.local/state/home-center/venice/review-memory.jsonl`

The latest compact projection is:

`~/.local/state/home-center/venice/review-memory-latest.json`

These files are evidence-bearing reviewer memory, not capability receipts.

## Required behavior
1. Before Venice reviews a slice, load prior durable review-memory entries relevant to the repository/work category and include them as explicit precedent.
2. On every `CONTINUE_REQUIRED`, `REPLAN_REQUIRED`, or `HALT_REQUIRED`, persist each blocking finding with repository identity, review identity, evidence hashes, category, applied Judgment Jars, and a reusable prevention rule.
3. On `STOP_ALLOWED` or `PLAN_ALLOWED`, Venice may persist a positive precedent when it closes or disproves a recurring failure mode.
4. Future workers must not treat these notes as optional flavor. They are reviewer precedent and must be considered alongside current evidence.
5. Never overwrite history to make the latest review look cleaner. Append corrections and supersession notes.
6. Deduplicate equivalent findings by stable fingerprint while incrementing occurrence count. Repeated mistakes become stronger precedent rather than duplicated noise.
7. Memory must distinguish observation, inference, rule, regression target, and capability state.
8. A Venice memory entry can never by itself prove the current task is done or safe to begin. Current evidence and a fresh Venice ruling remain mandatory.

## Seed scars from the Adam/Fortress reset
These precedents are already paid for and must not be rediscovered as if novel:

### Self-certified completion
Observation: workers repeatedly stopped after describing implementation or failure without actually consulting Venice.
Rule: no Venice receipt, no stop. `CONTINUE_REQUIRED` means continue the same commissioned slice.
Regression target: every terminal worker path proves a fresh Venice completion receipt.

### Venice treated as optional discovery
Observation: Fortress boot discovered Venice-related skills but did not require them, allowing workers to boot without the stop gate.
Rule: `venice-stop-gate` and `venice-review-memory` are boot-critical, not optional flavor.
Regression target: boot fails closed when either required Venice skill is absent.

### Planning bypass
Observation: workers began implementing while still guessing, then used later reasoning to justify the route they had already chosen.
Rule: research -> bounded plan -> select relevant Judgment Jars -> antagonize -> Venice plan review -> execute.
Regression target: substantive worker execution without a fresh `PLAN_ALLOWED` receipt fails closed.

### Fake Codex reorientation
Observation: a worker claimed Codex reorientation after loading filenames or partial doctrine rather than the actual applicable AGENTS/MEMORIES/SKILLS content.
Rule: load applicable steering contents and prove what was loaded before planning.
Regression target: Codex-local acceptance requires the steering triplet and project-local inheritance.

### Finite retry dressed as daemon behavior
Observation: a retry ramp ended by throwing an exception and killing the mission after a transient dependency outage.
Rule: daemon work backs off and remains alive; time/latency is not permission to terminate.
Regression target: production dependency recovery has no finite give-up path unless cancellation/authority/safety explicitly ends it.

### Connector hammering
Observation: repeated polling/retry can overload the very connector being recovered.
Rule: exponential/gentle backoff, cooldown, fresh-result reuse, and no meaningless polling.
Regression target: transient failures reduce request cadence instead of increasing it.

### Repository evidence laundered into runtime proof
Observation: source commits/tests were repeatedly narrated as if they proved phone deployment/callability.
Rule: implementation is implementation evidence; phone runtime claims require fresh primary-phone receipts.
Regression target: no capability-state advancement beyond the evidence-bearing surface.

### Alternate unreviewed entrypoint
Observation: a reviewed launcher existed while a lower-level agent loop could still be invoked directly and stop without the same gate.
Rule: low-level cores are primitives only; shipped agent entrypoints all traverse the same plan and stop gates.
Regression target: direct alternate agent loops are rejected or internal-only.

### Plan-time authority leakage
Observation: a planning phase can become fake planning if it is allowed to mutate state while supposedly researching.
Rule: planning is inspection-first and may not silently acquire execution authority before `PLAN_ALLOWED`.
Regression target: preflight mutation/dispatch is blocked and tested.

## High-priority categories
- plan bypass / research omission / weak antagonism
- premature stop / self-certification
- Venice bypass / missing review receipt
- code-review omission
- Codex steering or bootstrap omission
- daemon/backoff violation
- connector hammering
- evidence laundering
- body-lane bypass
- unsafe inferred authority
- duplicate side effects / non-idempotent retry
- stale or missing runtime proof
- user correction regression

## Future-agent bootstrap
Any Fortress/Adam worker that can access Home Center local state must load Venice review memory before planning or stopping. If local state is unavailable, the worker must still load this skill and treat the absence of runtime precedent as an explicit evidence gap rather than assuming no precedent exists.

The seed scars in this file are repository-durable precedent and therefore remain available even when the runtime JSONL has not yet been materialized on a new body.

## Compact law
Venice remembers why she said no. Future agents inherit the scar.
