# Operator Owner Surgery Canonical Result Fingerprint

## Purpose
Keep the descriptor-shadow receipt bound to the exact canonical owner-surgery result even when JSON-shaped source evidence contains hostile Unicode such as a POSIX surrogateescape-shaped filename.

This skill owns evidence identity only. It does **not** own canonical promotion authority, a second descriptor authority, a second receipt projector, filesystem atomicity, Android runtime, phone execution, P0 recovery, deployment, delivery, or acceptance.

## Core laws
`CANONICAL RESULT FINGERPRINT != CANONICAL ARTIFACT IDENTITY != PROMOTION AUTHORITY`.

`VALID-UNICODE FINGERPRINT STABILITY != PERMISSION TO CRASH ON SURROGATE-BEARING SOURCE EVIDENCE`.

`SURROGATE-SAFE RECEIPT IDENTITY != FILESYSTEM ATOMICITY`.

`SUPPORTING POLICY != OWNER WIRED != REGRESSION EXECUTED != TESTED != RUNTIME != DEPLOYED != DELIVERED != ACCEPTED`.

## Supporting source
`tools/try_forever_canonical_result_fingerprint.py` is **SUPPORTING SOURCE**.

It uses the existing descriptor-shadow canonical serialization shape:
- sorted JSON object keys;
- compact separators;
- `ensure_ascii=false`;
- `allow_nan=false`;
- UTF-8 encoding.

The only hostile-text hardening is `errors="surrogatepass"` during encoding. Ordinary valid-Unicode payloads therefore retain the existing fingerprint value; an otherwise-unencodable surrogate-bearing source payload receives deterministic receipt identity instead of crashing the evidence lane.

## Regression source
`tools/test_try_forever_canonical_result_fingerprint.py` is **REGRESSION SOURCE / UNEXECUTED**.

It pins:
- insertion-order independence;
- material-evidence sensitivity;
- exact parity with the legacy fingerprint for valid Unicode;
- deterministic surrogate-bearing evidence;
- rejection of non-finite numeric evidence.

`tools/test_try_forever_descriptor_shadow_canonical_result_fingerprint_owner_boundary.py` remains **REGRESSION SOURCE / UNEXECUTED**. Its owner-wiring expectation is now satisfied by authenticated source, but the fixture has not executed and therefore grants no TESTED state.

## Owner truth
Current owner: `tools/try_forever_owner_surgery_descriptor_shadow_audit.py`, schema `try-forever-owner-surgery-descriptor-shadow.v3`.

Authenticated source wiring:
- base owner blob before surgery: `92e916f8d64168990a221ca9d5469699ef6273b8`;
- owner surgery commit: `f57e556e6025f93b6b3b01ec9cedac95868b28e7`;
- resulting owner blob: `44bc3af31e645f33abf542139995c3707ef8e210`;
- prepared patch provenance: `patches/try-forever-descriptor-shadow-canonical-result-fingerprint-owner.patch` = **APPLIED_SOURCE**.

At this checkpoint:
- supporting fingerprint policy: **YES / SOURCE**;
- descriptor-shadow owner consumption: **YES / SOURCE_WIRED**;
- hostile regression source: **YES / UNEXECUTED**;
- owner-boundary regression source: **YES / UNEXECUTED**;
- TESTED: **NO**;
- runtime UI/TalkBack: **NO**;
- deployed/callable/executed/delivered/accepted: **NO**.

## Duplicate-architecture law
Do not create a second descriptor shadow or second receipt projector. The existing descriptor-shadow owner consumes the shared canonical-result fingerprint policy; future work must preserve that ownership.

## P0 / phone firewall
Consumes no Phone Hands, primary-phone command, P0 recovery queue, Nightcore, Pocket TTS, Chromium, Context Organs, physical acceptance, or P0 coordination.
