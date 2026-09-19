---
name: pose-lab-sprite-recovery
description: Recover and use the existing Pose Lab V2 / Sprite Lab 2D animation review chain on Drew's phone without redesigning it. Use when resuming sprite-frame, contact-sheet, slicer, GIF/manifest, or April/ASCII-Kinesis animation work.
---

# Pose Lab / Sprite Lab Recovery

## Mission boundary

Use the existing animation stack. Do not replace Pose Lab, invent a new viewer, or route around the recovered phone surfaces.

Primary repo:
- `Valar05/pose-lab-v2`

Recovered phone surfaces:
- Pose Lab V2: `http://127.0.0.1:4173/`
- Sprite Lab diagnostic: `http://127.0.0.1:4174/`

The 2D Pose Lab viewer accepts an alternate manifest through the existing `manifest` query parameter:

```text
http://127.0.0.1:4173/?view=2d&manifest=<ABSOLUTE_OR_RELATIVE_MANIFEST_URL>&animation=<ID>
```

This is the preferred fast review path when the phone server is already running. It uses the existing `src/sprite-viewer.js` surface and the stable `pose-lab-v2-2d-animation-set-v1` schema.

## Thunder recovery

When runtime truth is stale, recover the animation family through Thunder before broad archaeology:

```sh
cd /storage/emulated/0/Documents/GodotProjects/thunder-brainstorm || exit 1

python thunder_brainstorm.py workspace search "pose lab"
python thunder_brainstorm.py workspace search "sprite lab"
python thunder_brainstorm.py workspace search "intelligent slicer"
python thunder_brainstorm.py workspace search "slicer"
python thunder_brainstorm.py workspace search "contact sheet"
python thunder_brainstorm.py workspace search "animation"
python thunder_brainstorm.py workspace search "sprite"
```

For likely hits:

```sh
python thunder_brainstorm.py workspace show <slug>
python thunder_brainstorm.py workspace recover <slug>
```

Select the repo with direct naming, recent activity, attached recovery docs, safely recoverable state, and ownership of the live animation surface.

## Existing 2D contract

Pose Lab's 2D reviewer:
- plays frame assets directly from a manifest;
- supports per-frame timing;
- supports play/pause and frame stepping;
- supports onion and delta review;
- supports fixed ground guide, zoom, and multiple backgrounds;
- defaults to the stable `pose-lab-v2-2d-animation-set-v1` schema;
- accepts arbitrary manifest URLs through `?manifest=`.

A successful shell, HTTP 200, or manifest write is not visual acceptance. The user must be able to open the actual review URL and see the intended motion.

## Source-video → contact-sheet → review lane

For performance-derived animation:

1. Preserve the original source video.
2. Extract semantic extrema from the source rather than inventing evenly spaced frames.
3. Save the exact source contact sheet.
4. Retarget appearance while preserving support/root/contact/load relationships.
5. Build the Pose Lab manifest with exact frame order and per-frame durations.
6. Open the existing Pose Lab 2D route with the candidate manifest.
7. Inspect at 1×, ½×, Onion, and Delta.
8. Promote only after the visible animation reads correctly.

Do not treat a contact sheet as proof that motion works. Playback is required.

## April / Original Proof

Current April source artifacts are persisted in ChatGPT Library under:

`/ASCII Kinesis/April Original Proof/`

The current diagnostic manifest is persisted in the Pose Lab repo at:

`public/assets/april/thirdskin/animations.inline.json`

It contains the six-frame April Idle candidate as inline image data so an already-running phone Pose Lab can review it without first pulling binary frame assets.

Current semantic source keys:
- K0 Loaded Stillness
- K1 Pressure Take-Up
- K2 Hip Accept / Support Ownership
- K3 Deepest Coil
- K4 Rebound / Secondary Catch
- K5 Return Vector / Ready Neutral

Source intent: loaded while standing still, explicitly Ryu-like stored readiness.

The inline manifest is diagnostic deployment, not final canonical asset storage. Once visually accepted, persist the final transparent frame bytes as normal repository assets and replace the inline diagnostic manifest with canonical frame paths.

## Evidence standard

Completion for a review deployment requires:
1. persisted manifest or frame assets in the authoritative repository;
2. exact review URL;
3. visible playback on the existing Pose Lab/Sprite Lab surface;
4. any promotion/acceptance gate required by the project.

Never report repo persistence, local generation, or an HTTP 200 as visual acceptance.
