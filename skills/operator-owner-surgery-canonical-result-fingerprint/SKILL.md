# Operator Owner Surgery Canonical Result Fingerprint

## Purpose
Keep descriptor-shadow and final operator-receipt identities deterministic even when JSON-shaped source evidence contains hostile Unicode or pathological recursive/container shapes.

This skill owns evidence identity only. It does **not** own canonical promotion authority, a second descriptor authority, a second receipt projector, filesystem atomicity, Android runtime, phone execution, P0 recovery, deployment, delivery, or acceptance.

## Core laws
`CANONICAL RESULT FINGERPRINT != CANONICAL ARTIFACT IDENTITY != PROMOTION AUTHORITY`.

`EXACT BUILT-IN DICT OBSERVATION != ARBITRARY PYTHON MAPPING / DICT SUBCLASS`.

`VALID-UNICODE FINGERPRINT STABILITY != PERMISSION TO CRASH ON SURROGATE-BEARING SOURCE EVIDENCE`.

`HOSTILE RECURSION / OVERFLOW != PERMISSION TO ESCAPE THE TYPED FINGERPRINT BOUNDARY`.

`SOURCE_WIRED != REGRESSION EXECUTED != TESTED != RUNTIME != DEPLOYED != DELIVERED != ACCEPTED`.

## Supporting source
`tools/try_forever_canonical_result_fingerprint.py` is **IMPLEMENTED SOURCE**.

Admission now begins with one exact built-in `dict`. Custom `Mapping` / `dict` subclasses are rejected before JSON serialization so caller-owned container callbacks cannot participate in fingerprint evidence work. Existing authoritative consumers already pass detached plain dictionaries, so this closes the hostile container channel without changing ordinary result identity.

Serialization remains:
- sorted JSON object keys;
- compact separators;
- `ensure_ascii=false`;
- `allow_nan=false`;
- UTF-8 encoding with `surrogatepass` only for otherwise-unencodable surrogate evidence.

Ordinary valid-Unicode payloads therefore retain the existing fingerprint value. JSON encoder `RecursionError` / `OverflowError` remain contained inside `CanonicalResultFingerprintError`.

## Regression source
`tools/test_try_forever_canonical_result_fingerprint.py` is **REGRESSION SOURCE / UNEXECUTED**.

It pins:
- insertion-order independence;
- material-evidence sensitivity;
- exact parity with the legacy fingerprint for valid Unicode;
- deterministic surrogate-bearing evidence;
- rejection of non-finite numeric evidence;
- typed rejection of deeply recursive hostile evidence;
- rejection of a hostile `dict` subclass **before** its overridden `items()` callback can execute.

`tools/test_try_forever_descriptor_shadow_canonical_result_fingerprint_owner_boundary.py` remains **REGRESSION SOURCE / UNEXECUTED**. Source inspection shows the descriptor-shadow owner consumes the shared organ; fixture execution is still a separate capability state.

## Current owner truth
The shared organ has two current source consumers in this branch:

1. `tools/try_forever_owner_surgery_descriptor_shadow_audit.py`, schema `try-forever-owner-surgery-descriptor-shadow.v3` — **SOURCE_WIRED**.
2. `tools/try_forever_owner_surgery_descriptor_shadow_operator_receipt.py`, schema `try-forever-owner-surgery-descriptor-shadow-operator-receipt.v4` — **SOURCE_WIRED** through `_operator_receipt_sha256(...)`.

Current capability truth:
- fingerprint organ implementation: **YES / SOURCE**;
- exact built-in-dict fingerprint admission: **YES / SOURCE**;
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
