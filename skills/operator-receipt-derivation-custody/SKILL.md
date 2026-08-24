# Operator Receipt Derivation Custody

## Purpose
Prove that the bounded upstream fields inside the final descriptor-shadow operator receipt were actually derived from the supplied raw descriptor-shadow evidence through the existing self-integrity/projector chain, without allowing undeclared final fields to hitchhike inside a re-signed v4 envelope.

This skill creates no second receipt owner, projector, descriptor authority, runtime controller, phone path, or P0 organ.

## Core laws
`MATCHING FINAL RECEIPT DIGEST != PROOF OF RAW -> BOUNDED PROJECTION DERIVATION`.

`MATCHING RAW EVIDENCE SHA != PROOF THAT SUMMARY / STATUS / COMPARISON FIELDS CAME FROM THAT RAW EVIDENCE`.

`EXPECTED DERIVED FIELDS AS A SUBSET != EXACT FINAL v4 FIELD NAMESPACE`.

`A RE-SIGNED UNKNOWN FIELD != AN ADMITTED RECEIPT FIELD`.

`DERIVATION CUSTODY = RECOMPUTE EXISTING SELF-INTEGRITY/PROJECTOR OUTPUT FROM THE SUPPLIED RAW MAPPING + REQUIRE EXACT UPSTREAM FIELD PARITY`.

`FINAL FIELDSET CUSTODY = DERIVED PROJECTION FIELDS + EXPLICIT FINAL-OWNER FIELD ALLOWLIST, EXACTLY`.

`SOURCE_WIRED != REGRESSION_EXECUTED != TESTED != RUNTIME != DEPLOYED != CALLABLE != EXECUTED != DELIVERED != ACCEPTED`.

## Existing owners
- `tools/try_forever_owner_surgery_descriptor_shadow_audit.py` remains the raw descriptor-shadow source owner.
- `tools/try_forever_owner_surgery_shadow_receipt_self_integrity.py` remains the self-integrity owner.
- `tools/try_forever_owner_surgery_shadow_receipt_projection.py` remains the sole bounded display projector.
- `tools/try_forever_owner_surgery_descriptor_shadow_operator_receipt.py` remains the final operator receipt owner.

## Supporting source
`tools/try_forever_operator_receipt_derivation_custody.py` reuses the existing self-integrity/projector chain and requires exact parity for every field that chain derives.

Default supporting mode still leaves final-owner fields outside this policy's ownership. A new explicit `allowed_extra_fields` mode closes the complete receipt field namespace and rejects undeclared or missing final fields. The policy also rejects non-string field names and duplicate/empty final-field declarations.

This is supporting source only. It grants no authority, regression execution, TESTED state, runtime state, deployment, phone delivery, or acceptance.

## Existing-owner source wiring
The final v4 owner already exposes `verify_operator_receipt_derivation_against_raw_evidence(repo_root, receipt, raw_result)` and calls it in the normal build path. Authenticated current owner blob before this heartbeat's proposed fieldset surgery: `b1da64ae3d50c26dd415d73e6000fb5ddda51183`.

That owner currently calls `require_operator_receipt_projection_derivation(...)` without the new exact-fieldset allowlist. Therefore:
- projection derivation owner wiring: **YES / SOURCE_WIRED**;
- final exact-fieldset owner wiring: **NO / RED**.

Exact base-locked owner surgery is preserved at `patches/try-forever-operator-receipt-fieldset-custody-owner.patch` with status `CORRECTED_PROPOSED_NOT_APPLIED`. Patch existence is not implementation.

## Regression source
`tools/test_try_forever_operator_receipt_derivation_custody.py` is SOURCE / UNEXECUTED. It now pins both modes:
- default supporting mode permits unrelated final-owner fields because it does not own them;
- exact final-owner mode rejects an undeclared re-signed field;
- exact final-owner mode rejects a missing declared field;
- duplicate final-field declarations fail closed;
- existing counterfeit summary/status/missing-derived-field/wrong-schema wounds remain rejected.

`tools/test_try_forever_operator_receipt_derivation_owner_boundary.py` is SOURCE / UNEXECUTED and intentionally RED against the current owner. It requires the existing final-owner derivation helper to pass `allowed_extra_fields` directly into the existing derivation policy; nested-function counterfeit calls remain excluded by direct-body AST evidence.

## Current capability truth — 2026-08-24 10:03 CT
- supporting derivation policy: **YES / SOURCE**;
- exact-fieldset supporting mode: **YES / SOURCE**;
- final owner projection-derivation consumption: **YES / SOURCE_WIRED**;
- final owner exact-fieldset consumption: **NO / RED**;
- authenticated owner readback: **YES**;
- hostile supporting regression: **YES / UNEXECUTED**;
- owner-boundary regression: **YES / UNEXECUTED**;
- exact owner surgery: **YES / CORRECTED_PROPOSED_NOT_APPLIED**;
- regression execution: **NO**;
- TESTED: **NO**;
- runtime UI/TalkBack: **NO**;
- deployed/callable/executed/delivered/accepted: **NO**.

## P0 / phone firewall
Consume no Phone Hands ticket, primary-phone execution, recovery queue/relay, Nightcore, Pocket TTS, Chromium, Context Organs, physical acceptance, or P0 coordination. P0 evidence remains read-only.
