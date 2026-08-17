# Heartbeat Invisible Semantic Controls

Use this skill when heartbeat labels, reasons, evidence, source locators, or review surfaces can contain meaningful zero-width Unicode controls whose semantics are real but whose presence is hard for an operator to see.

## Canonical wound

Invisible does **not** mean invalid.

The existing heartbeat semantic safety correctly rejects ISO controls, malformed UTF-16, and directional bidi controls. Keep that gate. Do **not** extend it into a blanket `Character.FORMAT` ban or an invisible-character ban.

Unicode assigns legitimate semantics to several zero-width characters:

- `U+200B` ZERO WIDTH SPACE — word/line-break opportunity, including use in languages without visible word spacing
- `U+2060` WORD JOINER — preferred invisible control for preventing a line break
- `U+200D` ZERO WIDTH JOINER — grapheme/emoji/script shaping
- `U+200C` ZERO WIDTH NON-JOINER — language/script shaping
- `U+FEFF` BYTE ORDER MARK with legacy ZWNBSP history

The real wound is **evidence visibility**: exact source identity can contain meaningful invisible controls that ordinary visual prose does not expose.

## Source rule

`HeartbeatInvisibleSemanticControlPolicy` is a projection organ, not an acceptance gate.

It must preserve the original source string and offer a separate explicit evidence projection using deterministic markers such as:

- `\u{200B ZWSP}`
- `\u{200C ZWNJ}`
- `\u{200D ZWJ}`
- `\u{2060 WJ}`
- `\u{FEFF BOM}`

Backslash is reserved as the diagnostic marker introducer. Literal source backslashes are doubled in the projection. That distinction is load-bearing: actual `Reg<ZWSP>net` and literal source text spelling `Reg\u{200B ZWSP}net` must not collapse to the same evidence display.

Never delete, trim, normalize, or replace the canonical source string just to make it easier to display. Projection is human-readable evidence beside the source, not a new canonical identity.

## Unicode discrimination scar

The first 0900 strategy treated U+200B/U+2060/U+FEFF as poison. Primary Unicode review disproved that assumption. Preserve the correction:

- U+200B and U+2060 have intentional line-breaking semantics.
- ZWJ/ZWNJ have intentional shaping semantics.
- FEFF has BOM/legacy ZWNBSP semantics.
- Therefore invisibility alone cannot justify rejection.

Originality Tax consequence: do not reintroduce the rejected blanket-ban strategy under a different name.

## Consumer integration law

Policy existence is not consumer wiring.

Current capability state until an existing consumer adopts the diagnostic projection:

- projection policy source: YES
- regression source: YES
- canonical parser projection consumption: NO
- typed-source detail projection consumption: NO
- scene/TalkBack evidence projection consumption: NO
- Android runtime behavior: NO
- TalkBack runtime proof: NO
- deployed/callable/executed/delivered/accepted: NO

When wiring later, compose the existing semantic owners. Do not create a second parser, scene graph, overlay controller, renderer, transport, or P0 coordinator.

## Accessibility doctrine

Routine speech should not gratuitously read Unicode bookkeeping. Explicit evidence/detail surfaces may reveal invisible controls when exact text identity matters. Keep that projection bounded before any future TalkBack use.

Existing bidi/ISO/malformed-surrogate rejection remains separate and authoritative. A revealable layout/shaping control is not a bidi attack merely because it is invisible.

## Regression doctrine

Pin all of these independently:

1. U+200B, U+2060, U+FEFF, U+200D, and U+200C are revealable with deterministic markers.
2. Their exact source strings remain unchanged.
3. Ordinary Unicode passes through the explicit evidence projection unchanged.
4. Literal backslashes are escaped so marker-like source text cannot alias an actual invisible control.
5. Existing RLO/bidi and ISO-control rejection remains unchanged and is not replaced by this projection helper.
6. No normalization turns an invisible source distinction into a counterfeit canonical identity.
7. After future consumer wiring, explicit evidence projection and routine speech remain separate capability claims.

Regression source is not TESTED evidence until an authorized test lane actually executes it.

## P0 / phone firewall

This skill owns no Phone Hands action, primary-phone command, queue/relay work, recovery mutation, deployment, physical acceptance, Nightcore, Pocket TTS, Chromium, or Context Organ action. Those remain with their canonical owners.
