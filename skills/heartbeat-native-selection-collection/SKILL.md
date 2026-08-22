# Heartbeat Native Selection Collection

## Purpose
Keep persistent heartbeat-light selection semantically honest across DOM specimens and the existing native Operator Overlay owner.

A heartbeat light selects one item whose Why/Consequence/Evidence/Source appears in a shared detail surface. Activating the selected light does not switch selection off. This is a persistent one-of-many state machine, not a toggle.

## Core law
`PERSISTENT ONE-OF-MANY ≠ TOGGLE`.

Selection, keyboard focus, accessibility focus, activation, and detail presentation are separate state machines. Do not infer one from another.

### DOM / source specimens
Use radio-style semantics for a persistent mutually-exclusive light set:
- one `radiogroup` owner;
- each light exposes `role=radio` + `aria-checked`;
- exactly one selected light owns the tab stop when a selection exists;
- Arrow keys move and select deterministically; Home/End may select first/last;
- activating the already-selected light keeps it selected;
- the shared detail surface remains a separate persistent region;
- dynamic detail is inert text, not injected HTML.

This supersedes older heartbeat source-specimen wording that treated persistent light selection as `aria-pressed` toggle state. The reusable `persistent-selection-semantics` law is authoritative on this point.

### Native Android source contract
The existing `OperatorOverlayService` already carries a semantic selected id and calls `Button.setSelected(...)`. That is not the complete accessibility collection contract by itself.

`HeartbeatSelectionAccessibilityPolicy` defines source-only collection/item semantics from the already accepted `HeartbeatOverlayViewModel.Model`:
- one single-selection collection when controls exist;
- because the native control strip is a horizontal list, Android collection geometry is **rows = item count, columns = 1**;
- each item uses zero-based `rowIndex=index`, `columnIndex=0` for native collection geometry;
- a separate source-level one-based `positionInSet=index+1` remains useful for human/set-order semantics;
- semantic id remains the identity across reorder;
- stale selection does not invent a replacement selection;
- selection does not claim keyboard or accessibility focus ownership.

The Android platform documents a horizontal list as one column with as many rows as list items. Do not transpose this into one row/many columns merely because the Views are laid out left-to-right; that was caught and repaired in the 2026-08-21 19:57 Regnet pass.

Before native owner state may be called `SOURCE_WIRED`, direct owner evidence must include both the existing selected-state lifecycle and explicit collection/item semantics for the heartbeat row/items. Comments, literals, wrong methods, policy existence, or a patch artifact do not count.

For the current minSdk 26 source contract, any eventual owner implementation must also respect Android API availability. Do not silently replace source policy with API-level assumptions or claim runtime TalkBack behavior from `AccessibilityNodeInfo` source alone.

## Touch and motion
Keep the existing minimum touch target and visible-focus contracts. Selection semantics do not authorize new animation. Christmas-light motion remains governed by material heartbeat transition identity; selecting a light to inspect detail is not a new heartbeat transition.

## Contact preservation
An interrupted or rejected heartbeat keeps the last-good visible selection surface. Do not expose discarded attempted controls as current collection items. A stale selected id may yield zero selected items rather than inventing a new selected identity.

## Capability membrane
Keep these separate:
`requested → supporting source → owner source wired → regression executed → tested → runtime UI → runtime TalkBack → deployed → callable → executed → delivered → accepted`.

A Java policy, JUnit source, DOM specimen, or owner probe is not runtime TalkBack proof.

## Current PR #329 truth — 2026-08-21 19:57 CT
- persistent-selection reusable doctrine: **YES**;
- corrected radio-style heartbeat DOM specimen: **SOURCE YES**;
- `HeartbeatSelectionAccessibilityPolicy`: **SUPPORTING SOURCE YES**;
- Android horizontal geometry Regnet correction: **APPLIED SOURCE YES**;
- deterministic JUnit source: **YES / UNEXECUTED**;
- direct-owner source probe + hostile fixture: **YES / UNEXECUTED**;
- current native owner selected-state lifecycle: **YES / SOURCE**;
- native collection/item owner wiring: **NO / PARTIAL_UNSAFE**;
- TESTED / runtime UI / runtime TalkBack / deployed / phone delivered / accepted: **NO**.

## P0 / phone firewall
This skill owns no Phone Hands ticket, primary-phone command, recovery queue, Nightcore, Pocket TTS, Chromium, Context Organs, physical acceptance, or P0 coordination. Repository/source work does not reopen the shared phone surface.

## Done for one pulse
Light this skill only when the persistent-selection contract, native collection semantics, owner evidence boundary, or source specimen materially changes. Once those source seams are stable, keep it dark until fresh evidence changes them.
