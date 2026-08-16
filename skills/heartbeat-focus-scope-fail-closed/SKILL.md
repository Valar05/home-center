# Heartbeat Focus-Scope Fail-Closed

## Purpose

Prevent ambiguous loss of heartbeat-child keyboard focus from being misreported as proof that a structural rebuild destroyed focus. This skill is a narrow safety scar layered on `heartbeat-viewport-contact`, `heartbeat-native-ui-projection`, and `execution-truth`.

## Current source truth

The existing `OperatorOverlayService` still calls the backward-compatible five-argument `HeartbeatViewportRestorePolicy.shouldRestoreCapturedOwner(...)` and still observes keyboard focus only inside `heartbeatLights`.

The backward-compatible overload therefore **must fail closed** when a keyboard-derived ticket sees empty heartbeat-child focus. Missing focus-scope evidence is not rebuild evidence. The explicit overload is the only source path allowed to grant empty-focus amnesty, and only when both facts are supplied:

1. the actual heartbeat mutation may destroy the native focused Button; and
2. no direct keyboard focus is known elsewhere under the existing overlay owner.

This change is intentionally conservative. Until the existing owner supplies those facts, a keyboard-derived viewport ticket may decline to restore after an ambiguous rebuild rather than risk yanking the wall after focus moved to STOP, Adam input, or another overlay control.

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

A non-heartbeat focused overlay control is a competing interaction owner for a keyboard-derived viewport restore. A selected heartbeat semantic id remains a separate state. TalkBack accessibility focus remains a separate unproven runtime state.

## Regression doctrine

At minimum preserve source fixtures proving:

- the legacy five-argument overload rejects ambiguous empty heartbeat focus;
- the explicit overload rejects empty focus for a stable in-place mutation;
- the explicit overload permits rebuild-caused empty focus only when no direct overlay focus is known elsewhere;
- non-heartbeat direct focus cancels a keyboard-derived rebuild ticket;
- the same non-empty heartbeat keyboard owner remains valid;
- selection-derived tickets are not invalidated merely by unrelated keyboard-focus motion.

Regression source is not test evidence until an authorized runner executes it.

## Evidence membrane

Track independently:

`requested → fail-closed legacy policy source → regression source → existing-owner explicit focus-scope wiring → tested → runtime viewport observed → runtime keyboard focus observed → runtime TalkBack observed → deployed → callable → executed → delivered → accepted`

Current bounded truth for this scar:

- fail-closed legacy policy source: **YES**
- regression source: **YES**
- existing-owner explicit mutation-class/focus-scope wiring: **NO**
- deterministic tests: **NO / blocked by the current Actions budget boundary**
- runtime/deployed/callable/executed/delivered/accepted: **NO**

## P0 / phone firewall

This is independent non-phone source work. It must not consume Phone Hands, primary-phone execution, queue/device probes, Fortress recovery orchestration, Nightcore, Pocket TTS, Chromium, Context Organs, or the P0 physical acceptance chain.
