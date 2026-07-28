# Vacation Audio Reader Repair Evidence

## Authority

- Repository: `Valar05/home-center`
- Remote main before integration: `777969c5feb43bd292ac8c41b1e3a656169be6f2`
- Working branch: `agent/fortress-model-foundry`
- Production Home Center before this repair: `homecentermcp-00150-guh`
- Production Audio Reader before this repair: `audiolibraryapi-00011-yaj`
- Production rollback targets: the two revisions above until the post-deploy proof records successors.
- Publish rule: Home Center MCP deployment is forbidden unless HEAD is a clean exact `origin/main` commit.

## Immutable Sources

### Day 1 Part 6

- Producer receipt: `vacation-day1-part6-royal-cove-final-soundscape-v1-20260727`
- Name: `Vacation-of-a-Lifetime-Day-1-Part-6-Royal-Cove-Final-Soundscape.ogg`
- Byte length: `3096594`
- SHA-256: `7e094b6c87d1505f64c2e3937f4f5659721ca559adfaa020c144c4239fcd851f`
- GCS generation: `1785193738831144`

### Day 1 Part 7

- Producer receipt: `vacation-day1-part7-veranda-final-soundscape-v1-20260727`
- Name: `Vacation-of-a-Lifetime-Day-1-Part-7-The-Veranda-Final-Soundscape.ogg`
- Byte length: `6105347`
- SHA-256: `5d2cb55c0396c46f39921c6f81679712736bb70d3e3e1c6f7f8751d7948f0978`
- GCS generation: `1785194005799673`

The producer receipts are owned by `dclarke1005@gmail.com`. The existing GCS
object metadata incorrectly used `drew` and `approved:true`, and neither
object had an owner-scoped Audio Reader catalog entry. Those defects are the
registration target. The bytes are not a mutation target.

## Repair Contract

- `audio.render_register` is dynamically discoverable below the unchanged
  `drive_operation` MCP boundary.
- It accepts only an owner-scoped terminal successful `audio.render` receipt.
- Ownership comes from the authenticated principal and must match the producer
  receipt actor.
- It verifies source byte length, SHA-256, and GCS generation before and after
  metadata repair.
- It removes legacy `approved` metadata, records authorization as
  `owner_scoped`, and records human acceptance as `unreviewed`.
- It creates or reuses a private digest-addressed Audio Reader catalog record.
- It proves Reader discovery, authorization, and a bounded media-header read.
- It performs no render, synthesis, Cartesia call, Drive copy, public exposure,
  or binary transfer.
- Exact replay reuses the catalog identity.
- Future `audio.render` calls cannot report `completed` until the same Reader
  registration and playback checks succeed. Legacy completions without Reader
  proof report `registration_required`.

## Repository Verification

- `sh tools/run_regression_tests.sh`: passed.
- `sh tools/home_center_ci_validate.sh`: passed.
- `node tools/audio_reader_registration_contract_test.mjs`: passed.
- `node tools/audio_render_contract_test.mjs`: passed.
- `node tools/foundry_contract_test.mjs`: passed.
- Baseline and final top-level MCP contract SHA-256:
  `64fe900eeaaf2928c2b6114829ee758ff73cc05700373085a1ae63b6484d05f1`.
- Foundry exact replay duplicate uploads: `0`.
- Blender attached GIF replay duplicate Drive creates: `0`.

## Catalog Contradiction And Repair

The first post-deploy protocol gate rejected production even though the service
was healthy: production capabilities reported
`2026-07-27.render-review-egress-v1`, while
`tools/home_center_production_blender_tool_catalog_test.mjs` still required
`2026-07-26.status-contract-v1`. The owning layer was the repository test,
not the Work Mode host or MCP runtime. The replacement manifest is generated
from the same `createHomeCenterMcpServer` registrations used by runtime. It
contains 58 complete public tool contracts, per-tool schema hashes and
file-bearing fields. Canonical tools SHA-256 remains
`64fe900eeaaf2928c2b6114829ee758ff73cc05700373085a1ae63b6484d05f1`;
public manifest SHA-256 is
`db08ac23a79a77f30720efd01a4a53658eb113e62bff3785a892966a330872cd`.

## Live Proof

Pending merge to `main`, exact-main deployment, authenticated receipt-only
registration of both parts, Audio Reader browse/play calls, and byte identity
readback. Do not replace this section with health-only evidence or private
`gs://` references.
