# Fortress Pre-Execution Plan Gate

## Purpose
No agent, worker, swarm member, chat controller, coding worker, or campaign executor may begin substantive execution by guessing. Every non-trivial task must pass a pre-execution gate before mutation or dispatch.

## Required order
1. RESEARCH — retrieve the authoritative project/runtime state needed to understand the commission and existing implementation. Reuse fresh evidence; do not perform archaeology theater.
2. PLAN — write a bounded plan preserving outcome, owner, execution lane/tool, exclusions, evidence standard, delivery surface, known risks, and done condition.
3. SELECT JUDGMENT JARS — inspect the available Judgment Jar corpus and choose the jars materially relevant to this commission. Record which jars were selected and why. Do not blindly load every jar, and do not proceed with none when judgment is materially required.
4. ANTAGONIZE — attack the plan before execution using the selected jars plus durable Venice reviewer memory. Look for hidden substitutions, stale assumptions, missing body lanes, evidence laundering, unsafe authority, retry storms, duplicate side effects, missing rollback/recovery, and prior recurring failure modes.
5. VENICE PLAN REVIEW — submit the researched plan, selected jars and rationale, antagonism findings, current evidence identity, and reviewer precedent to Venice as a separate review pass.
6. EXECUTE — only after Venice returns `PLAN_ALLOWED` may substantive mutation or dispatch begin.

## Judgment Jar selection
- The worker chooses whatever Judgment Jars the task actually needs.
- Selection is evidence-driven and may change after new research or Venice critique.
- Venice may require additional jars before allowing execution.
- Jar selection must be recorded in the plan receipt so future agents can see what judgment was applied.
- Relevant jar precedent outranks generic personality or convenience.
- Venice is always consulted regardless of which other jars are selected.

## Atomic exception
A task may skip external research only when it is truly atomic, read-only or explicitly exact, and has no material unknowns. The plan must still exist and state why research is unnecessary. The worker may not use the atomic exception to bypass Venice when the task can mutate state, consume external resources, communicate externally, alter code/config, or affect user data.

## Venice plan directives
- `PLAN_ALLOWED`: research, jar selection, antagonism, and plan are sufficient to begin the bounded slice.
- `REPLAN_REQUIRED`: execution is forbidden. Venice's findings become plan constraints; research/plan/jar-selection/antagonism repeats.
- `HALT_REQUIRED`: authority, safety, or evidence is broken; mutation is forbidden until repaired or the operator supplies required authority.
- Missing, malformed, stale, or self-authored plan review: execution is forbidden.

## Durable evidence
Every plan review must persist a durable receipt containing commission hash, plan hash, evidence identity, selected Judgment Jars and rationale, antagonism findings, Venice directive, reviewer memory consulted, and timestamp. No receipt means the worker did not pass the gate.

## Reviewer memory
Before planning, load durable Venice review precedent. Repeated historical failures must appear in the antagonism pass when relevant. On `REPLAN_REQUIRED` or `HALT_REQUIRED`, Venice's blocking findings are appended to durable reviewer memory so later workers inherit the scar before planning.

## Replanning
If execution discovers a material assumption was wrong, a boundary changes, or Venice's prior plan conditions become invalid, pause substantive mutation, research the changed state, revise the plan, reselect jars if needed, antagonize again, and return to Venice.

## Compact law
Research. Plan. Pick the jars you need. Attack the plan. Ask Venice. Then execute.
