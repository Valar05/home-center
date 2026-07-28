# Systemic Artifact Transport

Home Center uses content-addressed identity independently from transport location. An artifact identity contains SHA-256, byte length, media type, and stable logical filename. Locations may be Home Center artifacts, Drive resources, GCS objects, GitHub blobs, or staged upload receipts; temporary URLs and attachment handles are never identity.

Substantial binary data must not cross chat, JSON/Base64, logs, stdout, or a PTY. Prefer existing durable references or server-side copy. Upload immutable bytes once, reuse by digest, verify length and SHA-256 before readiness, and stage independent files with bounded concurrency and deterministic manifest ordering.

Long operations separate reference resolution, queueing, staging, acceptance, execution, publication, and human review. Exact idempotency binds logical inputs and artifact digests. Changed inputs under the same key fail. Ambiguous external mutation uses `needs_reconciliation`; rejected creative output uses `rejected` or `revision_requested` and links a changed successor.

## Active Paths

- Top-level Work Mode bytes enter through `drive_ingest_file` or `storage_ingest_artifact`.
- Durable GLBs and scripts are resolved as exact owner-scoped Home Center artifacts.
- `artifact_transport.preflight` reports resolution, hashes, sizes, chosen path, reuse, concurrency, and compatibility.
- `artifact.delivery.materialize_receipt` discovers only artifacts named by one terminal owner-scoped receipt, verifies GCS readback, and reuses private Drive delivery by digest.
- Foundry publishes immutable cloud review routes directly and uses the shared viewer.

Historical renderer receipts remain a private internal receipt source for generic read-only materialization. Their old producer name is not accepted or advertised. Materialization never re-executes a producer or alters human acceptance.

## Required Errors

Owned boundaries return specific codes for unsupported references, wrong size, digest mismatch, expired staging, Git LFS pointer bytes, invalid GLB magic/version/declared length, unsupported script version/operation, idempotency conflict, blank review canvas, retired capability, and unauthorized ownership. Bare `INVALID_ARGUMENT` is not an owned response contract.
