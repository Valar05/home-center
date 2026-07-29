# Hyperbolic TvTroper Retrieval

## Contract

Hyperbolic's TvTroper lane is GCS-only. Google Drive is not a storage, indexing, retrieval, backup, or fallback dependency for this corpus.

The canonical source is RyokoExtra/TvTroper `pages.zip` at Hugging Face commit `65ca60f908e536ce4ec1ac123415596379f363cd`. The dataset repository declares Apache-2.0; the archived TV Tropes pages themselves display CC BY-NC-SA 3.0 terms. Preserve both provenance statements when reusing results.

## Existing-system owners

- Storage Transfer Service owns the server-side source download into `gs://home-center-dclar-hyperbolic-corpus/source/huggingface.co/datasets/RyokoExtra/TvTroper/resolve/main/pages.zip`.
- GCS owns the canonical ZIP and generated index shards.
- GCS `index/v2/` owns the resumable full-record NDJSON shards generated from the ZIP.
- BigQuery table `home-center-dclar.hyperbolic_corpus.tvtroper_records` owns the deployed searchable and full-record serving copy; its `search_text` column has a BigQuery search index.
- Private Cloud Run service `tvtroper-retrieval` owns indexed query execution and full-record readback.
- Home Center's stable `drive_operation` dispatcher owns the ChatGPT surface under the exact registry operation name `tvtroper_operation`.

The TVTroper operation must not become another top-level MCP tool. This keeps Home Center's public connector schema stable while allowing the operation registry to evolve behind `drive_operation`.

## Record contract

Search returns a `record_id`, URL, title, namespace, page name, ZIP entry, line number, and snippet. Fetch accepts that exact `record_id` and returns the full original HTML record from BigQuery, with provenance back to the GCS ZIP generation, ZIP entry, line, and CRC. BigQuery was loaded only from the generated `index/v2/` GCS shards.

The GCS ZIP remains canonical source authority; the GCS shards and BigQuery table are deployed retrieval copies. No record enters this lane through Drive.

## Stable-dispatcher operations

- `drive_operation {operation: "tvtroper_operation", args: {operation: "status", args: {}}}`
- `drive_operation {operation: "tvtroper_operation", args: {operation: "search", args: {query: "Deal with the Devil", limit: 8}}}`
- `drive_operation {operation: "tvtroper_operation", args: {operation: "get", args: {record_id: "<exact id from search>"}}}`

Indexer source and schema live under `tvtroper-retrieval/`. The Cloud Run job `tvtroper-index-build` is resumable because each ZIP entry maps to a deterministic completion marker and one or more bounded GCS shards; completed entries are skipped.

## Acceptance gate

Do not update or promote the Hyperbolic skill until a zero-minimum-instance cold start produces a new retrieval `boot_id`, a deployed MCP search returns a real corpus match, and deployed MCP fetch returns the full matched HTML record from the GCS-derived deployed table with exact archive provenance. Build, source-contract, health, and warm-path checks are guardrails only.

The dispatcher repair has an additional gate: Home Center's top-level public manifest must retain the same tool count and canonical hash, `tvtroper_operation` must appear only in the runtime registry, and ChatGPT must search then fetch the exact returned `record_id` through `drive_operation`.

## Historical backend acceptance: 2026-07-29

- Storage Transfer operation `transferOperations/transferJobs-7315853636110702416-6631111775810956604` copied exactly 20,683,956,439 bytes to GCS.
- Cloud Run job execution `tvtroper-index-build-lzx4f` completed all 16 tasks; BigQuery contains 651,522 rows and zero missing HTML records.
- Search index `tvtroper_text_search` reached 100% coverage with zero unindexed rows. Deployed search job `job_q1cDJCMLirXxVN8y3-JR8vGXbE2u` reports `indexUsageMode: FULLY_USED`.
- From zero capacity, Cloud Run logged `AUTOSCALING` and booted process `42c40afa-aab2-4a5e-a4fb-c1c07959f843`. The historical direct-tool revision found `Main/DealWithTheDevil` and fetched its full 225,435-byte HTML record.
- Machine-readable receipts: `tools/command_center_invokability_evidence/tvtroper_cold_start_e2e_20260729.json` and `tools/command_center_invokability_evidence/tvtroper_hyperbolic_skill_promotion_20260729.json`.

A new stable-dispatcher ChatGPT receipt is required before this repair is complete.
