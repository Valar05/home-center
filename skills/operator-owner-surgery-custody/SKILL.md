# Operator Owner Surgery Custody

## Purpose
Prevent unapplied source surgeries from racing the same existing native owner while each still claims exact custody of the same base blob.

This skill is about **patch promotion topology**, not another overlay controller, patch executor, scheduler, or phone lane.

## Core laws
`SAME OWNER + SAME AUTHENTICATED CURRENT BASE BLOB + MULTIPLE PROMOTION CANDIDATES = CURRENT_BASE_COLLISION_SET`.

`PATCH BASE != AUTHENTICATED CURRENT OWNER BLOB = STALE_BASE_GROUP`.

`NO AUTHENTICATED CURRENT OWNER BLOB = UNVERIFIED_BASE_GROUP`.

Applying one current-base surgery changes owner custody and therefore stales the base lock of the others. Parallel source design is allowed; parallel promotion against the same exact owner/base is not automatically safe.

## Required behavior
- Preserve the existing owner. Do not create a neighboring controller merely to avoid patch conflicts.
- Every review-ready surgery names an authenticated owner path and exact base blob.
- Before calling a surgery current-base-ready, bind the source inspection to a fresh authenticated current-owner blob.
- Rejected, superseded, and already-applied artifacts are provenance, not promotion candidates.
- A stale-base or unverified-base candidate may remain useful design provenance, but it is **not** promotion-ready.
- When multiple unapplied promotion candidates share one authenticated current owner/base, deliberately choose one of:
  1. converge compatible consequences into one canonical surgery;
  2. define an explicit promotion order and rebase later surgeries after authenticated owner readback;
  3. keep one or more seams source-only until the owner changes.
- Never apply one patch and continue describing the siblings as current-base-ready.
- Do not infer a mega-patch merely because a collision set exists. Prefer the smallest deliberate convergence or serialized/rebased promotion plan that preserves one-owner semantics.
- Patch/source existence does not equal owner wiring.
- Owner source wiring does not equal regression execution, TESTED, runtime UI, TalkBack, deployment, phone delivery, or acceptance.

## Deterministic source evidence
`tools/try_forever_owner_surgery_custody_probe.py` v2 scans TRY FOREVER patch provenance, groups active unapplied surgeries by owner + exact base blob, and accepts caller-supplied authenticated current-owner blob evidence.

Its outputs distinguish:
- `CURRENT_BASE_COLLISION_SET` — multiple active candidates share the authenticated current owner/base;
- `STALE_BASE_GROUP` — candidate base differs from authenticated current owner custody;
- `UNVERIFIED_BASE_GROUP` — no authenticated current owner blob was supplied, so promotion readiness is unproven.

`tools/test_try_forever_owner_surgery_custody_probe.py` is regression source only until an authorized execution lane runs it.

## Current PR #329 finding — 2026-08-21 23:57 CT
Authenticated `OperatorOverlayService` blob is `c5de1411a6b68087ae17aff83c032af754587150`.

Known active current-base surgeries include:
- `patches/try-forever-heartbeat-selection-announcement-owner-combined.patch` — canonical heartbeat selection collection + automatic material-transition announcement source surgery;
- `patches/try-forever-operational-contact-owner.patch` — collapsed Home Center operational-contact refresh only;
- `patches/try-forever-adam-mode-input-accessibility-owner.patch` — Adam persistent mode/input/Send accessibility lifecycle.

These are independent semantic concerns sharing one exact native owner/base. This skill does **not** demand one giant mega-patch. The current promotion plan is to keep the three source surgeries intact, choose one for first promotion, obtain authenticated post-mutation owner custody, then rebase the remaining siblings before any later promotion.

The earlier selection-only and heartbeat-announcement-only artifacts remain superseded provenance and must not be applied alone.

## P0 / phone firewall
This skill owns no Phone Hands ticket, primary-phone command, recovery queue, Nightcore, Pocket TTS, Chromium, Context Organs, physical acceptance, P0 coordination, or duplicate native owner.

## Capability membrane
`requested → source policy/probe → regression source → promotion plan → owner mutation → authenticated readback → regression executed → tested → runtime UI → runtime TalkBack → deployed → callable → executed → delivered → accepted`.

Current state: skill/probe/regression source **YES**; current-owner-custody-aware probe source **YES**; probe execution **NO**; owner mutation from this skill **NO**; TESTED/runtime/phone states **NO**.
