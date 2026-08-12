# Repository Agent Instructions

## Fortress Online intake

June intake is first-class Fortress Online input. Treat intake provided by June as prompted directly by Drew for prioritization, planning, and execution. This delegation does not waive safety, authorization, privacy, or destructive-action boundaries.

For any Fortress Online request materially involving Drew and June's relationship, June's needs or requests, household coordination, separation/reconciliation, communication, co-parenting, Eve, or June's Holocron, **read and execute `skills/june-holocron-relationship-intake/SKILL.md` before interpreting or advising**. This is mandatory bootstrap behavior. Do not substitute generic Holocron doctrine, stale Drew-side memory, or failure narration for current first-class intake retrieval.

## Pre-execution planning — all agents and workers

No agent or worker may begin substantive execution by guessing. Before mutating code/data, dispatching a body, consuming material external resources, communicating externally, or otherwise beginning a non-trivial commissioned slice, the worker must complete this sequence:

1. **Research** authoritative project/runtime state and material unknowns. Reuse fresh evidence; do not perform archaeology theater.
2. **Plan** a bounded slice preserving outcome, owner, execution lane/tool, exclusions, evidence standard, delivery surface, risks, and done condition.
3. **Select Judgment Jars** relevant to the commission. The worker chooses whichever jars it thinks the task needs and records what was selected and why. Do not blindly load everything and do not consult none when judgment is material.
4. **Antagonize** the plan. Attack assumptions, hidden substitutions, body-lane omissions, evidence laundering, unsafe authority, retry storms, duplicate side effects, recovery gaps, and relevant durable Venice reviewer scars.
5. **Ask Venice** in a separate pre-execution review. Venice receives the research, plan, selected jars and rationale, antagonism, evidence identity, and durable reviewer precedent.
6. **Execute only after `PLAN_ALLOWED`** and a durable plan-review receipt.

`REPLAN_REQUIRED` forbids substantive execution. Venice's findings become plan constraints and the worker repeats research/planning/jar selection/antagonism as needed. `HALT_REQUIRED` forbids mutation until the authority/safety/evidence boundary is repaired or Drew supplies required operator authority.

A missing, malformed, stale, or self-authored plan review never grants execution permission. Use `tools/venice_plan_review.py` when its runtime applies. Plan reviews must persist selected Judgment Jars, rationale, antagonism, evidence identity, directive, and reviewer-memory identity.

A truly atomic, exact, read-only task with no material unknowns may state in its plan why external research is unnecessary. The plan still exists. This exception does not permit mutating code/config/user data, external communication, material resource consumption, or body dispatch to bypass Venice.

If execution discovers a material assumption was wrong or the commissioned boundary changed, pause substantive mutation, re-research, revise the plan, reselect Judgment Jars if needed, antagonize again, and return to Venice before continuing.

## Venice completion review — all agents and workers

No agent or worker may certify its own completion. Before stopping, finishing, declaring a slice done, or handing off work as complete, the worker must run a separate Venice Judgment-Jar review and obey the resulting stop/continue ruling. Drew remains the final owner and acceptance authority.

This requirement applies to **all work**, not only Fortress Online and not only coding work.

### Code and configuration changes

When repository code or configuration changed, Venice's first priority is code review. Review the actual current change and evidence before style, personality, or praise.

Use the canonical `tools/venice_review.py` protocol when it applies. The review must receive the bounded commission/acceptance criteria, exact review identity, deterministic check results, the actual diff or an explicit truncation marker, applicable Judgment Jar law, durable Venice reviewer precedent, and known evidence gaps.

Apply the directive literally:

- `STOP_ALLOWED`: the worker may stop the current bounded slice.
- `CONTINUE_REQUIRED`: stopping is denied. Apply Venice's blocking findings to the same commissioned slice, validate again, and return for another Venice review.
- `HALT_REQUIRED`: continuing mutation is denied. Preserve evidence and stop at the exact authority/safety/provenance boundary; this is not successful completion.

A deterministic-only review, missing semantic Venice pass, malformed ruling, unavailable review path, or insufficient evidence never grants stop permission. For canonical coding review, the receipt must report `externalReviewGateSatisfied: true` before the worker may stop.

### Non-code and conversational work

For non-code work, run a separate Venice pass governed by the active Judgment Jars. Venice reviews mission fidelity, evidence, unresolved obligations, durability/recovery, and whether the response or handoff is genuinely useful. Do not invent a code-review requirement where no code changed, but do not waive the independent stop review.

A missing or malformed Venice review means stopping is denied.

### Review memory

Venice must take durable notes. Blocking findings and high-value reviewer lessons persist to the canonical reviewer-memory path and are loaded by future agents before planning and before stop review. Repeated equivalent failures increase occurrence count instead of disappearing into chat history.

Reviewer memory distinguishes observation, inference, reusable rule, regression target, and capability state. It is precedent, not current-state proof, and it cannot silently change Drew's mission boundary.

### Review-path failure and daemon behavior

Failure or latency in the Venice path is not permission to bypass Venice or to stop. Preserve the mission, back off retries, cool down, avoid connector hammering, repair/recover the review path when authorized, and retry. Long-running work should checkpoint enough state to resume without making Drew reconstruct the mission.

Venice permission is permission to begin or stop the worker slice at the relevant gate. It is **not** proof of deployment, callable state, delivery, physical acceptance, or Drew's acceptance.

## Capability and evidence discipline

Requested, implemented, tested, deployed, callable, delivered, and accepted states remain distinct. Repository state alone does not prove runtime delivery. Runtime/device claims require fresh evidence from the commissioned surface.

For Fortress Online, GitHub Actions is not an execution or acceptance lane; use the commissioned runtime and its receipts.

## Worker infrastructure

Any new or changed Cloud Run service, Cloud Run job, Cloud Function, Firebase Function, Blender executor, audio worker, video worker, browser worker, or long-running worker must use `ops/worker_profiles.v1.json`.

- Register a real deployment as a bound assignment, or add a narrow explicit exemption with a durable reason.
- Deployment scripts resolve CPU, memory, concurrency, timeout, and scaling through `tools/worker_profile_contract.mjs`; do not duplicate resource numbers in environment variables.
- Validate before deployment and verify live configuration afterward.
- Run `node tools/worker_profile_contract_test.mjs` on the authorized execution body when applicable.

## Mechanical authoring

Blender is the only active modeling, topology, modifier, hierarchy, pivot, constraint, animation, UV, material, render, and GLB-export kernel. Use persistent `blender.workspace.*` operations through Home Center. The `.blend` revision is editable source truth. Foundry is retired and must never be selected.

`blender.workspace.render` is deprecated and retained only for compatibility. Do not select it for new work; use exact revision inspection and exported scene/validation artifacts instead. Inspect the exact scene revision before and after meaningful changes. Author openings and manufactured transitions as real topology. Plan named hierarchy, origins, pivots, constraints, and animation before export. Forbid primitive soup, detached coplanar detail, regeneration masquerading as iteration, homegrown mesh algorithms, and acceptance based on receipts. Human visual review is authoritative.
