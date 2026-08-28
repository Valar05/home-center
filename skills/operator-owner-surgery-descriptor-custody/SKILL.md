# Operator Owner Surgery Descriptor Custody

## Purpose
Strengthen TRY FOREVER owner-surgery **root and candidate custody** on runtimes that expose the required POSIX descriptor primitives, while preserving canonical v10 authority, exact capability boundaries, contact preservation, and the no-weaker-fallback law.

This skill owns descriptor custody doctrine only. It does **not** own a second custody probe, patch executor, overlay controller, scheduler, recovery daemon, phone lane, P0 coordinator, or physical acceptance chain.

## Core laws
`HELD DIRECTORY DESCRIPTOR + DESCRIPTOR-RELATIVE NAME OPERATIONS != UNIVERSAL FILESYSTEM ATOMICITY`.

`ENUMERATED NAME + CAPTURED NO-FOLLOW OBJECT IDENTITY != ATOMIC CANDIDATE-NAME BINDING`.

`DESCRIPTOR BACKEND SELECTED + CUSTODY WOUND != PORTABLE RETRY`.

`DESCRIPTOR PRIMITIVES UNAVAILABLE != DESCRIPTOR WOUND`.

`STRONGER CUSTODY BACKEND != PERMISSION TO DROP EXISTING OWNER EVIDENCE FIELDS`.

`ZERO PARTIAL CANDIDATE AUTHORITY != ZERO OBSERVED-WORK EVIDENCE`.

`IDENTIFIED ARTIFACT CUSTODY FAILURE != ANONYMOUS BACKEND FAILURE`.

`STRICT UTF-8 OR FILESYSTEM I/O FAILURE != RAW EXCEPTION ESCAPING THE CUSTODY DOMAIN`.

`ROOT PATH ENCODING FAILURE != RAW UNICODE EXCEPTION ESCAPING THE CUSTODY DOMAIN`.

`INVENTORY FAILURE != PARTIAL CANDIDATE AUTHORITY`.

`CLEANUP FAILURE != PERMISSION TO MASK AN EARLIER PRIMARY WOUND`.

`CANONICAL CALLER EXACT ROOT != PERMISSION TO LEAVE DIRECT DESCRIPTOR CONSTRUCTOR UNGATED`.

`CALLER os.PathLike CALLBACK != MACHINE ROOT EVIDENCE`.

`SOURCE_WIRED != REGRESSION EXECUTED != TESTED != RUNTIME != DEPLOYED != DELIVERED != ACCEPTED`.

## Capability admission
`tools/try_forever_directory_handle_binding_capability.py` reports `SUPPORTED_POSIX_PRIMITIVES` only when the current runtime exposes POSIX identity, `scandir(fd)`, descriptor-relative `open` and `stat`, no-follow stat, `O_DIRECTORY`, and `O_NOFOLLOW`.

Every machine control is exact before equality/truthiness classification: `os_name` is an exact built-in string and primitive-presence flags are exact built-in booleans. Missing any required primitive produces `PORTABLE_ATOMIC_BINDING_UNAVAILABLE` and keeps the canonical portable path primary.

## Existing descriptor organ
`tools/try_forever_posix_directory_handle_custody.py` is the single descriptor custody organ. It:
1. admits the root as one exact built-in string or the exact platform `Path` before capability lookup, `Path`/`os.fspath`, or filesystem semantics;
2. opens the named root once with `O_DIRECTORY|O_NOFOLLOW` and retains the descriptor as the authority root;
3. contains root path-encoding failure in `PosixDirectoryHandleCustodyUnavailable` rather than leaking raw `UnicodeError`;
4. requires an ordinary directory with usable identity;
5. opens a fresh `.` scan handle relative to the held root for each inventory, avoiding inherited directory-stream position;
6. counts all entries and matching candidates against independent exact integer budgets;
7. captures each matching candidate's no-follow identity and mode during enumeration;
8. rejects traversal syntax before descriptor-relative operations;
9. revalidates enumerated identity before open;
10. opens the candidate relative to the held root with `O_NOFOLLOW` and `O_NONBLOCK` where available;
11. requires pre-stat/open-fd identity agreement;
12. reads complete bytes through the hard max+1 throat;
13. requires post-read descriptor and name stability;
14. admits strict UTF-8 and returns byte count/SHA-256 only with the admitted observation;
15. contains root/inventory/artifact I/O failures in typed custody domains;
16. owns cleanup failure without masking an earlier primary wound or retrying a potentially recycled descriptor number;
17. carries bounded `entries_observed` / `candidates_observed` on typed inventory failure without returning any partial candidate inventory authority.

