# Home Center Storage Artifact Ingress

`storage_ingest_artifact` is the direct Work Mode file-bearing route for immutable factory assets. It writes canonical bytes to Cloud Storage, never Google Drive.

## Authority split

- Cloud Storage owns canonical binary assets and immutable indexes.
- Command Center receives the artifact catalog receipt and retrieval identity.
- Drive remains a deliberate human-publishing surface.
- Library or scratch may transport bytes but is not canonical authority.

## Required identity

- Stable `requestId` and `artifactId`.
- `artifactKind`, `project`, filename, and MIME type.
- Caller-provided `expectedSha256`; `expectedByteCount` is recommended.
- Bounded provenance describing the source authority.

New ingestion always begins at `lifecycleState: proposed`. Human acceptance is a separate promotion and cannot be declared through this upload operation.

## Verification

Acceptance requires:

- input SHA-256 and byte count;
- canonical GCS readback SHA-256 and byte count;
- exact equality;
- immutable manifest, by-ID, by-SHA, catalog, and request indexes;
- a readback-verified Command Center catalog receipt;
- a durable `home-center://artifacts/<artifactId>` reference and private authenticated browser URL.

Retries with the same identity attach. Reusing a request ID, artifact ID, object name, or content index for different bytes or metadata fails closed.

## Connector refresh fallback

The preferred route is the top-level `storage_ingest_artifact` host-file slot. When a conversation still has an older connector schema, `drive_operation` exposes:

- `storage.artifact.begin`
- `storage.artifact.append_chunk`
- `storage.artifact.commit`

Chunks are individually SHA-verified, composed in GCS, verified as one artifact, committed through the same canonical path, and deleted only after successful publication. The fallback accepts at most 32 chunks and is transport machinery, not a second storage authority.
