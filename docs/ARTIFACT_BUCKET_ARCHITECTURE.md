# Artifact Bucket Architecture

Canonical generated storage is private `gs://home-center-generated`. Source belongs in Git, curated knowledge in Drive, and generated machine artifacts in GCS. Drive is a publishing destination, not a render cache.

## Active Layout

Digest-addressed active layouts include `artifacts/sha256/`, `foundry/v2/`, `audio/`, `images/`, `video/`, `logs/`, and `temp/`. Foundry writes immutable GLBs and review evidence below `foundry/v2/<owner-hash>/<namespace>/<input-hash>/`. No active producer writes to a Blender-specific prefix.

Every durable object carries string metadata for `"owner"`, `"ownerEmail"`, `"project"`, `"stage"`, `"engine"`, `"createdBy"`, `"jobId"`, `"commit"`, `"timestamp"`, `"executionAuthorized"`, `"authorizationState"`, and `"humanAcceptance"`, plus SHA-256, byte count, media type, request identity, and artifact type. Authorization and human acceptance are separate. New output defaults to `humanAcceptance=unreviewed` and is never marked approved by transport code.

Producers write GCS first, verify readback length and SHA-256, register owner-scoped discovery, and only then report mechanical completion. User-facing handoff must be a private playable/downloadable resource or immutable shared-viewer route; a `gs://` string alone is not delivery.

## Retention

Lifecycle cleanup is explicit and bucket-managed:

- `temp/`: delete after 7 days.
- Intermediate generated outputs: delete after 30 days only where their prefix is covered by the configured lifecycle rule.
- `logs/`: delete after 14 days.
- Immutable promoted artifacts and producer receipts are not deleted by an implicit application retry.

Historical retired-producer objects remain read-only evidence. Generic receipt delivery may materialize an owner-scoped artifact from a real terminal receipt, but no active execution route points to a retired producer.

Implementation owners are `functions/artifact_ingest_service.js`, `functions/artifact_transport.js`, `functions/artifact_delivery_service.js`, `functions/artifact_bucket.js`, `functions/audio_catalog_service.js`, and `functions/foundry_capability.js`.
