# CODEX STARTS HERE

## Current Authority

Home Center publishes only from a clean commit that is exactly current `origin/main`. The release path is `tools/deploy_foundry_v2_release.sh`; it pauses the Foundry queue across the worker and MCP swap, verifies the deployed main commit and manifest hash, and resumes the queue through a trap.

The active 3D authoring lane is Fortress Model Foundry V2. It is dynamically discovered below the existing `drive_operation` MCP tool. Do not add a top-level Foundry tool or a second viewer.

The prior Cloud Blender execution lane and Command Center Codex worker discovery are retired. They are not catalogs, fallbacks, deploy targets, or repair candidates. Guessed calls return a 410 retirement error. Historical producer receipts remain readable only through generic owner-scoped receipt delivery.

## Read First

1. `docs/FORTRESS_MODEL_FOUNDRY.md`
2. `docs/ARTIFACT_TRANSPORT_SYSTEM.md`
3. `docs/ARTIFACT_BUCKET_ARCHITECTURE.md`
4. `docs/WORKER_RESOURCE_CONTRACT.md`
5. `docs/archive/CLOUD_EXECUTION_RETIREMENT_2026-07-27.md`

## Stable Contracts

- Home MCP entry point: `drive_operation`.
- Foundry operations: `foundry.asset.inspect`, `foundry.asset.run`, `foundry.asset.status`, `foundry.asset.promote`.
- Run contract: `home-center.foundry-run.v2`.
- Script contract: `foundry-js.v1`.
- Top-level MCP tool count after retirement: 57.
- Canonical top-level MCP SHA-256: `5c7cee977116422e47ae817920d41b63227d841348fd6c0769f6c9f1568b6498`.
- Public manifest SHA-256: `1a8592c9645de28951734999259a819cd66ca2521327001fb372fab4a7c80779`; generated in `contracts/home-center-public-tool-manifest.v1.json`, never hand-edited.
- Shared viewer: `https://valar05.github.io/model-viewer-lab/model-viewer.html`.

## Verification

`node tools/foundry_contract_test.mjs`
`node tools/cloud_blender_retirement_contract_test.mjs`
`node tools/worker_profile_contract_test.mjs`
`node tools/generate_home_center_public_manifest.mjs --check`
`sh tools/home_center_ci_validate.sh`

Mechanical completion is not human acceptance. A completed Foundry job must publish immutable fixed-view evidence and a shared-viewer URL as `review_ready/unreviewed`. Promotion requires a separate accepted review record bound to the exact receipt and result hash.
