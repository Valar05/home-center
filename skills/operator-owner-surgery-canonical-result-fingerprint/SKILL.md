# Operator Owner Surgery Canonical Result Fingerprint

## Purpose
Keep descriptor-shadow and final operator-receipt identities deterministic even when JSON-shaped source evidence contains hostile Unicode or pathological recursive/container shapes.

This skill owns evidence identity only. It does **not** own canonical promotion authority, a second descriptor authority, a second receipt projector, filesystem atomicity, Android runtime, phone execution, P0 recovery, deployment, delivery, or acceptance.

## Core laws
`CANONICAL RESULT FINGERPRINT != CANONICAL ARTIFACT IDENTITY != PROMOTION AUTHORITY`.

`VALID-UNICODE FINGERPRINT STABILITY != PERMISSION TO CRASH ON SURROGATE-BEARING SOURCE EVIDENCE`.

`HOSTILE RECURSION / OVERFLOW != PERMISSION TO ESCAPE THE TYPED FINGERPRINT BOUNDARY`.

`SURROGATE-SAFE RECEIPT IDENTITY != FILESYSTEM ATOMICITY`.

`SOURCE_WIRED != REGRESSION EXECUTED != TESTED != RUNTIME != DEPLOYED != DELIVERED != ACCEPTED`.

## Supporting source
`tools/try_forever_canonical_result_fingerprint.py` is **IMPLEMENTED SOURCE**.

It uses the existing descriptor-shadow canonical serialization shape:
- sorted JSON object keys;
- compact separators;
- `ensure_ascii=false`;
- `allow_nan=false`;
- UTF-8 encoding with `surrogatepass` only for otherwise-unencodable surrogate evidence.

Ordinary valid-Unicode payloads therefore retain the existing fingerprint value. The organ now also contains JSON encoder `RecursionError` / `OverflowError` inside `CanonicalResultFingerprintError` rather than leaking process-level exceptions through receipt verification.

## Regression source
`tools/test_try_forever_canonical_result_fingerprint.py` is **REGRESSION SOURCE / UNEXECUTED**.

It pins:
- insertion-order independence;
- material-evidence sensitivity;
- exact parity with the legacy fingerprint for valid Unicode;
- deterministic surrogate-bearing evidence;
- rejection of non-finite numeric evidence;
- typed rejection of deeply recursive hostile evidence.

`tools/test_try_forever_descriptor_shadow_canonical_result_fingerprint_owner_boundary.py` remains **REGRESSION SOURCE / UNEXECUTED**. Its descriptor-shadow owner-wiring expectation is satisfied by authenticated source, but the fixture has not executed and therefore grants no TESTED state.

## Owner truth
The shared organ currently has two authenticated consumers in this TRY FOREVER branch:

1. `tools/try_forever_owner_surgery_descriptor_shadow_audit.py`, schema `try-forever-owner-surgery-descriptor-shadow.v3` — **SOURCE_WIRED** since owner surgery `f57e556e6025f93b6b3b01ec9cedac95868b28e7` (result blob `44bc3af31e645f33abf542139995c3707ef8e210`).
2. `tools/try_forever_owner_surgery_descriptor_shadow_operator_receipt.py`, schema `try-forever-owner-surgery-descriptor-shadow-operator-receipt.v4` — **SOURCE_WIRED** for final bounded operator-receipt identity through `_operator_receipt_sha256(...)` (authenticated owner blob before this heartbeat: `2920ae28ea56a9840cf7ca05a57ff9231469cb04`).

At this checkpoint:
- fingerprint organ implementation: **YES / SOURCE**;
- descriptor-shadow owner consumption: **YES / SOURCE_WIRED**;
- final-v4 operator-receipt owner consumption: **YES / SOURCE_WIRED**;
- hostile regression source: **YES / UNEXECUTED**;
- TESTED: **NO**;
- runtime UI/TalkBack: **NO**;
- deployed/callable/executed/delivered/accepted: **NO**.

## Duplicate-architecture law
Do not create a second descriptor shadow, receipt owner, or fingerprint implementation. Existing owners consume this shared evidence-identity organ; future work must preserve that ownership.

## P0 / phone firewall
Consumes no Phone Hands, primary-phone command, P0 recovery queue, Nightcore, Pocket TTS, Chromium, Context Organs, physical acceptance, or P0 coordination.
