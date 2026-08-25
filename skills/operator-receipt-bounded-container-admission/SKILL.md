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
- **TEMPORAL EVIDENCE IS RECEIPT EVIDENCE; IT DOES NOT GET A MAPPING EXCEPTION**.
- **DIAGNOSTIC CONTEXT != CANONICAL RECEIPT IDENTITY**.
- **UNBOUNDED DIAGNOSTIC INPUT != BOUNDED DIAGNOSTIC PROJECTION**.
- Reject unsupported container shape; do not normalize it into authority.
- Preserve accepted diagnostic text exactly; only the existing diagnostic projector may escape or whole-identity-collapse it for prose.
- This admission layer owns no semantic receipt authority, digest authority, TESTED/runtime state, deployment, callability, execution, delivery, acceptance, phone, or P0 mutation.

## Existing organs

Compose the existing snapshot/receipt organs. Do not create another receipt owner, snapshot owner, projector, temporal owner, verifier daemon, or phone execution lane.

Current source surfaces:
- `tools/try_forever_operator_receipt_snapshot_admission_policy.py` — **IMPLEMENTED SOURCE**.
- `tools/try_forever_operator_receipt_snapshot_custody.py` — **EXISTING OWNER SOURCE_WIRED**.
- `tools/try_forever_operator_receipt_derivation_custody.py` — **EXACT-CONTAINER SOURCE_WIRED**.
- `tools/try_forever_operator_receipt_identity_fieldset.py` — **EXACT-CONTAINER SOURCE_WIRED**.
- `tools/try_forever_owner_surgery_shadow_receipt_projection.py` — **EXACT-CONTAINER SOURCE_WIRED**.
- `tools/try_forever_owner_surgery_shadow_receipt_self_integrity.py` — **EXACT-CONTAINER SOURCE_WIRED**.
- `tools/try_forever_owner_surgery_shadow_temporal_binding.py` — **EXACT-CONTAINER SOURCE_WIRED**.
- `tools/try_forever_owner_surgery_shadow_temporal_receipt_integrity.py` — **EXACT-CONTAINER SOURCE_WIRED**.
- `tools/try_forever_owner_surgery_descriptor_shadow_operator_receipt.py` — **FINAL-v4 PUBLIC TYPE CONTRACT SOURCE_WIRED** at authenticated owner blob `42cd1fceccfae861e9e5edd129b145b15969d401`.
- `tools/test_try_forever_operator_receipt_exact_container_surfaces.py` — **CONVERGENCE SOURCE / UNEXECUTED**; now includes derivation, fieldset, temporal binding, and temporal receipt-integrity callback/type boundaries.
- `tools/test_try_forever_shadow_receipt_exact_snapshot_boundary.py` — **SOURCE / UNEXECUTED**.
- `tools/test_try_forever_operator_receipt_public_type_contract.py` — **CONVERGENCE SOURCE / UNEXECUTED**.
- `patches/try-forever-operator-receipt-public-type-contract.patch` — **APPLIED_SOURCE** by commit `04767647bcfc9ef29b6b867d5db7c7e6e8dbc66f`.

## Current source truth

The snapshot-custody owner:
- admits root and nested objects only through exact built-in-dict admission before traversal;
- rejects Mapping subclasses/custom mappings without invoking caller-owned iteration;
- admits root diagnostic context before escaping/projection;
- preserves exact key/value identity, finite budgets, one-observation detachment, and the capability membrane.

The derivation and identity-fieldset surfaces advertise and admit exact built-in `dict` receipt/raw inputs and exact tuple field vocabularies before traversal.

The descriptor-shadow display projector and self-integrity owner advertise exact built-in `dict` input and consume the bounded snapshot-custody organ before semantic reads.

The temporal-binding policy and its receipt-integrity context gate now advertise exact built-in `dict` canonical/shadow evidence and snapshot both caller-owned inputs before schema, identity, witness, comparison, backend, status, or capability reads. They reuse the existing snapshot-custody organ; no second temporal/snapshot owner was created.

The final v4 operator receipt reverification APIs advertise the same exact built-in `dict` receipt/raw inputs already required by `snapshot_verification_inputs(...)`. Runtime rejection and public type capability therefore converge at source across the known receipt and temporal chain.

So:
- supporting admission policy: **YES / SOURCE**;
- snapshot owner consumption: **YES / SOURCE_WIRED**;
- derivation exact-container custody: **YES / SOURCE_WIRED**;
- fieldset exact-container custody: **YES / SOURCE_WIRED**;
- projector exact-container custody: **YES / SOURCE_WIRED**;
- self-integrity exact-container custody: **YES / SOURCE_WIRED**;
- temporal-binding exact-container custody: **YES / SOURCE_WIRED**;
- temporal receipt-integrity exact-container custody: **YES / SOURCE_WIRED**;
- final-v4 public type-contract convergence: **YES / SOURCE_WIRED**;
- known receipt/temporal exact-container convergence: **YES / SOURCE**;
- hostile/convergence regression source: **YES / UNEXECUTED**;
- TESTED/runtime UI/runtime TalkBack/deployed/callable/executed/delivered/accepted: **NO**.

## Review scars

Earlier snapshot hardening bounded values produced *after* Mapping iteration, which did not bound arbitrary Python work executed by Mapping itself. Admission moved ahead of traversal. The 2026-08-25 09:00 review found the same smell in derivation and final-fieldset custody and repaired those surfaces. The 11:00 review repaired the display projector and self-integrity owner. The 12:01 review found the final-v4 reverification API still advertised broader Mapping capability even though runtime already rejected it. The 12:58 repair applied that existing owner surgery and authenticated result blob `42cd1fceccfae861e9e5edd129b145b15969d401`.

The 14:03 review then found the phrase **whole known receipt stack convergence** was still too broad: both temporal public surfaces retained arbitrary `Mapping` contracts and read caller-owned evidence before a snapshot. That contradiction was repaired by composing the existing snapshot-custody organ into both temporal entrypoints and extending the existing hostile exact-container regression. Regression execution remains separate; source convergence does not advance TESTED.

## P0 / phone firewall

This skill has no phone/P0 authority. Phone Runtime, Phone Hands, recovery queues/relays, Nightcore, Pocket TTS, Chromium, Context Organs, and physical acceptance remain untouched.