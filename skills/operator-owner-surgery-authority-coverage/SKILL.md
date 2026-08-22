# Operator Owner Surgery Authority Coverage

## Purpose
Prevent authenticated custody for one owner from laundering another owner's unverified surgery authority into a generic `ownerEvidenceAdmitted=true` claim.

This skill owns one evidence law. It does **not** own a second custody probe, backend, patch executor, overlay controller, recovery daemon, phone lane, P0 coordinator, or physical acceptance chain.

## Core law
`SOME AUTHENTICATED OWNER CUSTODY != AUTHENTICATED CUSTODY FOR EVERY AUTHORITY GROUP`.

Authority is owner-specific:
- `CURRENT_BASE_COLLISION_SET` requires an authenticated current-owner blob for that exact owner and `baseBlob == currentOwnerBlob`.
- `STALE_BASE_GROUP` requires an authenticated current-owner blob for that exact owner and `baseBlob != currentOwnerBlob`.
- `UNVERIFIED_BASE_GROUP` means that exact owner has **no** authenticated current-owner blob.
- An unverified group may coexist with authenticated custody for a different owner, but the result must not claim generic owner evidence admitted.
- An unverified group that also claims `currentOwnerBlob`, or whose owner exists in `currentOwnerBlobs`, is contradictory evidence and fails closed.

`EXHAUSTIVE EVIDENCE != OWNER COVERAGE`.

`SUPPORTING SOURCE != REGRESSION EXECUTED != CANONICAL OWNER COMPOSITION != TESTED != RUNTIME != DELIVERED`.

## Current source surfaces
- `tools/try_forever_owner_surgery_backend_policy.py` validates authority-group shape and owner-specific custody relationships in the supporting backend-result admission throat.
- `tools/test_try_forever_owner_surgery_backend_policy.py` pins valid collision/stale groups plus cross-owner and contradictory unverified-group cases. Regression source is **UNEXECUTED**.
- `skills/operator-owner-surgery-backend-selection/SKILL.md` composes this law into the broader backend-selection/result-admission doctrine.
- `docs/try-forever/operator-owner-surgery-backend-selection-source-specimen.html` makes the owner-coverage stop touchable without claiming runtime UI/TalkBack/phone delivery.

## Canonical-owner boundary
Canonical custody remains `tools/try_forever_owner_surgery_custody_probe.py` schema v10. This source slice does not replace that owner or claim that backend selection is integrated into it.

The separate canonical zero-partial-authority wound also remains open: `patches/try-forever-owner-surgery-zero-partial-authority.patch` is prepared but unapplied. Owner-specific coverage does not close incomplete-inventory authority leakage inside canonical v10.

## P0 / phone firewall
This skill consumes no Phone Hands ticket, primary-phone command, P0 recovery queue, Nightcore, Pocket TTS, Chromium, Context Organs, physical acceptance, or P0 coordination. P0 receipts remain read-only evidence.

## Capability membrane
Current state at 2026-08-22 18:00 CT: supporting implementation **YES** · authenticated remote readback **YES** · regression source **YES / UNEXECUTED** · touchable source organism **YES** · canonical backend-owner composition **NO** · TESTED/runtime/deployed/phone/delivered/accepted **NO**.
