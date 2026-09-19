# Pose Lab Sprite Recovery

Use this skill when recovering or deploying browser-native sprite animation review on Drew's phone.

## Current runtime
- Pose Lab V2 review surface: `http://127.0.0.1:4173/`
- Sprite Lab diagnostic surface: `http://127.0.0.1:4174/`
- Pose Lab repository: `Valar05/pose-lab-v2`
- The 2D viewer accepts a manifest override through the `manifest` query parameter.

## Recovery order
1. Recover Pose Lab V2.
2. Recover Sprite Lab / intelligent slicer / contact-sheet tooling.
3. Preserve current local runtime and handoffs before replacing anything.
4. Prefer exact source video -> semantic extrema -> contact sheet -> frame set -> manifest -> Pose Lab review.
5. A contact sheet is not acceptance. Playback in Pose Lab is the truth surface.

## April original-proof lane
The current April Thirdskin idle diagnostic manifest is:
`public/assets/april/thirdskin/animations.inline.json`

Open it on the phone with:
`http://127.0.0.1:4173/?view=2d&manifest=https%3A%2F%2Fraw.githubusercontent.com%2FValar05%2Fpose-lab-v2%2Fmain%2Fpublic%2Fassets%2Fapril%2Fthirdskin%2Fanimations.inline.json&animation=idle`

The source performance is Drew's loaded-standing-still/Ryu-style idle. The six semantic keys are:
- K0 Loaded Stillness
- K1 Pressure Take-Up
- K2 Hip Accept / Support Ownership
- K3 Deepest Coil
- K4 Rebound / Secondary Catch
- K5 Return Vector / Ready Neutral

The manifest is diagnostic review truth, not final canonical animation acceptance.

## Failure handling
If Pose Lab reports `Animation manifest returned 404`, verify the exact raw GitHub path exists before giving Drew another localhost link. Do not report deployment based on a planned or nonexistent path.


## Private-repo manifest rule
`Valar05/pose-lab-v2` is private. A phone browser fetching
`raw.githubusercontent.com/Valar05/pose-lab-v2/...` without GitHub auth receives 404 even when the file exists.
Do not use a raw-GitHub manifest URL as the localhost Pose Lab handoff.

Preferred order:
1. Serve the manifest and frame assets from the phone checkout / localhost surface.
2. If the phone write lane is temporarily unavailable but Pose Lab is already running, use a self-contained `data:application/json;base64,...` manifest override whose frames are also data URLs. This is diagnostic review only.
3. Do not mistake authenticated connector readback for browser reachability.

Before giving Drew a localhost link, verify the manifest transport from the same browser-reachable lane. A GitHub connector fetch is not that proof.


## Subtle-idle redraw rule
For subtle idles, per-frame image generation is a red failure mode. Similar semantic keys must not be independently redrawn: costume folds, straps, hoses, face, silhouette, and weapon detail will jitter more than the intended motion.

Required order for subtle motion:
1. lock one appearance-authority frame;
2. derive motion from the source performance/contact sheet;
3. deform or rig the same pixels deterministically for nearby keys;
4. keep feet/world anchors explicit;
5. use generated redraws only for genuinely different semantic poses, never as the in-between mechanism;
6. judge the result in playback before promoting it.

If playback reads as texture crawl, silhouette creep, or costume boil, reject the candidate even if every still frame looks good. Do not try to rescue redraw jitter with timing tweaks.


## Contact-sheet generation rule
Contact sheets are the unit of generation and retargeting.

- When source motion exists, extract the chosen source frames first and assemble ONE contact sheet that preserves every full source frame. Do not crop away feet, hands, props, or other motion evidence unless the user explicitly asks for a crop.
- Feed that entire source contact sheet directly as the image input/reference for character retargeting.
- Generate the corresponding target poses as ONE full contact sheet in one image-generation operation.
- Never generate six independent target images for a six-frame contact sheet. Independent generations cause identity, costume, scale, silhouette, prop, and camera drift.
- Do not replace source keys with invented “equivalent” poses. The point of a performed video is to preserve the actual keys and relationships.
- No stabilization, puppet deformation, or other smart interpolation before the direct source-contact-sheet -> target-contact-sheet pass has been evaluated.
- If the source video contains feet, preserve them in the source contact sheet and target contact sheet.


## Two-key bridge rule
When two authored contact-sheet frames carry the event, use those exact endpoints and derive only connective frames between them.

Rules:
- keep the authored endpoint pixels unchanged;
- use deterministic articulated deformation for intermediate frames;
- keep planted foot and world anchors explicit;
- do not whole-image crossfade or optical-flow blend endpoints;
- do not create ghost silhouettes or double exposures;
- allow the destination authored key to arrive as a deliberate graphic snap;
- reverse from the destination key for recovery rather than generating extra poses;
- validate in Pose Lab playback, not only as still images.

Pattern: AUTHORED KEY -> PROCEDURAL COMPRESSION -> AUTHORED KEY -> PROCEDURAL RECOVERY.
The bridge is connective motion only and must not invent a new semantic pose or redesign the character.


## Two-key displacement morph rule
Two-Key Snap connective motion must be a true displacement/deformation of one body between two sacred authored endpoint images.

Hard requirements:
- Key A and Key B remain exact authored images at the endpoints.
- Intermediate frames must move pixels/spatial regions through one-to-one deformation. They must not alpha-crossfade A and B, pixel-vote between A and B, or composite both bodies.
- At every intermediate frame there is one head, one torso, two arms/hands, two legs/feet, one weapon/holster set. Duplicate hands, limbs, faces, silhouettes, or weapon edges are automatic FAIL.
- Use articulated/body-region or mesh/landmark-guided warping with explicit endpoint correspondences. The bridge should visibly change pose, not merely texture.
- Planted feet must remain world-anchored unless the authored endpoint itself moves them.
- If a limb changes position substantially, the deformation must carry that same limb through space. Do not leave a ghost at the origin.
- Never label a crossfade or mixed-pixel dissolve as displacement morphing.
- Visual acceptance requires that A visibly becomes B in playback while anatomy remains singular and coherent.
