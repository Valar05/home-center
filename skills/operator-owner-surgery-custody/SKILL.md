# Operator Owner Surgery Custody

## Purpose
Prevent unapplied source surgeries from racing the same existing owner while each still claims exact custody of the same base blob.

This skill owns **promotion topology and evidence custody**, not another overlay controller, patch executor, scheduler, recovery daemon, phone lane, P0 coordinator, or neighboring provenance owner.

## Core laws
`SAME OWNER + SAME AUTHENTICATED CURRENT BASE BLOB + MULTIPLE PROMOTION CANDIDATES = CURRENT_BASE_COLLISION_SET`.

`ARTIFACT BASE != AUTHENTICATED CURRENT OWNER BLOB = STALE_BASE_GROUP`.

`NO AUTHENTICATED CURRENT OWNER BLOB = UNVERIFIED_BASE_GROUP`.

`MATCHING OWNER-SURGERY ARTIFACT THAT CANNOT BE SAFELY ADMITTED = EVIDENCE INCOMPLETE`.

`PATCHES ROOT REDIRECTOR / PERSISTENT IDENTITY DRIFT / IDENTITY UNAVAILABLE = ZERO PARTIAL PROMOTION AUTHORITY`.

`UNBOUNDED DIRECTORY ENTRIES != BOUNDED CANDIDATE SET`.

`PREFIX CONTENT NEVER EARNS SURGERY AUTHORITY`.

`POST-SCAN ROOT STABILITY != FINAL AUTHORITY ROOT STABILITY`.

`STATE CONTAINS "PROPOSED" != PROMOTION READY`.

`PATHNAME PRE/POST IDENTITY BRACKET != ATOMIC DIRECTORY BINDING`.

Applying one current-base surgery changes owner custody and therefore stales the base lock of the others. Parallel source design is allowed; parallel promotion against the same exact owner/base is not automatically safe.

## Owner-surgery artifact family
Owner surgery provenance currently exists in more than one durable representation:
- textual `patches/try-forever-*.patch` artifacts;
- structured `patches/try-forever-*.delta.json` artifacts using `try-forever-owner-delta.v1`.

A custody probe that scans only one representation is a discovery aid, not exhaustive promotion evidence. Likewise, a scan that silently drops a matching malformed artifact, follows a redirector, waits on a special file, traverses an unbounded directory, normalizes authority text, or begins from an untrusted `patches/` root while claiming a complete inventory is not exhaustive evidence.

## Finite custody throats
### 0. Root topology / persistent-identity throat
Before directory traversal, the named `patches/` root is captured with the existing portable no-follow root-identity organ from `tools/try_forever_skill_root_identity.py`:
- symlink/junction-style redirector roots fail closed before traversal;
- ordinary-directory identity must expose a nonzero inode/file-index token;
- the same root identity is re-observed after bounded traversal;
- persistent device/inode/type/redirector drift withholds the entire candidate inventory;
- root capture/revalidation failure yields bounded `artifact_root` evidence and **zero partial promotion authority**.

This reuses one existing root-custody organ instead of growing owner-surgery-specific topology logic.

**Boundary:** pathname identity revalidation is not atomic cross-platform directory binding. Complete swap-and-restore between observations and filesystem identity reuse remain unclosed.

### 1. Directory traversal throat
Only after root admission, the `patches/` inventory is non-recursive and bounded before parsing:
- inspect at most **32,768 directory entries**;
- every entry counts, including unrelated names;
- max+1 fails the whole promotion inventory closed;
- never treat the first N matching paths as exhaustive after traversal overflow.

### 2. Matching candidate throat
From the bounded directory observation:
- admit at most **2,048** matching patch/delta candidate paths;
- candidate max+1 fails the whole promotion inventory closed;
- deterministic sorting happens only after bounded admission.

Directory-entry and candidate budgets are separate on purpose.

