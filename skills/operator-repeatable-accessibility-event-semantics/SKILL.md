# Operator Repeatable Accessibility Event Semantics

## Purpose
Prevent accessibility announcement migration from replacing useful repeatable receipts with fake freshness or a blanket live-region cannon. This is repository/source doctrine only; it owns no phone/P0/runtime lane.

## Core distinction
A live region is a semantic **value-change** surface. A native control exposes an **action**. A persistent selected/result surface exposes **state**. Removing an explicit event receipt is allowed only when that consequence has a complete owner contract for identical repeats, failure/result behavior, focus, mute, and persistent inspection.

## Current consequence states
1. **Automatic heartbeat material transition — SOURCE_WIRED.**
   - This is the narrow value-change case.
   - Existing transition/announcement identity gates the consequence.
   - `OperatorOverlayService` now uses `AccessibilityAnnouncementSemanticPolicy` to select one-shot live-region mode for `HEARTBEAT_MATERIAL_TRANSITION` and resets the live region to `NONE` afterward.
   - WAITING, SKIP_UNCHANGED, and pre-contact clearing explicitly force `NONE`.
   - The old heartbeat-summary `announceForAccessibility(...)` call is removed from the owner.

2. **Spotify explicit command receipt — migration blocked.**
   - Blocker: `SPOTIFY_REPEATABLE_RECEIPT_UNRESOLVED`.
   - Keep the existing bounded explicit receipt.

3. **Heartbeat explicit detail selection — migration blocked.**
   - Blocker: `DETAIL_REPEAT_SELECTION_RECEIPT_UNRESOLVED`.
   - Persistent selection/detail semantics exist, but repeated explicit selection has not earned receipt removal.

4. **Adam send confirmation — migration blocked, repeat-cycle contract sharpened.**
   - Blocker remains `ADAM_REPEAT_SEND_RESULT_UNRESOLVED`.
   - Source policy now explicitly requires an intervening READY state before a later successful SENT state can stand in for a repeatable result receipt.
   - The intended lifecycle is: successful send → SENT; the field is cleared; any newer unsent source, including rejected OVER_BUDGET contact, drives SENT → READY; only a later successful submit may drive READY → SENT again.
   - This prevents a permanently true SENT sticker from masquerading as evidence of repeated successful sends.
   - Native Adam result-state ownership is still not wired, so keep the existing explicit send receipt. Supporting lifecycle design is not permission to remove it.

## Applied owner custody
The canonical combined selection + material-transition surgery is **APPLIED_SOURCE**:
- base owner blob: `c5de1411a6b68087ae17aff83c032af754587150`;
- applied owner commit: `47e7ac3410b48596ad22d1c72a94580133e1596f`;
- resulting owner blob: `2935243f136359e3489a89108406e888b0ec2911`;
- provenance: `patches/try-forever-heartbeat-selection-announcement-owner-combined.patch`.

The same mutation composes `HeartbeatSelectionAccessibilityPolicy` into the native collection lifecycle. Horizontal geometry remains **rows=1 / columns=N**, with `rowIndex=0` and `columnIndex=itemIndex`; the owner consumes policy fields rather than duplicating those constants.

`tools/test_try_forever_heartbeat_owner_patch_convergence.py` is convergence regression source. It requires the native collection helper and heartbeat live-region wiring while preserving the Spotify/detail/Adam legacy receipts. It remains **UNEXECUTED**.

## Laws
1. Repeated action does not automatically imply repeated announcement; replacement semantics must be complete first.
2. Same value is not fresh evidence. Never mutate text only to trigger accessibility output.
3. Do not blanket-live-region a frequently refreshed value; background/poll paths stay silent unless independently authorized.
4. Collection geometry follows the rendered axis; the horizontal strip is one row of item columns.
5. Selection is state, not focus. Do not steal keyboard/accessibility focus.
6. A one-shot live-region consequence must reset after the intended mutation.
7. Repeatable receipts with unresolved blockers stay in the sole owner.
8. Compose `OperatorOverlayService`; never create a neighboring accessibility-event controller.
9. Capability membrane: `policy source → owner source wired → regression source → regression executed → tested → runtime TalkBack → deployed → delivered → accepted`.
10. P0 firewall: no Phone Hands, recovery orchestration, Nightcore, Pocket TTS, Chromium, Context Organs, PR317/PR318 mutation, or physical acceptance.
11. A persistent success state may replace a repeatable explicit receipt only if source truth guarantees that another material attempt must leave that success state before a later success can re-enter it. For Adam Send, that means READY must intervene before a later SENT; OVER_BUDGET unsent contact must also break stale SENT.
12. Supporting repeat-cycle semantics do not green-paint native owner wiring. Until `OperatorOverlayService` actually owns the READY/SENT lifecycle and its source/runtime evidence converges, the legacy Adam send receipt stays present.

## Current truth
- heartbeat horizontal collection policy: **SOURCE_WIRED / ROWS=1 / COLUMNS=N**;
- heartbeat material-transition migration: **SOURCE_WIRED / APPLIED_SOURCE**;
- Spotify receipt migration: **NO / blocker non-NONE**;
- repeated detail-selection receipt migration: **NO / blocker non-NONE**;
- Adam repeat-result cycle contract: **SUPPORTING SOURCE YES / READY MUST INTERVENE BEFORE REPEATED SENT**;
- Adam send receipt migration: **NO / blocker non-NONE / NATIVE RESULT OWNER UNWIRED**;
- owner-convergence regression source: **YES / UNEXECUTED**;
- TESTED / runtime TalkBack / deployed / callable / executed / delivered / accepted: **NO absent fresh evidence**.
