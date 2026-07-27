# Fortress Model Foundry

## Boundary

Fortress Model Foundry is a dynamically discovered Home Center capability pack. It is not a top-level MCP tool, MCP server, connector, plugin, or viewer.

The installed MCP boundary remains the authenticated `tools/list` captured in `contracts/home-center-top-level-mcp.v1.json`. Its canonical SHA-256 is:

`64fe900eeaaf2928c2b6114829ee758ff73cc05700373085a1ae63b6484d05f1`

Foundry registers below the existing `drive_operation` tool in `driveOperationRegistry()`. The dynamically discoverable operation IDs are:

- `foundry.asset.inspect`
- `foundry.asset.run`
- `foundry.asset.status`
- `foundry.asset.promote`

The top-level tool name, description, annotations, and input schema are unchanged. `tools/foundry_contract_test.mjs` compares the complete canonical tool array, not only the names, and rejects any top-level Foundry tool.

## Existing Owners

- Dynamic discovery and routing: `drive_operation` and `driveOperationRegistry()` in `functions/home_center_mcp.js`.
- Artifact ingress and immutable identity: `functions/artifact_ingest_service.js`.
- Asynchronous dispatch: Firebase Cloud Tasks and `foundryAssetWorker`.
- Worker sizing and scaling: `media-forge-light` in `ops/worker_profiles.v1.json`.
- Durable artifacts: the existing `HOME_CENTER_ARTIFACT_BUCKET` bucket.
- Human review: the shared Model Viewer Lab at `https://valar05.github.io/model-viewer-lab/model-viewer.html`.

No Command Center Codex worker, Blender service, second viewer, or mutable global `latest` participates.

## Trust And State

The controller accepts only an authenticated owner. A Home Center artifact source is resolved through that owner's immutable artifact manifest. The manifest byte length and SHA-256 are bound into the logical request. The worker downloads the canonical object and verifies both before execution.

The durable state flow is:

`accepted -> queued -> running -> completed | failed`

Publication is separate:

`completed/private_unpromoted -> explicitly approved immutable promotion`

Only `foundry.asset.promote` creates public review links. It accepts an owner-scoped terminal successful job, exact result hash, and `approved=true`. Promotion never recompiles a model and never changes human acceptance state.

## Request Contract

`foundry.asset.run` accepts:

- `source`: omitted only for procedural hard-surface work, or a `home_center_artifact` / `foundry_fixture` reference;
- `recipe`: `home-center.foundry-recipe.v1`;
- `parameters`: bounded JSON object, maximum 32 KiB;
- `reviewPreset`: currently `fixed-four-view`;
- `idempotencyKey`: exact replay binding;
- `namespace`: mandatory isolated job namespace.

The input hash binds capability version, resolved immutable source identity, recipe, parameters, review preset, and namespace. Reusing an idempotency key with changed input fails with `foundry.idempotency_conflict`. Exact replay attaches to the existing job and does not enqueue or upload again.

## MVP Recipe Vocabulary

### Hard Surface

The first specimen uses a profile extrusion with chamfered/beveled corners, material assignment, mirrored bracket instances, repeated wheel instances, a socket component, and topology/normal/bounds validation.

Supported MVP command:

- `mechanical_specimen`

The kernel is deliberately bounded. Arbitrary booleans, sculpting, organic generation, and a modifier ecosystem are unsupported.

### Character Setup

The first specimen uses the deterministic `foundry-character-v1` fixture. It adds `weapon_socket_r` below `hand_r`, appends one inverse-bind matrix while preserving the original prefix and joint order, and attaches an unskinned rigid prop below the new joint.

Supported MVP commands:

- `add_weapon_bone`
- `attach_rigid_prop`

The preservation evidence compares pre-existing mesh geometry, JOINTS/WEIGHTS accessors, morph target data, materials, animations, original joint order, and original inverse-bind bytes. Weight painting and automatic rigging are unsupported.

### Animation

The first specimen trims `fixture_idle`, interpolates exact boundary keys, retimes the result, adjusts one deliberate rotation key, and exports `fixture_idle_foundry`.

Supported MVP commands:

- `trim_clip`
- `retime_clip`
- `set_rotation_key`

Geometry and skin evidence must remain byte-identical at the accessor level. Compatible-skeleton retargeting, IK recipes, clip combining, mirroring, and root-motion edits remain later bounded increments.

## Worker Isolation

