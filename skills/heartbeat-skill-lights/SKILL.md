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

`HeartbeatSkillPolicy.Candidate` may carry the complete typed envelope, and `hasTypedSourceContract(...)` distinguishes those records from legacy candidates whose provenance fields are intentionally empty. Legacy materiality is not silently changed during migration. The typed source gate also rejects unsafe semantic text before it can become display-ready speech/touch state; exact canonical payload is rejected rather than rewritten.

### Closed-world v1 envelope
`heartbeat-skill-lights.v1` is a closed-world canonical envelope. Unknown root members and unknown light members are rejected rather than ignored. This prevents misspelled fields or aspirational capability fields such as `deployed`/`uiRendered` from silently hitchhiking beside valid telemetry and later being mistaken for evidence.

The pure policy performs source-shape validation for `repository_skill` locators: they must be exact `skills/.../SKILL.md`-shaped forward-slash paths and must reject traversal, backslashes, duplicate separators, or non-skill files. **That source-shape check does not prove repository existence.** Actual existence is earned only by repository-grounded discovery/readback. Never promote syntax validation into provenance verification.

The existing `ACTION_HEARTBEAT -> OverlayUpdateReceiver -> OperatorState` ingress may persist an exact bounded heartbeat-light JSON payload as opaque UTF-8 identity: base64 bytes, byte count, SHA-256, and update timestamp. `OperatorStateProvider` may expose that same stored identity through its existing read-only query surface. This is ingress persistence only. It does **not** validate the JSON into typed candidates, render a scene, prove TalkBack behavior, deploy to a phone, or establish physical acceptance.

### Persisted identity before semantic ingestion
Opaque persistence is not trustworthy merely because all four metadata fields exist. `HeartbeatPersistedEnvelopeProjection` is the pure source seam that checks the decoded UTF-8 payload against its persisted identity **before** semantic parsing is attempted.

- decoded payload byte length must stay within the same 32768-byte ingress ceiling and exactly equal the declared stored byte count;
- stored SHA-256 metadata must be canonical lowercase 64-character hex and must exactly match the decoded UTF-8 payload;
- the persisted update identity must be present (`updatedMs > 0`);
- a storage-integrity rejection must not invoke `HeartbeatEnvelopeParser`; it preserves the exact visible-contact/checkpoint identity through the existing scene-preservation organ, re-materializes all one-shot motion off, and exposes the exact integrity boundary;
- storage acceptance advances only to semantic-attempt permission. The canonical parser may still reject the envelope, and an accepted parser result may still be presentation-incomplete (for example `complete=false`);
- valid storage identity, parser acceptance, presentation acceptance, rendered UI, deployment, phone callability, execution, delivery, and acceptance remain separate capability states.

The helper deliberately does **not** read `SharedPreferences`, decode Android base64, own `OperatorState`, render the overlay, touch transport, consume the phone surface, or mutate P0 recovery. Until the existing overlay owner actually decodes the stored payload and calls this seam, persisted runtime payload consumption remains **NO** even though the pure integrity/projection source exists.

### Semantic text safety
Canonical heartbeat text eventually becomes spoken/touched detail, evidence display, and checkpoint identity. The pure parser therefore applies field-specific character limits to `pulseId`, `id`, `label`, provenance, activation reason, consequence, and evidence boundary rather than relying only on the raw JSON-string ceiling.

Decoded canonical semantic text must reject ISO control characters, unpaired UTF-16 surrogates, and directional bidi spoofing controls: U+061C, U+200E/U+200F, U+202A..U+202E, and U+2066..U+2069. Valid surrogate pairs remain ordinary inert Unicode data. U+200D ZERO WIDTH JOINER also remains valid because it is legitimate in emoji/grapheme sequences even though Java categorizes it as `Character.FORMAT`. Do **not** copy the broader human-facing log-boundary sanitizer into canonical payload semantics and accidentally outlaw useful Unicode.

This is a semantic-ingestion rule, not an execution filter: command-looking text remains data and must never be evaluated or sent to a shell merely because it appears inside a heartbeat field. A directional-control wound is rejected rather than stripped so checkpoint/evidence identity is never silently rewritten.

Wire protocol tokens are not exempt from decoded-string safety merely because they are short. `schema` and `state` must validate decoded control characters, surrogate structure, and directional bidi controls **before** trimming/normalization, then apply their own narrow token bounds. A control character, unpaired surrogate, or bidi direction control that trim or display order could otherwise hide is a fail-closed protocol wound, not a canonical token. `pulseId` follows the same rule before it can become visible/attempted scene identity.

`HeartbeatSkillPolicy` repeats the decoded semantic safety check at the display-ready source-contract boundary so direct source callers cannot bypass parser assumptions. `HeartbeatSceneGraph` also rejects an unsafe directly supplied pulse id without echoing that identity into the attempted frame. The exact reusable rule is durable at `skills/semantic-text-safety/SKILL.md`.

