# Operator Owner Surgery Custody

## Purpose
Prevent unapplied source surgeries from racing the same existing owner while each still claims exact custody of the same base blob.

This skill is about **promotion topology and evidence custody**, not another overlay controller, patch executor, scheduler, recovery daemon, or phone lane.

## Core laws
`SAME OWNER + SAME AUTHENTICATED CURRENT BASE BLOB + MULTIPLE PROMOTION CANDIDATES = CURRENT_BASE_COLLISION_SET`.

`ARTIFACT BASE != AUTHENTICATED CURRENT OWNER BLOB = STALE_BASE_GROUP`.

`NO AUTHENTICATED CURRENT OWNER BLOB = UNVERIFIED_BASE_GROUP`.

`MATCHING OWNER-SURGERY ARTIFACT THAT CANNOT BE SAFELY ADMITTED = EVIDENCE INCOMPLETE`.

`PATCHES ROOT REDIRECTOR / PERSISTENT IDENTITY DRIFT / IDENTITY UNAVAILABLE = ZERO PARTIAL PROMOTION AUTHORITY`.

`UNBOUNDED DIRECTORY ENTRIES != BOUNDED CANDIDATE SET`.

`PREFIX CONTENT NEVER EARNS SURGERY AUTHORITY`.

`POST-SCAN ROOT STABILITY != FINAL AUTHORITY ROOT STABILITY`.

Applying one current-base surgery changes owner custody and therefore stales the base lock of the others. Parallel source design is allowed; parallel promotion against the same exact owner/base is not automatically safe.

## Owner-surgery artifact family
Owner surgery provenance currently exists in more than one durable representation:
- textual `patches/try-forever-*.patch` artifacts;
- structured `patches/try-forever-*.delta.json` artifacts using `try-forever-owner-delta.v1`.

A custody probe that scans only one representation is a discovery aid, not exhaustive promotion evidence. Likewise, a scan that silently drops a matching malformed artifact, follows a redirector, waits on a special file, traverses an unbounded directory, or begins from an untrusted `patches/` root while claiming a complete inventory is not exhaustive evidence.

## Four finite custody throats
### 0. Root topology / persistent-identity throat
Before directory traversal, the named `patches/` root is captured with the existing portable no-follow root-identity organ from `tools/try_forever_skill_root_identity.py`:
- symlink/junction-style redirector roots fail closed before traversal;
- ordinary-directory identity must expose a nonzero inode/file-index token;
- the same root identity is re-observed after bounded traversal;
- persistent device/inode/type/redirector drift withholds the entire candidate inventory;
- root capture/revalidation failure yields a bounded `artifact_root` discovery error and **zero partial promotion authority**.

This is deliberate reuse of an existing root-custody organ, not a second owner-surgery-specific topology stack.

**Boundary:** pre/post identity revalidation is not an atomic cross-platform directory binding. A complete swap-and-restore between observations and filesystem identity reuse remain explicitly unclosed.

### 1. Directory traversal throat
Only after root admission, the `patches/` inventory is non-recursive and bounded before parsing:
- inspect at most **32,768 directory entries**;
- every entry counts, including unrelated names;
- max+1 fails the whole promotion inventory closed;
- do not treat the first N matching paths as exhaustive authority after traversal overflow.

This corrects the first v5 attempt: bounding only `Path.glob(...)` matches bounded stored candidates, but it did **not** bound work spent scanning unrelated directory entries.

### 2. Matching candidate throat
From the bounded directory observation:
- admit at most **2,048** matching patch/delta candidate paths;
- candidate max+1 fails the whole promotion inventory closed;
- deterministic sorting happens only after bounded admission.

The directory-entry and candidate budgets are separate on purpose. A directory can contain huge unrelated clutter without producing many matching artifacts, or many matching artifacts without much unrelated clutter.

### 3. Finite ordinary-artifact throat
Every admitted patch/delta reuses the existing hardened finite-artifact observation organ in `tools/try_forever_generated_index_artifact_observation.py` rather than growing a second no-follow/I/O custody stack. Its reusable consequences are:
- named-path topology admission before authority-facing content I/O;
- ordinary regular-file requirement;
- no-follow / nonblocking flags where the platform exposes them;
- Windows named-path reparse rejection;
- path-to-open-descriptor identity/size/mtime agreement;
- bounded complete EOF at **1 MiB**;
- strict UTF-8;
- post-read descriptor and named-path stability checks.

