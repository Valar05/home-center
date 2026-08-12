# Vlad Pixel Forge runtime boundary

Vlad Pixel Forge is phone-native. Godot may be used as an authoring/forge tool but is not the delivery runtime. GitHub Actions is not an execution or acceptance lane.

The first neural specimen is the TokForge SD1.5-LCM Pixel Art MNN bundle. It is a fused pixel-art SD1.5/LCM MNN bundle intended for a four-step in-process MNN diffusion engine. The batch-1 variant expects a CFG-skip engine and should not be treated as a generic `mnncli` text-to-image model.

Therefore the runtime architecture is:

1. stage the nine-file MNN model bundle under bounded phone storage;
2. expose a tiny Android-native PixelForge session wrapper backed by MNN;
3. accept a structured generation request (prompt, seed, width, height, steps=4, cfg=1.0 for batch-1);
4. generate only into a temporary working raster;
5. reduce/quantize to the engine's tiny canonical pixel artifact;
6. delete the large intermediate unless explicitly retained for debugging;
7. emit a receipt with model hashes, seed, wall time, peak memory when available, thermal state, output dimensions, palette size, canonical byte count, and intermediate deletion state.

Acceptance is phone evidence: an actual generated artifact plus receipt from the primary phone. Repository presence is implementation only.
