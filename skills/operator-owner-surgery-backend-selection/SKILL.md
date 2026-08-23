# Operator Owner Surgery Backend Selection

## Purpose
Select the strongest **admitted** owner-surgery custody backend without silently weakening evidence after a stronger backend has actually been selected by the canonical owner.

This skill owns backend-selection and result-admission doctrine only. It does **not** own a second custody probe, patch executor, overlay controller, recovery daemon, phone lane, P0 coordinator, or physical acceptance chain.

## Core laws
`PLATFORM CAPABILITY ADMISSION != CANONICAL OWNER INTEGRATION`.

`DESCRIPTOR BACKEND SELECTED + DESCRIPTOR CUSTODY FAILURE != PERMISSION TO RETRY THROUGH WEAKER PATHNAME CUSTODY`.

`DESCRIPTOR SHADOW AUDIT != DESCRIPTOR BACKEND SELECTED`.

`DESCRIPTOR PRIMITIVES UNAVAILABLE != FAILURE OF PORTABLE v10`.

`STRONGER BACKEND != PERMISSION TO DROP DIRECTORY/CANDIDATE COUNTS, discoveryErrors, currentOwnerBlobs, OR PROMOTION-MEMBER EVIDENCE`.

`INCOMPLETE EXHAUSTIVE CUSTODY + PROMOTION AUTHORITY = INVALID EVIDENCE`.

`OWNER A CUSTODY != OWNER B AUTHORITY`.

`GROUP SHELL != MEMBER AUTHORITY`.

`SUPPORTING SOURCE != REGRESSION EXECUTED != TESTED != RUNTIME != DEPLOYED != DELIVERED != ACCEPTED`.

## Selection source
`tools/try_forever_owner_surgery_backend_policy.py` is supporting source only.

- `SUPPORTED_POSIX_PRIMITIVES` selects `HELD_DIRECTORY_DESCRIPTOR` for a **future canonical-owner composition**.
- `PORTABLE_ATOMIC_BINDING_UNAVAILABLE` keeps `PORTABLE_PATHNAME_REVALIDATION` as the canonical portable backend.
- Unknown capability text fails closed.
- Once a canonical classification attempt actually selects held-descriptor custody, descriptor setup/inventory/artifact/cleanup failure terminates that attempt. Do not retry the same evidence through portable custody and call the weaker result equivalent.

## Result-admission throat
`admit_selected_backend_result(...)` is the source-only gate between backend work and owner authority.

It requires:
- exact selected backend identity and no weaker-fallback claim;
- non-negative integer directory-entry/candidate counts with candidates ≤ entries;
- `discoveryErrors` and `evidenceComplete` to agree exactly;
- exact lowercase authenticated `currentOwnerBlobs`;
- collision/stale/unverified groups to obey their owner/base/current-owner meanings;
- every promotion member to be canonical Surgery-shaped evidence for the same owner/base and exact promotion-ready state;
- distinct members and distinct owner/base groups so duplicate evidence cannot manufacture cardinality;
- incomplete exhaustive custody to carry **zero** promotion-authority groups.

The gate reports exhaustive evidence separately from owner evidence. A complete scan without authenticated current-owner custody is not owner evidence. Authenticated custody for one owner does not upgrade another owner's unverified group.

Diagnostic surgeries may remain after a wounded scan. Diagnostic source inspection is not promotion authority.

## Current canonical owner truth
Canonical custody remains `tools/try_forever_owner_surgery_custody_probe.py` schema v10.

The previously documented **zero-partial-authority wound is closed at source level**. Current canonical source builds promotion groups only when `discoveryErrors` is empty; healthy surgery records may survive as diagnostics without promotion authority. The applied repair and current PR checkpoint are the authority for that state.

Do **not** resurrect the older doctrine that the zero-partial repair is `CORRECTED_PROPOSED_NOT_APPLIED`. That was stale historical state.

Do not treat a hard-coded historical owner blob in this skill as everlasting current custody. Promotion work must refresh authenticated owner readback at execution time.

Current capability state:
- portable v10 canonical owner: **SOURCE_WIRED**;
- zero-partial-authority owner behavior: **SOURCE_WIRED**;
- backend-selection policy: **SUPPORTING SOURCE**;
- backend result-admission policy: **SUPPORTING SOURCE**;
- POSIX descriptor custody: **SUPPORTING SOURCE**;
- descriptor shadow audit: **SUPPORTING SOURCE / NON-AUTHORITATIVE**;
- backend/descriptor regressions: **SOURCE / UNEXECUTED**;
- canonical owner consumes backend-selection policy: **NO**;
- canonical owner consumes descriptor backend: **NO**;
- descriptor/root/candidate atomicity: **NO**;
- TESTED/runtime/deployed/phone/delivered/accepted: **NO**.

## Descriptor shadow staging
`tools/try_forever_owner_surgery_descriptor_shadow_audit.py` may compare the existing held-directory custody source against canonical portable inventory evidence while canonical v10 remains the sole authority producer.

Shadow states are deliberately different from owner-selected backend states:
- `SHADOW_MATCH` = independent staging evidence agrees on compared paths/metrics; **not owner integration**;
- `SHADOW_DIVERGED` = stop and investigate evidence semantics before integration;
- `DESCRIPTOR_UNAVAILABLE` = descriptor primitives were never selected for authority, so canonical portable custody simply remains authority;
- `DESCRIPTOR_WOUND` = the non-authoritative shadow failed its own custody gate; canonical authority is unchanged.

A future **selected descriptor authority** failure is different: that must fail closed with no portable retry in the same classification attempt.

## Descriptor source relationship
`tools/try_forever_posix_directory_handle_custody.py` is the stronger POSIX supporting source. It holds the root directory descriptor, uses fresh descriptor-relative scan handles, carries enumeration-time candidate identity into observation, bounds entries/candidates/bytes, performs no-follow descriptor-relative work, keeps strict UTF-8 and typed I/O/cleanup wounds, and preserves evidence metrics.

Its existence does not prove universal filesystem atomicity, Windows parity, canonical-owner integration, regression execution, runtime behavior, or delivery.

## Review / regression surfaces
Relevant source-only regression surfaces include:
- `tools/test_try_forever_owner_surgery_backend_policy.py`;
- `tools/test_try_forever_owner_surgery_authority_member_integrity.py`;
- `tools/test_try_forever_owner_surgery_v10_contract.py`;
- `tools/test_try_forever_owner_surgery_descriptor_shadow_audit.py`;
- the descriptor custody I/O, cleanup, budget, and candidate-identity fixtures.

Their existence is not execution evidence.

## Duplicate-architecture law
Do not create a descriptor promotion owner beside canonical v10. Future integration must compose the existing canonical owner, backend-selection/result-admission policy, and descriptor custody organ. The descriptor shadow is allowed only because it cannot emit promotion authority.

## Accessibility / touch
Source specimens may make backend/shadow/evidence states touch-inspectable with non-color semantics and reduced-motion behavior. Source art must explicitly remain SOURCE ONLY and may not claim Android runtime, TalkBack runtime, phone delivery, or acceptance.

## P0 / phone firewall
This skill consumes no Phone Hands ticket, primary-phone command, P0 recovery queue, Nightcore, Pocket TTS, Chromium, Context Organs, physical acceptance, or P0 coordination. P0 receipts remain read-only evidence.

## Capability membrane
`requested → supporting source → authenticated source readback → regression source → regression executed → canonical owner composition → authenticated owner readback → TESTED → runtime → deployed → callable → executed → delivered → accepted`.
