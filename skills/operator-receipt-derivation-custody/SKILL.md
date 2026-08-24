# Operator Receipt Derivation Custody

## Purpose
Prove that the bounded upstream fields inside the final descriptor-shadow operator receipt were actually derived from the supplied raw descriptor-shadow evidence through the existing self-integrity/projector chain.

This skill creates no second receipt owner, projector, descriptor authority, runtime controller, phone path, or P0 organ.

## Core laws
`MATCHING FINAL RECEIPT DIGEST != PROOF OF RAW -> BOUNDED PROJECTION DERIVATION`.

`MATCHING RAW EVIDENCE SHA != PROOF THAT SUMMARY / STATUS / COMPARISON FIELDS CAME FROM THAT RAW EVIDENCE`.

`RAW LINKAGE + FINAL IDENTITY + UPSTREAM CONTRACT IDENTITY ARE NECESSARY BUT NOT SUFFICIENT FOR DERIVATION CUSTODY`.

`DERIVATION CUSTODY = RECOMPUTE EXISTING SELF-INTEGRITY/PROJECTOR OUTPUT FROM THE SUPPLIED RAW MAPPING + REQUIRE EXACT UPSTREAM FIELD PARITY`.

`DERIVATION CUSTODY MUST NOT EMBED RAW MACHINE EVIDENCE OR CREATE A SECOND PROJECTOR`.

`SUPPORTING SOURCE != OWNER WIRED != REGRESSION EXECUTED != TESTED != RUNTIME != DEPLOYED != CALLABLE != EXECUTED != DELIVERED != ACCEPTED`.

## Existing owners
- `tools/try_forever_owner_surgery_descriptor_shadow_audit.py` remains the raw descriptor-shadow source owner.
- `tools/try_forever_owner_surgery_shadow_receipt_self_integrity.py` remains the self-integrity owner.
- `tools/try_forever_owner_surgery_shadow_receipt_projection.py` remains the sole bounded display projector.
- `tools/try_forever_owner_surgery_descriptor_shadow_operator_receipt.py` remains the final operator receipt owner.

## Supporting source
`tools/try_forever_operator_receipt_derivation_custody.py` reuses the existing self-integrity/projector chain and requires exact parity for every field that chain derives. Final operator-owned fields are deliberately outside this supporting policy.

The policy returns a bounded source receipt with every capability state false. It grants no authority or runtime state.

## Regression source
`tools/test_try_forever_operator_receipt_derivation_custody.py` is SOURCE / UNEXECUTED. It proves the supporting gate rejects:
- counterfeit summary text;
- counterfeit status;
- missing derived fields;
- wrong raw source schema;
while leaving unrelated final-owner fields outside its ownership.

`tools/test_try_forever_operator_receipt_derivation_owner_boundary.py` is intentionally RED / UNEXECUTED. It requires the existing final owner to gain a derivation reverification helper that consumes this policy and requires the normal build path to use that helper before returning a final receipt.

## Current capability truth — 2026-08-24 09:07 CT
- supporting derivation policy: **YES / SOURCE**;
- hostile supporting regression: **YES / UNEXECUTED**;
- RED existing-owner boundary: **YES / UNEXECUTED**;
- final owner derivation-custody consumption: **NO**;
- regression execution: **NO**;
- TESTED: **NO**;
- runtime UI/TalkBack: **NO**;
- deployed/callable/executed/delivered/accepted: **NO**.

## P0 / phone firewall
Consume no Phone Hands ticket, primary-phone execution, recovery queue/relay, Nightcore, Pocket TTS, Chromium, Context Organs, physical acceptance, or P0 coordination. P0 evidence remains read-only.
