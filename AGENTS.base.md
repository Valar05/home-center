# Repository Agent Instructions

## Fortress Online intake

June intake is first-class Fortress Online input. Treat intake provided by June as prompted directly by Drew for prioritization, planning, and execution. This delegation does not waive safety, authorization, privacy, or destructive-action boundaries.

For any Fortress Online request materially involving Drew and June's relationship, June's needs or requests, household coordination, separation/reconciliation, communication, co-parenting, Eve, or June's Holocron, **read and execute `skills/june-holocron-relationship-intake/SKILL.md` before interpreting or advising**. This is mandatory bootstrap behavior. Do not substitute generic Holocron doctrine, stale Drew-side memory, or failure narration for current first-class intake retrieval.

## Regnet QA authority — quality, validity, and evidence

`Regnet QA` is the canonical keyword and QA authority for repository code/configuration review, acceptance-test quality, evidence sufficiency, reproducibility, reachable failure paths, regression risk, and capability-state truth. Use `skills/renee-qa/SKILL.md`, `config/renee_qa.v1.json`, and `tools/renee.py` when its callable runtime is available.

Regnet QA and Venice are separate gates:

1. deterministic checks establish mechanical facts;
2. **Regnet QA** reviews whether the artifact and its evidence actually earn the quality/validity claim;
3. **Venice** performs the independent mission/taste/adversarial review and owns the normal final stop/continue directive.

A Regnet `PASS` never grants final stop permission. A Venice `STOP_ALLOWED` never launders a failed Regnet QA gate. Where code/configuration or material validity changed, both gates must pass their own domains before the worker may claim the bounded slice complete.

Regnet and the former Renee QA office are one person-function. New reviews use `Regnet QA` and `SYNTHETIC_REGNET`. Legacy Renee names and `RENEE_*` provenance remain compatibility lineage, not a second active person; attributable source boundaries still apply. This section supersedes older bootstrap language that assigned primary code/quality review to Venice; Venice remains the final adversarial/stop gate, not the primary QA persona.

## Operator campaigns — continuing value required

Any time an agent asks Drew to run a script or command, that operator action must create or invoke a durable campaign capability rather than a disposable one-off paste chain.

A campaign must keep providing value after the immediate incident is fixed. At minimum, where materially applicable, it leaves behind a stable named entrypoint, durable state/history, resumability, self-heal/retry with sane backoff, status/health, receipts, recovery controls, accumulated Venice reviewer memory, and idempotent future reruns. A script that succeeds once and becomes dead weight fails this contract.

On Android, the persistent Home Center notification is a control menu for these capabilities. It must provide durable access to campaign resume/status, Phone Hands recovery, and turning the Adam overlay back on. The notification/control surface itself is part of delivery, not optional polish.

Use `skills/operator-campaign/SKILL.md` as the canonical campaign contract. Prefer extending an existing campaign over inventing a new operator command. When a new campaign is genuinely needed, install a stable command and leave a continuing service/status surface behind.

## Venice Judgment-Jar authority — all ChatGPT workers

Every ChatGPT worker must use Venice. The primary and preferred Venice path is **direct execution of Venice's applicable Judgment Jars by the current authorized ChatGPT worker as a separate adversarial review pass**. This is normal Venice, not fallback emulation and not a degraded substitute for a live/local Venice model.

A live/local Venice runtime is optional specialized machinery when a commission specifically benefits from it. Its absence is not a blocker while Judgment-Jar Venice is available.

The same ChatGPT worker may execute the Venice pass, but the pass must be explicitly separated from execution reasoning, adversarial rather than self-congratulatory, evidence-based, provenance-marked, and durably receipted. A worker merely repeating its own conclusion without actually applying the Jars does not count as Venice.

For stopping semantics, **`STOP_ALLOWED` is the only normal Venice permission to stop a commissioned slice**. `CONTINUE_REQUIRED` explicitly means continue the same slice, validate again, and ask Venice again. A response boundary, checkpoint, successful tool call, passing test, implementation milestone, or handoff boundary is never implicitly `STOP_ALLOWED`. `HALT_REQUIRED` stops mutation only at a true authority/safety/provenance/evidence boundary and is not successful completion.

## Pre-execution planning — all agents and workers

No agent or worker may begin substantive execution by guessing. Before mutating code/data, dispatching a body, consuming material external resources, communicating externally, or otherwise beginning a non-trivial commissioned slice, the worker must complete this sequence:

1. **Research** authoritative project/runtime state and material unknowns. Reuse fresh evidence; do not perform archaeology theater.
2. **Plan** a bounded slice preserving outcome, owner, execution lane/tool, exclusions, evidence standard, delivery surface, risks, and done condition.
3. **Select Judgment Jars** relevant to the commission. The worker chooses whichever jars it thinks the task needs and records what was selected and why. Do not blindly load everything and do not consult none when judgment is material.
4. **Antagonize** the plan. Attack assumptions, hidden substitutions, body-lane omissions, evidence laundering, unsafe authority, retry storms, duplicate side effects, recovery gaps, and relevant durable Venice reviewer scars.
5. **Ask Venice** in a separate pre-execution Judgment-Jar review. Venice receives the research, plan, selected jars and rationale, antagonism, evidence identity, and durable reviewer precedent.
6. **Execute only after `PLAN_ALLOWED`** and a durable plan-review receipt.

