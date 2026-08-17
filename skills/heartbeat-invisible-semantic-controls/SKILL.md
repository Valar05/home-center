# Heartbeat Invisible Semantic Controls

Use this skill when heartbeat labels, reasons, evidence, source locators, protocol-facing semantic text, or parser diagnostics can contain invisible Unicode formatting that changes exact identity without giving the operator an honest visible distinction.

## Canonical wound

The existing heartbeat semantic safety already rejects ISO controls, malformed UTF-16, and directional bidi controls. Do **not** replace that with a blanket `Character.FORMAT` ban: Unicode shaping has legitimate invisible characters.

This skill adds only three presentation-alias controls to the unsafe set:

- `U+200B` ZERO WIDTH SPACE
- `U+2060` WORD JOINER
- `U+FEFF` BYTE ORDER MARK / ZERO WIDTH NO-BREAK SPACE

Preserve at minimum:

- `U+200D` ZERO WIDTH JOINER — legitimate grapheme/emoji joining
- `U+200C` ZERO WIDTH NON-JOINER — legitimate language shaping
- ordinary supplementary Unicode

## Source rule

Use `HeartbeatInvisibleSemanticControlPolicy` as the narrow policy organ. It composes with `HeartbeatSkillPolicy.isSafeSemanticText`; it does not normalize, trim, delete, replace, or repair poisoned source text into an accepted identity.

A rejected invisible alias must remain rejection evidence. Do not turn `Reg<ZWSP>net` into `Regnet`, because that destroys the exact source distinction and can create counterfeit checkpoint/provenance truth.

## Consumer integration law

Policy existence is not consumer wiring.

Until the existing semantic consumers call the narrow policy, capability state is:

- policy source: YES
- regression source: YES
- canonical parser consumption: NO
- direct typed-source gate consumption: NO
- scene defense-in-depth consumption: NO
- Android runtime behavior: NO
- TalkBack runtime proof: NO
- deployed/callable/executed/delivered/accepted: NO

When wiring later, modify the existing semantic owners. Do not create a second parser, scene graph, overlay controller, renderer, transport, or P0 coordinator.

## Parser diagnostics

Do not call these three controls “bidi-direction controls.” If the parser consumes this policy later, emit a distinct bounded boundary such as `contains an invisible semantic control` while preserving the existing bidi diagnostic for directional controls.

Unknown or duplicate JSON member names containing an unsafe invisible control must not be echoed into operator speech/log/review surfaces; use the existing safe member-name placeholder path.

## Accessibility and motion

The problem is evidence/contact legibility, not typography aesthetics. Rejection should flow through the existing fail-closed scene/contact-preservation organ. A rejected alias earns no new Christmas-light motion and must not introduce a phantom selectable/touchable owner.

## Regression doctrine

Pin all of these independently:

1. U+200B, U+2060, and U+FEFF reject.
2. U+200D ZWJ remains accepted.
3. U+200C ZWNJ remains accepted.
4. Existing RLO/bidi and ISO-control rejection remains accepted behavior.
5. No normalization turns poisoned evidence into a valid identity.
6. After consumer wiring, parser/direct-source/scene paths agree and last-good contact is preserved with motion clamped.

Regression source is not TESTED evidence until an authorized test lane actually executes it.

## P0 / phone firewall

This skill owns no Phone Hands action, primary-phone command, queue/relay work, recovery mutation, deployment, physical acceptance, Nightcore, Pocket TTS, Chromium, or Context Organ action. Those remain with their canonical owners.