This source rule does not imply that persisted runtime payloads are already routed through the parser.

## Runtime semantics
The Operator Overlay should consume a typed heartbeat-light payload rather than infer doctrine from prose. Preserve previous durable light state until the new pulse is complete; never flash aspirational work as active.

A light may summarize a skill, but it may not claim a later capability state than its evidence proves. Preserve `requested -> implemented -> tested -> deployed -> callable -> executed -> delivered -> accepted` distinctions.

Repository/source progress does not unlock a shared physical execution surface. A green source/test light must not be interpreted as transport, connector-egress, phone execution, deployment, or physical acceptance.

Raw heartbeat payload persistence is not semantic ingestion. A pure persisted-identity verifier/projection is also not runtime ingestion until the existing overlay owner actually supplies stored bytes/metadata to it. Until the overlay parses the persisted envelope into validated candidates, consumes the scene model, renders the controls, and produces authorized runtime evidence, UI-rendered/deployed/callable/delivered/accepted remain separate unresolved states.

## Deterministic scene specimen
`HeartbeatSceneGraph` is a pure, non-rendering specimen that composes `HeartbeatSkillPolicy`. It does **not** own the overlay, transport, queue, phone runtime, or execution authority.

The specimen exists to make later rendering boring and auditable:

- material-light order becomes stable focus order;
- each node carries a minimum 48 dp touch target contract;
- state is exposed by text/semantic description plus a non-color token;
- a typed node preserves provenance, activation reason, concrete consequence, and evidence boundary for touch/TalkBack detail;
- the scene itself consumes only `selectDisplayReadyLights(...)`; a material candidate missing the complete typed source/evidence contract rejects the attempted frame rather than silently becoming a weaker node;
- a complete pulse with a blank pulse identity is invalid and cannot replace the last complete contact surface;
- an unsafe direct pulse identity containing control/malformed-surrogate/directional-bidi text is rejected before it can become `attemptedPulseId`; the last-good contact survives and the unsafe id is not echoed into speech or visual state;
- rejected/incomplete refreshes expose an exact `refreshBoundary`, preserve the last complete frame, and never earn transition motion;
- motion is allowed only when state or consequence actually changes, or when a material light is added or removed; evidence/provenance metadata refresh alone does not earn Christmas-light motion;
- an incomplete refresh preserves the last complete visible frame and exposes the interrupted attempted pulse separately;
- an interrupted refresh never receives celebratory/Christmas-light motion.

The scene may consume `HeartbeatEnvelopeParser.Result` directly as a **pure source composition seam**. An accepted parsed pulse delegates to the ordinary scene builder. A rejected parser result preserves last-good contact and carries the exact parser boundary into `refreshBoundary`. Pre-parser integrity wounds may use `preserveRejectedRefresh(...)`, which delegates to the same preservation organ and clamps all preserved node motion off. These seams do not wire `OperatorState`, a renderer, Android UI, transport, or phone execution; they merely prevent a later consumer from inventing weaker handoffs.

Until an existing renderer consumes this model and runtime evidence proves it, the scene graph remains source-only implementation.

### Checkpoint and idempotence identity
`HeartbeatFrameCheckpoint` is a pure source-side fingerprint helper over the already-built semantic frame. It does not persist anything and does not become a new controller.

- `contactSha256(frame)` fingerprints the exact visible last-good contact semantics, including pulse identity and touch/TalkBack provenance/evidence detail. Attempted refresh identity and rejection text are excluded so a failed refresh cannot mutate the fingerprint of what remains visible.
- `transitionSha256(frame)` fingerprints stable light identity, state, and consequence in stable-id canonical order: exactly the fields allowed to earn transition motion. Pulse identity, evidence, provenance, timestamps, and pure visible-scene reorder cannot manufacture another Christmas blink.
- an evidence-only complete refresh may change contact identity while preserving transition identity;
- a pure reorder may change contact identity/focus positions while preserving transition identity and `transitionMotionAllowed=false`;
- an incomplete/rejected refresh preserves both last-good identities;
- a real state/consequence/add/remove transition changes transition identity.

These hashes are source contracts for future consumers. Their existence does not prove any runtime persistence, rendering, retry dedupe, or device behavior.

## Touch and TalkBack
Skill lights are first-class controls/semantics, not color dots.

