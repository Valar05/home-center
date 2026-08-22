# Operator Owner Surgery Custody

## Purpose
Prevent unapplied source surgeries from racing the same existing native owner while each still claims exact custody of the same base blob.

This skill is about **patch promotion topology**, not another overlay controller, patch executor, scheduler, or phone lane.

## Core law
`SAME OWNER + SAME BASE BLOB + MULTIPLE PROMOTION CANDIDATES = COLLISION SET`.

Applying one surgery changes owner custody and therefore stales the base lock of the others. Parallel source design is allowed; parallel promotion against the same exact owner/base is not automatically safe.

## Required behavior
- Preserve the existing owner. Do not create a neighboring controller merely to avoid patch conflicts.
- Every review-ready surgery names an authenticated owner path and exact base blob.
- Rejected, superseded, and already-applied artifacts are provenance, not promotion candidates.
- When multiple unapplied promotion candidates share one owner/base, deliberately choose one of:
  1. converge compatible consequences into one canonical surgery;
  2. define an explicit promotion order and rebase later surgeries after authenticated owner readback;
  3. keep one or more seams source-only until the owner changes.
- Never apply one patch and continue describing the siblings as current-base-ready.
- Patch/source existence does not equal owner wiring.
- Owner source wiring does not equal regression execution, TESTED, runtime UI, TalkBack, deployment, phone delivery, or acceptance.

## Deterministic source evidence
`tools/try_forever_owner_surgery_custody_probe.py` scans TRY FOREVER patch provenance and groups active unapplied surgeries by owner + exact base blob. A group with more than one promotion candidate becomes `COLLISION_SET`.

`tools/test_try_forever_owner_surgery_custody_probe.py` is regression source only until an authorized execution lane runs it.

## Current PR #329 finding — 2026-08-21 22:59 CT
The selection-collection repair and heartbeat automatic material-transition migration both targeted `OperatorOverlayService` blob `c5de1411a6b68087ae17aff83c032af754587150`. They are now converged into `patches/try-forever-heartbeat-selection-announcement-owner-combined.patch`; the two standalone artifacts are superseded provenance and must not be applied alone.

Fresh archaeology also shows other independent unapplied owner surgeries on that same owner/base family, including collapsed operational-contact and Adam mode/input accessibility work. This skill does **not** demand one giant mega-patch. It demands that promotion be serialized/converged deliberately with authenticated owner readback so a source-ready surgery cannot silently become stale after a sibling lands.

## P0 / phone firewall
This skill owns no Phone Hands ticket, primary-phone command, recovery queue, Nightcore, Pocket TTS, Chromium, Context Organs, physical acceptance, P0 coordination, or duplicate native owner.

## Capability membrane
`requested → source policy/probe → regression source → promotion plan → owner mutation → authenticated readback → regression executed → tested → runtime UI → runtime TalkBack → deployed → callable → executed → delivered → accepted`.

Current state: skill/probe/regression source **YES**; probe execution **NO**; owner mutation from this skill **NO**; TESTED/runtime/phone states **NO**.
