# Home Center Drive File Ingress Contract

`drive_ingest_file` is the reusable top-level file-bearing bridge from ChatGPT Work Mode into private Google Drive.

## Input

- `requestId`: stable idempotency and audit key.
- `file`: top-level host file upload. Paths, URLs, Base64 strings, and nested descriptors are rejected.
- `name`, `mimeType`, and `parentFolderId`: optional Drive metadata.
- `expectedSha256`: optional caller-side provenance lock.
- `callerNote`: bounded audit summary.

The default ceiling is 256 MiB and can be lowered through `HOME_CENTER_DRIVE_INGEST_MAX_BYTES`.

## Safety and recovery

The bridge hashes the received bytes before mutation. A reused request ID must match the same bytes, filename, MIME type, and destination folder. The Drive object carries private app properties for request ID and SHA-256, allowing recovery after an ambiguous response without creating a second copy. Multiple matching objects quarantine the request.

Files are created private by default. No public permission is added.

## Acceptance

A successful receipt requires:

- uploaded byte count and SHA-256;
- Drive readback byte count and SHA-256;
- exact equality between upload and readback;
- `verified: true`;
- stable Drive file ID, durable `drive://` reference, and web view link;
- a completed Drive Bridge audit record containing the input SHA-256.

The operation is not accepted merely because Google returned a file ID.
