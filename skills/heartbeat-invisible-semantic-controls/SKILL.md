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

## Projection-expansion scar

A legal source field can become much larger after every invisible control is expanded into a diagnostic marker. Therefore **source bounds are not speech bounds**.

`boundedEvidenceProjection(...)` applies the budget after projection and treats each marker/escaped-backslash unit atomically. Truncation may happen only between projection units; never cut a `\u{...}` marker in half and never silently repair the canonical source to satisfy a speech budget.

## Consumer integration law

Policy existence is not consumer wiring.

Current source capability after the 1000 slice:

- projection policy source: YES
- bounded post-projection detail source: YES
- regression source: YES
- `HeartbeatOverlayViewModel.LightControl.detailContentDescription` consumption: YES / SOURCE WIRING
- `HeartbeatFrameAccessibility` explicit detail accessors: YES / SOURCE WIRING
- existing `OperatorOverlayService` explicit light-tap detail path consumes the view-model detail: YES / EXISTING-OWNER SOURCE WIRING
- compact light `contentDescription` projection consumption: NO BY DESIGN
- collapsed/routine heartbeat speech projection consumption: NO BY DESIGN
- Android runtime behavior observed: NO
- TalkBack runtime proof: NO
- deployed/callable/executed/delivered/accepted: NO

The owner seam remains the existing Operator Overlay. Do not create a second parser, scene graph, overlay controller, renderer, transport, or P0 coordinator.

## Accessibility doctrine

Routine speech should not gratuitously read Unicode bookkeeping. The compact light description and collapsed heartbeat announcement remain unchanged.

Explicit on-demand evidence/detail is different: once the operator selects a light, legitimate invisible semantics may be named through the collision-safe marker projection. That spoken/detail projection must be bounded **after marker expansion**, because a source-side bound does not bound the expanded output.

The exact scene fields remain canonical evidence and are not truncated or rewritten by this speech/detail projection.

Existing bidi/ISO/malformed-surrogate rejection remains separate and authoritative. A revealable layout/shaping control is not a bidi attack merely because it is invisible.

## Regression doctrine

Pin all of these independently:

1. U+200B, U+2060, U+FEFF, U+200D, and U+200C are revealable with deterministic markers.
2. Their exact source strings remain unchanged.
3. Ordinary Unicode passes through the explicit evidence projection unchanged except for the reserved literal-backslash escape rule.
4. Literal backslashes are escaped so marker-like source text cannot alias an actual invisible control.
5. Bounded projection applies its budget after expansion and never cuts one marker/escape unit in half.
6. Existing RLO/bidi and ISO-control rejection remains unchanged and is not replaced by this projection helper.
7. Compact/routine light speech remains unchanged when on-demand evidence projection is wired.
8. The exact scene source fields survive even when on-demand detail speech is truncated.
9. No normalization turns an invisible source distinction into a counterfeit canonical identity.

Regression source is not TESTED evidence until an authorized test lane actually executes it.

## P0 / phone firewall

This skill owns no Phone Hands action, primary-phone command, queue/relay work, recovery mutation, deployment, physical acceptance, Nightcore, Pocket TTS, Chromium, or Context Organ action. Those remain with their canonical owners.
