# Authenticated GCS Filesystem

## Purpose And Owner

Home Center exposes private generated storage as an owner-scoped logical filesystem below the existing `drive_operation` dispatcher. `functions/gcs_filesystem_service.js` owns paths, immutable versions, mutation receipts, trash, and authenticated byte delivery. `functions/artifact_ingest_service.js` remains the only owner of Work Mode binary ingress and canonical artifact registration.

This is not raw bucket access. Callers cannot supply a GCS path, bucket, URL, signed URL, local path, Base64 body, or terminal payload. A file source must be an authenticated Home Center artifact or a version already owned by the caller. Ownership is derived from the authenticated principal, never request arguments.

## Dynamic Operations

- `storage.filesystem.create`
- `storage.filesystem.append`
- `storage.filesystem.copy`
- `storage.filesystem.move`
- `storage.filesystem.rename`
- `storage.filesystem.overwrite`
- `storage.filesystem.trash`
- `storage.filesystem.restore`
- `storage.filesystem.list`
- `storage.filesystem.stat`
- `storage.filesystem.versions`
- `storage.filesystem.download`

These operations are dynamically discoverable through `drive_operation`. They are not top-level MCP tools and do not change the installed connector schema.

## Identity And Storage

A logical file has a stable owner-scoped `fileId` and absolute POSIX path. Each content mutation creates an immutable version containing SHA-256, byte length, MIME type, filename, GCS generation, parent version, provenance, and operation. Move and rename only change the logical path. Copy creates another logical file that reuses the same verified immutable bytes. Append uses server-side GCS composition and verifies the resulting length and digest before installing the new head.

Firestore collections:

- `gcsFilesystemFiles`: durable file identity and current head;
- `gcsFilesystemPaths`: active owner/path lookup;
- `gcsFilesystemVersions`: immutable version history;
- `gcsFilesystemMutations`: idempotent mutation receipts;
- `gcsFilesystemTrashEntries`: restorable owner-scoped trash entries.

Mutation receipts are also written immutably under `indexes/filesystem/v1/receipts/{ownerHash}/`. Artifact digest discovery uses `indexes/artifacts/v2/by-owner-sha256/{owner}/{sha256}.json`. The former v1 global digest index is compatibility-only and is never returned across owners.

## Mutation Rules

Every mutation requires `approved: true`, a stable `requestId`, and authenticated ownership. This approval authorizes execution; it does not imply human acceptance. New files retain `humanAcceptance: unreviewed` unless a separate owned review flow changes it.

Mutations of an existing file require `expectedVersionId`. Exact-input idempotency is checked before current-head or current-path validation, so replay still attaches after later moves, versions, trash, or restore operations and performs no duplicate byte staging. Reusing a request ID with different logical inputs returns `storage.filesystem.idempotency_conflict`. A new request against a stale head returns `storage.filesystem.version_conflict`.

Overwrite and historical restore create successor versions; they do not erase history. There is no permanent-delete operation.

## Trash And Retention

Trash removes the active path and creates an owner-scoped entry under `/.trash/`. The original path, immutable head, and provenance remain available for 30 days. Firestore TTL expires the trash entry, and GCS lifecycle removes the corresponding trash pointer after 30 days. Immutable content and historical file/version records are not silently destroyed by the trash operation.

Restore returns a nonexpired trash entry to its original path or an explicit unoccupied owner path. An active file can also restore a historical version as a new head, preserving lineage.

## Delivery

`storage.filesystem.download` verifies stored bytes against the selected immutable version before returning a private `resource_link`. The content endpoint requires Home Center OAuth on every GET or HEAD, enforces the owner boundary, supports one bounded byte range, and returns `Content-Length`, MIME type, filename, ETag, and `X-Content-SHA256`. Private `gs://` addresses and public URLs are not user-facing delivery.

## Artifact Projection

Canonical artifacts are projected lazily into deterministic logical paths:

`/artifacts/{project}/{artifactKind}/{artifactId}/{filename}`

Projection occurs after supported artifact ingest/commit/read operations. It reuses canonical bytes and is idempotent by artifact ID and digest. Existing historical artifacts become visible when read through their authenticated Home Center artifact identity; no bucket-wide owner-unsafe scan is performed.

## Verification And Deployment

Run:

`node tools/gcs_filesystem_contract_test.mjs`

`node tools/artifact_ingest_contract_test.mjs`

`sh tools/home_center_ci_validate.sh`

`tools/deploy_blender_workspace_release.sh` deploys the committed Firestore indexes and TTL through the active GCP identity plus the generated-bucket lifecycle before replacing code, then verifies the deployed source identity. It does not require a separate interactive Firebase login. Home Center may be published only from a clean commit equal to current `origin/main` through that guarded release script.

Rollback the service to the immediately previous recorded Home Center revision and retain the new Firestore collections and immutable GCS objects. They are additive and do not alter older artifact identities.
