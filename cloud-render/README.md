# Command Center Blender Render Service

`render.blender_glb` is the non-agent Cloud Run renderer behind Command Center MCP. The operation accepts either typed MCP host files or existing durable references:

- `glbFile`: uploaded `.glb` binary file
- `scriptFile`: uploaded Blender Python file
- `glbRef`: `drive://`, `bucket://`, or `gs://` GLB reference
- `scriptRef`: `drive://`, `bucket://`, or `gs://` Python reference
- `scriptText`: inline Python fallback for small scripts

Exactly one GLB source and one script source are required. Uploaded files are hashed, validated, sanitized, staged to GCS by the MCP function, materialized into a unique Cloud Run temp job directory, and then passed to Blender without shell interpolation. The renderer returns a bundle: frames, contact sheet, diagnostic renders, `.blend`/`.glb` artifacts, native pose data, original script, input/output hashes, Blender settings, stdout/stderr, and a validation manifest.

The Blender script is invoked as:

```text
blender --background --python network_disabled_wrapper.py -- render.py input.glb output_dir settings.json script-output-manifest.json
```

The script must write `script-output-manifest.json` under `output_dir` with these optional relative paths:

```json
{
  "renderedFrames": ["frames/f00.png"],
  "fixedCameraRenders": ["frames/f00.png"],
  "diagnosticViewRenders": ["diagnostic/depth_f00.png"],
  "modifiedBlend": "scene.blend",
  "animatedGlb": "animated.glb",
  "nativePoseAnimationData": "pose-data.json"
}
```

Missing required bundle classes or a nonzero Blender exit marks the render failed, but stdout, stderr, partial outputs, hashes, and validation evidence are still published when possible.

## GIF Playback Contract

The renderer keeps four frame authorities separate:

- `authoredKeys`: animation keys reported by the Blender script when available. If the script does not provide them, the renderer reports them unavailable instead of inventing data.
- `evidenceFrames`: rendered PNG frames used for inspection, contact sheets, and fixed-camera evidence.
- `gifFrames`: explicit ordered playback frame indices selected from `evidenceFrames`.
- `gifTimingMs`: one playback duration per selected GIF frame.

Callers may pass the bounded selection through render settings or the execution contract:

```json
{
  "gifFrames": [0, 2, 4, 6],
  "gifTimingMs": [110, 100, 110, 100]
}
```

If `gifFrames` is omitted, the renderer falls back to all evidence frames for backward compatibility and records `gifFrameSelection: "fallback"`. Contact sheets always use `evidenceFrames`, not the GIF playback subset.

GIF assembly prepares every selected PNG on a fresh transparent canvas, applies per-frame delay and `Background` disposal before encoding each frame, and avoids optimization that can preserve stale pixels outside the current alpha mask.
