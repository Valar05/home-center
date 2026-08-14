# Fortress Serialized Execution Doctrine

Authority: Drew Clarke
Status: ACTIVE doctrine candidate on zero-token continuation branch
Incident source: `docs/fortress-incidents/2026-08-13-serialized-work-token-collapse.md`

## Prime directive
Bring home the smallest usable treasure first, then continue. Preserve the whole commission durably; do not implement the whole commission at once.

## Default loop
`retrieve -> choose dependency-unlocking MVP -> execute -> canary -> persist receipt -> reduce next action -> continue`

The loop is mandatory whether or not the operator says `Fortress online`.

## Lean slice rule
A slice must be the smallest change that either:

- becomes directly usable by the operator;
- removes the blocker on the next usable capability; or
- creates required evidence for a capability claim.

If a proposed slice mostly adds framework, abstraction, prose, or generalized machinery while a named user-facing gate remains broken, reject or shrink it.

## Serialization rule
Only one dependency-critical slice owns the foreground acceptance gate. Other ideas are captured durably as backlog/state, not expanded into concurrent mega-implementation. Parallel work is allowed only when it cannot obscure the foreground gate, consume the operator as transport, or make receipts ambiguous.

## Continuation rule
Response completion is not mission completion. `CONTINUE_REQUIRED` means continue through the next authorized action. Before context/token/runtime loss can strand the campaign, persist a restart record containing:

- objective;
- cumulative constraints and exclusions;
- authorized lane/tool;
- requested / implemented / tested / deployed / callable / delivered / accepted states;
- last persistent receipts;
- blocker;
- exact deterministic next action.

A restarted worker must retrieve this state and resume from evidence. It must not ask the operator to reconstruct it from memory.

## Token-drought rule
Hosted inference exhaustion is an execution-mode transition, not a stop condition. Preserve the exact campaign and decay toward authorized local/deterministic execution. Never silently spend, silently change lane, or turn the operator into command transport.

## Promise firewall
Never say a capability exists because it is planned, documented, source-present, or theoretically reachable. Report each capability state separately. A future-tense promise is not progress evidence.

## Canary ladder
For every foreground gate, test from cheapest to most real, and stop calling it green at the first layer that has not passed:

1. static/schema/source invariant;
2. deterministic unit/contract test;
3. historical incident replay;
4. clean-process restart/recovery test;
5. persistent-source readback at exact commit;
6. deployed/runtime liveness;
7. real operator-path canary;
8. repeat canary sufficient to expose persistence/recovery defects.

A lower rung never substitutes for a higher commissioned evidence rung.

## Chromium Throne first gate
Until accepted otherwise, Chromium Throne is the foreground delivery gate for the next session. The minimum usable proof is:

- installer contract green at the exact source commit;
- install receipt persisted;
- dedicated browser launches;
- authenticated ChatGPT Pro-reasoning worker is persistently identified;
- one real task crosses the Throne and returns a durable receipt;
- continuation survives one checkpoint/response boundary without a fresh worker unless explicit recovery requires rotation;
- two real interface-evolution generations complete with persistent receipts;
- no Instant default, no hidden parallel worker farm, no narrated continuation counted as execution.

Only after this proof may downstream work replace Chromium Throne as the foreground gate.

## Hunger
Assume the model is forgetful, lazy, context-starved, wrong, or absent. Durable mechanics must still recover state, enforce boundaries, and identify the next action. The human is not synchronization middleware.

## Hyperbolic
Assume omissions compound, receipts reorder, branches stale, shells freeze, connectors fail, inference vanishes, and workers confidently guess. Make every transition explicit, typed where possible, persistent, replayable, and fail-closed against false completion.

## Definition of done
Done means the commissioned artifact exists on the commissioned persistent surface and the commissioned evidence lane proves it. Everything else is an intermediate state with a next action.