### 3. Finite ordinary-artifact throat
Every admitted patch/delta reuses `tools/try_forever_generated_index_artifact_observation.py` rather than growing a second no-follow/I/O custody stack. Reused consequences include:
- named-path topology admission before authority-facing content I/O;
- ordinary regular-file requirement;
- no-follow / nonblocking flags where the platform exposes them;
- Windows named-path reparse rejection;
- path-to-open-descriptor identity/size/mtime agreement;
- bounded complete EOF at **1 MiB**;
- strict UTF-8;
- post-read descriptor and named-path stability checks.

Symlink/reparse/special-file topology, path/object drift, malformed UTF-8, or max+1 content becomes bounded `discoveryError` evidence. This still does **not** claim universal filesystem atomicity, swap-and-restore immunity, or identity-reuse immunity.

### 4. Final root authority gate
Root custody must bracket the authority-producing artifact observations, not only directory traversal. If the named root persistently changes after post-scan revalidation but before/during artifact reads, every surgery/collision/stale/unverified authority from that inventory must be cleared before emission.

The prepared v9 surgery carries this final root gate. It remains a persistent-drift improvement, not atomic binding.

## Exact owner-surgery state admission
Promotion authority must never come from substring matching. Supporting source authority is `tools/try_forever_owner_surgery_state_policy.py`.

Current exact promotion-ready states are:
- `PROPOSED_NOT_APPLIED`
- `CORRECTED_PROPOSED_NOT_APPLIED`

Rules:
- state must already be a canonical uppercase ASCII/digit/underscore token;
- no `.strip()`, case folding, control removal, or other normalization may turn rejected text into authority;
- `NOT_PROPOSED`, `PROPOSEDISH`, `PROPOSED_NOT_APPLIED_EXTRA`, or any other unknown token is **not** promotion-ready;
- unknown but canonical historical state may remain readable provenance, but cannot enter promotion-candidate groups;
- invalid state evidence becomes a bounded admission failure, not a quiet skip and not a process abort.

Regression source: `tools/test_try_forever_owner_surgery_state_policy.py` — **UNEXECUTED**.

## Representation-specific admission
Textual patch provenance requires exact base-owner metadata, exact admitted state/status, and owner evidence. Unreadable bytes, malformed UTF-8, over-budget input, non-ordinary topology, artifact drift, missing metadata, or invalid state become bounded `discoveryErrors`; they do not earn authority.

Structured owner deltas may use historical compatible exact aliases for base blob (`baseBlob`, `ownerBaseBlob`, `baseOwnerBlob`) and state (`state`, `status`). Multiple supported aliases must agree exactly. Duplicate JSON members, conflicting aliases, unsupported schema, malformed JSON, invalid owner/base/state, malformed UTF-8, over-budget input, non-ordinary topology, or artifact drift fail closed.

## Current implementation / prepared promotion
`tools/try_forever_owner_surgery_custody_probe.py` **v7** remains the implemented owner-surgery custody probe. It already provides:
- no-follow `patches/` root admission around bounded non-recursive traversal;
- separate 32,768 directory-entry and 2,048 candidate budgets;
- finite ordinary patch/delta artifact custody;
- current/stale/unverified grouping against authenticated current-owner blobs;
- zero partial authority on root/traversal/candidate failure.

Current outputs include `CURRENT_BASE_COLLISION_SET`, `STALE_BASE_GROUP`, `UNVERIFIED_BASE_GROUP`, bounded `discoveryErrors`, and `evidenceComplete`.

### Prepared v9 root + state surgery — 2026-08-22 06:02 CT
`patches/try-forever-owner-surgery-custody-v9-root-state.patch` is the canonical prepared owner surgery against probe blob `a3a11139faf426ddeae90c035708d4a3e0e1e36f`.

It deliberately converges two compatible authority repairs against the same owner/base:
1. final post-artifact root revalidation before emitting promotion authority;
2. exact fail-closed surgery-state admission through `try_forever_owner_surgery_state_policy.py`.

State: **CORRECTED_PROPOSED_NOT_APPLIED**.

The older `patches/try-forever-owner-surgery-custody-v8-final-root.patch` is **SUPERSEDED_BY_V9__DO_NOT_APPLY** historical provenance and must not be promoted independently.

