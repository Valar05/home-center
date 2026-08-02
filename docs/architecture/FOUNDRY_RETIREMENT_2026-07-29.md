# Foundry Retirement

Status: authoritative
Decision date: 2026-07-29

Foundry is retired. It cannot author, inspect, rerun, modify, promote, or dispatch geometry through Home Center. Historical artifact bytes, stable artifact URLs, audit records, and recorded review states remain readable. Historical existence does not imply active capability.

The egg-like D78461 output and visible z-fighting exposed a false authoring contract: green receipts and custom mesh operations did not provide close, persistent scene control or truthful visual iteration. The replacement architecture is Home Center for persistent revision control and Blender for modeling, topology, modifiers, hierarchy, pivots, constraints, animation, UVs, materials, rendering, and GLB export.

Agents must use exactly these live operations through `drive_operation`:

- `blender.workspace.create`
- `blender.workspace.inspect`
- `blender.workspace.history`
- `blender.workspace.mutate`
- `blender.workspace.restore`
- `blender.workspace.render` — deprecated compatibility operation; do not select for new work
- `blender.workspace.export`
- `blender.workspace.status`

Cached calls beginning `foundry.` fail with `CAPABILITY_RETIRED`, `dispatched:false`, and the Blender replacement. The deployed commit and UTC completion time are written after the main-only release to the immutable record `gs://home-center-generated/retirement/foundry/<deployed-commit>.json` and read back before release completion.
