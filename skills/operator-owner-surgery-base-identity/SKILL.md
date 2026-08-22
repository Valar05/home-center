# Operator Owner Surgery Base Identity

## Purpose
Keep owner-surgery base-blob evidence exact. A base owner blob is an authority token, not display text and not a value to repair by normalization.

This skill owns no patch executor, overlay controller, recovery daemon, phone lane, P0 coordinator, or second custody probe. It composes with the existing `try_forever_owner_surgery_custody_probe.py` owner.

## Core law
`NORMALIZATION-DEPENDENT BASE BLOB TEXT != AUTHENTICATED OWNER IDENTITY`.

If a patch or structured delta says an owner base blob in uppercase, padded, control-bearing, or otherwise non-canonical text, the evidence must be rejected. Lowercasing it into a valid SHA is not evidence preservation.

## Current wound
Canonical owner-surgery custody v10 currently normalizes base identity in two places:
- textual patch evidence matches hexadecimal case-insensitively and then lowercases the captured blob;
- structured delta evidence lowercases the supplied base blob before validating it.

That means uppercase evidence can become canonical authority after parsing.

## Regression source
`tools/test_try_forever_owner_surgery_base_blob_exactness.py` — **UNEXECUTED**.

It requires:
- lowercase 40-hex patch base evidence is admitted exactly;
- uppercase patch base evidence is rejected rather than normalized;
- lowercase structured-delta base evidence is admitted exactly;
- uppercase structured-delta base evidence is rejected rather than normalized.

## Prepared existing-owner surgery
`patches/try-forever-owner-surgery-base-blob-exactness.patch` is **CORRECTED_PROPOSED_NOT_APPLIED** against authenticated owner blob `fa8dfa5ea510f187d9d613d733a33b0a0bf4fb0f`.

The surgery is intentionally narrow:
- patch header spelling may remain case-flexible for historical compatibility;
- the captured 40-hex evidence token itself must already satisfy the lowercase SHA contract;
- structured delta base evidence is validated before any case transformation;
- no second parser or custody owner is created.

## Capability membrane
Supporting source **YES** · regression source **YES / UNEXECUTED** · exact owner patch **YES / NOT APPLIED** · canonical owner base-identity wiring **NO** · TESTED/runtime/deployed/phone/delivered/accepted **NO**.

## P0 / phone firewall
Consumes no Phone Hands, primary-phone command, recovery queue, Nightcore, Pocket TTS, Chromium, Context Organs, physical acceptance, or P0 coordination.
