# Home Center Drive File Ingress Contract

`drive_ingest_file` is the reusable top-level file-bearing bridge from ChatGPT Work Mode into private Google Drive.

## Input

- `requestId`: stable idempotency and audit key.
- `file`: top-level ChatGPT host file parameter. Discovery declares `_meta["openai/fileParams"] = ["file"]`; ChatGPT supplies an object containing required `download_url` and `file_id`, with optional `mime_type` and `file_name`.
- Home Center accepts that typed object only. Workspace paths, bare attachment handles, arbitrary URL strings, Base64 strings, and nested descriptors are rejected.
- `name`, `mimeType`, and `parentFolderId`: optional Drive metadata.
- `expectedSha256`: optional caller-side provenance lock.
- `callerNote`: bounded audit summary.

The default ceiling is 256 MiB and can be lowered through `HOME_CENTER_DRIVE_INGEST_MAX_BYTES`.

## Safety and recovery

The ingress adapter validates a credential-free HTTPS host-file URL, rejects private/reserved network destinations and unsafe redirects, and streams the response into a mode-600 function-private temporary file while enforcing the byte ceiling and computing SHA-256. It never logs the signed URL or file handle and never buffers the full attachment in process memory. Drive upload and Drive readback are both streamed; the temporary file is deleted in a guaranteed cleanup boundary. A reused request ID must match the same bytes, filename, MIME type, and destination folder. The Drive object carries private app properties for request ID and SHA-256, allowing recovery after an ambiguous response without creating a second copy. Multiple matching objects quarantine the request.

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

## Complete binary readback

Stored Drive binaries use owner-bound sessions beneath the stable drive_operation tool; the top-level MCP catalog does not change:

1. drive_binary_read_begin streams and hashes the whole Drive object, snapshots its metadata, and returns chunk count and whole-file SHA-256.
2. drive_binary_read_chunk returns one indexed Base64 range plus its own SHA-256 and records only the bounded progress receipt in Firestore.
3. drive_binary_read_status verifies that the Drive snapshot is unchanged and returns served and missing chunk indexes for recovery.
4. drive_binary_read_complete requires the reconstructed byte count and SHA-256, requires every chunk receipt, then streams and hashes Drive again before returning verified true.

Sessions reject another owner, Google-native files, empty or oversized binaries, source mutation, missing chunks, and reconstructed-identity mismatch. The older drive_read_binary_chunk operation remains available for compatibility.