`candidate_inventory(...)` is the evidence-bearing inventory surface. Compatibility projections do not replace it. `DescriptorInventoryCustodyError` is evidence metadata only; its counts never become candidate authority.

## Canonical owner relationship
Canonical authority remains `tools/try_forever_owner_surgery_custody_probe.py`, schema v10. It **SOURCE_WIRES** descriptor custody directly:
- exact classification root and budget controls are admitted before backend dispatch;
- exact current platform capability is classified;
- `select_owner_surgery_backend(...)` selects one backend;
- on `HELD_DIRECTORY_DESCRIPTOR`, canonical v10 enters `HeldDirectoryCustody` itself using the already-admitted exact platform Path;
- it consumes `candidate_inventory(...)` for total entry/candidate evidence;
- it consumes `observe_utf8_regular_file(...)` for held-root exact bytes/identity/witness evidence;
- those exact observations are parsed by the already-owned `parse_owner_surgery_observation(...)` semantic producer;
- descriptor setup/inventory/artifact/cleanup wounds produce zero surgery authority for the descriptor attempt and never trigger a portable retry;
- typed inventory wounds preserve bounded observed counts in the canonical receipt;
- artifact-custody wounds after successful inventory preserve the already-identified artifact path/kind plus inventory counts while returning zero surgery authority;
- promotion authority remains globally suppressed whenever `discoveryErrors` is non-empty.

This closes canonical descriptor failure-evidence parity at **SOURCE_WIRED** level. It does not prove regression execution or runtime behavior.

## Direct constructor root boundary
`HeldDirectoryCustody(path)` calls `_require_directory_root(...)` before capability lookup or any path/filesystem operation. Only one exact built-in string or the exact platform `Path` is admitted. Arbitrary `os.PathLike`, `str` subclasses, and `Path` subclasses are rejected without caller callbacks receiving a vote.

`patches/try-forever-posix-directory-root-exact-input.patch` remains historical **APPLIED_SOURCE** provenance. Direct root and root-encoding regressions remain **SOURCE / UNEXECUTED**.

## Contact preservation
Descriptor composition preserves the canonical evidence contract on success and failure:
- `artifactDirectoryEntriesObserved`;
- `artifactCandidatesObserved`;
- already-identified failing artifact path/kind;
- `artifactContentWitnesses` for admitted observations;
- `discoveryErrors` and `evidenceComplete`;
- `currentOwnerBlobs`;
- `collisionSets`;
- `staleBaseGroups`;
- `unverifiedBaseGroups`;
- zero partial promotion authority on discovery wounds.

Inventory max+1 counts the observed violating entry/candidate as work evidence but returns no partial inventory. Artifact-custody failure stops descriptor surgery authority immediately while keeping the complete held-root inventory counts already observed before that artifact read.

Portable root-identity revalidation remains primary only when descriptor primitives are unavailable. Descriptor selection itself emits `portableFallbackAttempted=false`.

## Exact classification-control custody
The canonical owner closes the pre-dispatch boundary:
- root must be one exact platform `Path` before path callbacks can participate;
- `max_candidates` and `max_entries` must be exact built-in integers within declared ceilings before comparison/truthiness;
- hostile Path/int subclasses therefore cannot run caller code while influencing backend selection or resource budgets.

Inside the descriptor organ, direct root, basename strings, integer budgets, and expected `DescriptorCandidate` values all have exact input gates.

## Review scars retained
**Scan position is state.** Fresh descriptor-relative scan handles prevent one inventory from inheriting another scan's position.

