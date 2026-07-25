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
