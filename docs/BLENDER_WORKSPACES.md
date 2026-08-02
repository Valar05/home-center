# Persistent Blender Workspaces

Home Center supplies owner identity, idempotency, immutable revisions, constraints, validation, provenance, storage, signed retrieval, and production automation. Blender 4.5.12 LTS is the pinned geometry and animation kernel.

The eight `blender.workspace.*` operations are dynamically discovered beneath the stable `drive_operation` MCP tool. `blender.workspace.render` is deprecated and retained only for compatibility; agents must not select it for new work. Inspection plus exported scene and validation artifacts are the active review evidence lane. The top-level MCP schema does not change. Create and every mutation require `approved:true` and an idempotency key. Mutations require the exact current `baseRevisionId`; stale and concurrent writes fail closed. Restore creates a successor revision and never overwrites history.

Typed recipes use `home-center.blender-workspace-recipe.v1`. The private `home-center-blender` service runs only stored typed recipes through `bpy` and BMesh. User Python, subprocess instructions, arbitrary host paths, network requests, embedded script auto-execution, generic workers, and autonomous agents are not part of the contract.

Inspection returns scene hierarchy, stable object/data/component IDs, transforms, dimensions, parents, origins, collections, modifiers, constraints, materials, actions and channels, topology counts, boundaries, linked data, cameras, lights, bounds, and warnings from the exact `.blend`. The deprecated compatibility renderer and active export path both bind an explicit immutable revision. Export preserves articulated hierarchy, pivots, materials, and named NLA animations.

The `.blend` revision is editable source truth. Receipts and metrics are evidence, never artistic acceptance. Review results remain `unreviewed` until Drew records a verdict through the accepted external review lane.

Release only through `tools/deploy_blender_workspace_release.sh` from a clean checkout exactly matching `origin/main`.
