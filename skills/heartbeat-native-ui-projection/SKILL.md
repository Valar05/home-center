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
9. suppresses automatic and explicit heartbeat speech while globally muted while still advancing semantic announcement history.

If live child count/order/tag identity disagrees with the planned structure, the service must fail safe to the existing canonical rebuild path. It must never guess which changed child corresponds to which semantic light.

A scroll/container wrapper must not become a competing TalkBack destination that masks child controls.

## Focus truth
Stable semantic selection is not the same claim as stable native focus. The source now avoids destroying stable child objects on content-only changes, which preserves the **opportunity** for keyboard/TalkBack focus to remain on the same native object. This is an implemented source property only. Actual Android focus retention and TalkBack behavior remain unproven until an authorized runtime/test body observes them.

## Collapsed semantics
Collapsed description comes from `HeartbeatFrameAccessibility.collapsedContentDescription(frame)`. Do not rebuild attention ordering, counts, or interrupted-refresh speech in a second implementation.

## Duplicate-architecture law
Do not add a neighboring overlay service, controller, renderer, state store, heartbeat receiver, transport path, or phone executor. The existing `OperatorOverlayService` is the owner; source wiring must compose into it.

## Evidence membrane
Keep these states separate:

`requested -> implemented source -> regression source -> tested -> existing-owner source wired -> runtime UI observed -> TalkBack exercised -> deployed -> callable -> executed -> delivered -> accepted`

GitHub blob readback proves durable source presence and exact source wiring only. It does not prove Android compilation, runtime view creation, focus retention, phone delivery, or physical acceptance. Regression source is not a passing test until an authorized deterministic test body actually executes it.

## Done for one source pulse
A pulse may count this skill as lit only when the projection, existing-owner source wiring, regression source, or review materially changes. If no projection consequence changes, leave the light dark rather than listing the skill decoratively.
