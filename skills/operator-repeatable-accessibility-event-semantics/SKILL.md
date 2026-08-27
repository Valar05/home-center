# Operator Repeatable Accessibility Event Semantics

## Purpose

Prevent deprecated announcement migration from replacing useful semantics with a fake event cannon. Repeated explicit actions must remain understandable, but **not every repeated press requires a repeated synthetic spoken confirmation**.

This skill is repository/source accessibility doctrine only. It owns no Android View, controller, renderer, phone execution, P0 recovery, deployment, delivery, or acceptance lane.

## Core distinction

A live region is a semantic **value-change** surface. A native control exposes an **action**. A persistent selected/result surface exposes **state**. Those ingredients can describe a replacement, but a plausible replacement design is not automatically safe enough to remove an existing explicit event receipt.

The exact promotion question is:

`Has this repeatable explicit event been reviewed as a complete owner contract, including identical-repeat behavior, failure/result behavior, focus ownership, mute behavior, persistent inspection, and the correct native selection geometry?`

Until yes, fail closed, keep the legacy event receipt, and carry a typed `MigrationBlocker` that says what remains unresolved.

## Current TRY FOREVER contract

1. **Spotify explicit command receipt — design exists / owner migration NOT ready.**
   - The command button names the action and `spotifyStatus` exposes a changing result value.
   - A changed-status live-region design exists, but identical-repeat event semantics remain unresolved as an owner contract.
   - Blocker: `SPOTIFY_REPEATABLE_RECEIPT_UNRESOLVED`.
   - `ownerMigrationReady=false`; keep the legacy receipt for now.

2. **Heartbeat explicit detail selection — design exists / owner migration NOT ready.**
   - The light owns semantic selection and the detail well persistently exposes Why/Consequence/Evidence/Source.
   - Re-selection semantics are not yet accepted as a complete replacement for the explicit event receipt.
   - Blocker: `DETAIL_REPEAT_SELECTION_RECEIPT_UNRESOLVED`.
   - `ownerMigrationReady=false`; keep the legacy receipt for now.

3. **Adam send confirmation — design exists / owner migration NOT ready.**
   - Mode-specific action/result semantics exist in source design.
   - Same-mode resend and future asynchronous result/failure semantics are not yet accepted as a complete owner contract.
   - Blocker: `ADAM_REPEAT_SEND_RESULT_UNRESOLVED`.
   - `ownerMigrationReady=false`; keep the legacy receipt for now.

4. **Automatic heartbeat material transition — separate value-change case / owner migration READY.**
   - Existing transition/announcement identity already represents a material semantic change.
   - Blocker: `NONE`.
   - The narrow one-shot polite-live-region design remains the only review-ready announcement migration.

## Authenticated owner revalidation — 2026-08-27 16:00 source checkpoint

Fresh PR-head readback keeps capability states separate:

- `OperatorOverlayService.java` remains exact blob `c5de1411a6b68087ae17aff83c032af754587150` and still contains the legacy Spotify, heartbeat-summary, heartbeat-detail, and Adam announcement receipts;
- `patches/try-forever-heartbeat-selection-announcement-owner-combined.patch` remains base-locked to that exact owner blob and **CANONICAL_PROPOSED_NOT_APPLIED**;
- the heartbeat selection policy had a separate supporting-source defect: a horizontal strip was transposed into rows=N / columns=1;
- that supporting policy is now corrected to rows=1 / columns=N with `rowIndex=0` and `columnIndex=item index`;
- its deterministic JUnit and doctrine/source regressions were converged, but remain **UNEXECUTED**;
- the combined patch delegates row/column values to the policy rather than hard-coding them, so its owner blob lock remains current after the supporting policy correction;
- therefore heartbeat automatic transition migration remains **REVIEW_READY DESIGN / OWNER_WIRED NO**, while Spotify/detail/Adam blockers remain non-`NONE` and their legacy receipts remain untouched.

Fresh Android framework orientation guidance supports the geometry correction: a horizontally scrolling layout reports one accessibility row and item-count columns. Reference: https://developer.android.com/reference/androidx/recyclerview/widget/RecyclerView.LayoutManager

This is an exact source boundary, not runtime evidence and not permission to consume the phone/P0 surface.

