# Heartbeat Native UI Projection

## Purpose
Project an already-built `HeartbeatSceneGraph.Frame` into a deterministic UI-ready model for the existing Operator Overlay without creating a second renderer, controller, transport, queue, or phone execution path.

## Boundary
This skill owns **source projection and existing-owner source composition only**. It may create or review pure view-model/source artifacts, existing-`OperatorOverlayService` source wiring, and JVM regression source. It must not claim that Android executed or rendered the model, that a phone received it, or that the interface was deployed, callable, delivered, or accepted.

The existing `OperatorOverlayService` remains the sole UI owner. `HeartbeatOverlayViewModel` translates the preserved semantic frame into controls and descriptions consumed by that service's source path; this is **source wiring**, not runtime-render proof.

## Input truth
Consume only `HeartbeatSceneGraph.Frame`.

- Never project raw candidates around the scene gate.
- When refresh fails closed, project only the last-good nodes already preserved in the frame.
- Never surface discarded attempted candidates as current UI state.
- Retain exact `refreshBoundary` separately from bounded human-facing speech.

## Control contract
Each projected light control carries:

- stable semantic `id` for selection retention across reorder;
- compact visible label containing both the non-color state token and state word;
- compact content description from the scene node;
- on-demand detail content description with reason, consequence, evidence, and provenance;
- deterministic focus index;
- minimum touch target from the scene contract (currently 48 dp); the existing owner must honor it on both width and height;
- one-shot transition-motion flag copied from the accepted/preserved scene.

Visible labels are bounded by Unicode code point. Truncation must not split surrogate pairs. Full detail remains separately available through the existing bounded TalkBack projection.

## Existing-owner source wiring
The existing service source now:

1. reads the existing `OperatorState` persisted Base64/byte-count/SHA/update identity;
2. decodes Base64 to exact bytes and enters `HeartbeatOverlayRefreshPlan.projectPersisted`;
3. compares **structure**, render/content, and announcement identities independently;
4. replaces native heartbeat child objects only when ordered semantic ids change, or when live child identity has drifted from the deterministic contract;
5. when structure is stable, verifies child count/order/tag identity and refreshes the **same native Button objects in place** rather than using `removeAllViews()`;
6. refreshes visible label, both-axis touch minimums, semantic tag, selected state, compact content description, and the current click-detail closure on those stable objects;
7. retains selection by semantic light id;
8. exposes compact content descriptions on each control and explicit detail on touch;
9. suppresses automatic and explicit heartbeat speech while globally muted while still advancing semantic announcement history;
10. before any material heartbeat view mutation, reads the accepted selected id and direct keyboard-focused heartbeat Button separately;
11. measures each live native candidate against the current horizontal viewport using `HeartbeatViewportRestorePolicy.hasVisibleViewportContact(...)`;
12. chooses visible accepted selection first, visible accepted direct keyboard focus second, otherwise no viewport anchor; an offscreen durable selection cannot suppress a visible keyboard fallback;
13. captures that chosen anchor's pre-mutation viewport offset and capture-time selected/focused interaction evidence;
14. applies the same restore-ticket path to stable in-place refresh, structural rebuild, and live-structure-drift fallback rebuild;
15. records the mutation that actually happened: structural/fallback rebuild may destroy native keyboard focus; successful in-place refresh may not claim rebuild amnesty;
16. schedules one-shot pre-draw restoration so new child geometry has been laid out before bounded scroll math runs;
17. after layout, re-finds current heartbeat keyboard focus and separately asks the existing overlay root whether **any** direct keyboard focus exists;
18. calls the explicit captured-owner policy overload with generation, accepted model, selected id, heartbeat keyboard-focused id, actual mutation class, and overlay-wide direct-focus presence;
19. re-finds the same semantic anchor and applies bounded scroll geometry only when captured interaction ownership still passes; stale/missing ids do not become index guesses or neighboring controls.