Hostile source fixtures:
- `tools/test_try_forever_owner_surgery_final_root_revalidation.py` — late persistent root replacement;
- `tools/test_try_forever_owner_surgery_state_policy.py` — substring/normalization/type attacks.

Both are **REGRESSION SOURCE / UNEXECUTED**.

## Stronger atomic-binding capability gate
`tools/try_forever_directory_handle_binding_capability.py` separates portable pathname custody from a stronger POSIX descriptor-bound design.

Python exposes file-descriptor and `dir_fd` capability sets platform-by-platform. The supporting source therefore reports `SUPPORTED_POSIX_PRIMITIVES` only when all required source primitives are present: POSIX runtime, `scandir(fd)`, `open(..., dir_fd=...)`, `O_DIRECTORY`, and `O_NOFOLLOW`.

This status is **not atomicity proof**. It only means the source surface exists to design a held-directory-descriptor implementation. Filesystem semantics, descriptor-relative artifact reads, tests, owner integration, runtime behavior, and every later capability state remain separate.

If the required primitives are absent, the verdict is `PORTABLE_ATOMIC_BINDING_UNAVAILABLE`; do not upgrade pathname pre/post revalidation into an atomic claim.

Regression source: `tools/test_try_forever_directory_handle_binding_capability.py` — **UNEXECUTED**.

## Required behavior
- Preserve the existing owner. Do not create a neighboring controller or probe to avoid surgery conflicts.
- Every review-ready surgery names one owner path and exact base blob.
- Before calling a surgery current-base-ready, bind source inspection to fresh authenticated current-owner blob evidence.
- Rejected, superseded, unknown-state, and already-applied artifacts are provenance, not promotion candidates.
- A stale-base or unverified-base candidate may remain useful design provenance, but is **not** promotion-ready.
- Any root/traversal/candidate/artifact/state admission error makes exhaustive custody unproven.
- On root, traversal, or candidate failure, emit **zero partial promotion authority**.
- A root check before artifact reads cannot authorize later artifact-derived promotion after persistent root replacement; final authority needs a root observation after artifact authority work too.
- Multiple current-base candidates require deliberate convergence, explicit serialized/rebased promotion, or continued source-only status.
- Never apply one surgery and continue calling siblings current-base-ready without authenticated rebase/readback.
- Do not infer a mega-patch merely because a collision set exists.
- Source/provenance existence does not equal owner wiring.
- Owner source wiring does not equal regression execution, TESTED, runtime UI, TalkBack, deployment, phone delivery, or acceptance.

## Mutation-lane truth
The prepared v9 patch is not implementation. Do not reconstruct the large owner from partial/truncated readback merely to manufacture an owner-mutation receipt. Do not enqueue duplicate offline-worker sludge. Apply only through an authorized safe existing-owner mutation body that yields authenticated owner readback.

## P0 / phone firewall
This skill owns no Phone Hands ticket, primary-phone command, recovery queue, Nightcore, Pocket TTS, Chromium, Context Organs, physical acceptance, P0 coordination, or duplicate native owner. P0 receipts are read-only evidence here.

## Capability membrane
`requested → source policy/probe → authenticated readback → regression source → regression executed → promotion plan → owner mutation → authenticated owner readback → tested → runtime UI → runtime TalkBack → deployed → callable → executed → delivered → accepted`.

Current state at 2026-08-22 06:02 CT: canonical probe v7 **IMPLEMENTED SOURCE**; exact state policy **IMPLEMENTED SUPPORTING SOURCE**; v9 final-root + state owner surgery **PREPARED / NOT APPLIED**; v8 **SUPERSEDED**; root/pathname persistent-drift revalidation **SOURCE**; atomic root binding **NO**; atomic primitive capability classifier **SUPPORTING SOURCE / UNEXECUTED**; hostile regressions **SOURCE / UNEXECUTED**; owner mutation from this slice **NO**; TESTED/runtime/phone/deployed/delivered/accepted **NO**.
