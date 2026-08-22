# Operator Owner Surgery Custody

## Purpose
Prevent unapplied source surgeries from racing the same existing owner while each still claims exact custody of the same base blob.

This skill is about **promotion topology and evidence custody**, not another overlay controller, patch executor, scheduler, recovery daemon, or phone lane.

## Core laws
`SAME OWNER + SAME AUTHENTICATED CURRENT BASE BLOB + MULTIPLE PROMOTION CANDIDATES = CURRENT_BASE_COLLISION_SET`.

`ARTIFACT BASE != AUTHENTICATED CURRENT OWNER BLOB = STALE_BASE_GROUP`.

`NO AUTHENTICATED CURRENT OWNER BLOB = UNVERIFIED_BASE_GROUP`.

`MATCHING OWNER-SURGERY ARTIFACT THAT CANNOT BE SAFELY ADMITTED = EVIDENCE INCOMPLETE`.

`UNBOUNDED DIRECTORY ENTRIES != BOUNDED CANDIDATE SET`.

`PREFIX CONTENT NEVER EARNS SURGERY AUTHORITY`.

Applying one current-base surgery changes owner custody and therefore stales the base lock of the others. Parallel source design is allowed; parallel promotion against the same exact owner/base is not automatically safe.

## Owner-surgery artifact family
Owner surgery provenance currently exists in more than one durable representation:
- textual `patches/try-forever-*.patch` artifacts;
- structured `patches/try-forever-*.delta.json` artifacts using `try-forever-owner-delta.v1`.

A custody probe that scans only one representation is a discovery aid, not exhaustive promotion evidence. Likewise, a scan that silently drops a matching malformed artifact, follows a redirector, waits on a special file, or traverses an unbounded directory while claiming a bounded inventory is not exhaustive evidence.

## Three finite custody throats
### 1. Directory traversal throat
The `patches/` inventory is non-recursive and bounded before parsing:
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
- If directory traversal, candidate collection, or any matching artifact admission produces a discovery error, do not call the candidate inventory exhaustive.
- On traversal or candidate overflow, emit **zero partial promotion authority** from that inventory.
- When multiple unapplied promotion candidates share one authenticated current owner/base, deliberately choose one of:
  1. converge compatible consequences into one canonical surgery;
  2. define an explicit promotion order and rebase later surgeries after authenticated owner readback;
  3. keep one or more seams source-only until the owner changes.
- Never apply one surgery and continue describing siblings as current-base-ready.
- Do not infer a mega-patch merely because a collision set exists. Prefer the smallest deliberate convergence or serialized/rebased promotion plan that preserves one-owner semantics.
- Source/provenance existence does not equal owner wiring.
- Owner source wiring does not equal regression execution, TESTED, runtime UI, TalkBack, deployment, phone delivery, or acceptance.

## Deterministic source evidence
`tools/try_forever_owner_surgery_custody_probe.py` **v6**:
- performs one bounded non-recursive directory scan;
- counts all directory entries;
- bounds the matching patch+delta candidate set separately;
- reuses the existing finite ordinary-file observer for each admitted artifact;
- groups active unapplied surgeries by owner + exact base blob;
- accepts caller-supplied authenticated current-owner blob evidence.

Its outputs distinguish:
- `CURRENT_BASE_COLLISION_SET` — multiple active candidates share the authenticated current owner/base;
- `STALE_BASE_GROUP` — candidate base differs from authenticated current owner custody;
- `UNVERIFIED_BASE_GROUP` — no authenticated current owner blob was supplied, so promotion readiness is unproven;
- `discoveryErrors` + `evidenceComplete=false` — traversal, candidate-set, or artifact evidence could not be safely admitted, so exhaustive custody is unproven.

`tools/test_try_forever_owner_surgery_custody_probe.py` now includes hostile source fixtures for:
- candidate max+1 with zero partial authority;
- unrelated directory-entry max+1 with zero partial authority;
- matching special/non-ordinary topology;
- malformed patch metadata and UTF-8;
- over-budget patch/delta evidence;
- conflicting aliases and duplicate JSON members.

It remains regression source only until an authorized non-phone execution lane runs it.

## Current PR #329 source truth — 2026-08-22
The native overlay owner is not mutated by this skill slice. Owner-surgery custody v6 is repository/source evidence only.

Known patch-form current-base promotion candidates remain design provenance subject to fresh authenticated owner custody and this inventory's completeness. A known list is never automatically an exhaustive list.

The earlier selection-only and heartbeat-announcement-only artifacts remain superseded provenance and must not be applied alone.

## P0 / phone firewall
This skill owns no Phone Hands ticket, primary-phone command, recovery queue, Nightcore, Pocket TTS, Chromium, Context Organs, physical acceptance, P0 coordination, or duplicate native owner.

## Capability membrane
`requested → source policy/probe → authenticated readback → regression source → regression executed → promotion plan → owner mutation → authenticated owner readback → tested → runtime UI → runtime TalkBack → deployed → callable → executed → delivered → accepted`.

Current state: v6 skill/probe source **YES**; bounded traversal + candidate + finite-artifact hostile regression source **YES / UNEXECUTED**; owner mutation from this skill **NO**; TESTED/runtime/phone states **NO**.
