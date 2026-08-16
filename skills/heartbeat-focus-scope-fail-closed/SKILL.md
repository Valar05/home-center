# Heartbeat Focus-Scope Fail-Closed

## Purpose

Prevent stale heartbeat viewport restores from treating persistent selection or missing heartbeat-child keyboard focus as stronger evidence than newer interaction. This skill is a narrow safety scar layered on `heartbeat-viewport-contact`, `heartbeat-native-ui-projection`, and `execution-truth`.

## Current source truth

The existing `OperatorOverlayService` now consumes the explicit seven-argument `HeartbeatViewportRestorePolicy.shouldRestoreCapturedOwner(...)` overload. The owner supplies both facts the pure policy requires:

1. whether the heartbeat mutation that actually occurred may destroy the native focused Button; and
2. whether any direct keyboard focus currently exists anywhere under the existing overlay root.

Structural rebuild and live-structure-drift fallback rebuild set `mutationMayDestroyKeyboardFocus=true`; successful stable in-place refresh leaves it false. `root.findFocus() != null` is used only as overlay-wide direct keyboard-focus presence. It is **not** TalkBack accessibility focus.

The backward-compatible five-argument overload still fails closed on ambiguous empty heartbeat focus and remains valid for callers that lack complete focus-scope evidence.

## Interaction-ownership law

Persistent semantic selection is not absolute navigation ownership. A newer direct keyboard-focus move can supersede a selection-anchored viewport ticket without activating the newly focused light.

For both selection-derived and keyboard-derived tickets:

- preserve the capture-time keyboard-focused semantic id as evidence even if that secondary id disappears from the accepted current model;
- if a different non-empty heartbeat keyboard focus appears after capture, the pending restore is stale;
- if heartbeat-child focus becomes empty, a captured non-empty keyboard focus may receive amnesty only for a mutation that could destroy native focus and only when no direct overlay focus exists elsewhere;
- if no keyboard focus existed at capture or after mutation and explicit overlay scope proves no direct focus, a selection-derived ticket may remain valid;
- direct keyboard focus on STOP, Adam input, or another non-heartbeat overlay control is a competing interaction owner;
- none of these predicates query, infer, or claim TalkBack accessibility focus.

A change in persistent selection still supersedes the older ticket directly. A persistent selection remaining unchanged does **not** erase newer keyboard navigation.

## Ownership and duplicate-architecture law

- `OperatorOverlayService` remains the sole Android UI owner.
- `HeartbeatViewportRestorePolicy` remains pure policy; it must not grow Android view traversal or a second focus tracker.
- Overlay-wide direct-focus evidence belongs to the existing owner's current view tree.
- Do not query or infer TalkBack accessibility focus from `View.findFocus()` or `View.isFocused()`; this skill is about direct keyboard focus only.
- Do not create another overlay controller, renderer, state store, focus daemon, phone path, or recovery lane to solve this seam.

## Mutation-class law

`mutationMayDestroyKeyboardFocus` must describe what actually happened in that refresh:

- structural rebuild: **true**;
- live-structure-drift fallback that actually rebuilds: **true**;
- successful stable in-place content refresh: **false**.

Do not derive this flag from the original plan alone. A content refresh can fall back to rebuild after child/tag drift is discovered, so the final mutation result is authoritative.

## Overlay focus-scope law

The owner distinguishes:

- current heartbeat-child keyboard-focused semantic id; and
- whether **any** direct keyboard focus currently exists elsewhere under the overlay root.

A non-heartbeat focused overlay control is a competing interaction owner for either a keyboard-derived or selection-derived viewport restore when that focus is newer than the capture. TalkBack accessibility focus remains a separate unproven runtime state.

## Regression doctrine

At minimum preserve source fixtures proving:

- the legacy five-argument overload rejects ambiguous empty heartbeat focus;
- the explicit overload rejects empty focus for a stable in-place mutation when a captured keyboard owner existed;
- the explicit overload permits rebuild-caused empty focus only when no direct overlay focus is known elsewhere;
- non-heartbeat direct focus cancels a stale rebuild ticket;
- the same non-empty heartbeat keyboard owner remains valid;
- a newer heartbeat keyboard-focus move supersedes a selection-anchored ticket even when persistent selection is unchanged;
- a captured keyboard baseline remains evidence when that secondary id disappears from the accepted current model;
- explicit no-focus scope can keep a touch-selected ticket valid when no keyboard owner existed at capture or restore time.

Regression source is not test evidence until an authorized runner executes it.

## Evidence membrane

Track independently:

`requested → interaction-ownership policy source → fail-closed legacy policy source → regression source → existing-owner explicit mutation/focus-scope wiring → tested → runtime viewport observed → runtime keyboard focus observed → runtime TalkBack observed → deployed → callable → executed → delivered → accepted`

Current bounded truth for this scar:

- interaction-ownership policy source: **YES**
- fail-closed legacy policy source: **YES**
- regression source: **YES**
- existing-owner explicit mutation-class/focus-scope wiring: **YES**
- exact GitHub readback of owner wiring: **YES**
- deterministic tests: **NO / blocked by the current Actions budget boundary**
- runtime viewport/runtime keyboard focus/runtime TalkBack/deployed/callable/executed/delivered/accepted: **NO**

Source wiring is not runtime proof. `root.findFocus()` establishes direct keyboard-focus presence only; it does not prove accessibility focus behavior.

## P0 / phone firewall

This is independent non-phone source work. It must not consume Phone Hands, primary-phone execution, queue/device probes, Fortress recovery orchestration, Nightcore, Pocket TTS, Chromium, Context Organs, or the P0 physical acceptance chain.
