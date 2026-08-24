# Operator Receipt Identity Fieldset

## Purpose
Keep final v4 receipt identity/raw-linkage reverification from accepting a re-signed undeclared field merely because its deterministic digest and raw-evidence SHA were recomputed.

This skill composes the existing final receipt owner, self-integrity owner, bounded projector, and derivation-custody law. It creates no second receipt owner/projector, descriptor authority, runtime controller, phone path, or P0 organ.

## Core laws
`MATCHING FINAL DIGEST != EXACT FINAL FIELD NAMESPACE`.

`MATCHING RAW EVIDENCE SHA != PERMISSION FOR A RE-SIGNED HITCHHIKER FIELD`.

`IDENTITY REVERIFICATION MUST FAIL CLOSED ON UNDECLARED OR MISSING FINAL FIELDS BEFORE DIGEST TRUST`.

`FINAL v4 FIELDSET = EXISTING SELF-INTEGRITY RECEIPT FIELDS UNION OPERATOR-OWNED FIELDS UNION DENIED-CAPABILITY FIELDS, EXACTLY`.

`INTENTIONAL EXACT-FALSE CAPABILITY REASSERTION != UNDECLARED FIELD`; the namespace is a set union and value semantics remain owned by existing gates.

`SOURCE POLICY != OWNER_WIRED != REGRESSION_EXECUTED != TESTED != RUNTIME != DEPLOYED != CALLABLE != EXECUTED != DELIVERED != ACCEPTED`.

## Supporting source
- `tools/try_forever_operator_receipt_identity_fieldset.py` defines the exact current self-integrity receipt vocabulary and the fail-closed final-union gate.
- `tools/test_try_forever_operator_receipt_identity_fieldset.py` is SOURCE / UNEXECUTED and binds that vocabulary to the real existing self-integrity output while attacking undeclared, missing, and duplicate-declaration cases.
- `tools/test_try_forever_operator_receipt_identity_fieldset_owner_boundary.py` is intentionally RED / SOURCE / UNEXECUTED until the existing final owner consumes the gate in `_require_final_receipt_contract`.

## Existing-owner promotion
`patches/try-forever-operator-receipt-identity-fieldset-owner.patch` is locked to authenticated final-owner blob `952a7de0e7f14b130264df7e5573fc8cd54a3928` and is `PROPOSED_NOT_APPLIED`.

The surgery is deliberately narrow: import the supporting gate and call it from the existing `_require_final_receipt_contract(...)` before deterministic digest trust. Because `verify_operator_receipt_against_raw_evidence(...)` already calls `verify_operator_receipt_identity(...)`, the same owner repair also closes raw-linkage-only hitchhikers without duplicating the gate.

Current owner consumption: **NO / RED**.

## Capability truth — 2026-08-24 13:00 CT
- supporting exact-fieldset identity policy: **YES / SOURCE**;
- supporting regression: **YES / UNEXECUTED**;
- owner-boundary regression: **YES / RED / UNEXECUTED**;
- exact owner surgery: **YES / PROPOSED_NOT_APPLIED**;
- authenticated owner readback: **YES**;
- owner identity/raw-linkage fieldset consumption: **NO**;
- TESTED: **NO**;
- runtime UI/TalkBack: **NO**;
- deployed/callable/executed/delivered/accepted: **NO**.

## Accessibility / evidence consequence
A bounded operator receipt is an accessibility-facing evidence object even when it is not runtime TalkBack output. Unknown re-signed fields must fail closed rather than becoming future unreviewed prose/capability surface. Keep raw machine evidence separate and do not use the display membrane to sanitize contradictory source evidence.

## P0 / phone firewall
Consume no Phone Hands ticket, primary-phone execution, recovery queue/relay, Nightcore, Pocket TTS, Chromium, Context Organs, physical acceptance, or P0 coordination. P0 evidence remains read-only.
