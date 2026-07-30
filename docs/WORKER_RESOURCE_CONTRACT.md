# Worker Resource Contract

`ops/worker_profiles.v1.json` is the machine authority for worker resources. `control-plane`, `media-forge-light`, `media-forge-heavy`, and `browser-session` are the available profiles.

`home-center-mcp` is the control-plane guardrail. `home-center-audio-render`, `home-center-video-render`, and `home-center-browser-worker` remain documented targets. `home-center-blender-workspace` is bound to `media-forge-heavy`: 4 vCPU, 8 GiB, concurrency 1, scale zero to four, timeout 1800 seconds. It executes one deterministic Blender operation against one explicit immutable scene revision per instance.

Bound deployments resolve values from the registry, reject ad hoc overrides, validate before mutation, and read back live configuration. The Blender workspace release requires a clean exact `origin/main`, deploys the replacement before removing the retired runtime, and never rolls back to a geometry-authoring fallback.
