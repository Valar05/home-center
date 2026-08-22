# Operator Owner Surgery Base Identity

## Purpose
Keep owner-surgery blob authority exact. Base-owner blob evidence and authenticated current-owner blob input are authority tokens, not display text and not values to repair by normalization.

This skill owns no patch executor, overlay controller, recovery daemon, phone lane, P0 coordinator, or second custody probe. It composes with the existing `try_forever_owner_surgery_custody_probe.py` owner.

## Core law
`NORMALIZATION-DEPENDENT OWNER BLOB TEXT != AUTHENTICATED OWNER IDENTITY`.

## Closed artifact-evidence seam
Canonical owner-surgery custody v10 now enforces exact artifact base identity in both admitted surgery forms:
- textual patch evidence may keep case-flexible header spelling, but the captured 40-hex evidence token must already satisfy the lowercase SHA contract;
- structured delta base evidence is validated before any case transformation and is never repaired by trimming/lowercasing.

Authenticated source wiring:
- applied commit: `2ba4254f8e9b736fe47dbe0f5192fe270397359a`;
- resulting owner blob: `d5c22feac7b3f71045cc139e120b2ae45a3b1c37`;
- provenance artifact: `patches/try-forever-owner-surgery-base-blob-exactness.patch` = **APPLIED_SOURCE**.

## Fresh independent wound: current-owner custody input
The same owner still normalizes the **authenticated current-owner blob input** used to decide current/stale/collision authority:
- `_parse_owner_blob(...)` applies `strip().lower()` before its lowercase-SHA check;
- `classify(...)` lowercases programmatic `current_owner_blobs` values before comparison.

That means uppercase or padded current-owner evidence can still be repaired into authority even though artifact base evidence can no longer do so.

This wound is intentionally **RED SUPPORTING SOURCE ONLY** this pulse. It is not folded into the already-applied artifact surgery without a separate owner review.

## Regression source
`tools/test_try_forever_owner_surgery_base_blob_exactness.py` — **UNEXECUTED**.

It now requires:
- lowercase patch/delta base evidence admitted exactly;
- uppercase patch/delta base evidence rejected rather than normalized;
- uppercase authenticated current-owner CLI blob rejected rather than normalized;
- padded authenticated current-owner CLI blob rejected rather than trimmed.

The current-owner tests are intentionally RED against current owner source. Source existence is not TESTED evidence.

## Capability membrane
Artifact base-identity owner wiring **YES / SOURCE_WIRED** · authenticated remote readback **YES** · current-owner exact-input wiring **NO / RED** · regression source **YES / UNEXECUTED** · TESTED/runtime/deployed/phone/delivered/accepted **NO**.

## P0 / phone firewall
Consumes no Phone Hands, primary-phone command, recovery queue, Nightcore, Pocket TTS, Chromium, Context Organs, physical acceptance, or P0 coordination.
