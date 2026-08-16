# Heartbeat Focus-Scope Fail-Closed

## Purpose

Prevent stale heartbeat viewport restores from treating persistent selection or missing heartbeat-child keyboard focus as stronger evidence than newer interaction. This skill is a narrow safety scar layered on `heartbeat-viewport-contact`, `heartbeat-native-ui-projection`, and `execution-truth`.

## Current source truth

The existing `OperatorOverlayService` still calls the backward-compatible five-argument `HeartbeatViewportRestorePolicy.shouldRestoreCapturedOwner(...)` and still observes keyboard focus only inside `heartbeatLights`.

The backward-compatible overload therefore **must fail closed** when heartbeat-child focus is empty. Missing focus-scope evidence is not rebuild evidence. The explicit overload is the only source path allowed to grant empty-focus amnesty, and only when both facts are supplied:

1. the actual heartbeat mutation may destroy the native focused Button; and
2. no direct keyboard focus is known elsewhere under the existing overlay owner.

This conservative fallback protects both keyboard-derived and selection-derived tickets until the existing owner supplies complete focus-scope evidence.

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

When the owner eventually wires the explicit overload, `mutationMayDestroyKeyboardFocus` must describe what actually happened in that refresh:

- structural rebuild: **true**;
- live-structure-drift fallback that actually rebuilds: **true**;
- successful stable in-place content refresh: **false**.

Do not derive this flag from the original plan alone. A content refresh can fall back to rebuild after child/tag drift is discovered, so the final mutation result is authoritative.

## Overlay focus-scope law

The owner must distinguish:

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
- existing-owner explicit mutation-class/focus-scope wiring: **NO**
- deterministic tests: **NO / blocked by the current Actions budget boundary**
- runtime/deployed/callable/executed/delivered/accepted: **NO**

## P0 / phone firewall

This is independent non-phone source work. It must not consume Phone Hands, primary-phone execution, queue/device probes, Fortress recovery orchestration, Nightcore, Pocket TTS, Chromium, Context Organs, or the P0 physical acceptance chain.