Symlink/reparse/special-file topology, path/object drift, malformed UTF-8, or max+1 content becomes a bounded `discoveryError`. This detects common redirector and replacement races but deliberately does **not** claim universal filesystem atomicity, swap-and-restore immunity, or identity-reuse immunity.

## Representation-specific admission
For textual patch provenance, missing exact base-owner metadata, missing state/status, missing owner evidence, unreadable bytes, malformed UTF-8, over-budget input, non-ordinary topology, or artifact drift become bounded `discoveryErrors`; they do not return a quiet `None` and they do not abort healthy sibling readback.

Structured owner deltas may use historical compatible spellings for their exact base blob (`baseBlob`, `ownerBaseBlob`, or `baseOwnerBlob`) and state (`state` or `status`). If multiple supported aliases occur, their values must agree exactly. Duplicate JSON members, conflicting aliases, unsupported schema, malformed JSON, invalid owner/base/state, malformed UTF-8, over-budget input, non-ordinary topology, or artifact drift become bounded `discoveryErrors`; they are not silently ignored.

## Required behavior
- Preserve the existing owner. Do not create a neighboring controller merely to avoid surgery conflicts.
- Every review-ready surgery names an owner path and exact base blob.
- Before calling a surgery current-base-ready, bind source inspection to a fresh authenticated current-owner blob.
- Rejected, superseded, and already-applied artifacts are provenance, not promotion candidates.
- A stale-base or unverified-base candidate may remain useful design provenance, but it is **not** promotion-ready.
- If root custody, directory traversal, candidate collection, or any matching artifact admission produces a discovery error, do not call the candidate inventory exhaustive.
- On root, traversal, or candidate failure, emit **zero partial promotion authority** from that inventory.
- A root check performed before artifact reads does not authorize later artifact-derived promotion if the named root persistently changes afterward. Final promotion authority requires a root observation that also brackets artifact authority work.
- When multiple unapplied promotion candidates share one authenticated current owner/base, deliberately choose one of:
  1. converge compatible consequences into one canonical surgery;
  2. define an explicit promotion order and rebase later surgeries after authenticated owner readback;
  3. keep one or more seams source-only until the owner changes.
- Never apply one surgery and continue describing siblings as current-base-ready.
- Do not infer a mega-patch merely because a collision set exists. Prefer the smallest deliberate convergence or serialized/rebased promotion plan that preserves one-owner semantics.
- Source/provenance existence does not equal owner wiring.
- Owner source wiring does not equal regression execution, TESTED, runtime UI, TalkBack, deployment, phone delivery, or acceptance.

## Deterministic source evidence
`tools/try_forever_owner_surgery_custody_probe.py` **v7** is the current implemented probe:
- reuses the existing portable no-follow root identity/revalidation organ around the named `patches/` root;
- performs one bounded non-recursive directory scan only after initial root admission;
- counts all directory entries;
- bounds the matching patch+delta candidate set separately;
- revalidates root identity after traversal before parsing candidates;
- reuses the existing finite ordinary-file observer for each admitted artifact;
- groups active unapplied surgeries by owner + exact base blob;
- accepts caller-supplied authenticated current-owner blob evidence.

Its outputs distinguish:
- `CURRENT_BASE_COLLISION_SET` — multiple active candidates share the authenticated current owner/base;
- `STALE_BASE_GROUP` — candidate base differs from authenticated current owner custody;
- `UNVERIFIED_BASE_GROUP` — no authenticated current owner blob was supplied, so promotion readiness is unproven;
- `artifact_root` discovery error + `evidenceComplete=false` — named root topology/identity could not be safely admitted or persistently revalidated;
- other `discoveryErrors` + `evidenceComplete=false` — traversal, candidate-set, or artifact evidence could not be safely admitted, so exhaustive custody is unproven.

