# TvTroper GCS retrieval lane

This is the narrow deployed adapter for Hyperbolic's trope retrieval.

- The canonical source stays in the RyokoExtra `pages.zip` object in GCS.
- `build-index.mjs` range-reads ZIP entries and writes resumable gzip NDJSON shards containing searchable fields plus the full original HTML to GCS `index/v2/`.
- BigQuery is loaded from those GCS shards and owns the deployed search index and serving copy of each full record.
- `service.mjs` exposes private `/search` and `/get` operations. Fetch returns the full matched HTML plus provenance back to the canonical GCS archive generation, ZIP entry, line, and CRC.
- Home Center MCP is the authenticated public tool surface. Google Drive is not in this path.
