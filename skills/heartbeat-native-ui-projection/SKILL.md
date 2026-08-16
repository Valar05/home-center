# Heartbeat Native UI Projection

## Purpose
Project an already-built `HeartbeatSceneGraph.Frame` into a deterministic UI-ready model for the existing Operator Overlay without creating a second renderer, controller, transport, queue, or phone execution path.

## Boundary
This skill owns **source projection only**. It may create or review pure view-model/source artifacts and JVM regression source. It must not claim that Android rendered the model, that a phone received it, or that the interface was deployed, callable, delivered, or accepted.

The existing `OperatorOverlayService` remains the UI owner. `HeartbeatOverlayViewModel` is a seam that makes future wiring boring: it translates the preserved semantic frame into controls and descriptions the existing service can consume later.

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
- minimum touch target from the scene contract (currently 48 dp);
- one-shot transition-motion flag copied from the accepted/preserved scene.

Visible labels are bounded by Unicode code point. Truncation must not split surrogate pairs. Full detail remains separately available through the existing bounded TalkBack projection.

## Collapsed semantics
Collapsed description comes from `HeartbeatFrameAccessibility.collapsedContentDescription(frame)`. Do not rebuild attention ordering, counts, or interrupted-refresh speech in a second implementation.

## Duplicate-architecture law
Do not add a neighboring overlay service, controller, renderer, state store, heartbeat receiver, transport path, or phone executor. If the existing overlay later consumes this model, wire it into the existing owner rather than growing a parallel UI organism.

## Evidence membrane
Keep these states separate:

`requested -> implemented source -> tested -> runtime wired -> UI rendered -> deployed -> callable -> executed -> delivered -> accepted`

A GitHub blob readback proves only durable source presence. Regression source is not a passing test until an authorized deterministic test body actually executes it.

## Done for one source pulse
A pulse may count this skill as lit only when the projection source, regression source, or review materially changes. If no projection consequence changes, leave the light dark rather than listing the skill decoratively.