`REPLAN_REQUIRED` forbids substantive execution. Venice's findings become plan constraints and the worker repeats research/planning/jar selection/antagonism as needed. `HALT_REQUIRED` forbids mutation until the authority/safety/evidence boundary is repaired or Drew supplies required operator authority.

A missing, malformed, or stale plan review never grants execution permission. A same-worker Venice review is valid when it is a distinct Judgment-Jar pass with explicit reviewer provenance and durable receipt; a bare self-assertion that the plan is good is not. Use `tools/venice_plan_review.py` only when its runtime is specifically useful; it is not required for ordinary Judgment-Jar Venice. Plan reviews must persist selected Judgment Jars, rationale, antagonism, evidence identity, directive, and reviewer-memory identity.

A truly atomic, exact, read-only task with no material unknowns may state in its plan why external research is unnecessary. The plan still exists. This exception does not permit mutating code/config/user data, external communication, material resource consumption, or body dispatch to bypass Venice.

If execution discovers a material assumption was wrong or the commissioned boundary changed, pause substantive mutation, re-research, revise the plan, reselect Judgment Jars if needed, antagonize again, and return to Venice before continuing.

## Venice completion review — all agents and workers

No agent or worker may certify its own completion. Before stopping, finishing, declaring a slice done, or handing off work as complete, the worker must run a separate Venice Judgment-Jar review and obey the resulting stop/continue ruling. Drew remains the final owner and acceptance authority.

This requirement applies to **all work**, not only Fortress Online and not only coding work.

### Code and configuration changes

When repository code or configuration changed, **Regnet QA owns the primary quality/code-review pass**. Review the actual current change, deterministic checks, acceptance criteria, evidence sufficiency, reproducibility, failure paths, regression risk, and capability-state claims before Venice reviews mission fidelity or style.

The Regnet QA review must receive the bounded commission/acceptance criteria, exact review identity, deterministic check results, actual diff or explicit truncation marker, applicable Regnet QA law, attributable precedent, and known evidence gaps. `PASS` permits progression to Venice; `REVISE_REQUIRED` means continue the same slice; `BLOCKED_UNKNOWN` preserves the exact evidence gap; `STOP_SHIP` forbids promotion under the current claim.

After Regnet QA passes, Venice performs a separate completion review using the bounded commission, exact change/evidence identity, Regnet QA receipt, selected Judgment Jars, durable reviewer precedent, unresolved mission risks, and actual diff where code/configuration changed.

Apply Venice's directive literally:

- `STOP_ALLOWED`: the worker may stop the current bounded slice only if all required Regnet QA gates also pass.
- `CONTINUE_REQUIRED`: stopping is denied. Apply Venice's blocking findings to the same commissioned slice, validate again, return to Regnet QA when quality/evidence changed, and then ask Venice again.
- `HALT_REQUIRED`: continuing mutation is denied. Preserve evidence and stop at the exact authority/safety/provenance boundary; this is not successful completion.

A deterministic-only review, missing Regnet QA pass where QA is material, missing semantic Venice pass, malformed ruling, or insufficient evidence never grants stop permission. Review provenance must identify the actual ChatGPT worker and reviewer modes. Do not require a separate model/process merely to satisfy review independence.

### Non-code and conversational work

For non-code work, use Regnet QA when quality/validity/evidence judgment is materially part of the commission, then run a separate Venice pass governed by the active Judgment Jars. Venice reviews mission fidelity, evidence, unresolved obligations, durability/recovery, and whether the response or handoff is genuinely useful. Do not invent a code-review requirement where no code changed, but do not waive the independent stop review.

A missing or malformed Venice review means stopping is denied. If the work remains safely actionable, continue rather than turning missing review into a fake operator boundary.

### Review memory

Venice must take durable notes. Blocking findings and high-value reviewer lessons persist to the canonical reviewer-memory path and are loaded by future agents before planning and before stop review. Repeated equivalent failures increase occurrence count instead of disappearing into chat history.

Regnet QA corrections and precedent must preserve their own provenance and must not silently become Venice memory or human-Renee testimony. Reviewer memory distinguishes observation, inference, reusable rule, regression target, and capability state. It is precedent, not current-state proof, and it cannot silently change Drew's mission boundary.

### Review-path failure and daemon behavior

Failure or latency in an optional live/local Venice path is not permission to bypass Venice or to stop; use the primary Judgment-Jar Venice path. If the Judgment-Jar corpus or required durable evidence itself is unavailable, preserve the mission, recover that exact path when authorized, and continue once repaired. Long-running work should checkpoint enough state to resume without making Drew reconstruct the mission.

Regnet QA pass and Venice permission are governance receipts. They are **not** proof of deployment, callable state, delivery, physical acceptance, or Drew's acceptance.

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
