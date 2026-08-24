# Operator Owner Surgery Raw Capability Membrane

## Purpose
Prevent a bounded descriptor-shadow operator receipt from laundering contradictory raw capability claims into harmless-looking false output.

The existing raw shadow owner may only enter operator self-integrity when its capability membrane is explicit and fail-closed. A projector emitting `false` does not repair raw evidence that claimed `tested=true`, runtime capability, phone delivery, authority, or owner mutation.

## Core laws
`BOUNDED PROJECTOR FALSE != PERMISSION TO SANITIZE RAW TRUE`.

`MISSING CAPABILITY FIELD != FALSE`.

`FALSEY VALUE != BOOLEAN FALSE`.

`RAW descriptorAuthorityAdmitted / ownerMutation / regressionExecuted / tested / runtimeUi / runtimeTalkBack / phoneDelivered = EXACT FALSE`.

`CONTRADICTORY RAW CAPABILITY EVIDENCE = FAIL CLOSED BEFORE DISPLAY PROJECTION`.

`RAW MACHINE EVIDENCE != BOUNDED OPERATOR RECEIPT`.

`SOURCE_WIRED != REGRESSION EXECUTED != TESTED != RUNTIME != DEPLOYED != DELIVERED != ACCEPTED`.

## Existing organs
`tools/try_forever_owner_surgery_descriptor_shadow_audit.py` remains the sole raw descriptor-shadow evidence producer and currently emits the denied capability fields as exact false.

`tools/try_forever_owner_surgery_shadow_receipt_self_integrity.py` remains the existing self-integrity owner and sole gate before bounded projection.

`tools/try_forever_owner_surgery_shadow_receipt_projection.py` remains the sole bounded display projector.

`tools/try_forever_owner_surgery_descriptor_shadow_operator_receipt.py` remains the bounded operator receipt command.

No second descriptor authority, projector, receipt owner, controller, recovery organ, or phone path is created by this skill.

## Supporting source
`tools/try_forever_shadow_raw_capability_membrane.py` is **YES / SUPPORTING_SOURCE**. It requires every denied raw capability field to be present and exactly boolean false.

## Owner wiring
The existing self-integrity owner is **YES / SOURCE_WIRED**.

Authenticated source promotion:
- base owner blob: `ae76c2d7db2b71cd1b1c2518e62625bf5483538d`;
- applied commit: `2acfa301f849889f73bcd50f69af9be217b57374`;
- resulting owner blob: `bd25082da9c7644fd48301a43e91ac53bc389b9d`.

The owner calls `require_raw_shadow_capability_membrane(result)` after exact descriptor-shadow schema admission and before status/context evaluation or bounded projection. Self-integrity schema v2 and operator receipt schema v3 remain unchanged.

## Regression source
`tools/test_try_forever_shadow_raw_capability_membrane.py` is **YES / UNEXECUTED** and attacks missing fields plus truthy/falsey substitutes.

`tools/test_try_forever_shadow_raw_capability_owner_boundary.py` is **YES / SOURCE-WIRED EXPECTATION / UNEXECUTED** and requires the existing self-integrity owner to reject raw capability overclaims before projection.

`tools/test_try_forever_shadow_raw_capability_operator_boundary.py` is **YES / SOURCE-WIRED EXPECTATION / UNEXECUTED** and pins the same requirement through the actual bounded operator receipt command.

Do not call any regression passed merely because source exists.

## Applied surgery provenance
`patches/try-forever-shadow-raw-capability-membrane-owner.patch` is **APPLIED_SOURCE** and records the exact base owner blob, applied commit, and resulting owner blob.

## Current capability truth
- supporting raw capability policy: **YES / SOURCE**;
- self-integrity owner consumes raw capability membrane: **YES / SOURCE_WIRED**;
- pure hostile regression source: **YES / UNEXECUTED**;
- owner-boundary regression source: **YES / UNEXECUTED**;
- operator-command regression source: **YES / UNEXECUTED**;
- regression execution: **NO**;
- TESTED: **NO**;
- runtime UI/TalkBack: **NO**;
- descriptor authority: **NO**;
- deployed/callable/executed/delivered/accepted: **NO**.

## Accessibility / operator truth
Operator-facing evidence must never look safer than its raw source merely because the display projector emits conservative constants. Contradictory source capability state is an integrity wound and must be rejected before projection.

## P0 / phone firewall
Consume no Phone Hands ticket, primary-phone command, recovery chain, Nightcore, Pocket TTS, Chromium, Context Organs, physical acceptance, or P0 coordination. P0 evidence remains read-only.
