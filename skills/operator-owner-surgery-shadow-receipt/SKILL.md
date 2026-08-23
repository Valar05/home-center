# Operator Owner Surgery Shadow Receipt

## Purpose
Keep exact descriptor-shadow machine evidence separate from safe operator/TalkBack display evidence.

The raw descriptor shadow remains the source record. Operator display is a bounded projection and owns no custody authority, backend selector, overlay controller, phone lane, P0 coordinator, runtime renderer, or acceptance path.

## Core laws
`RAW EVIDENCE != ROUTINE OPERATOR DISPLAY`.

`RAW FAILURE BOUNDARY != TALKBACK PROSE`.

`REPOSITORY PATH IDENTITY != DISPLAY PATH`.

`EXTERNAL HOST PATH != HASH ORACLE`.

`FALSE COMPARISON != COMPARISON UNAVAILABLE`.

`SHADOW_MATCH REQUIRES SELF-INTEGRITY BEFORE DISPLAY`.

`OPERATOR RECEIPT COMMAND != SECOND RECEIPT PROJECTOR`.

`SHADOW RECEIPT != DESCRIPTOR AUTHORITY != TESTED != RUNTIME != DELIVERED`.

## Existing display projector
`tools/try_forever_owner_surgery_shadow_receipt_projection.py` remains the sole bounded display projector.

It requires exact descriptor-shadow v3 source, exact canonical-result SHA-256, no descriptor authority, no owner mutation, bounded artifact metadata, and boolean-or-null comparison truth. Repository paths use the existing provenance path projector; external host paths become `<external-path>`; raw failure prose is replaced by a deterministic boundary digest plus fixed status meaning.

## Self-integrity consumption
`tools/try_forever_owner_surgery_shadow_receipt_self_integrity.py` remains the supporting integrity gate around the projector. It recomputes completed comparison truth from raw artifacts/counters and validates temporal receipt context before delegating to the projector.

`tools/try_forever_owner_surgery_descriptor_shadow_operator_receipt.py` is the **SOURCE_WIRED operator receipt command**. It composes:

`audit_descriptor_shadow -> project_shadow_receipt_with_self_integrity -> existing display projector`.

The raw audit remains separately callable for machine evidence. The operator command adds only bounded capability metadata and explicitly denies second projector, second descriptor authority, phone/P0 consumption, TESTED, runtime, deployment, delivery, and acceptance.

## Regression surface
`tools/test_try_forever_owner_surgery_shadow_receipt_projection.py` — **SOURCE / UNEXECUTED**.

`tools/test_try_forever_owner_surgery_shadow_receipt_self_integrity.py` — **SOURCE / UNEXECUTED**.

`tools/test_try_forever_owner_surgery_descriptor_shadow_operator_receipt.py` — **SOURCE / UNEXECUTED** and pins the owner-command composition, raw-boundary non-leakage, contradictory-evidence rejection, stale-temporal-wound rejection, and capability membrane.

Do not call any regression passed merely because source exists.

## Current capability state
- raw descriptor shadow evidence: **YES / SOURCE**;
- bounded display projector: **YES / SOURCE**;
- self-integrity gate: **YES / SUPPORTING SOURCE**;
- operator receipt command consuming self-integrity: **YES / SOURCE_WIRED**;
- authenticated repository readback: **YES**;
- hostile regression source: **YES / UNEXECUTED**;
- regression execution: **NO**;
- Android/TalkBack runtime consumption: **NO**;
- canonical descriptor authority integration: **NO**;
- TESTED/deployed/phone/delivered/accepted: **NO**.

## Accessibility / touch
Operator-facing receipts must not describe a failed comparison as a negative measurement, expose raw host/error prose, or say MATCH when their own artifact lists/counters/temporal receipt contradict the claim. A source specimen may make the raw→self-audit→display membrane touch-inspectable using native HTML semantics, non-color state, large targets, and reduced motion. It must remain SOURCE ONLY.

## P0 / phone firewall
This skill consumes no Phone Hands, primary-phone execution, recovery chain, Nightcore, Pocket TTS, Chromium, Context Organs, physical acceptance, or P0 coordination.
