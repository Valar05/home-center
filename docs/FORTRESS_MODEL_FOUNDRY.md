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
- `reviewPreset: fixed-six-view | registered-model-sheet-only`;
- mandatory idempotency key and isolated namespace;
- optional exact parent job/result binding for a successor;
- optional `home-center.foundry-model-sheet.v1` with strict public-domain front/side/top inputs, or backward-compatible `home-center.foundry-model-sheet.v2` with declared front/side planes, optional top, calibrated transforms, immutable PNG identities, and either strict public-domain provenance or explicitly non-production synthetic workflow-fixture provenance.

Recipe-based V1 requests return `foundry.contract.retired`. Unknown versions and operations fail explicitly.

## Script API

The sandbox emits a bounded operation plan. It has no network, process, module, worker, wall-clock, eval, or Function access. Planning is limited to 256 KiB of script, 64 MiB, five seconds, 4096 operations, and 100 bounded notes.

Namespaces cover:

- `asset.inspect`;
- Primitive construction: section-loft, profile, box, cylinder, box-derived subdivision-cage, empty pivot group, bounded array, mirror, instance, hierarchy, material assignment.
- Mesh: deterministic shared-cage silhouette fitting, Catmull-Clark subdivision, normal repair, weld, and transactional Manifold Boolean. `fitSubdivisionCage` uses the same bounded cage across every declared plane and exports its pre/post metrics and digest.
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

`review.modelSheet` requires one box-derived control cage and one final target node. V1 remains the strict front/side/top public-domain contract. V2 declares its plane order and requires front plus side; top is optional. Both contracts bind immutable reference image identities, meter calibration, axis frame, contours, cage-point landmarks, scale anchor, and provenance into the job input hash.

`foundry.mesh.fitSubdivisionCage` is the first-class fitting operation. It runs a bounded fixed-order coordinate-descent solver against every declared silhouette using the production Catmull-Clark surface, without exporting intermediate geometry or accepting per-view cages. Evidence records initial and final per-view boundary metrics, evaluation count, solver version, initial cage digest, and fitted shared-cage digest.

The cage is evidence, not exported proxy geometry. Model-sheet proof publishes each exact reference plane, cage overlay, final-surface overlay, signed difference image, registration JSON, fit JSON, contact sheet, and standalone `model-sheet-cage.json`. The registration, fit report, cage artifact, and manifest all bind the same cage digest.

Each declared view must independently pass silhouette IoU, p95 boundary error normalized to the scale anchor, aperture error when present, and landmark error. Scores are never averaged across views. An asserted fit fails the worker closed, and a red or missing fit report cannot be promoted.

## Review Gate

A `fixed-six-view` run contains the successor GLB, six fixed PNGs, a contact sheet, optional skeletal overlay, validation report, preservation evidence, change evidence, manifest, and bounded logs. A `registered-model-sheet-only` run intentionally omits generic perspective/fixed-view imagery and publishes only the GLB, declared registered-plane evidence, cage, reports, manifest, and logs. Every output is SHA-256 and byte-length verified after storage readback.

The Three.js renderer samples output pixels. Uniform or empty canvases fail with `foundry.review.blank_canvas`; no review packet is published. Final visual judgment uses only the immutable cloud URL and shared viewer.

## Deployment

Only run:

`sh tools/deploy_foundry_v2_release.sh home-center-dclar`

The script refuses a branch, dirty tree, stale main, or unguarded worker-only deployment. It pauses `foundryAssetWorker`, deploys the worker and both MCP functions from one merged main commit, verifies release identity, and resumes the queue.

## Verification

`node tools/foundry_contract_test.mjs` proves deterministic hard-surface compilation, vertex-purpose coverage, production-budget enforcement, preflight rejection of the historical 20k-class loft request, transactional Boolean limits, promotion gating, weapon-bone insertion and rigid attachment, animation editing without geometry/skin mutation, dynamic discovery, exact replay, namespace isolation, bounded logs, timeout termination, review publication, no top-level Foundry tool, no mutable latest, and no retired-renderer invocation.

`node tools/foundry_model_sheet_contract_test.mjs` preserves the v1 three-plane contract. `node tools/foundry_front_side_workflow_contract_test.mjs` proves v2 front/side calibration, synthetic-fixture restrictions, initial-box failure, deterministic shared-cage fitting, standalone cage evidence, registered-only output policy, one closed crude volume, and the unchanged 57-tool public schema.

Live acceptance additionally requires authenticated dynamic discovery, three completed cloud specimens, immutable URL readback, visible shared-viewer evidence, and two namespaced jobs that cannot resolve to each other.

## D78461 Proof Fixture

The first model-sheet proof source is under docs/evidence/d78461-model-sheet-v1/. proof-source.json binds the generated schematic planes and d78461-bare-casting.foundry.js. tools/build_d78461_model_sheet_fixture.mjs deterministically regenerates those inputs.

Scope is the manufacturing casting: one connected shell with ring, gun, commander, loader, and left pistol-port openings. Mantlet, barrel, cupola, hatch covers, lifting eyes, fittings, textures, and tank hull are forbidden. The reference is a transparent schematic normalization of cited public-domain US government sources, not a claim to possess an original factory orthographic drawing or to reproduce ballistic thickness. No successor candidate may be generated until this casting has green registered fit, accepted cloud/Sense evidence, and an accepted artifact review bound to the exact result.

The accepted proof is v8 under `docs/evidence/d78461-model-sheet-v8/`. Its `cloud-proof.json` binds the production job, immutable promoted artifacts, unchanged per-view fit thresholds, active accepted Sense frame, purpose review, and promotion. v1-v7 remain immutable red/revision evidence. The gate was unlocked by promotion `c14574a357c252215ab275fd2cdd6ea916fbd664`; the proof workflow generated no subsequent candidate.

## Front/Side Workflow Proof

The neutral proof fixture lives under `docs/evidence/foundry-front-side-proof-v1/` and is regenerated by `tools/build_foundry_front_side_proof_fixture.mjs`. Its Foundry script contains no authored control-point overrides, booleans, vehicle identity, apertures, accessories, fixed-view request, or perspective render. It creates one 34-control-vertex box cage, fits that shared cage to the calibrated front and side silhouettes, subdivides once into `Crude_Turret_Volume`, and requests registered-only evidence.

Live acceptance is exactly one owner-scoped `foundry.asset.run` job through `drive_operation`. Read-only status polling and idempotent attachment to that same job are allowed; a second namespace, changed geometry, relaxed threshold, successor, aesthetic review, or promotion is forbidden. The immutable automatic-review publication and Sense record are the terminal receipts.