- Minimum touch target: 48 dp.
- Do not use color as the only state signal; pair it with text/state semantics.
- Tap exposes or announces the skill label, state, reason, concrete consequence, evidence/boundary, and typed provenance when available.
- Stable focus order follows the rendered light order.
- Compact content description form: `Skill <label>, <state>. <consequence>.`
- Typed detail additionally exposes `Why`, `Evidence`, and `Source`; legacy records must not invent those fields.
- A light must never silently toggle operator authority, remote input, or execution mode.
- When collapsed, the overlay may summarize the count, but TalkBack must still expose the material states. FAULT/BLOCKED identities are named before non-attention lights within the bounded naming budget; if attention itself exceeds that budget, the summary must state the exact number of omitted blocked/fault attention lights that remain available by touch.
- Persistent selection of one light controlling a shared always-present detail surface uses selection semantics such as `aria-pressed`; do not claim `aria-expanded` unless content is actually expanded/collapsed by that control.

`HeartbeatFrameAccessibility` derives collapsed and detail speech from the already-built visible `HeartbeatSceneGraph.Frame`, not from raw candidates. This is deliberate: when refresh fails closed, TalkBack must describe the same last-good lights the scene preserves and may append the exact interrupted-refresh boundary, but must never announce discarded attempted content as current state. Stable detail lookup uses the visible scene focus index only.

The source-only DOM contact sheet at `docs/try-forever/heartbeat-skill-lights-source-specimen.html` is a deliberately touchable/keyboard-reachable accessibility specimen: semantic buttons, minimum 48px targets, explicit non-color tokens, focus visibility, persistent pressed selection, detail disclosure, live selection status, and reduced-motion handling. It is **not** Operator Overlay runtime evidence and must never be reported as deployed, callable, physically presented, or accepted.

The source-only contact-preservation specimen at `docs/try-forever/heartbeat-contact-sheet-source-specimen.html` visualizes complete, interrupted-preserved, evidence-only refresh, and materially recovered frames. It has no autoplay loop: one brief semantic motion is allowed only on a selected frame whose transition fingerprint changes, and `prefers-reduced-motion` disables that motion. The specimen is repository source art only, not Android runtime proof.

The source-only motion-clamp specimen at `docs/try-forever/heartbeat-motion-clamp-source-specimen.html` demonstrates distinct fail-closed wounds including malformed `schema`/`state` protocol text, persisted byte-count/SHA mismatch **before** semantic parsing, malformed raw UTF-8, semantic identity collision, and directional bidi poisoning. Its semantic-bidi state explicitly distinguishes rejected RLO/LRI-style controls from legitimate ZWJ Unicode. All rejection states preserve last-good visible contact and earn no transition motion. It is a teaching/reference organism only, not evidence that the Android overlay has consumed the persisted identity, parsed the JSON, or rendered either rejection.

## Visual rule
Use native/vector/DOM/drawable primitives. No raster status art. Warm walls and Christmas-light motion are allowed only when they encode real transitions; blinking without a state transition is forbidden.

The SVG and DOM source specimens are implementation references only. Their existence proves source art exists; it does not prove an Android renderer consumed them or that a phone displayed them.

## Failure Is The Shovel
A repeated failure cannot merely relight the same fault. The next pulse must either change recovery method/evidence path or preserve the fault with a new exact reason. Originality is paid in recovery strategy, not wording.

## Contact preservation
Do not erase the prior successful heartbeat before the new one is durable. A crash during refresh must leave the last known good skill-light receipt readable, with the interrupted pulse distinguishable as incomplete.

Opaque ingress persistence must be atomic enough that a failed write does not masquerade as a new durable heartbeat. The stored byte count and SHA-256 exist so later consumers can prove which exact payload they observed rather than trusting a timestamp alone. Before semantic parsing, decoded UTF-8 bytes must be checked against that persisted byte count and SHA. A mismatch is a storage-integrity wound: preserve exact visible-contact/checkpoint identity through the existing scene-preservation seam, re-materialize all preserved motion off, expose the integrity boundary, and do not invoke the semantic parser on untrusted identity.

A pulse that is syntactically marked complete but is semantically anonymous or contains material lights without the typed display contract is still incomplete for presentation purposes. Preserve last-good contact and expose the exact rejection boundary instead of clearing the surface or displaying downgraded telemetry.

A syntactically valid JSON envelope with unknown canonical members is also invalid for presentation. Preserve last-good contact; do not accept schema drift by silence.

A syntactically valid envelope whose decoded `schema`, `state`, `pulseId`, or typed semantic field contains a control character, unpaired surrogate, or directional bidi control is likewise invalid for presentation even if trimming or bidi display order would reveal or disguise familiar text. Preserve the last-good frame and expose the parser/scene boundary; malformed or spoofable semantic text never earns motion or a new contact checkpoint. Do not strip the control and pretend the rewritten value is canonical source identity.

## Done
This skill is satisfied only when the current heartbeat can name which skills lit, why, what each changed, and what evidence supports the result. UI wiring is a separate capability state and must not be claimed until the existing Operator Overlay actually decodes the persisted payload, verifies its identity, parses it, renders it, and exposes it on device through an authorized lane.
