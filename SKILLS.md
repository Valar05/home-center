# Home Center — Codex Local Skills

Status: active reusable procedures for the phone Adam/Codex worker.
Owner: Drew Clarke.

These are project-local procedures distilled from the researched GodotProjects Codex workspace bootstrap and current Home Center doctrine. They are not an agent framework and do not replace repo-native tools.

## 1. Workspace Project Bootstrap

Trigger: beginning work from the phone inside `/storage/emulated/0/Documents/GodotProjects`.

Procedure:

1. Identify the commissioned project/repository.
2. Read the applicable local `AGENTS.md`, `MEMORIES.md`, `SKILLS.md`, `PROJECT_ORIENTATION.md`, and Motivated Mode contract when present.
3. Inspect repository status and the narrow files relevant to the commission.
4. Discover project-native validation before editing.
5. Preserve archive/generated/imported boundaries.

Done: the worker can state the project, governing local docs, current repo state, and intended validation without guessing.

## 2. Bounded Codex Work Loop

Trigger: any natural-language Adam execution request.

Procedure:

`inspect -> one typed action -> observe -> update plan -> verify -> repeat`

Rules:

- one action at a time;
- evidence before confidence;
- smallest coherent edit;
- do not silently substitute tools or architecture;
- never call source-only implementation deployed or accepted;
- prose cannot authorize execution.

Done: commissioned outcome is evidenced or a real boundary is identified.

## 3. Shared-Storage Write Operator

Trigger: Android shared storage, `.codex`, or another path likely to reject ordinary patch mechanics.

Procedure:

1. Classify the path and authority.
2. Choose a write method known to work for that surface.
3. Perform the smallest write.
4. Read back/validate immediately.
5. If a method fails, inspect current state and change method; do not hammer the same rejected operation.

Done: bytes and intended semantics are verified on the target surface.

## 4. Project-Native Verification

Trigger: after a code/config/data mutation.

Procedure:

1. Run the narrowest relevant deterministic check.
2. Run broader project-native smoke/build validation when warranted.
3. Inspect `git diff --check` and the actual diff.
4. If the claim concerns a phone/device/deployment, require fresh runtime evidence from that surface.

Done: evidence supports exactly the capability state being claimed.

## 5. Agent Handoff And Session Memory

Trigger: substantial work, interruption, daemon checkpoint, or handoff.

Procedure:

Record:

- exact commission;
- project/workspace;
- task starting commit;
- changed paths/current diff state;
- tests/evidence;
- unresolved findings;
- next bounded action.

Do not rewrite history into a flattering summary. Preserve failures and recovery state.

Done: another worker/process can resume without Drew reconstructing the mission.

## 6. Venice Completion / Code Review

Trigger: every worker proposal to `respond`, `finish`, declare done, or hand off a completed slice.

Procedure:

1. Collect the full task delta from pinned task base through current HEAD/worktree.
2. For code/config changes, perform code review first: mission fidelity, regressions, correctness, failure handling, verification, runtime truth, durability, simplicity.
3. Apply active Judgment Jars.
4. Return canonical `STOP_ALLOWED`, `CONTINUE_REQUIRED`, or `HALT_REQUIRED` semantics.
5. On `CONTINUE_REQUIRED`, feed critique back into the same work loop and continue.

Done: Venice explicitly permits stopping. Drew remains final acceptance authority.

## 7. Daemon Backoff And Continuation

Trigger: slow operations, connector latency, queueing, rate limits, temporary network/model failure, or long-running work.

Procedure:

1. Preserve pending action and mission state.
2. Back off roughly 1s, 2s, 4s, 8s, 15s, 30s, then use a gentle cadence.
3. Never busy-loop or spam status probes.
4. Checkpoint long work durably.
5. Resume the original commissioned outcome after transport recovers.

Done: the requested outcome is verified and Venice permits stopping, or a genuine authority/safety boundary is reached.

## 8. Durable Overlay Delivery

Trigger: Adam finishes work initiated from the Android overlay.

Procedure:

1. Execute the task once.
2. Persist the result before delivery.
3. Retry delivery with backoff if the overlay is temporarily unavailable.
4. Advance the request acknowledgement only after delivery succeeds.
5. If pending delivery state is corrupt, fail closed and quarantine it; never blindly rerun a potentially side-effecting task.

Done: response delivery is acknowledged exactly once, or durable halted state preserves the unresolved delivery problem.