## Laws

1. **Repeated action does not automatically imply repeated announcement.** Prefer native action + persistent semantic result when that replacement contract is actually complete.
2. **Design-ready is not owner-migration-ready.** Keep those capability states separate.
3. **Migration-unready must name its wound.** A typed blocker is required; do not leave `false` as unexplained archaeology.
4. **Same value is not fresh evidence.** Never mutate text solely to trigger accessibility output.
5. **Changed async result may use a live region.** Gate it to the explicit action and actual semantic value change; startup/poll changes remain silent unless independently authorized.
6. **Selection is state.** Selection+detail can be part of a replacement, but must not silently erase a meaningful event receipt before acceptance.
7. **Collection geometry follows the rendered axis.** A horizontal native strip is one row with item columns; do not transpose it while claiming selection semantics are complete.
8. **Action labels track action.** Mode/state-sensitive controls must expose their exact current action.
9. **No fake freshness.** No decorative timestamps, counters, punctuation, zero-width markers, or opaque request IDs.
10. **Do not steal focus.** Programmatic focus movement needs its own interaction contract and runtime proof.
11. **Do not blanket-live-region a frequently refreshed value.** A live region that speaks polls is a regression, not accessibility.
12. **Review-ready patch custody is exact.** Only a migration intended for promotion tracks the authenticated current owner blob. Rejected historical surgery must stay rejected rather than being continuously rebased into a tempting current-looking patch.
13. **One owner.** Compose `OperatorOverlayService`; do not create a neighboring accessibility-event controller.
14. **Capability membrane:** `policy source → regression source → owner patch → owner source wired → regression executed → tested → runtime TalkBack → deployed → delivered → accepted`.
15. **P0 firewall:** no Phone Hands, primary-phone execution, recovery orchestration, Nightcore, Pocket TTS, Chromium, Context Organs, or physical acceptance.

## Owner acceptance questions

Before removing one legacy `announceForAccessibility(...)` call:

- Is its typed `MigrationBlocker` now `NONE`, and what evidence paid that blocker?
- Is the control/action accurately named?
- Is the resulting semantic state/value persistently inspectable?
- Does collection geometry match the rendered orientation and item order?
- What happens when the same action repeats and the persistent value does not change?
- What happens on asynchronous failure or delayed result?
- For live-region use, did the semantic value actually change?
- Can background/poll work mutate the same surface, and is that path gated silent?
- Does the design preserve mute, selection, focus, viewport-contact, and contact-preservation laws?
- Does the existing native owner carry the design?
- Is any one-shot live-region authority reset after the intended mutation?
- Does regression source distinguish source design from owner wiring and runtime proof?

If any owner event-semantics question is unresolved, keep the legacy call and keep a non-`NONE` typed blocker.

## Current PR #329 source truth — 2026-08-27 16:00

- doctrine: **YES / IMPLEMENTED_SOURCE**;
- supporting semantic designs for all four consequences: **YES**;
- heartbeat horizontal collection policy: **SOURCE_CORRECTED / ROWS=1 / COLUMNS=N**;
- heartbeat material transition: **OWNER_MIGRATION_READY=true / blocker NONE / OWNER_WIRED NO**;
- Spotify receipt: **OWNER_MIGRATION_READY=false / typed blocker / OWNER_WIRED NO**;
- repeated detail selection: **OWNER_MIGRATION_READY=false / typed blocker / OWNER_WIRED NO**;
- Adam send confirmation: **OWNER_MIGRATION_READY=false / typed blocker / OWNER_WIRED NO**;
- canonical combined heartbeat-selection + material-transition patch: **CANONICAL_PROPOSED_NOT_APPLIED / exact current owner blob lock**;
- geometry + owner-patch regression source: **YES / UNEXECUTED**;
- authenticated current owner still contains all four legacy calls: **YES / blob c5de1411a6b68087ae17aff83c032af754587150**;
- She-Raw pre-execution consultation at this checkpoint: **FAULT / account connection HTTP 400**, no substitute reviewer;
- TESTED / runtime TalkBack / deployed / callable / executed / delivered / accepted: **NO unless fresh exact-head evidence proves otherwise**.