**Candidate name is not candidate object.** Enumeration identity is carried into the later bounded read; persistent replacement is rejected. Swap-and-restore and identity reuse remain outside the claim.

**Stronger backend must preserve metrics.** Total directory entries remain distinct from matching candidate count, including fail-closed inventory evidence.

**Budget overflow returns no partial inventory.** Entry/candidate max+1 rejects authority while preserving bounded observed-work counts in the typed wound.

**Identified artifact failure stays identified.** Once held-root inventory identified the path/kind, a later descriptor artifact-custody failure is not collapsed to anonymous backend evidence.

**Text/I/O failure remains custody failure.** Malformed UTF-8 and authority-facing filesystem errors are typed and do not leak raw decoder/OS exceptions as evidence.

**Root encoding failure is typed.** Exact root admission does not imply every exact string is encodable by the host filesystem.

**Cleanup owns failure only when primary.** Cleanup cannot replace a more informative body/inventory/artifact wound.

## Regression surfaces
Relevant descriptor regressions remain source-only unless separately executed:
- `tools/test_try_forever_posix_directory_handle_custody.py`;
- `tools/test_try_forever_posix_directory_handle_io_failures.py`;
- `tools/test_try_forever_posix_directory_handle_cleanup_failures.py`;
- `tools/test_try_forever_posix_directory_handle_exact_input_boundary.py`;
- `tools/test_try_forever_posix_directory_handle_root_exact_input_boundary.py`;
- `tools/test_try_forever_posix_directory_inventory_failure_evidence.py`;
- `tools/test_try_forever_directory_handle_binding_capability.py`;
- `tools/test_try_forever_owner_surgery_descriptor_backend_composition_boundary.py`;
- `tools/test_try_forever_owner_surgery_descriptor_failure_evidence_parity.py`;
- `tools/test_try_forever_owner_surgery_classification_exact_input_boundary.py`.

The descriptor failure-evidence parity fixture is now **CONVERGENCE SOURCE / UNEXECUTED**. The direct inventory failure-evidence fixture pins the supporting organ's typed count contract as **SOURCE / UNEXECUTED**. Their presence does not make the implementation TESTED.

## Atomicity boundary
Descriptor integration still does **not** claim universal filesystem atomicity, swap-and-restore immunity, inode/file-index reuse immunity, Windows descriptor parity, regression execution, Android runtime behavior, deployment, phone delivery, or acceptance.

## Current capability state
- supporting descriptor implementation: **YES / SOURCE_WIRED ORGAN**;
- authenticated GitHub source readback: **YES**;
- bounded inventory metrics on success: **SOURCE_WIRED**;
- bounded observed-work metrics on inventory failure: **SOURCE_WIRED**;
- enumeration→read candidate identity handoff: **SOURCE_WIRED**;
- identified artifact failure path/kind preservation in canonical v10: **SOURCE_WIRED**;
- typed root/inventory/artifact/cleanup failure containment: **SOURCE_WIRED**;
- root path-encoding error containment: **SOURCE_WIRED**;
- exact direct-root/basename/budget/expected-candidate input custody: **SOURCE_WIRED**;
- canonical v10 exact classification root/budget admission: **SOURCE_WIRED**;
- canonical v10 backend selection + descriptor consumption: **SOURCE_WIRED**;
- semantic producer consumption on descriptor bytes: **SOURCE_WIRED**;
- descriptor failure-evidence parity: **SOURCE_WIRED**;
- descriptor failure-evidence regressions: **SOURCE / UNEXECUTED**;
- universal atomic root/candidate binding: **NO universal claim**;
- TESTED/runtime UI/runtime TalkBack/deployed/callable/executed/delivered/accepted/phone delivered: **NO**.

## P0 / phone firewall
This skill consumes no Phone Hands ticket, primary-phone command, recovery queue, Nightcore, Pocket TTS, Chromium, Context Organs, physical acceptance, or P0 coordination. P0 receipts remain read-only evidence.

## Capability membrane
`requested → implemented/source-wired → authenticated source readback → regression source → regression executed → TESTED → runtime → deployed → callable → executed → delivered → accepted`.
