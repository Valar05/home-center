# Fortress Model Foundry V2

## Boundary

Foundry is Home Center's asynchronous, sandboxed direct-GLB scripting engine. One `foundry.asset.run` submission loads a complete immutable GLB outside chat, executes one bounded `foundry-js.v1` program, applies a batch of scene, mesh, material, rig, animation, validation, and camera operations, renders fixed evidence, and exports one immutable successor.

Foundry is dynamically registered below `drive_operation`. It is not a top-level MCP tool, plugin, connector, generic organic generator, synchronous per-operation chat API, or alternate viewer.

## Existing Owners

- Discovery and dispatch: `driveOperationRegistry()` in `functions/home_center_mcp.js`.
- Immutable source identity: `functions/artifact_ingest_service.js`.
- Planning sandbox: `functions/foundry_script_runtime.mjs` using QuickJS.
- Direct GLB kernel: `functions/foundry_kernel.mjs` using glTF Transform, Three.js math, meshoptimizer, and manifold-3d.
- Visual evidence: `functions/foundry_review_renderer.mjs` using Three.js in isolated headless Chromium.
- Isolated execution: `foundryAssetWorker` and `functions/foundry_worker_process.mjs`.
- Review: immutable artifact routes plus the shared Model Viewer Lab.

No ordinary Foundry execution invokes an external 3D application or falls back to a retired renderer.

## Contract

`foundry.asset.run` accepts:

- `contractVersion: home-center.foundry-run.v2`;
- `domain: hard_surface | character_setup | animation`;
- optional exact owner-scoped `home_center_artifact` source for procedural hard-surface work, required otherwise;
- inline or owner-scoped artifact script using `foundry-js.v1`;
- bounded parameters;
- `reviewPreset: fixed-six-view`;
- mandatory idempotency key and isolated namespace;
- optional exact parent job/result binding for a successor.

Recipe-based V1 requests return `foundry.contract.retired`. Unknown versions and operations fail explicitly.

## Script API

The sandbox emits a bounded operation plan. It has no network, process, module, worker, wall-clock, eval, or Function access. Planning is limited to 256 KiB of script, 64 MiB, five seconds, 4096 operations, and 100 bounded notes.

Namespaces cover:

- `asset.inspect`;
- section-loft, profile, box, cylinder, transform, reparent, instance, array, mirror, and separation scene work;
- normal repair, weld, and bounded manifold boolean mesh work;
- material creation and assignment;
- bone add, rename, orient, reparent, and rigid prop attachment;
- clip trim, retime, key edit, loop, and controlled root motion;
- fixed views and bounded validation assertions.

Unsupported operations stop honestly. Weight painting, automatic arbitrary rigging, organic geometry, sculpting, general modifier compatibility, and implicit fallback are out of scope.

## State And Identity

`accepted -> queued -> running -> completed | failed`

Successful execution publishes:

`completed -> review_ready/unreviewed -> accepted | rejected | revision_requested`

Outputs use `foundry/v2/{ownerHash}/{namespace}/{inputHash}/{resultHash}/...`. Identity binds immutable source and script hashes, parameters, domain, namespace, review preset, contract versions, and exact parent lineage. Exact replay attaches and transfers zero duplicate bytes. No mutable `latest` exists.

Rejected work remains immutable evidence and must link to a changed successor plan. Promotion requires an accepted owner-scoped review record bound to the exact job and result hash.

`foundry.asset.status` authenticates the caller before returning failure evidence. Failed jobs include only bounded, redacted tails from the exact owner/namespace/input/attempt log objects after byte-length and SHA-256 readback verification. Logs never appear in run receipts, capability listings, or another owner's status.

Inspect-only jobs preserve the exact source GLB bytes as their successor. Structural inspection uses the glTF Transform texture API directly, so embedded material textures are inspected without dereferencing a nonexistent wrapper. This is the regression contract for the hash-locked Regnet material-bearing source.

## Review Gate

Each successful run must contain the successor GLB, six fixed PNGs, a contact sheet, optional skeletal overlay, validation report, preservation evidence, change evidence, manifest, and bounded logs. Every output is SHA-256 and byte-length verified after storage readback.

The Three.js renderer samples output pixels. Uniform or empty canvases fail with `foundry.review.blank_canvas`; no review packet is published. Final visual judgment uses only the immutable cloud URL and shared viewer.

## Deployment

Only run:

`sh tools/deploy_foundry_v2_release.sh home-center-dclar`

The script refuses a branch, dirty tree, stale main, or unguarded worker-only deployment. It pauses `foundryAssetWorker`, deploys the worker and both MCP functions from one merged main commit, verifies release identity, and resumes the queue.

## Verification

`node tools/foundry_contract_test.mjs` proves deterministic hard-surface compilation, weapon-bone insertion and rigid attachment, animation editing without geometry/skin mutation, dynamic discovery, exact replay, namespace isolation, bounded logs, timeout termination, review publication, explicit promotion, no top-level Foundry tool, no mutable latest, and no retired-renderer invocation.

Live acceptance additionally requires authenticated dynamic discovery, three completed cloud specimens, immutable URL readback, visible shared-viewer evidence, and two namespaced jobs that cannot resolve to each other.
