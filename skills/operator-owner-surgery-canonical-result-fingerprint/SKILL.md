# Operator Owner Surgery Canonical Result Fingerprint

## Purpose
Keep descriptor-shadow and final operator-receipt identities deterministic while preserving exact JSON-shaped evidence custody, including hostile Unicode and pathological Python container shapes.

This skill owns evidence identity only. It does **not** own canonical promotion authority, a second descriptor authority, a second receipt projector, filesystem atomicity, Android runtime, phone execution, P0 recovery, deployment, delivery, or acceptance.

## Core laws
`CANONICAL RESULT FINGERPRINT != CANONICAL ARTIFACT IDENTITY != PROMOTION AUTHORITY`.

`EXACT ROOT DICT != EXACT RECURSIVE JSON SHAPE`.

`PYTHON TUPLE / NON-STRING KEY / DICT SUBCLASS != JSON EVIDENCE AFTER NORMALIZATION`.

`VALID-UNICODE FINGERPRINT STABILITY != PERMISSION TO CRASH ON SURROGATE-BEARING SOURCE EVIDENCE`.

`SOURCE_WIRED != REGRESSION EXECUTED != TESTED != RUNTIME != DEPLOYED != DELIVERED != ACCEPTED`.

## Supporting source
`tools/try_forever_canonical_result_fingerprint.py` is **IMPLEMENTED SOURCE**.

Fingerprint admission now reuses the existing one-observation `snapshot_json_mapping(...)` organ before hashing. That means every nested value must already be exact JSON-shaped Python evidence:
- objects are exact built-in `dict` containers with non-empty string keys;
- arrays are exact built-in `list` containers;
- scalars are exact JSON null/boolean/int/finite-float/string shapes;
- tuples, mapping/dict subclasses, non-string keys, non-finite numbers, and other Python-only shapes fail closed before `json.dumps` can normalize them;
- existing snapshot depth/node/text/integer/encoded-size budgets bound fingerprint evidence work.

Serialization after that detached snapshot remains:
- sorted JSON object keys;
- compact separators;
- `ensure_ascii=false`;
- `allow_nan=false`;
- UTF-8 encoding with `surrogatepass` only for otherwise-unencodable surrogate evidence.

Ordinary exact JSON with valid Unicode therefore retains the existing fingerprint value. The fix narrows hostile/non-JSON shapes without churning valid receipt identity.

## Regression source
`tools/test_try_forever_canonical_result_fingerprint.py` is **REGRESSION SOURCE / UNEXECUTED**.

It pins:
- insertion-order independence;
- material-evidence sensitivity;
- exact parity with the legacy fingerprint for ordinary valid Unicode;
- deterministic surrogate-bearing evidence;
- rejection of non-finite numeric evidence;
- typed rejection of deeply recursive hostile evidence;
- rejection of root and nested `dict` subclasses before overridden callbacks can execute;
- rejection of tuple→array and integer-key→string-key normalization.

`tools/test_try_forever_descriptor_shadow_canonical_result_fingerprint_owner_boundary.py` remains **REGRESSION SOURCE / UNEXECUTED**. Source inspection shows the descriptor-shadow owner consumes the shared organ; fixture execution is still a separate capability state.

## Current owner truth
The shared organ has two current source consumers in this branch:

1. `tools/try_forever_owner_surgery_descriptor_shadow_audit.py`, schema `try-forever-owner-surgery-descriptor-shadow.v3` — **SOURCE_WIRED**.
2. `tools/try_forever_owner_surgery_descriptor_shadow_operator_receipt.py`, schema `try-forever-owner-surgery-descriptor-shadow-operator-receipt.v4` — **SOURCE_WIRED** through `_operator_receipt_sha256(...)`.

Current capability truth:
- fingerprint organ implementation: **YES / SOURCE**;
- recursive exact-JSON fingerprint admission: **YES / SOURCE**;
- bounded snapshot reuse: **YES / SOURCE**;
- descriptor-shadow owner consumption: **YES / SOURCE_WIRED**;
- final-v4 operator-receipt owner consumption: **YES / SOURCE_WIRED**;
- hostile regression source: **YES / UNEXECUTED**;
- TESTED: **NO**;
- runtime UI/TalkBack: **NO**;
- deployed/callable/executed/delivered/accepted: **NO**.

## Duplicate-architecture law
Do not create a second descriptor shadow, receipt owner, snapshotter, or fingerprint implementation. Existing owners consume the shared exact-JSON snapshot and evidence-identity organs; future work must preserve that ownership.

## P0 / phone firewall
Consumes no Phone Hands, primary-phone command, P0 recovery queue, Nightcore, Pocket TTS, Chromium, Context Organs, physical acceptance, or P0 coordination.
