# Operator Owner Surgery Exhaustive Authority

## Purpose
Keep diagnostic source inspection separate from promotion authority when an owner-surgery inventory is incomplete.

This skill owns one evidence law. It does **not** own a second custody probe, patch executor, overlay controller, recovery daemon, phone lane, P0 coordinator, or physical acceptance chain.

## Core law
`EVIDENCE COMPLETE = FALSE != PERMISSION TO EMIT PARTIAL PROMOTION AUTHORITY`.

A safely parsed sibling surgery may remain useful diagnostic provenance. It must not become `CURRENT_BASE_COLLISION_SET`, `STALE_BASE_GROUP`, or `UNVERIFIED_BASE_GROUP` authority when another matching surgery artifact in the same exhaustive inventory cannot be safely admitted.

Therefore:
- diagnostic `surgeries` may survive a wounded exhaustive scan;
- `discoveryErrors` must preserve the wound;
- `evidenceComplete` must be `false`;
- all promotion-authority groups must be empty until exhaustive custody is restored;
- stronger backend selection must reject incomplete results that still carry those authority groups;
- source policy/patch existence is not owner wiring, regression execution, TESTED, runtime, deployment, delivery, or acceptance.

## Current source surfaces
- `tools/try_forever_owner_surgery_backend_policy.py` now has a supporting result-admission gate that rejects incomplete backend results carrying partial promotion authority.
- `tools/test_try_forever_owner_surgery_backend_policy.py` pins the result-admission contract as **REGRESSION SOURCE / UNEXECUTED**.
- `tools/test_try_forever_owner_surgery_zero_partial_authority.py` is an intentionally RED current-owner regression: two healthy current-base surgeries plus one wounded matching artifact must retain diagnostics but emit zero current/stale/unverified authority.
- `patches/try-forever-owner-surgery-zero-partial-authority.patch` is an exact current-owner surgery against `tools/try_forever_owner_surgery_custody_probe.py` blob `f3457f82f5ea135e303c6ca7b93491511a471dd7`.

## Current wound
Authenticated canonical v10 source currently computes promotion groups from healthy `surgeries` even when `discoveryErrors` is non-empty. That contradicts the custody doctrine already stating that a wounded matching artifact makes exhaustive authority incomplete.

The prepared owner surgery changes only promotion grouping: healthy surgery records stay available for diagnostics, but `active_groups` remains empty whenever `discoveryErrors` is non-empty.

State:
- supporting evidence-admission source **YES**;
- hostile regression source **YES / UNEXECUTED**;
- exact owner patch **YES / CORRECTED_PROPOSED_NOT_APPLIED**;
- canonical v10 owner consumes the repair **NO**;
- TESTED/runtime/deployed/phone/delivered/accepted **NO**.

## Cross-pollination
The descriptor/backend-selection front exposed this contradiction because a future stronger backend cannot safely compose with a canonical result whose `evidenceComplete=false` while promotion groups remain non-empty. The result-admission throat therefore rejects that shape now, and the owner regression/patch define the narrower canonical repair.

## P0 / phone firewall
This skill consumes no Phone Hands ticket, primary-phone command, P0 recovery queue, Nightcore, Pocket TTS, Chromium, Context Organs, physical acceptance, or P0 coordination. P0 receipts remain read-only evidence.

## Capability membrane
`requested → supporting policy → authenticated source readback → regression source → owner patch → owner mutation → authenticated owner readback → regression executed → TESTED → runtime → deployed → callable → executed → delivered → accepted`.
