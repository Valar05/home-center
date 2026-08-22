# Operator Owner Surgery Custody

## Purpose
Prevent unapplied source surgeries from racing the same existing owner while each still claims exact custody of the same base blob.

This skill is about **promotion topology and evidence custody**, not another overlay controller, patch executor, scheduler, recovery daemon, or phone lane.

## Core laws
`SAME OWNER + SAME AUTHENTICATED CURRENT BASE BLOB + MULTIPLE PROMOTION CANDIDATES = CURRENT_BASE_COLLISION_SET`.

`ARTIFACT BASE != AUTHENTICATED CURRENT OWNER BLOB = STALE_BASE_GROUP`.

`NO AUTHENTICATED CURRENT OWNER BLOB = UNVERIFIED_BASE_GROUP`.

`RECOGNIZED OWNER-SURGERY ARTIFACT THAT CANNOT BE SAFELY PARSED = EVIDENCE INCOMPLETE`.

Applying one current-base surgery changes owner custody and therefore stales the base lock of the others. Parallel source design is allowed; parallel promotion against the same exact owner/base is not automatically safe.

## Owner-surgery artifact family
Owner surgery provenance currently exists in more than one durable representation:
- textual `patches/try-forever-*.patch` artifacts;
- structured `patches/try-forever-*.delta.json` artifacts using `try-forever-owner-delta.v1`.

A custody probe that scans only one representation is a discovery aid, not exhaustive promotion evidence.

Structured owner deltas may use historical compatible spellings for their exact base blob (`baseBlob`, `ownerBaseBlob`, or `baseOwnerBlob`) and state (`state` or `status`). If multiple supported aliases occur, their values must agree exactly. Duplicate JSON members, conflicting aliases, unsupported schema, malformed JSON, invalid owner/base/state, or other parse failure become bounded `discoveryErrors`; they are not silently ignored.

## Required behavior
- Preserve the existing owner. Do not create a neighboring controller merely to avoid surgery conflicts.
- Every review-ready surgery names an owner path and exact base blob.
- Before calling a surgery current-base-ready, bind source inspection to a fresh authenticated current-owner blob.
- Rejected, superseded, and already-applied artifacts are provenance, not promotion candidates.
- A stale-base or unverified-base candidate may remain useful design provenance, but it is **not** promotion-ready.
- If recognized surgery artifacts produced discovery errors, do not call the candidate inventory exhaustive.
- When multiple unapplied promotion candidates share one authenticated current owner/base, deliberately choose one of:
  1. converge compatible consequences into one canonical surgery;
  2. define an explicit promotion order and rebase later surgeries after authenticated owner readback;
  3. keep one or more seams source-only until the owner changes.
- Never apply one surgery and continue describing siblings as current-base-ready.
- Do not infer a mega-patch merely because a collision set exists. Prefer the smallest deliberate convergence or serialized/rebased promotion plan that preserves one-owner semantics.
- Source/provenance existence does not equal owner wiring.
- Owner source wiring does not equal regression execution, TESTED, runtime UI, TalkBack, deployment, phone delivery, or acceptance.

## Deterministic source evidence
`tools/try_forever_owner_surgery_custody_probe.py` **v3** scans both patch and structured-delta surgery provenance, groups active unapplied surgeries by owner + exact base blob, and accepts caller-supplied authenticated current-owner blob evidence.

Its outputs distinguish:
- `CURRENT_BASE_COLLISION_SET` — multiple active candidates share the authenticated current owner/base;
- `STALE_BASE_GROUP` — candidate base differs from authenticated current owner custody;
- `UNVERIFIED_BASE_GROUP` — no authenticated current owner blob was supplied, so promotion readiness is unproven;
- `discoveryErrors` + `evidenceComplete=false` — recognized owner-delta evidence could not be safely admitted, so exhaustive custody is unproven.

`tools/test_try_forever_owner_surgery_custody_probe.py` is regression source only until an authorized non-phone execution lane runs it.

## Current PR #329 source truth — 2026-08-22
Authenticated `OperatorOverlayService` blob is `c5de1411a6b68087ae17aff83c032af754587150`.

Known patch-form current-base promotion candidates include:
- `patches/try-forever-heartbeat-selection-announcement-owner-combined.patch`;
- `patches/try-forever-operational-contact-owner.patch`;
- `patches/try-forever-adam-mode-input-accessibility-owner.patch`.

The repository also contains structured owner-delta provenance for other owners. v2 scanned only `.patch`; therefore the previous three-item inventory was **known patch evidence, not an exhaustive repository owner-surgery inventory**. v3 closes that source blind spot, but its regression/exhaustive execution remains unproven until an authorized runner supplies a receipt.

The earlier selection-only and heartbeat-announcement-only artifacts remain superseded provenance and must not be applied alone.

## P0 / phone firewall
This skill owns no Phone Hands ticket, primary-phone command, recovery queue, Nightcore, Pocket TTS, Chromium, Context Organs, physical acceptance, P0 coordination, or duplicate native owner.

## Capability membrane
`requested → source policy/probe → authenticated readback → regression source → regression executed → promotion plan → owner mutation → authenticated owner readback → tested → runtime UI → runtime TalkBack → deployed → callable → executed → delivered → accepted`.

Current state: v3 skill/probe source **YES**; patch+delta regression source **YES / UNEXECUTED**; authenticated current owner readback **YES**; owner mutation from this skill **NO**; TESTED/runtime/phone states **NO**.