If live child count/order/tag identity disagrees with planned structure, the service fails safe to the existing canonical rebuild path. It never guesses which changed child corresponds to which semantic light.

A scroll/container wrapper must not become a competing TalkBack destination that masks child controls.

## Focus and viewport truth
Stable semantic selection is not the same claim as stable native focus. The source avoids destroying stable child objects on content-only changes, which preserves the **opportunity** for keyboard/TalkBack focus to remain on the same native object. This is an implemented source property only. Actual Android focus retention and TalkBack behavior remain unproven until an authorized runtime/test body observes them.

Stable native object identity is also not the same as stable **visible viewport contact**. In a horizontal scrolling row, an in-place label/content change can alter child widths and move the exact same Button away from its prior viewport offset. The existing service consumes the viewport-contact policy in source.

Anchor priority at capture is canonical and geometry-aware: **visible accepted selected semantic id first; visible direct keyboard-focused heartbeat Button second; otherwise no anchor**. That capture priority is not permanent navigation ownership. A newer direct heartbeat keyboard-focus move observed before restoration supersedes the captured ticket, including a selection-anchored ticket. TalkBack accessibility focus is deliberately neither queried nor synthesized.

Capture-time visibility chooses which existing live control owned contact. After layout, the owner revalidates captured interaction evidence rather than treating mutation-caused geometry changes as new user intent. The whole point of restoration is that layout may move the anchor.

A structural rebuild can destroy the old native keyboard-focused Button. But **empty heartbeat-child focus is ambiguous**: it can also mean direct focus moved to another overlay control such as STOP or Adam input. The existing service now supplies both facts needed by the explicit policy: whether the actual mutation may destroy native focus, and whether any direct keyboard focus exists under the overlay root. Empty-focus amnesty is therefore source-wired only when those facts permit it. `View.findFocus()` is direct keyboard-focus evidence, not TalkBack accessibility-focus evidence.

The owner restores on a one-shot pre-draw after mutation requested layout. This is stronger source ordering than a generic posted Runnable, but it remains **source wiring**, not proof that Android actually executed the path or that accessibility focus was retained.

## Collapsed semantics
Collapsed description comes from `HeartbeatFrameAccessibility.collapsedContentDescription(frame)`. Do not rebuild attention ordering, counts, or interrupted-refresh speech in a second implementation.

## Duplicate-architecture law
Do not add a neighboring overlay service, controller, renderer, state store, heartbeat receiver, transport path, or phone executor. The existing `OperatorOverlayService` is the owner; source wiring must compose into it.

## Evidence membrane
Keep these states separate:

`requested -> implemented source -> regression source -> tested -> existing-owner source wired -> visible-viewport-gate source wired -> focus-scope policy source -> existing-owner focus-scope source wired -> runtime UI observed -> runtime viewport observed -> runtime keyboard focus observed -> TalkBack exercised -> deployed -> callable -> executed -> delivered -> accepted`

Current source truth:

- existing-owner source wiring: **YES**
- geometry-aware visible-viewport-gate source wiring: **YES**
- focus-scope revalidation policy source: **YES**
- existing-owner focus-scope/mutation-class wiring: **YES**
- exact GitHub readback of that owner wiring: **YES**
- deterministic test execution: **NO / BLOCKED_ACTIONS_BUDGET**
- runtime UI/runtime viewport/runtime keyboard focus/runtime TalkBack/deployment/callability/execution/delivery/acceptance: **NO** until their own authorized evidence exists.

GitHub blob readback proves durable source presence and exact source wiring only. It does not prove Android compilation, runtime view creation, focus retention, viewport anchoring, phone delivery, or physical acceptance. Regression source is not a passing test until an authorized deterministic test body actually executes it.

## Done for one source pulse
A pulse may count this skill as lit only when the projection, existing-owner source wiring, viewport-contact policy, regression source, or review materially changes. If no projection consequence changes, leave the light dark rather than listing the skill decoratively.
