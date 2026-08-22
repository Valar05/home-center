# Operator Owner Surgery Base Identity

## Purpose
Keep owner-surgery blob authority exact. Base-owner blob evidence and authenticated current-owner blob input are authority tokens, not display text and not values to repair by normalization.

This skill owns no patch executor, overlay controller, recovery daemon, phone lane, P0 coordinator, or second custody probe. It composes with the existing `try_forever_owner_surgery_custody_probe.py` owner.

## Core law
`NORMALIZATION-DEPENDENT OWNER BLOB TEXT != AUTHENTICATED OWNER IDENTITY`.

## Source-wired artifact evidence
Canonical owner-surgery custody v10 enforces exact artifact base identity in both admitted surgery forms:
- textual patch evidence may keep case-flexible header spelling, but the captured 40-hex evidence token must already satisfy the lowercase SHA contract;
- structured delta base evidence is validated before any case transformation and is never repaired by trimming/lowercasing.

Applied artifact-evidence source:
- commit: `2ba4254f8e9b736fe47dbe0f5192fe270397359a`;
- resulting historical owner blob: `d5c22feac7b3f71045cc139e120b2ae45a3b1c37`;
- provenance artifact: `patches/try-forever-owner-surgery-base-blob-exactness.patch` = **APPLIED_SOURCE**.

## Source-wired authenticated current-owner custody
The formerly RED current-owner input seam is now wired in the same canonical owner:
- CLI `_parse_owner_blob(...)` no longer trims or lowercases the blob evidence token before validation;
- programmatic `classify(...)` no longer lowercases supplied current-owner blob values;
- both paths share fail-closed exact lowercase-SHA admission;
- malformed uppercase or padded blob evidence cannot be repaired into current-base authority.

Authenticated source wiring:
- applied commit: `bbc13531816eb48353d01c201b2ef4e8d3715563`;
- resulting owner blob: `f3457f82f5ea135e303c6ca7b93491511a471dd7`;
- owner report capability: `exactCurrentOwnerBlobAdmission = true`.

Owner-key handling was deliberately not widened in this surgery. CLI owner text retains its prior structural trimming behavior; this slice repairs only authenticated blob authority evidence.

## Regression source
`tools/test_try_forever_owner_surgery_base_blob_exactness.py` — **UNEXECUTED**.

It now requires:
- lowercase patch/delta base evidence admitted exactly;
- uppercase patch/delta base evidence rejected rather than normalized;
- lowercase authenticated current-owner CLI evidence admitted exactly;
- uppercase and padded authenticated current-owner CLI evidence rejected rather than normalized;
- lowercase programmatic current-owner evidence preserved exactly in the report;
- uppercase and padded programmatic current-owner evidence rejected rather than normalized.

Source existence is not TESTED evidence.

## Descriptor-custody boundary
The stronger POSIX held-directory backend remains supporting source only. Exact current-owner identity repair does not imply descriptor canonical-owner integration, universal filesystem atomicity, Windows parity, regression execution, runtime UI/TalkBack, deployment, phone callability, delivery, or acceptance.

## Capability membrane
Artifact base-identity owner wiring **YES / SOURCE_WIRED** · authenticated current-owner exact-input wiring **YES / SOURCE_WIRED** · authenticated remote readback **YES** · regression source **YES / UNEXECUTED** · descriptor owner integration **NO** · TESTED/runtime/deployed/phone/delivered/accepted **NO**.

## P0 / phone firewall
Consumes no Phone Hands, primary-phone command, recovery queue, Nightcore, Pocket TTS, Chromium, Context Organs, physical acceptance, or P0 coordination.
