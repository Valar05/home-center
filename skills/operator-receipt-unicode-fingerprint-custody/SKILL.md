# Operator Receipt Unicode Fingerprint Custody

## Purpose
Keep the existing final-v4 descriptor-shadow operator receipt identity deterministic when an allowed JSON-shaped field contains hostile Python surrogate text, without changing ordinary valid-Unicode receipt digests or creating another receipt owner/digest authority.

This skill owns evidence-identity composition only. It does **not** grant artifact authority, TESTED state, runtime capability, deployment, callability, execution, delivery, acceptance, phone execution, or P0 authority.

## Core laws
`VALID-UNICODE DIGEST STABILITY != PERMISSION TO CRASH ON SURROGATE-BEARING EVIDENCE`.

`SHARED EVIDENCE FINGERPRINT ORGAN != SECOND RECEIPT OWNER`.

`RECEIPT SHA-256 != ARTIFACT IDENTITY != PROMOTION AUTHORITY != TESTED != RUNTIME`.

`HELPER IMPORT ELSEWHERE != DIRECT FINAL-RECEIPT OWNER WIRING`.

`OWNER SOURCE_WIRED != REGRESSION EXECUTED != TESTED`.

## Existing organ reused
`tools/try_forever_canonical_result_fingerprint.py` is the existing surrogate-safe deterministic JSON evidence-identity organ. It uses the same sorted compact `ensure_ascii=false`, `allow_nan=false` JSON shape as the final operator receipt digest, with UTF-8 `surrogatepass` only for the otherwise-unencodable surrogate case.

For ordinary valid Unicode, this produces the same bytes and SHA-256 as ordinary UTF-8 encoding. Reuse it; do not create another deterministic JSON fingerprint implementation.

## Current owner truth
Existing final owner: `tools/try_forever_owner_surgery_descriptor_shadow_operator_receipt.py`.

Authenticated pre-surgery owner blob: `82af7cc572d2a95624fb549c387946068483c7e3`.

Applied owner surgery commit: `0ece6702d812d5ec6fea1b924526365fb385673e`.

Authenticated resulting owner blob: `2920ae28ea56a9840cf7ca05a57ff9231469cb04`.

Its `_operator_receipt_sha256(...)` now directly calls `canonical_result_sha256(...)` from the existing fingerprint organ. The local deterministic helper remains only for the deliberately `ensure_ascii=true` raw-machine-evidence digest path; it is no longer the final-v4 operator receipt identity owner.

Therefore:
- shared canonical-result fingerprint organ: **YES / SOURCE_WIRED in descriptor shadow**;
- final-v4 operator receipt reuse: **YES / SOURCE_WIRED**;
- exact surgery provenance: `patches/try-forever-operator-receipt-unicode-fingerprint-owner.patch` = **APPLIED_SOURCE**;
- hostile behavior regression: `tools/test_try_forever_operator_receipt_unicode_fingerprint.py` = **SOURCE / UNEXECUTED**;
- direct-owner boundary regression: `tools/test_try_forever_operator_receipt_unicode_fingerprint_owner_boundary.py` = **SOURCE / UNEXECUTED**;
- TESTED/runtime/deployed/callable/executed/delivered/accepted: **NO**.

## Acceptance preservation
Owner wiring remains source-valid only while authenticated readback proves the existing final owner directly delegates `_operator_receipt_sha256(...)` to the shared fingerprint organ or an exactly equivalent existing-organ composition while preserving ordinary valid-Unicode digest identity.

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
