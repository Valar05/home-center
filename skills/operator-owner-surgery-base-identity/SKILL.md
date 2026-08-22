# Operator Owner Surgery Base Identity

## Purpose
Keep owner-surgery base-blob evidence exact. A base owner blob is an authority token, not display text and not a value to repair by normalization.

This skill owns no patch executor, overlay controller, recovery daemon, phone lane, P0 coordinator, or second custody probe. It composes with the existing `try_forever_owner_surgery_custody_probe.py` owner.

## Core law
`NORMALIZATION-DEPENDENT BASE BLOB TEXT != AUTHENTICATED OWNER IDENTITY`.

If a patch or structured delta says an owner base blob in uppercase, padded, control-bearing, or otherwise non-canonical text, the evidence must be rejected. Lowercasing it into a valid SHA is not evidence preservation.

## Current owner truth
Canonical owner-surgery custody v10 now enforces exact artifact base identity in both admitted surgery forms:
- textual patch evidence may keep case-flexible header spelling, but the captured 40-hex evidence token must already satisfy the lowercase SHA contract;
- structured delta base evidence is validated before any case transformation and is never repaired by trimming/lowercasing.

Authenticated source wiring:
- applied commit: `2ba4254f8e9b736fe47dbe0f5192fe270397359a`;
- resulting owner blob: `d5c22feac7b3f71045cc139e120b2ae45a3b1c37`;
- provenance artifact: `patches/try-forever-owner-surgery-base-blob-exactness.patch` = **APPLIED_SOURCE**.

## Regression source
`tools/test_try_forever_owner_surgery_base_blob_exactness.py` — **UNEXECUTED**.

It requires:
- lowercase 40-hex patch base evidence is admitted exactly;
- uppercase patch base evidence is rejected rather than normalized;
- lowercase structured-delta base evidence is admitted exactly;
- uppercase structured-delta base evidence is rejected rather than normalized.

Source wiring does not make these fixtures executed test evidence.

## Capability membrane
Supporting source **YES** · canonical owner base-identity wiring **YES / SOURCE_WIRED** · authenticated remote readback **YES** · regression source **YES / UNEXECUTED** · TESTED/runtime/deployed/phone/delivered/accepted **NO**.

## P0 / phone firewall
Consumes no Phone Hands, primary-phone command, recovery queue, Nightcore, Pocket TTS, Chromium, Context Organs, physical acceptance, or P0 coordination.
