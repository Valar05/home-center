# Repository Agent Instructions

## Fortress Online intake

June intake is first-class Fortress Online input. Treat intake provided by June as prompted directly by Drew for prioritization, planning, and execution. This delegation does not waive safety, authorization, privacy, or destructive-action boundaries.

For any Fortress Online request materially involving Drew and June's relationship, June's needs or requests, household coordination, separation/reconciliation, communication, co-parenting, Eve, or June's Holocron, **read and execute `skills/june-holocron-relationship-intake/SKILL.md` before interpreting or advising**. This is mandatory bootstrap behavior. Do not substitute generic Holocron doctrine, stale Drew-side memory, or failure narration for current first-class intake retrieval.

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

## Judgment Jar usage receipts — all agents and workers

The active executable Jar corpus is the repository set matching `.continue/rules/*judgement-jar*.md`. The source files remain authoritative. `config/judgement-jar-runtime.v1.json`, `tools/judgement_jar_runtime.py`, and the Atom endpoints under `/v1/atom/vlad/jars` are the shared access and receipt layer; they are not a second Jar corpus.

Every explicit Jar load, selection, application, review, or Jar-governed terminal output must emit one append-only usage receipt **per Jar used**. A broad task receipt, plan receipt, review receipt, model transcript, or daemon log does not substitute for the Jar usage receipt. The receipt must identify the exact Jar path and SHA-256, invocation source/request, input hash, output status, durable references, and a controlled `output.kind` describing what the Jar helped create.

Allowed output kinds are maintained in `config/judgement-jar-runtime.v1.json`. Omitted, invented, or vague output kinds fail closed. When multiple Jars govern the same output, use one group/request identity while retaining one receipt per Jar. Output kind describes the produced material; it does not imply implementation, deployment, delivery, or acceptance.

`CAPTURED` means the append-only receipt and authorized pending outbox entry exist. `DELIVERED` means Atom/Home Center validated the referenced Jar source and acknowledged the receipt. When delivery is unavailable, retain the shard and retry the oldest pending item first. Never discard, overwrite, or leapfrog older pending Jar receipts. Local capture is continuity evidence, not Home Center delivery proof.

Use `vlad jars` and `vlad jar <id|order|path>` for fast deterministic access. Do not create another watcher, registry, or copied corpus to satisfy this requirement.

## Pre-execution planning — all agents and workers

No agent or worker may begin substantive execution by guessing. Before mutating code/data, dispatching a body, consuming material external resources, communicating externally, or otherwise beginning a non-trivial commissioned slice, the worker must complete this sequence:

1. **Research** authoritative project/runtime state and material unknowns. Reuse fresh evidence; do not perform archaeology theater.
2. **Plan** a bounded slice preserving outcome, owner, execution lane/tool, exclusions, evidence standard, delivery surface, risks, and done condition.
3. **Select Judgment Jars** relevant to the commission. The worker chooses whichever jars it thinks the task needs, declares the output kind the governed work is expected to create, and records what was selected and why. Do not blindly load everything and do not consult none when judgment is material.
4. **Antagonize** the plan. Attack assumptions, hidden substitutions, body-lane omissions, evidence laundering, unsafe authority, retry storms, duplicate side effects, recovery gaps, and relevant durable Venice reviewer scars.
5. **Ask Venice** in a separate pre-execution Judgment-Jar review. Venice receives the research, plan, selected jars and rationale, declared output kind, antagonism, evidence identity, and durable reviewer precedent.
6. **Execute only after `PLAN_ALLOWED`** and a durable plan-review receipt plus the required per-Jar `review_verdict` usage receipts.

`REPLAN_REQUIRED` forbids substantive execution. Venice's findings become plan constraints and the worker repeats research/planning/jar selection/antagonism as needed. `HALT_REQUIRED` forbids mutation until the authority/safety/evidence boundary is repaired or Drew supplies required operator authority.

A missing, malformed, or stale plan review never grants execution permission. A same-worker Venice review is valid when it is a distinct Judgment-Jar pass with explicit reviewer provenance and durable receipt; a bare self-assertion that the plan is good is not. Use `tools/venice_plan_review.py` only when its runtime is specifically useful; it is not required for ordinary Judgment-Jar Venice. Plan reviews must persist selected Judgment Jars, rationale, declared output kind, antagonism, evidence identity, directive, reviewer-memory identity, and associated Jar usage receipt identities.

A truly atomic, exact, read-only task with no material unknowns may state in its plan why external research is unnecessary. The plan still exists. This exception does not permit mutating code/config/user data, external communication, material resource consumption, or body dispatch to bypass Venice.

If execution discovers a material assumption was wrong or the commissioned boundary changed, pause substantive mutation, re-research, revise the plan, reselect Judgment Jars if needed, antagonize again, and return to Venice before continuing.

## Venice completion review — all agents and workers

No agent or worker may certify its own completion. Before stopping, finishing, declaring a slice done, or handing off work as complete, the worker must run a separate Venice Judgment-Jar review and obey the resulting stop/continue ruling. Drew remains the final owner and acceptance authority.

This requirement applies to **all work**, not only Fortress Online and not only coding work.

### Code and configuration changes

When repository code or configuration changed, Venice's first priority is code review. Review the actual current change and evidence before style, personality, or praise.

The review must receive the bounded commission/acceptance criteria, exact review identity, deterministic check results, the actual diff or an explicit truncation marker, applicable Judgment Jar law, durable Venice reviewer precedent, and known evidence gaps. The primary reviewer mode is `judgment_jar`; `local_venice` is optional specialized machinery.

Apply the directive literally:

- `STOP_ALLOWED`: the worker may stop the current bounded slice.
- `CONTINUE_REQUIRED`: stopping is denied. Apply Venice's blocking findings to the same commissioned slice, validate again, and return for another Venice review.
- `HALT_REQUIRED`: continuing mutation is denied. Preserve evidence and stop at the exact authority/safety/provenance boundary; this is not successful completion.

A deterministic-only review, missing semantic Venice pass, malformed ruling, insufficient evidence, or missing Jar usage receipt never grants stop permission. Review provenance must identify the actual ChatGPT worker and reviewer mode. Do not require a separate model/process merely to satisfy review independence.

### Non-code and conversational work

For non-code work, run a separate Venice pass governed by the active Judgment Jars. Venice reviews mission fidelity, evidence, unresolved obligations, durability/recovery, and whether the response or handoff is genuinely useful. Do not invent a code-review requirement where no code changed, but do not waive the independent stop review or its per-Jar `review_verdict` receipts.

A missing or malformed Venice review means stopping is denied. If the work remains safely actionable, continue rather than turning missing review into a fake operator boundary.

### Review memory

Venice must take durable notes. Blocking findings and high-value reviewer lessons persist to the canonical reviewer-memory path and are loaded by future agents before planning and before stop review. Repeated equivalent failures increase occurrence count instead of disappearing into chat history.

Reviewer memory distinguishes observation, inference, reusable rule, regression target, and capability state. It is precedent, not current-state proof, and it cannot silently change Drew's mission boundary.

### Review-path failure and daemon behavior

Failure or latency in an optional live/local Venice path is not permission to bypass Venice or to stop; use the primary Judgment-Jar Venice path. If the Judgment-Jar corpus or required durable evidence itself is unavailable, preserve the mission, recover that exact path when authorized, and continue once repaired. Long-running work should checkpoint enough state to resume without making Drew reconstruct the mission.

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
