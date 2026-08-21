# Heartbeat Collapsed-Owner Speech Load

## Purpose
Keep the accessibility surface that survives a collapsed Operator Overlay **useful as an action control** instead of turning it into a miniature audiobook.

A broad accepted heartbeat may contain dozens of material lights and up to twelve names in the normal collapsed scene summary. That breadth is appropriate when the heartbeat detail surface is explicitly inspected. It is not appropriate to transplant wholesale onto the persistent drag/expand handle, which TalkBack may encounter simply because the user navigated to the control.

## Canonical split
The existing source chain remains authoritative:

`HeartbeatSceneGraph.Frame -> HeartbeatOverlayViewModel -> HeartbeatCollapsedOwnerAccessibility -> OperatorOverlayService.dragHandle`

When the heartbeat detail subtree is collapsed, the surviving owner description contains only:

1. the existing drag/expand action;
2. the current material Home Center operational-status description supplied by the existing owner;
3. the canonical heartbeat summary (`waiting`, `0 LIGHTS`, `N LIGHTS`, `CONTACT HELD`, or `REFRESH BLOCKED`);
4. a compact exact attention status when blocked/fault lights exist;
5. zero-material contact truth when material count is zero;
6. interruption/contact-preservation truth when refresh is interrupted.

Per-light labels, ordinary active/recovered breadth, provenance, reason, consequence, and evidence remain behind explicit expansion/touch detail.

## Operational-status masking rule
A custom `contentDescription` replaces the visible TextView text as the semantic value. Therefore a collapsed drag handle whose visible compact text changes between states such as OFF / OFFLINE / ACTIVE / ON must not expose a custom description that talks only about heartbeat state and silently masks the changing Home Center operational truth.

`HeartbeatCollapsedOwnerAccessibility` now has a source overload that accepts the **already-derived owner status description**. It does not re-derive control, connectivity, remote-input, mute, phone, queue, or P0 state. That status input has its own 96-code-point returned budget before aggregate composition so an accidentally verbose status cannot starve heartbeat/contact truth.

This is supporting source only until `OperatorOverlayService.dragHandle` actually supplies the owner status description. Owner consumption, Android runtime, and TalkBack behavior remain separate states.

## Attention rule
Concise must not mean blind to danger.

A collapsed action control may omit ordinary per-light names, but it must preserve exact **blocked/fault counts** when either exists. Do not recover state by parsing visible labels or prose. The typed accepted/preserved scene is the authority.

Current compact shape:

`Attention: blocked N, fault N.`

When both counts are zero, the attention sentence is absent.

Attention counts are derived only from the visible accepted/preserved frame. A rejected or incomplete attempted pulse may not leak its blocked/fault state into current collapsed-owner speech. If the last-good frame has no attention states, a discarded attempted fault remains absent while `CONTACT HELD` explains the interrupted refresh.

Do not add active/recovered histogram chatter merely because those counts are available. That would rebuild the same routine speech-load problem in a slightly more bureaucratic hat.

## Aggregate returned budget
Per-field bounds do not prove the composed action-control description is bounded.

The entire collapsed-owner `contentDescription` has one hard returned Unicode code-point budget. The ellipsis, if needed, lives inside the same budget through `HeartbeatPlainTextBudget`.

The operator-status component also has a separate hard returned budget before aggregate composition. This protects the heartbeat/contact portion from starvation without rewriting the exact operational source state.

This is a **projection budget only**. Never truncate or rewrite canonical scene, pulse, evidence, provenance, checkpoint, or owner operational-state fields to make TalkBack quieter.

## Zero-material and wound truth
Preserve the existing contact distinctions:

- no accepted/preserved visible pulse -> waiting;
- accepted current zero-material pulse -> `HEARTBEAT • 0 LIGHTS` plus accepted-zero prose;
- interrupted zero-material last-good pulse -> `HEARTBEAT • CONTACT HELD` plus last-complete-zero prose and interruption truth;
- interrupted refresh before first accepted contact -> `HEARTBEAT • REFRESH BLOCKED` plus pre-contact interruption truth.

Node count is never a shortcut for contact identity.

## Existing-owner law
`OperatorOverlayService` remains the sole Android owner. `HeartbeatCollapsedOwnerAccessibility` is a pure projection consumed by the already-existing `dragHandle`.

Do not create a neighboring accessibility service, overlay controller, renderer, poller, state store, phone ingress path, or recovery daemon to solve speech load.

Updating `contentDescription` is state projection. It is not permission to call `announceForAccessibility(...)` on every heartbeat poll.

## Regression source
At minimum pin:

- a broad valid pulse whose expanded collapsed summary exceeds the drag-handle aggregate budget;
- the surviving drag-handle description stays within the aggregate budget;
- broad per-light labels and the full `States:` list are absent from the handle;
- exact blocked/fault counts remain present;
- a rejected/incomplete attempted fault does not leak into attention counts or current collapsed-owner prose;
- explicit expand-for-details action remains present;
- accepted-zero / waiting / held / blocked remain distinct;
- a material owner operational-status description survives the custom collapsed contentDescription instead of being masked;
- an overlong owner status is independently bounded while heartbeat summary/contact truth remains present;
- expanded mode preserves the ordinary overlay action description;
- exact scene/detail text remains available outside this concise projection.

Regression source is **not TESTED** until an authorized runner executes it.

## Current PR #329 source truth — 2026-08-21 1603
- `HeartbeatCollapsedOwnerAccessibility` overload for owner operational status: **IMPLEMENTED SOURCE YES**.
- Separate operator-status speech budget: **IMPLEMENTED SOURCE YES**.
- `HeartbeatCollapsedOwnerAccessibilityTest` operational-status and starvation fixtures: **REGRESSION SOURCE YES / UNEXECUTED**.
- `OperatorOverlayService.dragHandle` consumption of the new overload: **NO**. Authenticated owner still calls the heartbeat-only overload in this slice.
- Android runtime / TalkBack / deployment / phone delivery / acceptance: **NO**.

## Evidence membrane
Keep the states separate:

`requested -> implemented source -> exact GitHub readback -> regression source -> owner source wiring -> regression executed -> tested -> existing-owner runtime observed -> TalkBack exercised -> deployed -> callable -> executed -> delivered -> accepted`

Repository source can prove only repository/source states. It cannot prove Android runtime, TalkBack behavior, primary-phone delivery, or user acceptance.

## P0 / phone firewall
This skill owns no Phone Hands ticket, primary-phone command, queue/relay probe, Home Center recovery mutation, Nightcore, Pocket TTS, Chromium, Context Organ, physical acceptance, or P0 coordination.

Those surfaces remain with their canonical P0 owners.

## Done for one pulse
Light this skill only when collapsed-owner speech load, operational-state masking, urgent-state compactness, aggregate returned budget, accepted/preserved attention ownership, or runtime proof materially changes. Once the source seam is stable, keep it dark instead of turning the drag handle into office carpeting with a screen reader attached.
