# Heartbeat Skill Lights

## Purpose
Make every swarm heartbeat visibly expose which repository skills materially changed the work. A skill light is semantic telemetry, not decoration. If a skill did not contribute a concrete constraint, action, review, recovery, or exact boundary in the current pulse, it stays dark.

## Auto-selection
At the start of each heartbeat, discover applicable `SKILL.md` files and active judgment doctrines from the commissioned project. Do not use a fixed tiny favorites list. Select by current evidence and mission fit.

A light claimed as a **repository skill** must resolve to an actual repository skill path. A named law, jar, persona, or doctrine that has no matching `SKILL.md` may still be materially active, but its provenance must say `doctrine`/`jar` rather than pretending it is a repository skill. Discovery truth is part of the light.

Every selected light records:

- stable skill id/path or explicit doctrine/jar provenance;
- human label;
- activation reason;
- state: `active`, `blocked`, `fault`, or `recovered`;
- concrete consequence produced in this heartbeat;
- evidence or boundary that supports that consequence.

`active` and `recovered` require an actual state change in this heartbeat. `blocked` and `fault` may remain visible without progress only when they expose a current exact boundary. Empty consequences are dark.

## Typed source contract
A future renderer must receive explicit provenance and evidence rather than reverse-engineer meaning from labels or prose. The canonical source record is:

- `id`: stable lowercase identity used for deterministic dedupe;
- `label`: human-facing name;
- `provenanceKind`: one of `repository_skill`, `doctrine`, `jar`, `reviewer`, or `runtime_boundary`;
- `provenanceLocator`: exact repository path, doctrine/jar identifier, reviewer surface, or receipt/boundary locator;
- `activationReason`: why this light was selected for the current pulse;
- `state`: `active`, `blocked`, `fault`, or `recovered`;
- `changedThisPulse`: whether the represented condition materially changed in the current pulse;
- `consequence`: what the selected skill/jar/reviewer/boundary changed or prevented;
- `evidenceBoundary`: the receipt, source readback, exact blocker, or other evidence that earns the state.

A source record is invalid for display when `id`, `label`, `provenanceKind`, `provenanceLocator`, `activationReason`, `consequence`, or `evidenceBoundary` is empty. `repository_skill` additionally requires `provenanceLocator` to resolve to an actual `skills/<id>/SKILL.md` or another exact repository skill path. Do not infer provenance from the label.

This contract is source semantics only. It does not imply that `HeartbeatSkillPolicy.Candidate`, `OperatorState`, or the existing Operator Overlay already carries these fields. Until those existing owners are changed and tested through an authorized lane, the gap remains explicit rather than being hidden behind prose.

## Runtime semantics
The Operator Overlay should consume a typed heartbeat-light payload rather than infer doctrine from prose. Preserve previous durable light state until the new pulse is complete; never flash aspirational work as active.

A light may summarize a skill, but it may not claim a later capability state than its evidence proves. Preserve `requested -> implemented -> tested -> deployed -> callable -> executed -> delivered -> accepted` distinctions.

Repository/source progress does not unlock a shared physical execution surface. A green source/test light must not be interpreted as transport, connector-egress, phone execution, deployment, or physical acceptance.

## Deterministic scene specimen
`HeartbeatSceneGraph` is a pure, non-rendering specimen that composes `HeartbeatSkillPolicy`. It does **not** own the overlay, transport, queue, phone runtime, or execution authority.

The specimen exists to make later rendering boring and auditable:

- material-light order becomes stable focus order;
- each node carries a minimum 48 dp touch target contract;
- state is exposed by text/semantic description plus a non-color token;
- motion is allowed only when state or consequence actually changes;
- an incomplete refresh preserves the last complete visible frame and exposes the interrupted attempted pulse separately;
- an interrupted refresh never receives celebratory/Christmas-light motion.

Until an existing renderer consumes this model and runtime evidence proves it, the scene graph remains source-only implementation.

## Touch and TalkBack
Skill lights are first-class controls/semantics, not color dots.

- Minimum touch target: 48 dp.
- Do not use color as the only state signal; pair it with text/state semantics.
- Tap exposes or announces the skill label, state, reason, concrete consequence, and evidence/boundary.
- Stable focus order follows the rendered light order.
- Content description form: `Skill <label>, <state>. <consequence>.`
- A light must never silently toggle operator authority, remote input, or execution mode.
- When collapsed, the overlay may summarize the count, but TalkBack must still expose the material states.

## Visual rule
Use native/vector/DOM/drawable primitives. No raster status art. Warm walls and Christmas-light motion are allowed only when they encode real transitions; blinking without a state transition is forbidden.

## Failure Is The Shovel
A repeated failure cannot merely relight the same fault. The next pulse must either change recovery method/evidence path or preserve the fault with a new exact reason. Originality is paid in recovery strategy, not wording.

## Contact preservation
Do not erase the prior successful heartbeat before the new one is durable. A crash during refresh must leave the last known good skill-light receipt readable, with the interrupted pulse distinguishable as incomplete.

## Done
This skill is satisfied only when the current heartbeat can name which skills lit, why, what each changed, and what evidence supports the result. UI wiring is a separate capability state and must not be claimed until the existing Operator Overlay actually renders and exposes the payload on device.
