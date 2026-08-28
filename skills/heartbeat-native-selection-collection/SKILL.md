# Heartbeat Native Selection Collection

## Purpose
Keep persistent heartbeat-light selection semantically honest in the existing native Operator Overlay owner.

## Core law
`PERSISTENT ONE-OF-MANY ≠ TOGGLE`.

Selection, keyboard focus, accessibility focus, activation, detail presentation, and material-transition announcement are separate state machines. Do not infer one from another.

## Native collection contract
`HeartbeatSelectionAccessibilityPolicy` owns the accepted collection geometry for the horizontal heartbeat strip:
- controls present: **rows = 1, columns = item count**;
- item geometry: `rowIndex=0`, `columnIndex=itemIndex`;
- semantic id survives reorder; source-level `positionInSet=index+1` remains human/set-order evidence;
- stale selected id may yield zero selected items; never invent replacement selection;
- persistent selection does not request keyboard or accessibility focus.

The old rows=N / columns=1 doctrine was a transposition defect. Horizontal rendered order is modeled as columns in one row.

## Existing-owner lifecycle
Collection semantics belong to the collection lifecycle, not to per-child construction alone.

The existing `OperatorOverlayService` now counts as **SOURCE_WIRED** because it:
- preserves its canonical semantic selected id and native `Button.setSelected(...)` lifecycle;
- owns one `applyHeartbeatSelectionAccessibility(...)` helper;
- calls that helper after a full rebuild;
- calls it after stable in-place content synchronization;
- calls it again after persistent selection changes;
- delegates `rowCount`, `columnCount`, `rowIndex`, and `columnIndex` to `HeartbeatSelectionAccessibilityPolicy` instead of copying geometry constants.

Applied owner custody:
- base owner blob: `c5de1411a6b68087ae17aff83c032af754587150`;
- applied commit: `47e7ac3410b48596ad22d1c72a94580133e1596f`;
- resulting owner blob: `2935243f136359e3489a89108406e888b0ec2911`;
- canonical provenance: `patches/try-forever-heartbeat-selection-announcement-owner-combined.patch` = **APPLIED_SOURCE**.

The standalone native-selection and material-transition patches remain historical/superseded provenance and must not be applied independently.

## Accessibility and contact laws
- Keep existing minimum touch targets and visible-focus behavior.
- Selection does not authorize focus theft.
- An interrupted/rejected heartbeat keeps last-good visible contact; discarded attempted controls do not become current collection items.
- Selection itself does not authorize Christmas-light motion; motion remains governed by material heartbeat transition identity and reduced-motion/platform gates.
- The native source wiring is not runtime TalkBack evidence.

## Regression / capability membrane
`tools/test_try_forever_heartbeat_owner_patch_convergence.py` now treats the owner composition as convergence source and preserves Spotify/detail/Adam repeatable accessibility receipts.

Keep states separate:
`requested → supporting source → owner source wired → regression source → regression executed → tested → runtime UI → runtime TalkBack → deployed → callable → executed → delivered → accepted`.

Current truth:
- corrected horizontal geometry: **SOURCE_WIRED**;
- native collection/item owner wiring: **SOURCE_WIRED / APPLIED_SOURCE**;
- heartbeat material-transition live-region owner wiring: **SOURCE_WIRED / APPLIED_SOURCE**;
- Spotify/detail/Adam repeatable receipt migrations: **NOT APPLIED / blockers remain**;
- regression source: **YES / UNEXECUTED**;
- TESTED / runtime UI / runtime TalkBack / deployed / phone delivered / accepted: **NO**.

## P0 / phone firewall
This skill owns no Phone Hands ticket, primary-phone command, recovery queue, Nightcore, Pocket TTS, Chromium, Context Organs, PR317/PR318 mutation, physical acceptance, or P0 coordination. Repository/source work does not reopen the shared phone surface.

## Pulse rule
Light this skill only when persistent-selection semantics, collection geometry, owner lifecycle wiring, or their evidence state materially changes.
