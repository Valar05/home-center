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

`SOURCE_WIRED != REGRESSION_EXECUTED != TESTED != RUNTIME != DEPLOYED != CALLABLE != EXECUTED != DELIVERED != ACCEPTED`.

## Existing owners
- `tools/try_forever_owner_surgery_descriptor_shadow_audit.py` remains the raw descriptor-shadow source owner.
- `tools/try_forever_owner_surgery_shadow_receipt_self_integrity.py` remains the self-integrity owner.
- `tools/try_forever_owner_surgery_shadow_receipt_projection.py` remains the sole bounded display projector.
- `tools/try_forever_owner_surgery_descriptor_shadow_operator_receipt.py` remains the final operator receipt owner.

## Supporting source
`tools/try_forever_operator_receipt_derivation_custody.py` reuses the existing self-integrity/projector chain and requires exact parity for every field that chain derives. Final operator-owned fields are deliberately outside this supporting policy.

The policy returns a bounded source receipt with every capability state false. It grants no authority or runtime state.

## Existing-owner source wiring
The final v4 receipt owner now exposes `verify_operator_receipt_derivation_against_raw_evidence(repo_root, receipt, raw_result)`.

That helper first requires the existing v4 receipt identity + raw-evidence linkage membrane, then consumes `require_operator_receipt_projection_derivation(...)`. The normal `build_descriptor_shadow_operator_receipt(...)` path calls this stronger helper before return.

Authenticated Home Center GitHub-admin surgery:
- owner commit: `492db0348caab7307098ff2e487fae300943044b`;
- resulting owner blob: `b1da64ae3d50c26dd415d73e6000fb5ddda51183`.

This is existing-owner SOURCE_WIRED evidence only. It is not regression execution, TESTED state, runtime behavior, deployment, phone callability, delivery, or acceptance.

## Regression source
`tools/test_try_forever_operator_receipt_derivation_custody.py` is SOURCE / UNEXECUTED. It proves the supporting gate rejects:
- counterfeit summary text;
- counterfeit status;
- missing derived fields;
- wrong raw source schema;
while leaving unrelated final-owner fields outside its ownership.

`tools/test_try_forever_operator_receipt_derivation_owner_boundary.py` is SOURCE / UNEXECUTED. It now pins the source-wired owner shape: the existing final owner must retain the derivation reverification helper, that helper must directly consume the supporting derivation policy, and the normal build path must directly invoke the helper before return.

Code-first review repaired the first owner fixture before checkpoint: its initial `ast.walk` call did not truly prune nested function bodies. The final source uses direct-body AST visitation so nested-function counterfeit calls cannot satisfy owner evidence.

## Current capability truth — 2026-08-24 09:07 CT
- supporting derivation policy: **YES / SOURCE**;
- final owner derivation-custody consumption: **YES / SOURCE_WIRED**;
- authenticated owner readback: **YES**;
- hostile supporting regression: **YES / UNEXECUTED**;
- owner-boundary regression: **YES / UNEXECUTED**;
- regression execution: **NO**;
- TESTED: **NO**;
- runtime UI/TalkBack: **NO**;
- deployed/callable/executed/delivered/accepted: **NO**.

## P0 / phone firewall
Consume no Phone Hands ticket, primary-phone execution, recovery queue/relay, Nightcore, Pocket TTS, Chromium, Context Organs, physical acceptance, or P0 coordination. P0 evidence remains read-only.