`tools/test_try_forever_owner_surgery_custody_probe.py` includes hostile source fixtures for:
- root symlink rejection before traversal with zero partial authority;
- persistent root replacement after traversal with zero partial authority;
- candidate max+1 with zero partial authority;
- unrelated directory-entry max+1 with zero partial authority;
- matching special/non-ordinary topology;
- malformed patch metadata and UTF-8;
- over-budget patch/delta evidence;
- conflicting aliases and duplicate JSON members.

It remains regression source only until an authorized non-phone execution lane runs it.

## Prepared v8 final root commit gate — 2026-08-22 04:57 CT
Fresh readback of v7 exposed a narrower persistent-drift gap **after** its post-traversal root check. v7 revalidates the named `patches/` root, then reads/parses admitted artifact paths. If the root is persistently replaced after that check but before/during artifact observation, candidate paths can resolve through the replacement root before any later root custody check exists.

The bounded repair is deliberately not a new custody architecture:
1. retain root identity from before the authority-producing operation;
2. keep the existing v7 root bracket around bounded traversal;
3. observe/parse admitted finite artifacts through the existing artifact organ;
4. capture/revalidate the named root **again after artifact observations and before emitting surgery/collision/stale/unverified authority**;
5. if this final root gate fails, clear all surgery authority from that inventory and emit bounded `artifact_root` evidence.

Durable proposal:
- `patches/try-forever-owner-surgery-custody-v8-final-root.patch`
- base probe blob: `a3a11139faf426ddeae90c035708d4a3e0e1e36f`
- state: **CORRECTED_PROPOSED_NOT_APPLIED**

Hostile regression source:
- `tools/test_try_forever_owner_surgery_final_root_revalidation.py`
- requires a persistent root replacement after the post-scan check but before artifact read to produce zero surgery/collision/stale/unverified authority;
- state: **REGRESSION SOURCE / UNEXECUTED**.

**Important boundary:** this final observation improves persistent-drift custody but still is **not atomic root binding**. A complete swap-and-restore entirely between observations and filesystem identity reuse remain explicitly unclosed. Do not relabel v8 as atomic or runtime security proof.

## Mutation-lane truth for this repair
Home Center currently exposes Computer Hands operations, but `windows-hands-01` is offline with existing TRY FOREVER lanes and queue depth 4. Do not enqueue duplicate surgery merely to manufacture activity. The audited GitHub file-upsert surface is whole-file replacement, not a patch interpreter; the prepared v8 delta therefore remains unapplied until an authorized safe existing-owner mutation body is genuinely callable.

## Current PR #329 source truth — 2026-08-22 04:57 CT
The native overlay owner is not mutated by this skill slice. The canonical owner-surgery custody probe remains **v7 / IMPLEMENTED SOURCE**.

Root topology / persistent-identity revalidation through post-traversal **YES / SOURCE**. Final post-artifact root revalidation **NO / PREPARED PATCH ONLY**. Atomic root binding **NO**. Existing v7 regression source **YES / UNEXECUTED**. New v8 late-root regression source **YES / UNEXECUTED**.

Known patch-form current-base promotion candidates remain design provenance subject to fresh authenticated owner custody and this inventory's completeness. A known list is never automatically an exhaustive list.

The earlier selection-only and heartbeat-announcement-only artifacts remain superseded provenance and must not be applied alone.

## P0 / phone firewall
This skill owns no Phone Hands ticket, primary-phone command, recovery queue, Nightcore, Pocket TTS, Chromium, Context Organs, physical acceptance, P0 coordination, or duplicate native owner.

## Capability membrane
`requested → source policy/probe → authenticated readback → regression source → regression executed → promotion plan → owner mutation → authenticated owner readback → tested → runtime UI → runtime TalkBack → deployed → callable → executed → delivered → accepted`.

Current state: canonical v7 skill/probe source **YES**; v8 final-root patch **YES / PROPOSED_NOT_APPLIED**; root + bounded traversal + candidate + finite-artifact hostile regression source **YES / UNEXECUTED**; late-root final-gate regression source **YES / UNEXECUTED**; atomic root binding **NO**; owner mutation from this skill **NO**; TESTED/runtime/phone states **NO**.
