# CODEX STARTS HERE

## Current State

Systemic artifact transport is implemented and live-verified on
`agent/systemic-artifact-transport`, based on remote `main`
`7798c1b9cc116b89359febcee06ea8d22326f344`. The branch also includes the SMS
Calendar proposal commits. Candidate 001 completed the transport proof but
remains quarantined pending hosted Pose-is-God visual review.

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

## Deployment State

Production targets are `command-center-blender-render-00020-2bq`,
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
published, and replay transferred zero bytes. It does not release Candidate 001
from quarantine. Only the hosted visual review lane can do that.
