# Operator Owner Surgery Authority Coverage

## Purpose
Prevent authenticated custody for one owner from laundering another owner's unverified surgery authority into a generic `ownerEvidenceAdmitted=true` claim, and prevent hollow or duplicated group shells from manufacturing promotion authority.

This skill owns one evidence law. It does **not** own a second custody probe, backend, patch executor, overlay controller, recovery daemon, phone lane, P0 coordinator, or physical acceptance chain.

## Core laws
`SOME AUTHENTICATED OWNER CUSTODY != AUTHENTICATED CUSTODY FOR EVERY AUTHORITY GROUP`.

Authority is owner-specific:
- `CURRENT_BASE_COLLISION_SET` requires an authenticated current-owner blob for that exact owner and `baseBlob == currentOwnerBlob`.
- `STALE_BASE_GROUP` requires an authenticated current-owner blob for that exact owner and `baseBlob != currentOwnerBlob`.
- `UNVERIFIED_BASE_GROUP` means that exact owner has **no** authenticated current-owner blob.
- An unverified group may coexist with authenticated custody for a different owner, but the result must not claim generic owner evidence admitted.
- An unverified group that also claims `currentOwnerBlob`, or whose owner exists in `currentOwnerBlobs`, is contradictory evidence and fails closed.

`GROUP SHELL != PROMOTION AUTHORITY`.

Every promotion-authority member must be canonical Surgery-shaped evidence:
- member `owner` equals the group owner;
- member `base_blob` equals the group `baseBlob`;
- `path` is a non-empty artifact identity;
- `artifact_kind` is one of the canonical owner-surgery artifact kinds (`patch`, `delta_json`);
- `state` is exact owner-surgery state evidence and is promotion-ready under `try_forever_owner_surgery_state_policy`;
- `promotion_candidate` is literal `true`;
- duplicate member artifact identities cannot manufacture collision cardinality;
- duplicate owner/base authority groups fail closed;
- collision authority requires at least two distinct admitted members; stale/unverified authority requires at least one.

`EXHAUSTIVE EVIDENCE != OWNER COVERAGE != MEMBER INTEGRITY`.

`SUPPORTING SOURCE != REGRESSION EXECUTED != CANONICAL OWNER COMPOSITION != TESTED != RUNTIME != DELIVERED`.

## Current source surfaces
- `tools/try_forever_owner_surgery_backend_policy.py`, blob `0b35e517818f1f58a8f4fd03aeb3c71c49b73497`, validates authority-group shape, owner-specific custody relationships, and canonical member integrity in the supporting backend-result admission throat.
- `tools/test_try_forever_owner_surgery_backend_policy.py`, blob `9ff75443c46c2f533fdf40a05bb27c4f49e1b52e`, carries the broader backend-result regression source. It is **UNEXECUTED**.
- `tools/test_try_forever_owner_surgery_authority_member_integrity.py`, blob `605506266e77c91fb8adc12831c0ca7028eb00a3`, independently attacks hollow groups, duplicated members/groups, cross-owner/base members, unsupported kinds, and non-promotion states. It is **UNEXECUTED**.
- `skills/operator-owner-surgery-backend-selection/SKILL.md` composes this law into the broader backend-selection/result-admission doctrine.
- `docs/try-forever/operator-owner-surgery-backend-selection-source-specimen.html` makes the owner/member-coverage stop touchable without claiming runtime UI/TalkBack/phone delivery.

## Canonical-owner boundary
Canonical custody remains `tools/try_forever_owner_surgery_custody_probe.py` schema v10, authenticated blob `f3457f82f5ea135e303c6ca7b93491511a471dd7`. This source slice does not replace that owner or claim that backend selection is integrated into it.

The separate canonical zero-partial-authority wound remains open: `patches/try-forever-owner-surgery-zero-partial-authority.patch`, blob `f4084bc0157c6cbb97d68e8bb039cf5255642517`, is prepared but unapplied. Owner/member coverage does not close incomplete-inventory authority leakage inside canonical v10.

## P0 / phone firewall
This skill consumes no Phone Hands ticket, primary-phone command, P0 recovery queue, Nightcore, Pocket TTS, Chromium, Context Organs, physical acceptance, or P0 coordination. P0 receipts remain read-only evidence.

## Capability membrane
Current state at 2026-08-22 19:00 CT: supporting implementation **YES** · authenticated remote readback **YES** · member-integrity regression source **YES / UNEXECUTED** · touchable source organism **YES** · canonical backend-owner composition **NO** · canonical zero-partial repair **NO** · TESTED/runtime/deployed/phone/delivered/accepted **NO**.
