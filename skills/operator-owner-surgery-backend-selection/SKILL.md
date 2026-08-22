# Operator Owner Surgery Backend Selection

## Purpose
Select the strongest **admitted** owner-surgery custody backend without silently weakening evidence after a stronger backend has already been selected.

This skill owns backend-selection doctrine only. It does **not** own a second custody probe, patch executor, overlay controller, recovery daemon, phone lane, P0 coordinator, or physical acceptance chain.

## Core laws
`PLATFORM CAPABILITY ADMISSION != OWNER INTEGRATION`.

`DESCRIPTOR BACKEND SELECTED + DESCRIPTOR CUSTODY FAILURE != PERMISSION TO RETRY THROUGH WEAKER PATHNAME CUSTODY`.

`DESCRIPTOR PRIMITIVES UNAVAILABLE != FAILURE OF THE PORTABLE v10 BACKEND`.

`STRONGER BACKEND != PERMISSION TO DROP artifactDirectoryEntriesObserved OR artifactCandidatesObserved`.

`artifactCandidatesObserved > artifactDirectoryEntriesObserved = INVALID EVIDENCE`.

`EVIDENCE COMPLETE = FALSE + NONEMPTY PROMOTION AUTHORITY GROUPS = REJECTED COMPOSITION`.

`SUPPORTING SOURCE != REGRESSION EXECUTED != TESTED != RUNTIME != DEPLOYED != DELIVERED`.

## Selection contract
`tools/try_forever_owner_surgery_backend_policy.py` is supporting source only.

- `SUPPORTED_POSIX_PRIMITIVES` selects `HELD_DIRECTORY_DESCRIPTOR` for a future canonical-owner composition.
- `PORTABLE_ATOMIC_BINDING_UNAVAILABLE` keeps `PORTABLE_PATHNAME_REVALIDATION` as the primary backend.
- Unknown capability text fails closed rather than being normalized into a backend.
- Once held-descriptor custody is selected for a classification attempt, descriptor setup/inventory/artifact/cleanup failure terminates that attempt. The owner must not silently retry the same evidence through portable pathname custody and call the weaker result equivalent.
- Any future canonical-owner composition must preserve the existing v10 evidence fields `artifactDirectoryEntriesObserved` and `artifactCandidatesObserved`, exact owner-surgery state admission, exact base/current-owner blob admission, bounded error semantics, and the portable fallback on platforms where descriptor primitives are unavailable.

## Result-admission throat
`admit_selected_backend_result(...)` is the supporting composition gate between backend work and owner authority.

It requires:
- selected backend identity to remain exact;
- no claimed weaker fallback after selection;
- non-negative integer directory-entry and candidate counts;
- candidate count not to exceed total directory entries observed;
- boolean `evidenceComplete`;
- list-shaped `collisionSets`, `staleBaseGroups`, and `unverifiedBaseGroups`;
- incomplete exhaustive custody to carry **zero** promotion-authority groups.

Diagnostic `surgeries` may remain present when custody is incomplete. Diagnostic source inspection is not promotion authority.

This policy does **not** claim descriptor/root/candidate atomicity, universal filesystem guarantees, Windows parity, canonical-owner integration, regression execution, Android/runtime behavior, deployment, phone execution, delivery, or acceptance.

## Canonical owner relationship
Canonical custody remains `tools/try_forever_owner_surgery_custody_probe.py` schema v10.

Current canonical-owner state:
- portable v10 implementation **YES / SOURCE_WIRED**;
- descriptor supporting backend **YES / SUPPORTING SOURCE**;
- backend-selection policy **YES / SUPPORTING SOURCE**;
- backend result-admission policy **YES / SUPPORTING SOURCE**;
- backend-selection/result regression source **YES / UNEXECUTED**;
- focused v10 contract regression source **YES / UNEXECUTED**;
- canonical owner consumes backend-selection policy **NO**;
- canonical owner consumes descriptor backend **NO**;
- descriptor atomic root binding **NO**;
- descriptor atomic candidate binding **NO**;
- TESTED/runtime/deployed/phone/delivered/accepted **NO**.

### Current canonical wound: incomplete inventory can still project authority
The current v10 source sets `evidenceComplete=false` when any matching artifact produces a `discoveryError`, but healthy sibling surgeries can still feed `collisionSets`, `staleBaseGroups`, or `unverifiedBaseGroups`.

That shape is now rejected by the backend result-admission throat and pinned by `tools/test_try_forever_owner_surgery_zero_partial_authority.py` as a RED owner regression. `patches/try-forever-owner-surgery-zero-partial-authority.patch` is the narrow current-owner repair: preserve healthy surgery diagnostics, but do not build promotion groups while exhaustive custody is incomplete.

Owner repair state: **CORRECTED_PROPOSED_NOT_APPLIED**. Do not call the wound closed until authenticated owner readback shows the repair.

The older broad custody regression still contains historical expectations and must not be treated as current v10 proof merely because it exists. `tools/test_try_forever_owner_surgery_v10_contract.py` is a focused source fixture for the current public v10 schema/capability membrane. It is **UNEXECUTED**.

## Cross-pollination
The descriptor backend became strong enough that the next risk was not another low-level syscall wound; it was **composition semantics**. Without explicit selection and result gates, future owner composition could accidentally do either of these:

1. admit descriptor capability → select held-descriptor custody → hit a descriptor wound → retry through portable pathname custody → emit authority as though the stronger attempt succeeded;
2. receive `evidenceComplete=false` from an exhaustive scan → preserve healthy sibling promotion groups → call partial authority exhaustive.

Both are evidence laundering. The backend-selection organ makes the portable path a **platform fallback**, not an after-failure escape hatch, and the result-admission throat refuses partial promotion authority from incomplete custody.

## P0 / phone firewall
This skill consumes no Phone Hands ticket, primary-phone command, P0 recovery queue, Nightcore, Pocket TTS, Chromium, Context Organs, physical acceptance, or P0 coordination. P0 receipts remain read-only evidence.

## Capability membrane
`requested → supporting source → authenticated source readback → regression source → regression executed → canonical owner composition → authenticated owner readback → TESTED → runtime → deployed → callable → executed → delivered → accepted`.

Current state at 2026-08-22 17:01 CT: backend-selection supporting source **YES** · backend result-admission source **YES** · regression source **YES / UNEXECUTED** · focused v10 regression source **YES / UNEXECUTED** · zero-partial-authority RED owner regression **YES / UNEXECUTED** · exact owner repair **YES / NOT APPLIED** · canonical owner backend selection **NO** · descriptor owner integration **NO** · TESTED/runtime/deployed/phone/delivered/accepted **NO**.
