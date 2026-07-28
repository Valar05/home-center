# CODEX STARTS HERE

## 2026-07-27 Release Consolidation

Home Center MCP may publish only from a clean HEAD exactly equal to
`origin/main`. Feature-branch deployment is forbidden. Current remote main is
`d56b7b1748bfc448177c078aedaaaebad42b8215`, merged through PRs #120-#122.
Production Home Center MCP is `homecentermcp-00152-nen` at that exact commit;
Audio Reader is `audiolibraryapi-00012-dil`. Immediate rollback is
`homecentermcp-00151-yec` and `audiolibraryapi-00011-yaj`.

Vacation Day 1 Parts 6 and 7 are byte-preservingly registered under
`dclarke1005@gmail.com` as private `review/unreviewed` Reader items and
passed authenticated range playback. Read
`docs/evidence/vacation-audio-reader-repair-2026-07-27.md` for exact hashes,
generations, range receipts, and no-copy/no-rerender evidence.

## Current Work

Branch `agent/receipt-delivery-preflight` adds one producer-agnostic receipt
delivery path below `drive_operation`, strict GLB/LFS and Python preflight,
separate review/fix-forward lineage, and `needs_reconciliation` for ambiguous
renderer outcomes. It must merge as one direct-main PR and may deploy only after
that merged commit becomes clean exact `origin/main`. The top-level MCP tool
hash must remain
`64fe900eeaaf2928c2b6114829ee758ff73cc05700373085a1ae63b6484d05f1`.

## Read First

1. `docs/ARTIFACT_TRANSPORT_SYSTEM.md` - authority map, failures, architecture,
   performance, deployment evidence, rollback, and limitations.
2. `functions/artifact_transport.js` - canonical identity/location union,
   structured errors, schema, compatibility, preflight, bounded concurrency.
3. `functions/artifact_ingest_service.js` - existing catalog owner plus native
   resumable raw-binary adapter.
4. `functions/home_center_mcp.js` and `functions/command_center_mcp.js` -
   adapters and render lifecycle.
5. `cloud-render/src/render_bundle.mjs` - concurrent resolution/publication and
   v2 contract enforcement.

## Immutable Proof Inputs

- GLB: `diagnostic-regnet-sprint-stop.glb`, 682,056 bytes,
  `c10707777c404e9dda6af4d9cd450b321d12688402ac6894d54859cd30a06b35`.
- Script: `render-candidate-001.py`, 38,307 bytes,
  `ae64b5aec3a7fbf37aaba249074fc9f1ff48a7ef0d10e83907cdd7c75fd4bcea`.
- Source authority: `Valar05/pose-lab-v2` PR #12 head
  `cceec91bc8097ce1adcd28e01689137ca9d93707`.
- Existing large proof: Drive `1G6PsdVS24Zw8kqiWZgzRlM22hE_UhkFd`,
  181,652,767 bytes, SHA-256
  `4f4d7a973203e5f57493b7c6b7c41e5076bbe67f9164249cf107daa35b15c964`.

Do not ask for those bytes again. Candidate source objects already exist in
`gs://home-center-dclar-command-center-renders` and preflight adopts them.

## Verification Commands

`node tools/artifact_transport_contract_test.mjs`
`node tools/artifact_resumable_transport_test.mjs`
`node tools/artifact_transport_performance_test.mjs`
`node tools/artifact_ingest_contract_test.mjs`
`node tools/artifact_transport_preflight_integration_test.mjs`
`node tools/command_center_blender_upload_byte_preservation_test.mjs`
`node tools/home_center_render_github_source_materialization_test.mjs`
`node tools/command_center_blender_file_handoff_test.mjs`
`node tools/command_center_blender_render_contract_test.mjs`

Use a normal Linux/temp install from lockfiles for dependency-heavy tests. Android
shared storage can omit package-root files during npm extraction; that is an
environment issue, not a reason to weaken tests.

## Archived Deployment Snapshot Before Release Consolidation

The following targets are historical archaeology. Production targets were `command-center-blender-render-00020-2bq`,
`commandcentermcp-00072-jan`, `homecentermcp-00141-xin`, and private worker
`commandcenterrenderworker-00001-wun`, all at 100% traffic. Queue
`commandCenterRenderWorker` is RUNNING with concurrency four and one attempt.
Cloud Run job count is zero. Do not remove the worker without also deleting its
queue, and do not leave either behind during rollback. Exact rollback targets
and proof receipts are in `docs/ARTIFACT_TRANSPORT_SYSTEM.md`.

Repository and backend schemas include `settings.gifFrames`. The connected
host catalog in the proving session remained cached on the older top-level tool
schema; use the stable dispatcher until the connector is reconnected.

## Acceptance Guard

Transport success means exact bytes reached Blender, outputs and manifests were
published, and replay transferred zero bytes. Candidate 001 remains preserved but rejected; only a changed successor accepted in the hosted visual review lane can replace it.

## Archived Foundry Branch Snapshot

PR #121 has merged. The following paragraph records the pre-merge branch snapshot: `agent/fortress-model-foundry` was stacked on `agent/systemic-artifact-transport`. Read `docs/FORTRESS_MODEL_FOUNDRY.md` first. Foundry registers only below the existing `drive_operation` boundary. The authenticated production baseline is checked in at `contracts/home-center-top-level-mcp.v1.json`; its canonical SHA-256 is `64fe900eeaaf2928c2b6114829ee758ff73cc05700373085a1ae63b6484d05f1`. Run `node tools/foundry_contract_test.mjs` before review or deployment. Do not add a top-level Foundry tool, a second viewer, a Blender fallback, or a mutable `latest`.

Foundry live proof is in `docs/evidence/fortress-foundry-live-proof-2026-07-27.json`. Deployed revisions are `foundryassetworker-00001-bip` and `homecentermcp-00147-ket`; MCP rollback is `homecentermcp-00146-jub`. The canonical server path is green, while the Codex app adapter remains blocked by a host-owned `home_center_drive.` tool-name prefix mismatch. Do not alter the MCP contract to compensate.
