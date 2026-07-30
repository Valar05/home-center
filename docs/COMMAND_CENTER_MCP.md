# Command Center MCP

Command Center remains a bounded compatibility control plane for projects, managed knowledge buckets, app-control records, and browser sessions. Home Center reaches it through the stable `command_center_operation` bridge.

Command Center Codex agents and worker fleet discovery are retired. `agents.*`, `workers.*`, `hosts.*`, `jobs.*`, `machine_images.*`, `provisioning.*`, `codex_sessions.*`, `routing.*`, and `proof.*` are absent from both Home and Command Center catalogs. Guessed calls fail with `capability_retired.command_center_codex`. The Cloud Run Codex worker package, deployment script, profile binding, and CI lane are deleted.

The former cloud 3D renderer is also retired. No render tool or operation is advertised. Guessed legacy calls fail with `capability_retired.use_blender_workspace`. New 3D work uses Home Center `drive_operation` with `blender.workspace.*`; Command Center does not execute it.

Historical Command Center data remains owner-scoped and auditable. Retiring execution does not delete old receipts, logs, or artifacts. Generic receipt delivery may read a terminal historical receipt without exposing the old producer as a capability.
