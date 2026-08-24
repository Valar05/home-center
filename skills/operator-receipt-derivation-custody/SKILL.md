# Operator Receipt Derivation Custody

## Purpose
Prove that the bounded upstream fields inside the final descriptor-shadow operator receipt were actually derived from the supplied raw descriptor-shadow evidence through the existing self-integrity/projector chain, while preventing undeclared final fields or ambiguous namespace ownership from hitchhiking inside a re-signed v4 envelope.

This skill creates no second receipt owner, projector, descriptor authority, runtime controller, phone path, or P0 organ.

## Core laws
`MATCHING FINAL RECEIPT DIGEST != PROOF OF RAW -> BOUNDED PROJECTION DERIVATION`.

`MATCHING RAW EVIDENCE SHA != PROOF THAT SUMMARY / STATUS / COMPARISON FIELDS CAME FROM THAT RAW EVIDENCE`.

`EXPECTED DERIVED FIELDS AS A SUBSET != EXACT FINAL v4 FIELD NAMESPACE`.

`A RE-SIGNED UNKNOWN FIELD != AN ADMITTED RECEIPT FIELD`.

`DERIVED PROJECTION NAMESPACE ∩ FINAL-OWNER NAMESPACE MUST BE EMPTY`.

`DERIVATION CUSTODY = RECOMPUTE EXISTING SELF-INTEGRITY/PROJECTOR OUTPUT FROM THE SUPPLIED RAW MAPPING + REQUIRE EXACT UPSTREAM FIELD PARITY`.

`FINAL FIELDSET CUSTODY = DERIVED PROJECTION FIELDS + EXPLICIT DISJOINT FINAL-OWNER FIELD ALLOWLIST, EXACTLY`.

`SOURCE_WIRED != REGRESSION_EXECUTED != TESTED != RUNTIME != DEPLOYED != CALLABLE != EXECUTED != DELIVERED != ACCEPTED`.

## Existing owners
- `tools/try_forever_owner_surgery_descriptor_shadow_audit.py` remains the raw descriptor-shadow source owner.
- `tools/try_forever_owner_surgery_shadow_receipt_self_integrity.py` remains the self-integrity owner.
- `tools/try_forever_owner_surgery_shadow_receipt_projection.py` remains the sole bounded display projector.
- `tools/try_forever_owner_surgery_descriptor_shadow_operator_receipt.py` remains the final operator receipt owner.

## Supporting source
`tools/try_forever_operator_receipt_derivation_custody.py` reuses the existing self-integrity/projector chain and requires exact parity for every field that chain derives.

Default supporting mode still leaves final-owner fields outside this policy's ownership. Explicit `allowed_extra_fields` mode closes the complete receipt field namespace and rejects undeclared or missing final fields. It also rejects non-string/empty field names, duplicate final-field declarations, and overlap between derived projection fields and the final-owner allowlist.

This is supporting source only. It grants no authority, regression execution, TESTED state, runtime state, deployment, phone delivery, or acceptance.

## Existing-owner source wiring
Authenticated owner surgery commit: `2c7685cf9e5e2a8315c0da827bd1c7a9a6ea848d`.
Authenticated resulting owner blob: `952a7de0e7f14b130264df7e5573fc8cd54a3928`.

The final v4 owner now calls `require_operator_receipt_projection_derivation(...)` with the actual final-owner field families:
- `OPERATOR_OWNED_RECEIPT_FIELDS`;
- `FINAL_DENIED_CAPABILITY_FIELDS`.

Therefore:
- projection derivation owner wiring: **YES / SOURCE_WIRED**;
- final exact-fieldset owner wiring: **YES / SOURCE_WIRED**;
- final namespace disjointness: **YES / SUPPORTING SOURCE**, consumed by the owner because its current allowlist is disjoint.

Applied provenance is preserved at `patches/try-forever-operator-receipt-fieldset-custody-owner.patch`, status `APPLIED_SOURCE`.

## Regression source
`tools/test_try_forever_operator_receipt_derivation_custody.py` is SOURCE / UNEXECUTED. It pins:
- default supporting mode permits unrelated final-owner fields because it does not own them;
- exact final-owner mode rejects undeclared re-signed fields;
- exact final-owner mode rejects missing declared fields;
- duplicate final-field declarations fail closed;
- derived/final namespace overlap fails closed;
- existing counterfeit summary/status/missing-derived-field/wrong-schema wounds remain rejected.

`tools/test_try_forever_operator_receipt_derivation_owner_boundary.py` is SOURCE / UNEXECUTED and now requires more than a keyword-shaped call. Direct owner evidence must supply the exact starred field families `OPERATOR_OWNED_RECEIPT_FIELDS` and `FINAL_DENIED_CAPABILITY_FIELDS`; empty/wrong allowlists are `PARTIAL_UNSAFE` source evidence.

## Current capability truth — 2026-08-24 11:19 CT
- supporting derivation policy: **YES / SOURCE**;
- exact-fieldset supporting mode: **YES / SOURCE**;
- namespace-disjointness supporting rule: **YES / SOURCE**;
- final owner projection-derivation consumption: **YES / SOURCE_WIRED**;
- final owner exact-fieldset consumption: **YES / SOURCE_WIRED**;
- authenticated owner readback: **YES**;
- hostile supporting regression: **YES / UNEXECUTED**;
- owner-boundary regression: **YES / UNEXECUTED**;
- applied owner surgery provenance: **YES / APPLIED_SOURCE**;
- regression execution: **NO**;
- TESTED: **NO**;
- runtime UI/TalkBack: **NO**;
- deployed/callable/executed/delivered/accepted: **NO**.

## P0 / phone firewall
Consume no Phone Hands ticket, primary-phone execution, recovery queue/relay, Nightcore, Pocket TTS, Chromium, Context Organs, physical acceptance, or P0 coordination. P0 evidence remains read-only.
