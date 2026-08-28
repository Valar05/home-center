# Operator Owner Surgery Shadow Receipt

## Purpose
Keep exact descriptor-shadow machine evidence separate from safe operator/TalkBack display evidence while preserving a deterministic link between the two.

The raw descriptor shadow remains the source record. Operator display is a bounded projection and owns no custody authority, backend selector, overlay controller, phone lane, P0 coordinator, runtime renderer, or acceptance path.

## Core laws
`RAW EVIDENCE != ROUTINE OPERATOR DISPLAY`.

`RAW FAILURE BOUNDARY != TALKBACK PROSE`.

`RAW EVIDENCE SHA = LINKAGE, NOT RAW DISCLOSURE`.

`RAW EVIDENCE SHA != CANONICAL ARTIFACT IDENTITY != AUTHORITY != TESTED != RUNTIME`.

`REPOSITORY PATH IDENTITY != DISPLAY PATH`.

`EXTERNAL HOST PATH != HASH ORACLE`.

`FALSE COMPARISON != COMPARISON UNAVAILABLE`.

`WOUND STATUS MUST MATCH CANONICAL / CAPABILITY CONTEXT`.

`SHADOW_MATCH REQUIRES SELF-INTEGRITY BEFORE DISPLAY`.

`OPERATOR RECEIPT COMMAND != SECOND RECEIPT PROJECTOR`.

`SHADOW RECEIPT != DESCRIPTOR AUTHORITY != TESTED != RUNTIME != DELIVERED`.

## Existing display projector
`tools/try_forever_owner_surgery_shadow_receipt_projection.py` remains the sole bounded display projector.

It requires exact descriptor-shadow v3 source, exact canonical-result SHA-256, no descriptor authority, no owner mutation, bounded artifact metadata, and boolean-or-null comparison truth. Repository paths use the existing provenance path projector; external host paths become `<external-path>`; raw failure prose is replaced by a deterministic boundary digest plus fixed status meaning.

## Self-integrity consumption
`tools/try_forever_owner_surgery_shadow_receipt_self_integrity.py` is now self-integrity v2. It recomputes completed comparison truth from raw artifacts/counters, validates exact temporal receipt context, and also validates that wound/unavailable status agrees with canonical schema/completeness and descriptor capability context before delegating to the projector.

`tools/try_forever_owner_surgery_descriptor_shadow_operator_receipt.py` is the **SOURCE_WIRED operator receipt command**, now operator receipt schema v3. It composes:

`audit_descriptor_shadow -> rawMachineEvidenceSha256 -> project_shadow_receipt_with_self_integrity -> existing display projector -> operatorReceiptSha256`.

The raw audit remains separately callable for machine evidence. The operator command includes only the raw evidence digest, never the raw payload or raw boundary prose. `rawMachineEvidenceSha256` binds the receipt to exact raw JSON-shaped evidence; `operatorReceiptSha256` identifies the complete bounded operator payload. Both are evidence/checkpoint identities only.

The operator command adds bounded capability metadata and explicitly denies second projector, second descriptor authority, phone/P0 consumption, TESTED, runtime, deployment, delivery, and acceptance.

## Regression surface
`tools/test_try_forever_owner_surgery_shadow_receipt_projection.py` — **SOURCE / UNEXECUTED**.

`tools/test_try_forever_owner_surgery_shadow_receipt_self_integrity.py` — **SOURCE / UNEXECUTED**, including hostile wound-context mismatches.

`tools/test_try_forever_owner_surgery_descriptor_shadow_operator_receipt.py` — **SOURCE / UNEXECUTED** and pins owner-command composition, raw-evidence digest linkage, raw-only evidence drift, raw-boundary non-leakage, contradictory-evidence rejection, stale-temporal-wound rejection, and capability membrane.

Do not call any regression passed merely because source exists.

## Current capability state
- raw descriptor shadow evidence: **YES / SOURCE**;
- bounded display projector: **YES / SOURCE**;
- self-integrity v2 + wound-context gate: **YES / SOURCE_WIRED**;
- operator receipt command consuming self-integrity: **YES / SOURCE_WIRED**;
- raw machine-evidence digest binding: **YES / SOURCE_WIRED**;
- bounded operator receipt schema v3 + deterministic identity: **YES / SOURCE_WIRED**;
- authenticated repository readback: **YES**;
- hostile regression source: **YES / UNEXECUTED**;
- regression execution: **NO**;
- Android/TalkBack runtime consumption: **NO**;
- canonical descriptor authority integration: **NO**;
- TESTED/deployed/phone/delivered/accepted: **NO**.

## Accessibility / touch
Operator-facing receipts must not describe a failed comparison as a negative measurement, expose raw host/error prose, accept a wound label paired with unrelated healthy context, or say MATCH when their own artifact lists/counters/temporal receipt contradict the claim. A source specimen may make the raw→binding→self-audit→display membrane touch-inspectable using native HTML semantics, non-color state, large targets, and reduced motion. It must remain SOURCE ONLY.

## P0 / phone firewall
This skill consumes no Phone Hands, primary-phone execution, recovery chain, Nightcore, Pocket TTS, Chromium, Context Organs, physical acceptance, or P0 coordination.
