# Operator Repeatable Accessibility Event Semantics

## Purpose

Prevent deprecated announcement migration from replacing useful semantics with a fake event cannon. Repeated explicit actions must remain understandable, but **not every repeated press requires a repeated synthetic spoken confirmation**.

This skill is repository/source accessibility doctrine only. It owns no Android View, controller, renderer, phone execution, P0 recovery, deployment, delivery, or acceptance lane.

## Core distinction

A live region is a semantic **value-change** surface. A native control exposes an **action**. A persistent selected/result surface exposes **state**. Those ingredients can describe a replacement, but a plausible replacement design is not automatically safe enough to remove an existing explicit event receipt.

The exact promotion question is:

`Has this repeatable explicit event been reviewed as a complete owner contract, including identical-repeat behavior, failure/result behavior, focus ownership, mute behavior, and persistent inspection?`

Until yes, fail closed and keep the legacy event receipt.

## Current TRY FOREVER contract — 2026-08-21 0400

1. **Spotify explicit command receipt — design exists / owner migration NOT ready.**
   - The command button names the action and `spotifyStatus` exposes a changing result value.
   - A changed-status live-region design exists, but identical-repeat event semantics remain unresolved as an owner contract.
   - `ownerMigrationReady=false`; keep the legacy receipt for now.

2. **Heartbeat explicit detail selection — design exists / owner migration NOT ready.**
   - The light owns semantic selection and the detail well persistently exposes Why/Consequence/Evidence/Source.
   - Re-selection semantics are not yet accepted as a complete replacement for the explicit event receipt.
   - `ownerMigrationReady=false`; keep the legacy receipt for now.

3. **Adam send confirmation — design exists / owner migration NOT ready.**
   - Mode-specific action/result semantics exist in source design.
   - Same-mode resend and future asynchronous result/failure semantics are not yet accepted as a complete owner contract.
   - `ownerMigrationReady=false`; keep the legacy receipt for now.

4. **Automatic heartbeat material transition — separate value-change case / owner migration READY.**
   - Existing transition/announcement identity already represents a material semantic change.
   - The narrow one-shot polite-live-region owner surgery is the only currently review-ready migration.

## Laws

1. **Repeated action does not automatically imply repeated announcement.** Prefer native action + persistent semantic result when that replacement contract is actually complete.
2. **Design-ready is not owner-migration-ready.** Keep those capability states separate.
3. **Same value is not fresh evidence.** Never mutate text solely to trigger accessibility output.
4. **Changed async result may use a live region.** Gate it to the explicit action and actual semantic value change; startup/poll changes remain silent unless independently authorized.
5. **Selection is state.** Selection+detail can be part of a replacement, but must not silently erase a meaningful event receipt before acceptance.
6. **Action labels track action.** Mode/state-sensitive controls must expose their exact current action.
7. **No fake freshness.** No decorative timestamps, counters, punctuation, zero-width markers, or opaque request IDs.
8. **Do not steal focus.** Programmatic focus movement needs its own interaction contract and runtime proof.
9. **Do not blanket-live-region a frequently refreshed value.** A live region that speaks polls is a regression, not accessibility.
10. **One owner.** Compose `OperatorOverlayService`; do not create a neighboring accessibility-event controller.
11. **Capability membrane:** `policy source → regression source → owner patch → owner source wired → regression executed → tested → runtime TalkBack → deployed → delivered → accepted`.
12. **P0 firewall:** no Phone Hands, primary-phone execution, recovery orchestration, Nightcore, Pocket TTS, Chromium, Context Organs, or physical acceptance.

## Owner acceptance questions

Before removing one legacy `announceForAccessibility(...)` call:

- Is the control/action accurately named?
- Is the resulting semantic state/value persistently inspectable?
- What happens when the same action repeats and the persistent value does not change?
- What happens on asynchronous failure or delayed result?
- For live-region use, did the semantic value actually change?
- Can background/poll work mutate the same surface, and is that path gated silent?
- Does the design preserve mute, selection, focus, viewport-contact, and contact-preservation laws?
- Does the existing native owner carry the design?
- Is any one-shot live-region authority reset after the intended mutation?
- Does regression source distinguish source design from owner wiring and runtime proof?

If any owner event-semantics question is unresolved, keep the legacy call and mark **OWNER_MIGRATION_READY=false**.

## Current PR #329 source truth — 2026-08-21 0400

- doctrine: **YES / IMPLEMENTED_SOURCE**;
- supporting semantic designs for all four consequences: **YES**;
- heartbeat material transition: **OWNER_MIGRATION_READY=true / OWNER_WIRED NO**;
- Spotify receipt: **OWNER_MIGRATION_READY=false / OWNER_WIRED NO**;
- repeated detail selection: **OWNER_MIGRATION_READY=false / OWNER_WIRED NO**;
- Adam send confirmation: **OWNER_MIGRATION_READY=false / OWNER_WIRED NO**;
- broad four-consequence patch: **REJECTED_SUPERSEDED__DO_NOT_APPLY**;
- narrow heartbeat patch: **CORRECTED_PROPOSED_NOT_APPLIED**;
- owner-boundary regression source: **YES / UNEXECUTED**;
- authenticated existing owner still contains all four legacy calls: **YES**;
- Computer Hands worker: **offline** with existing TRY FOREVER lanes; no duplicate request;
- She-Raw pre-execution consultation: **FAULT / account connection HTTP 400**, no substitute reviewer;
- TESTED / runtime TalkBack / deployed / callable / executed / delivered / accepted: **NO**.
