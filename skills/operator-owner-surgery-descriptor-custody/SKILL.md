# Operator Owner Surgery Descriptor Custody

## Purpose
Strengthen TRY FOREVER owner-surgery **root and candidate custody** on runtimes that expose the required POSIX descriptor primitives, while preserving the canonical portable v10 owner, exact capability boundaries, and the no-weaker-fallback law.

This skill owns descriptor custody doctrine only. It does **not** own a second custody probe, patch executor, overlay controller, scheduler, recovery daemon, phone lane, P0 coordinator, or physical acceptance chain.

## Core laws
`HELD DIRECTORY DESCRIPTOR + DESCRIPTOR-RELATIVE NAME OPERATIONS != UNIVERSAL FILESYSTEM ATOMICITY`.

`ENUMERATED NAME + CAPTURED NO-FOLLOW OBJECT IDENTITY != ATOMIC CANDIDATE-NAME BINDING`.

`DESCRIPTOR BACKEND SELECTED + CUSTODY WOUND != PORTABLE RETRY`.

`DESCRIPTOR PRIMITIVES UNAVAILABLE != DESCRIPTOR WOUND`.

`STRONGER CUSTODY BACKEND != PERMISSION TO DROP EXISTING OWNER EVIDENCE FIELDS`.

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
9. revalidates the enumerated identity before open;
10. opens the candidate relative to the held root with `O_NOFOLLOW` and `O_NONBLOCK` where available;
11. requires pre-stat/open-fd identity agreement;
12. reads complete bytes through the hard max+1 throat;
13. requires post-read descriptor and name stability;
14. admits strict UTF-8 and returns byte count/SHA-256 only with the admitted observation;
15. contains root/inventory/artifact I/O failures in typed custody domains;
16. owns cleanup failure without masking an earlier primary wound or retrying a potentially recycled descriptor number.

`candidate_inventory(...)` is the evidence-bearing inventory surface. Compatibility projections do not replace it.

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
- promotion authority remains globally suppressed whenever `discoveryErrors` is non-empty.

This closes **canonical owner integration at SOURCE_WIRED level**. It does not prove regression execution or runtime behavior.

## Direct constructor root boundary
The descriptor organ now closes the direct constructor boundary too. `HeldDirectoryCustody(path)` calls `_require_directory_root(...)` before capability lookup or any path/filesystem operation. Only one exact built-in string or the exact platform `Path` is admitted. Arbitrary `os.PathLike`, `str` subclasses, and `Path` subclasses are rejected without caller callbacks receiving a vote.

`patches/try-forever-posix-directory-root-exact-input.patch` is **APPLIED_SOURCE**: base descriptor-owner blob `6eee417a…`, application commit `4bf66478…`. `tools/test_try_forever_posix_directory_handle_root_exact_input_boundary.py` is **CONVERGENCE SOURCE / UNEXECUTED** and requires rejection before hostile `__fspath__`, capability lookup, or filesystem open executes.

A neighboring exact-string failure path is also contained: root `os.open(...)` path encoding errors are converted to `PosixDirectoryHandleCustodyUnavailable`. `tools/test_try_forever_posix_directory_handle_io_failures.py` contains focused **SOURCE / UNEXECUTED** regression coverage for that error domain.

Do not inflate these source repairs into regression execution, runtime behavior, or universal filesystem atomicity.

## Contact preservation
The descriptor composition preserves the canonical evidence contract:
- `artifactDirectoryEntriesObserved`;
- `artifactCandidatesObserved`;
- `artifactContentWitnesses`;
- `discoveryErrors` and `evidenceComplete`;
- `currentOwnerBlobs`;
- `collisionSets`;
- `staleBaseGroups`;
- `unverifiedBaseGroups`;
- zero partial promotion authority on discovery wounds.

Portable root-identity revalidation remains the canonical primary path only when descriptor primitives are unavailable. Descriptor selection itself emits `portableFallbackAttempted=false`.

## Exact classification-control custody
The canonical owner closes the pre-dispatch boundary:
- root must be one exact platform `Path` object before path callbacks can participate;
- `max_candidates` and `max_entries` must be exact built-in integers within their declared ceilings before comparison/truthiness;
- hostile Path/int subclasses therefore cannot run caller code while influencing backend selection or resource budgets.

