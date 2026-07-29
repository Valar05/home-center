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
- optional exact parent job/result binding for a successor;
- optional home-center.foundry-model-sheet.v1 with immutable, SHA-256-bound 640x640 front/side/top PNG planes, meter calibration, axes, outer silhouette and aperture-feature contours, cage-point landmarks, scale anchor, and public-domain provenance.

Recipe-based V1 requests return `foundry.contract.retired`. Unknown versions and operations fail explicitly.

## Script API

The sandbox emits a bounded operation plan. It has no network, process, module, worker, wall-clock, eval, or Function access. Planning is limited to 256 KiB of script, 64 MiB, five seconds, 4096 operations, and 100 bounded notes.

Namespaces cover:

- `asset.inspect`;
- Primitive construction: section-loft, profile, box, cylinder, box-derived subdivision-cage, empty pivot group, bounded array, mirror, instance, hierarchy, material assignment.
- Mesh: deterministic Catmull-Clark subdivision, normal repair, weld, transactional Manifold Boolean.
- material creation and assignment;
- bone add, rename, orient, reparent, and rigid prop attachment;
- clip trim, retime, key edit, loop, and controlled root motion;
- fixed views, registered model-sheet review, and bounded validation assertions.

Unsupported operations stop honestly. Weight painting, automatic arbitrary rigging, organic geometry, sculpting, general modifier compatibility, and implicit fallback are out of scope.

## Geometry Economy Contract

Every topology-producing operation must declare a topology contract before it runs: complete vertex-purpose coverage, output vertex and triangle ceilings, maximum growth ratio, and a pending remove-or-merge challenge at the commissioned viewing error. Section lofts must justify every station and profile point; cylinders must record their screen-error sampling basis; Boolean output is constructed transactionally and discarded before replacing its operands when it exceeds its ceiling.

A hard-surface script must also declare component, complete-asset, and commissioned-scene budgets. The kernel preflights predictable expansion and reports unique source cost separately from expanded scene cost. The 250k-vertex/500k-triangle limits remain crash fuses only.

Machine completion reports `topologyValid` and `budgetValid`; `purposeValid` remains false until the accepted review record includes a remove-or-merge comparison for the exact immutable result. All three gates are required for promotion. None sets human visual acceptance by itself.

## State And Identity

`accepted -> queued -> running -> completed | failed`

Successful execution publishes:

`completed -> review_ready/unreviewed -> accepted | rejected | revision_requested`

Outputs use `foundry/v2/{ownerHash}/{namespace}/{inputHash}/{resultHash}/...`. Identity binds immutable source and script hashes, parameters, domain, namespace, review preset, contract versions, and exact parent lineage. Exact replay attaches and transfers zero duplicate bytes. No mutable `latest` exists.

Rejected work remains immutable evidence and must link to a changed successor plan. Promotion requires an accepted owner-scoped review record bound to the exact job and result hash.

`foundry.asset.status` authenticates the caller before returning failure evidence. Failed jobs include only bounded, redacted tails from the exact owner/namespace/input/attempt log objects after byte-length and SHA-256 readback verification. Logs never appear in run receipts, capability listings, or another owner's status.

Inspect-only jobs preserve the exact source GLB bytes as their successor. Structural inspection uses the glTF Transform texture API directly, so embedded material textures are inspected without dereferencing a nonexistent wrapper. This is the regression contract for the hash-locked Regnet material-bearing source.

## Model-Sheet Gate

review.modelSheet is additive to the existing fixed-six-view lane. It requires one box-derived control cage and one final target node. The v1 tank frame is +X forward, +Y up, +Z vehicle left; front looks from +X, left side from +Z, and top from +Y. The input hash binds image artifact identities, the 69-inch D78461 ring anchor where used, plane calibration, contours, landmarks, and provenance.

The cage is evidence, not exported proxy geometry. A 4x3x4 box has 82 named surface control vertices and 80 quads; two deterministic Catmull-Clark levels produce 2,560 triangles before apertures or other bounded CSG. Model-sheet proof publishes, for each plane, the exact reference, cage overlay, final-surface overlay, and signed difference image, plus registration JSON, per-plane fit JSON, and a three-plane contact sheet.

A fit passes only when front, side, and top each pass silhouette IoU, p95 boundary error normalized to the scale anchor, and landmark error. Scores are never averaged across views. A model-sheet job with a red or missing fit report cannot be promoted even if a separate human review record is accepted.

## Review Gate

Each successful run must contain the successor GLB, six fixed PNGs, a contact sheet, optional skeletal overlay, validation report, preservation evidence, change evidence, manifest, and bounded logs. A model-sheet run must additionally contain all registered front/side/top evidence named above. Every output is SHA-256 and byte-length verified after storage readback.

The Three.js renderer samples output pixels. Uniform or empty canvases fail with `foundry.review.blank_canvas`; no review packet is published. Final visual judgment uses only the immutable cloud URL and shared viewer.

## Deployment

Only run:

`sh tools/deploy_foundry_v2_release.sh home-center-dclar`

The script refuses a branch, dirty tree, stale main, or unguarded worker-only deployment. It pauses `foundryAssetWorker`, deploys the worker and both MCP functions from one merged main commit, verifies release identity, and resumes the queue.

## Verification

`node tools/foundry_contract_test.mjs` proves deterministic hard-surface compilation, vertex-purpose coverage, production-budget enforcement, preflight rejection of the historical 20k-class loft request, transactional Boolean limits, promotion gating, weapon-bone insertion and rigid attachment, animation editing without geometry/skin mutation, dynamic discovery, exact replay, namespace isolation, bounded logs, timeout termination, review publication, no top-level Foundry tool, no mutable latest, and no retired-renderer invocation.

`node tools/foundry_model_sheet_contract_test.mjs` proves cage limits, deterministic subdivision, non-exported cage evidence, strict three-plane/provenance input, independent per-plane rejection, aperture-edge fit math, repaired manifold CSG, geometry-economy enforcement, and the bounded bare D78461 casting.

Live acceptance additionally requires authenticated dynamic discovery, three completed cloud specimens, immutable URL readback, visible shared-viewer evidence, and two namespaced jobs that cannot resolve to each other.

## D78461 Proof Fixture

The first model-sheet proof source is under docs/evidence/d78461-model-sheet-v1/. proof-source.json binds the generated schematic planes and d78461-bare-casting.foundry.js. tools/build_d78461_model_sheet_fixture.mjs deterministically regenerates those inputs.

Scope is the manufacturing casting: one connected shell with ring, gun, commander, loader, and left pistol-port openings. Mantlet, barrel, cupola, hatch covers, lifting eyes, fittings, textures, and tank hull are forbidden. The reference is a transparent schematic normalization of cited public-domain US government sources, not a claim to possess an original factory orthographic drawing or to reproduce ballistic thickness. No successor candidate may be generated until this casting has green registered fit, accepted cloud/Sense evidence, and an accepted artifact review bound to the exact result.
