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
The existing service source may:

1. read the existing `OperatorState` persisted Base64/byte-count/SHA/update identity;
2. decode Base64 to exact bytes and enter `HeartbeatOverlayRefreshPlan.projectPersisted`;
3. compare render/announcement identities before rebuilding or speaking;
4. rebuild only the existing heartbeat child container with native buttons;
5. retain selection by semantic light id;
6. expose compact content descriptions on each control and explicit detail on touch;
7. suppress automatic and explicit heartbeat speech while globally muted.

A scroll/container wrapper must not become a competing TalkBack destination that masks child controls.

## Collapsed semantics
Collapsed description comes from `HeartbeatFrameAccessibility.collapsedContentDescription(frame)`. Do not rebuild attention ordering, counts, or interrupted-refresh speech in a second implementation.

## Duplicate-architecture law
Do not add a neighboring overlay service, controller, renderer, state store, heartbeat receiver, transport path, or phone executor. The existing `OperatorOverlayService` is the owner; source wiring must compose into it.

## Evidence membrane
Keep these states separate:

`requested -> implemented source -> regression source -> tested -> existing-owner source wired -> runtime UI observed -> TalkBack exercised -> deployed -> callable -> executed -> delivered -> accepted`

GitHub blob readback proves durable source presence and exact source wiring only. It does not prove Android compilation, runtime view creation, phone delivery, or physical acceptance. Regression source is not a passing test until an authorized deterministic test body actually executes it.

## Done for one source pulse
A pulse may count this skill as lit only when the projection, existing-owner source wiring, regression source, or review materially changes. If no projection consequence changes, leave the light dark rather than listing the skill decoratively.