`tools/test_try_forever_owner_surgery_classification_exact_input_boundary.py` is **SOURCE / UNEXECUTED**.

Inside the descriptor organ, direct root, basename strings, integer budgets, and expected `DescriptorCandidate` values now all have exact input gates.

## Review scars retained
**Scan position is state.** Fresh descriptor-relative scan handles prevent one inventory from inheriting another scan's position.

**Candidate name is not candidate object.** Enumeration identity is carried into the later bounded read; persistent replacement is rejected. Swap-and-restore and identity reuse remain outside the claim.

**Stronger backend must preserve metrics.** Total directory entries remain distinct from matching candidate count.

**Budget overflow returns no partial inventory.** Entry/candidate max+1 rejects the inventory.

**Text/I/O failure remains custody failure.** Malformed UTF-8 and authority-facing filesystem errors are typed and do not leak raw decoder/OS exceptions as evidence.

**Root encoding failure is typed.** Exact root admission does not imply every exact string is encodable by the host filesystem; encoding failure remains a typed custody-unavailable boundary.

**Cleanup owns failure only when primary.** Cleanup cannot replace a more informative body/inventory/artifact wound.

## Regression surfaces
Relevant descriptor regressions remain source-only unless separately executed:
- `tools/test_try_forever_posix_directory_handle_custody.py`;
- `tools/test_try_forever_posix_directory_handle_io_failures.py`;
- `tools/test_try_forever_posix_directory_handle_cleanup_failures.py`;
- `tools/test_try_forever_posix_directory_handle_exact_input_boundary.py`;
- `tools/test_try_forever_posix_directory_handle_root_exact_input_boundary.py`;
- `tools/test_try_forever_directory_handle_binding_capability.py`;
- `tools/test_try_forever_owner_surgery_descriptor_backend_composition_boundary.py`;
- `tools/test_try_forever_owner_surgery_classification_exact_input_boundary.py`.

The descriptor composition boundary and direct-constructor root boundary are **CONVERGENCE SOURCE / UNEXECUTED**. The focused basename/budget/candidate exact-input and root I/O fixtures remain hostile **SOURCE / UNEXECUTED**. Their presence does not make the implementation TESTED.

## Atomicity boundary
Descriptor integration strengthens root/name custody but still does **not** claim:
- universal filesystem atomicity;
- immunity to swap-and-restore between observations;
- immunity to inode/file-index reuse;
- Windows descriptor parity;
- regression execution;
- runtime Android behavior;
- deployment, phone delivery, or acceptance.

## Current capability state
- supporting descriptor implementation: **YES / SOURCE_WIRED ORGAN**;
- authenticated GitHub source readback: **YES**;
- bounded inventory metrics: **SOURCE_WIRED**;
- enumeration→read candidate identity handoff: **SOURCE_WIRED**;
- typed root/inventory/artifact/cleanup failure containment: **SOURCE_WIRED**;
- root path-encoding error containment: **SOURCE_WIRED**;
- exact direct-root/basename/budget/expected-candidate input custody: **SOURCE_WIRED**;
- canonical v10 exact classification root/budget admission: **SOURCE_WIRED**;
- direct `HeldDirectoryCustody(...)` exact root admission: **SOURCE_WIRED**;
- canonical v10 backend selection: **SOURCE_WIRED**;
- canonical v10 descriptor consumption: **SOURCE_WIRED**;
- semantic producer consumption on descriptor bytes: **SOURCE_WIRED**;
- descriptor composition provenance patch: **APPLIED_SOURCE**;
- descriptor root exact-input surgery: **APPLIED_SOURCE**;
- descriptor composition and exact-input regressions: **SOURCE / UNEXECUTED**;
- atomic root binding: **NO universal claim**;
- atomic candidate binding: **NO universal claim**;
- TESTED/runtime UI/runtime TalkBack/deployed/callable/executed/delivered/accepted/phone delivered: **NO**.

## P0 / phone firewall
This skill consumes no Phone Hands ticket, primary-phone command, recovery queue, Nightcore, Pocket TTS, Chromium, Context Organs, physical acceptance, or P0 coordination. P0 receipts remain read-only evidence.

## Capability membrane
`requested → implemented/source-wired → authenticated source readback → regression source → regression executed → TESTED → runtime → deployed → callable → executed → delivered → accepted`.