`foundryAssetWorker` launches `functions/foundry_worker_process.mjs` as a detached Node process. The parent:

- uses one artifact per worker instance;
- streams stdout and stderr to separate 64 KiB bounded files;
- kills the complete process group on timeout;
- verifies source bytes before launch;
- enforces source, parameter, geometry, runtime, and output ceilings;
- publishes output files only after worker success;
- readback-verifies every output byte length and SHA-256;
- stores bounded logs privately and omits their contents from chat receipts.

The normal path uses glTF Transform and PNGJS. It never invokes Blender and has no Blender fallback.

## Immutable Addressing

Successful outputs use:

`foundry/v1/{ownerHash}/{namespace}/{inputHash}/{resultHash}/{filename}`

Durable artifacts include:

- `foundry-result.glb`
- `contact-sheet.png`
- `skeletal-overlay.png` for character domains
- `validation-report.json`
- `preservation-evidence.json`
- `foundry-manifest.json`
- bounded private stdout/stderr logs

Promotion links use an immutable `promotionId` derived from `jobId` and `resultHash`. Model Viewer deep links bind the exact promoted GLB and manifest URLs. There is no `latest` alias.

## Limits

- Source GLB: 256 MiB default.
- Parameters: 32 KiB.
- Commands: 64.
- Vertices: 250,000.
- Triangles: 500,000.
- Output aggregate: 256 MiB default.
- Worker runtime: 10 minutes by default, hard ceiling 25 minutes; deployment ceiling 30 minutes.
- Worker logs: 64 KiB per stream.
- Worker concurrency: one artifact per instance; maximum eight instances from `media-forge-light`.

## Verification

```sh
npm --prefix functions ci
node tools/foundry_contract_test.mjs
node tools/worker_profile_contract_test.mjs
sh tools/home_center_ci_validate.sh
```

The Foundry contract test covers the three specimens, GLB round trips, preservation, dynamic discovery, complete top-level MCP equality, unsupported versions/commands, exact replay, idempotency conflict, namespace isolation, immutable addressing, timeout termination, bounded logs, explicit promotion, viewer-link stability, zero duplicate uploads, no mutable latest, and no Blender invocation.

## Deployment

Deploy the worker first:

```sh
sh tools/deploy_foundry_worker.sh home-center-dclar
```

The script resolves resources from `ops/worker_profiles.v1.json`, validates before deployment, creates or updates the private task queue, and verifies the backing Cloud Run service after deployment.

Then deploy the existing MCP function without changing connector registration:

```sh
sh tools/deploy_functions_termux.sh home-center-dclar homeCenterMcp
```

After deployment:

1. Authenticate to the existing MCP endpoint and recapture canonical `tools/list`.
2. Require SHA-256 `64fe900eeaaf2928c2b6114829ee758ff73cc05700373085a1ae63b6484d05f1`.
3. Call existing `capabilities` and verify the four namespaced Foundry operations.
4. Invoke specimens through existing `drive_operation`.
5. Poll `foundry.asset.status` to terminal state.
6. Explicitly promote the successful result and open immutable review links.
7. Replay the exact run and verify no duplicate queueing or object upload.
8. Run two namespaces concurrently and verify distinct job IDs, input hashes, cache keys, manifests, and promotions.

No connector uninstall, reinstall, reconnect, or reauthorization is part of deployment.

## Rollback

1. Route `homeCenterMcp` to the exact prior verified revision.
2. Disable new submissions by removing the Foundry operation entries in a follow-up repository commit and redeploying that verified commit.
3. Delete the `foundryAssetWorker` function and `foundryAssetWorker` queue together only after confirming no jobs are queued or running.
4. Retain immutable result objects and promotion receipts according to artifact retention policy; do not delete human review evidence as part of code rollback.

A rollback must not leave either the worker or its task queue orphaned.

## Known Limitations

- The fixture proves preservation and bounded transforms; arbitrary production rigs require explicit compatibility recipes.
- No weight painting, automatic rigging, organic generation, sculpting, arbitrary booleans, Cycles, `.blend` compatibility, or Blender fallback.
- Static review images use a deterministic fixed wireframe projection; human acceptance occurs in the shared cloud viewer.
- Public promotion makes the selected immutable review artifacts accessible by unguessable content-bound links. Private-only review delivery is a separate access-control increment.
- Retargeting, IK, clip composition, root-motion edits, UV transforms, mesh weld/repair recipes, and broader hard-surface commands remain explicit future additions, not claimed capability.
