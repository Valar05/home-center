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
