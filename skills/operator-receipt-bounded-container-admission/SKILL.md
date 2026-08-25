# Operator Receipt Bounded Container Admission

## Purpose

Keep receipt verification's **bounded-work** claim honest at every Python container boundary that owns evidence, not only at the first snapshot entrypoint. Arbitrary `Mapping`, `dict` subclasses, or caller-defined iterable families can execute caller-owned Python code before node/text/field budgets get a chance to bound work. Exact JSON object evidence therefore uses exact built-in containers before traversal.

This skill also separates canonical receipt evidence from diagnostic root context. Caller-supplied diagnostic context is not authority and crosses a small source ceiling before JSON escaping or projection can allocate work on its behalf.

## Laws

- **ARBITRARY PYTHON MAPPING != BOUNDED JSON OBJECT OBSERVATION**.
- **EXACT JSON OBJECT != DICT SUBCLASS WITH CALLER CODE**.
- **ARBITRARY ITERABLE FAMILY != BOUNDED FIELD VOCABULARY**.
- **LIST IS ALREADY EXACT; OBJECT ADMISSION MUST BE EQUALLY EXACT**.
- **PUBLIC TYPE CAPABILITY MUST NOT EXCEED RUNTIME ADMISSION**.
- **DIAGNOSTIC CONTEXT != CANONICAL RECEIPT IDENTITY**.
- **UNBOUNDED DIAGNOSTIC INPUT != BOUNDED DIAGNOSTIC PROJECTION**.
- Reject unsupported container shape; do not normalize it into authority.
- Preserve accepted diagnostic text exactly; only the existing diagnostic projector may escape or whole-identity-collapse it for prose.
- This admission layer owns no semantic receipt authority, digest authority, TESTED/runtime state, deployment, callability, execution, delivery, acceptance, phone, or P0 mutation.

## Existing organs

Compose the existing snapshot/receipt organs. Do not create another receipt owner, snapshot owner, projector, verifier daemon, or phone execution lane.

Current source surfaces:
- `tools/try_forever_operator_receipt_snapshot_admission_policy.py` — **IMPLEMENTED SOURCE**.
- `tools/try_forever_operator_receipt_snapshot_custody.py` — **EXISTING OWNER SOURCE_WIRED**.
- `tools/try_forever_operator_receipt_derivation_custody.py` — **EXACT-CONTAINER SOURCE_WIRED**.
- `tools/try_forever_operator_receipt_identity_fieldset.py` — **EXACT-CONTAINER SOURCE_WIRED**.
- `tools/try_forever_owner_surgery_shadow_receipt_projection.py` — **EXACT-CONTAINER SOURCE_WIRED**.
- `tools/try_forever_owner_surgery_shadow_receipt_self_integrity.py` — **EXACT-CONTAINER SOURCE_WIRED**.
- `tools/test_try_forever_operator_receipt_exact_container_surfaces.py` — **SOURCE / UNEXECUTED**.
- `tools/test_try_forever_shadow_receipt_exact_snapshot_boundary.py` — **SOURCE / UNEXECUTED**.
- `tools/test_try_forever_operator_receipt_public_type_contract.py` — **RED SOURCE / UNEXECUTED** for the remaining final-owner public type contract.

## Current source truth

The snapshot-custody owner:
- admits root and nested objects only through exact built-in-dict admission before traversal;
- rejects Mapping subclasses/custom mappings without invoking caller-owned iteration;
- admits root diagnostic context before escaping/projection;
- preserves exact key/value identity, finite budgets, one-observation detachment, and the capability membrane.

The derivation and identity-fieldset surfaces advertise and admit exact built-in `dict` receipt/raw inputs and exact tuple field vocabularies before traversal.

The descriptor-shadow display projector and self-integrity owner now advertise exact built-in `dict` input and each consumes the existing bounded snapshot-custody organ before semantic reads. Their runtime and public type contracts are converged at source.

### Remaining exact public-contract wound

`tools/try_forever_owner_surgery_descriptor_shadow_operator_receipt.py` is final operator receipt schema **v4**, but its public reverification helpers still advertise `Mapping[str, object]` for receipt/raw evidence even though `snapshot_verification_inputs(...)` admits exact built-in `dict` only. Runtime rejection is already fail-closed; the public type capability is broader than runtime admission.

Current promotion evidence:
- RED regression: `tools/test_try_forever_operator_receipt_public_type_contract.py` — **SOURCE / UNEXECUTED**;
- exact base-blob-locked surgery: `patches/try-forever-operator-receipt-public-type-contract.patch` — **PROPOSED_NOT_APPLIED** against owner blob `2920ae28ea56a9840cf7ca05a57ff9231469cb04`;
- existing final owner mutation: **NO**.

So:
- supporting admission policy: **YES / SOURCE**;
- snapshot owner consumption: **YES / SOURCE_WIRED**;
- derivation exact-container custody: **YES / SOURCE_WIRED**;
- fieldset exact-container custody: **YES / SOURCE_WIRED**;
- projector exact-container custody: **YES / SOURCE_WIRED**;
- self-integrity exact-container custody: **YES / SOURCE_WIRED**;
- final-v4 public type-contract convergence: **NO / RED**;
- hostile regression source: **YES / UNEXECUTED**;
- whole receipt stack exact-container convergence: **NO / PARTIAL**;
- TESTED/runtime UI/runtime TalkBack/deployed/callable/executed/delivered/accepted: **NO**.

## Review scars

Earlier snapshot hardening bounded values produced *after* Mapping iteration, which did not bound arbitrary Python work executed by Mapping itself. Admission moved ahead of traversal. The 2026-08-25 09:00 review found the same smell in derivation and final-fieldset custody and repaired those surfaces. The 11:00 review repaired the display projector and self-integrity owner. The 12:01 review found the final-v4 reverification API still **advertises** broader Mapping capability even though runtime already rejects it; that final public contract remains intentionally RED rather than being silently green-painted.

## P0 / phone firewall

This skill has no phone/P0 authority. Phone Runtime, Phone Hands, recovery queues/relays, Nightcore, Pocket TTS, Chromium, Context Organs, and physical acceptance remain untouched.
