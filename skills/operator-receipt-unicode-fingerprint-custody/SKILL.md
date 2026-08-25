# Operator Receipt Unicode Fingerprint Custody

## Purpose
Keep the existing final-v4 descriptor-shadow operator receipt identity deterministic when an allowed JSON-shaped field contains hostile Python surrogate text, without changing ordinary valid-Unicode receipt digests or creating another receipt owner/digest authority.

This skill owns evidence-identity composition only. It does **not** grant artifact authority, TESTED state, runtime capability, deployment, callability, execution, delivery, acceptance, phone execution, or P0 authority.

## Core laws
`VALID-UNICODE DIGEST STABILITY != PERMISSION TO CRASH ON SURROGATE-BEARING EVIDENCE`.

`SHARED EVIDENCE FINGERPRINT ORGAN != SECOND RECEIPT OWNER`.

`RECEIPT SHA-256 != ARTIFACT IDENTITY != PROMOTION AUTHORITY != TESTED != RUNTIME`.

`HELPER IMPORT ELSEWHERE != DIRECT FINAL-RECEIPT OWNER WIRING`.

`SUPPORTING PATCH != OWNER WIRED != REGRESSION EXECUTED`.

## Existing organ to reuse
`tools/try_forever_canonical_result_fingerprint.py` is the existing surrogate-safe deterministic JSON evidence-identity organ. It already uses the same sorted compact `ensure_ascii=false`, `allow_nan=false` JSON shape as the final operator receipt digest, with UTF-8 `surrogatepass` only for the otherwise-unencodable surrogate case.

For ordinary valid Unicode, this produces the same bytes and SHA-256 as ordinary UTF-8 encoding. Reuse it; do not create another deterministic JSON fingerprint implementation.

## Current owner wound
Existing final owner: `tools/try_forever_owner_surgery_descriptor_shadow_operator_receipt.py`.

Authenticated owner blob at this checkpoint: `82af7cc572d2a95624fb549c387946068483c7e3`.

Its `_operator_receipt_sha256(...)` still calls the local deterministic JSON helper with `ensure_ascii=false`, whose ordinary UTF-8 encoding does not carry the surrogate-safe encoding law already owned elsewhere.

Therefore:
- shared canonical-result fingerprint organ: **YES / SOURCE_WIRED in descriptor shadow**;
- final-v4 operator receipt reuse: **NO / RED**;
- exact owner surgery: `patches/try-forever-operator-receipt-unicode-fingerprint-owner.patch` = **CORRECTED_PROPOSED_NOT_APPLIED**;
- hostile behavior regression: `tools/test_try_forever_operator_receipt_unicode_fingerprint.py` = **SOURCE / UNEXECUTED**;
- direct-owner boundary regression: `tools/test_try_forever_operator_receipt_unicode_fingerprint_owner_boundary.py` = **RED SOURCE / UNEXECUTED**;
- TESTED/runtime/deployed/callable/executed/delivered/accepted: **NO**.

## Acceptance
A future owner promotion may advance only when authenticated readback proves the existing final owner directly delegates `_operator_receipt_sha256(...)` to the shared fingerprint organ (or an exactly equivalent existing-organ composition) while preserving ordinary valid-Unicode digest identity.

The hostile behavior regression must pin:
- ordinary Unicode parity with the pre-repair final-receipt algorithm;
- insertion-order independence;
- deterministic surrogate-bearing evidence;
- material evidence drift changes digest;
- non-finite numeric evidence fails closed.

The direct-owner regression must reject a helper import or mention that is not consumed in the direct `_operator_receipt_sha256(...)` owner body. Regression source is not TESTED evidence merely because it exists.

## Accessibility / contact consequence
This is evidence robustness, not a new spoken surface. Preserve existing operator-facing projection and valid-Unicode receipt identity; do not churn ordinary receipt IDs or add routine speech.

## Duplicate-architecture law
Reuse the existing final receipt owner and existing surrogate-safe fingerprint organ. Do not create a second receipt owner, receipt projector, descriptor authority, digest controller, recovery daemon, or phone path.

## P0 / phone firewall
Consumes no Phone Hands ticket, primary-phone command, P0 recovery chain, Nightcore, Pocket TTS, Chromium, Context Organs, physical acceptance, or P0 coordination.
