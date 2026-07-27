# Systemic Artifact Transport

Status: implemented, deployed, and live-verified; Candidate 001 remains visually quarantined

Baseline: remote `main` at `7798c1b9cc116b89359febcee06ea8d22326f344`

Captured: 2026-07-27 America/Chicago

## Prompt Contract Ledger

- Current command: build on current remote `main`, integrate the SMS Calendar
  changes, and repair artifact transport across Home Center, Command Center,
  Work Mode attachments, Drive, GitHub, Cloud Run workers, and renderers.
- Repeated concrete requirements: substantial binary bytes never traverse chat,
  JSON/Base64, logs, stdout, or PTYs; immutable bytes upload once by SHA-256;
  independent files stage with bounded concurrency; resumable chunks verify;
  schemas agree; Candidate 001 reaches Blender without another user upload.
- Forbidden stale premise: a Regnet-only envelope patch, another Base64 size
  adjustment, or one successful render is the transport repair.
- Required artifact: one versioned content-addressed reference union, shared
  resolver/stager, preflight, specific errors, telemetry, tests, deployment, and
  durable handoff.
- Accepted evidence lane: repository contract, deployed schema, observed runtime,
  and host attachment behavior are recorded separately; live proof requires
  receipts, hashes, timings, output manifests, and zero-transfer replay.
- False green: bare `INVALID_ARGUMENT`, restaging equal bytes, asking Drew to
  reattach, serial source staging, missing before/after measurements, or treating
  transport success as Pose-is-God animation acceptance.

## Authorities

| Authority | Current truth |
| --- | --- |
| Repository | `Valar05/home-center`, current `main` `7798c1b`. PRs #116-#118 added Drive ingress, Storage ingress, and a Base64 chunk fallback. SMS commits are replayed on `agent/systemic-artifact-transport`. |
| Pose proof source | `Valar05/pose-lab-v2` draft PR #12, head `cceec91bc8097ce1adcd28e01689137ca9d93707`. Candidate remains quarantined. |
| Home Center MCP | ACTIVE `homecentermcp-00141-xin`, build `afafc24d-b1b0-458e-9ce8-61e31cc2d5a3`, 100% traffic, readiness green. |
| Command Center MCP | ACTIVE `commandcentermcp-00072-jan`, build `062c2cda-f653-4b1a-b4c7-85882b76a584`, 100% traffic, readiness green. |
| Blender renderer | ACTIVE `command-center-blender-render-00020-2bq`, image digest `sha256:c4472114eaa28620aefb02b3b5c4e194cd1f5410f85a05a4f9923ec56b90d439`, 4 CPU, 8 GiB, concurrency 1, timeout 1800, max scale 4, 100% traffic. |
| Render task worker | ACTIVE `commandcenterrenderworker-00001-wun`, build `58c33ee4-882f-4f3c-91b1-71020a287183`, 1 CPU, 512 MiB, concurrency 1, timeout 1800, max scale 4, private. |
| Render task queue | RUNNING `commandCenterRenderWorker`, bounded to four concurrent dispatches and four dispatches/second, `maxAttempts=1`. |
| Cloud Run jobs | Zero jobs in `home-center-dclar/us-central1` after deployment. The transport repair did not create a proof job. |
| Object storage | Generated proof outputs are in `gs://home-center-generated`; immutable input staging/catalog remains in `gs://home-center-dclar-command-center-renders`. No proof bucket was created. |

## Transport Map

| Boundary | Public/runtime schema | Transport | Limits and retry | Serialization and reuse |
| --- | --- | --- | --- | --- |
| Work Mode -> `storage_ingest_artifact` | Top-level host `File` plus identity fields | Host binary attachment, then whole `arrayBuffer()`, then GCS save | 256 MiB configured; function request/host limits remain external | One file only; full buffering; SHA index reuse occurs after bytes already crossed host boundary |
| Work Mode -> `drive_ingest_file` | Top-level host `File` | Host binary attachment, whole buffer, Drive multipart/media upload, full Drive readback | 256 MiB configured | One file only; no cross-tool content-addressed reuse |
| Work Mode -> `render_blender_glb` | Host currently exposes only `idempotencyKey`, `renderId`, `cache`, `glbFile`, `scriptFile` | Two host files, each fully buffered, then GCS | GLB 250 MiB; script 1 MiB | Command Center stages GLB then script sequentially; equal bytes are written under request-scoped paths before cache lookup |
| Home Center dispatcher -> render | `glbRef`/`scriptRef`, GitHub descriptors, Drive refs, or inline script | JSON metadata only after Home Center materializes to GCS | GitHub timeout 120 s; Drive and GCS provider limits | Home Center loops through GLB then script serially; GitHub has source-label cache, not a shared digest catalog |
| Drive -> Home Center staging | `drive://fileId` | Drive response stream into GCS stream | GLB/script configured limits | Server-side streaming, but no server-side copy and no digest lookup before transfer; sources stage sequentially |
| GitHub -> Home Center staging | repository/ref/path | Authenticated GitHub raw stream into GCS | GitHub timeout 120 s | Cached per source descriptor; the same digest at another ref/path uploads again |
| Command Center -> Blender service | JSON containing refs/settings/contracts | Small JSON metadata | Function timeout 300 s; renderer live timeout 900 s | Synchronous call; no prompt accepted receipt/status split |
| GCS/Drive -> Blender workdir | `gs://`, `drive://`, `bucket://`, legacy inline upload object | Whole-object download into memory | GLB 250 MiB; script 1 MiB | Blender downloads GLB, then script sequentially; legacy Base64 decoder remains |
| Blender -> GCS outputs | Local files -> GCS upload | Binary GCS upload | 180 MiB/file, 400 MiB total | Frame, fixed view, diagnostic, and remaining output uploads are globally sequential |
| GCS -> Drive publication | Generated artifact plus optional Drive target | GCS download to memory then Drive stream and full readback | Provider limits; no explicit bounded concurrency | Deliberate publication copy, but currently full-buffered |
| `storage.artifact.append_chunk` | JSON `chunkBase64` | Base64 in MCP JSON | 700 KiB decoded max, 128 chunks, about 87.5 MiB maximum | Sequential caller operations; contradicts the new no-substantial-Base64 contract |
| GitHub Actions artifacts | `actions/upload-artifact@v4` | GitHub artifact service | Repo workflows retain one day | Quota exhaustion is storage policy, not byte corruption or transport marshalling |
| Terminal/PTTY | No supported contract | Text/base64 output | Truncation observed at 181 MB archive | Forbidden for binary transport |

## Failure Matrix

| Evidence | Repository contract | Deployed/host behavior | Classification |
| --- | --- | --- | --- |
| 181,652,767-byte Regnet Drive ZIP | Drive can hold it; exact SHA-256 `4f4d7a973203e5f57493b7c6b7c41e5076bbe67f9164249cf107daa35b15c964` | Prior PTY/Base64 transfer silently truncated | Wrong transport selection; never repeat |
| 880 KiB generated index | JSON/file tools imply reusable content movement | Connector single-file payload rejected it | Host payload ceiling is below repository expectations |
| Drive link in host upload slot | Direct render schema requires host `File` | Correct Drive bytes cannot inhabit the host `File` field | Reference-kind/schema mismatch |
| Real Work Mode files | Zod accepts `File` and repository tests pass | Connected invocation produced bare `INVALID_ARGUMENT` before Blender | Host marshalling disagreement; owned boundary lacks diagnostics |
| `gifFrames` | Renderer and Command Center accept it under settings; fallback exists | Connected top-level tool omits `settings` and therefore omits `gifFrames` | Public/backend schema disagreement |
| Multi-file render | Two immutable inputs are hashable | GLB and script stage and resolve sequentially | Accidental serialization |
| Repeat render | Render cache keys final refs and settings | File bytes may be restaged before cache lookup | Idempotency occurs too late |
| Live renderer resources | Repo worker profile is authoritative | Live concurrency 160 and smaller instance shape | Deployment drift and collision risk |
| `find_by_sha256` read | Registry advertises the operation | Connected call returned only `INVALID_ARGUMENT` | Bare owned-boundary validation failure |

## Candidate 001 Proof Identity

Pose Lab PR #12 head `cceec91` binds:

- `diagnostic-regnet-sprint-stop.glb`: 682,056 bytes, SHA-256
  `c10707777c404e9dda6af4d9cd450b321d12688402ac6894d54859cd30a06b35`;
- `render-candidate-001.py`: 38,307 bytes, SHA-256
  `ae64b5aec3a7fbf37aaba249074fc9f1ff48a7ef0d10e83907cdd7c75fd4bcea`.

Both exact digests already exist in the private legacy render-input bucket under
GitHub-cache objects. The repair must adopt/reuse those objects by digest. It
must not fetch GitHub or ask Drew to upload them again.

Candidate status remains `quarantined-pending-visual-review`. Transport proof may
establish execution, byte identity, and output publication only.

## Large-File Proof Authority

The existing Drive ZIP `1G6PsdVS24Zw8kqiWZgzRlM22hE_UhkFd` is 181,652,767
bytes with Drive MD5 `1569b7cce0ffdd7d547c4eb6b1aa7384` and repository SHA-256
`4f4d7a973203e5f57493b7c6b7c41e5076bbe67f9164249cf107daa35b15c964`.
The proof should resolve and reuse the Drive location without copying 181 MB.
Interruption/resume behavior should use bounded controlled fixture bytes.

## Required Replacement

One contract must separate immutable identity from location, select a transfer
path by consumer capability, preflight before mutation, stage independent files
with bounded concurrency, verify bytes before ready, and return versioned
receipts with structured field errors. Legacy Base64 chunks may remain only as a
small explicitly deprecated compatibility adapter; they cannot be the large-file
path.


## Implemented Contract

Implementation status: repository-verified; deployment and live proof follow this section.

- Canonical reference: `home-center.artifact-reference.v1` separates immutable
  `sha256`, `byteLength`, `mediaType`, and `fileName` from a location
  union: GCS, Drive, GitHub, host upload, Command Center bucket, or inline
  metadata.
- Transport receipt: `home-center.artifact-transport.v1` binds request ID to
  logical operation, artifact identities, and consumer capabilities. Temporary
  URLs are excluded from identity and bounded status.
- Renderer request: `home-center.blender-render-request.v2`. Home Center's
  public JSON schema and Command Center/renderer validation are generated from
  `functions/artifact_transport.js`; `gifFrames` and `gifTimingMs` are
  present at all owned boundaries.
- Preflight states are `accepted|failed`; resumable publication uses
  `staging -> uploaded -> ready -> completed` and fails closed before
  publication on any range or whole-object digest mismatch.
- Long binary ingress uses a private GCS resumable session. Raw bytes travel
  directly from the client to GCS. Commit range-reads and SHA-verifies every
  declared chunk at bounded concurrency four, stream-verifies the whole object,
  then server-side copies it into the existing immutable catalog.
- Legacy Base64 chunks are compatibility-only and capped at 65,536 decoded
  bytes. Renderer inline Base64 has the same cap. The observed 880 KiB connector
  failure establishes that JSON is not a file transport; no larger JSON
  threshold is used.
- Independent Home Center Drive/GitHub sources, Command Center host files,
  renderer input resolution, and renderer output publication use bounded
  concurrency. Result arrays retain deterministic input order.
- Host render staging uses `artifacts/sha256/<digest>/<filename>`, create-if-
  absent, and verifies any preexisting object before reporting reuse.

## Operations

| Operation | Contract |
| --- | --- |
| `artifact_transport.preflight` | Resolve an artifact-reference array, verify provider metadata, choose reuse/stage path, persist bounded receipt. |
| `artifact_transport.status` | Owner-only bounded receipt; no bytes, tokens, or private URLs. |
| `storage.artifact.resumable_begin` | Bind request and chunk manifest, create private GCS raw-binary upload target, return accepted receipt. |
| `storage.artifact.resumable_resume` | Owner-only reissue of the private session target. |
| `storage.artifact.resumable_status` | Owner-only progress without session target. |
| `storage.artifact.resumable_commit` | Verify ranges and whole object, publish by server-side copy, catalog, dispose staging object. |

Firestore adds `artifactTransportReceipts` and
`artifactTransportUploadSessions`. Both use direct document lookup by request
ID; no composite index is required. The latter contains the private resumable
session URL and is reachable only through authenticated, owner-checked
operations. Retention cleanup is intentionally not automatic; explicit abort or
successful commit disposes staging bytes, and a future scheduled policy may
remove abandoned sessions only after a documented retention window.

## Measurements And Tests

Synthetic equal-latency staging fixture (four files, 80 ms each): serialized
`343 ms`; bounded concurrency four `91 ms`; measured speedup `3.77x`.
This proves scheduler behavior, not provider throughput. Candidate 001 live timings
were: accepted receipt `1.830 s`, queue-to-worker start `1.223 s`, input
resolution wall time `408 ms`, Blender execution `51,862 ms`, output upload
`10,003 ms`, and total renderer time `73,889 ms`.

Automated contracts cover metadata-only requests, small host staging, bounded
parallel multi-file ordering, interruption/resume, digest reuse, same/different
idempotency input, corrupt chunk, wrong length, unsupported/expired references,
schema disagreement, concurrent jobs, sibling failure isolation, and redacted
logs. The exact Candidate 001 preflight fixture resolves 720,363 bytes with zero
transfer; the existing 181,652,767-byte Drive ZIP resolves with zero transfer.

## Security And Privacy

Operational status strips authorization, signed/upload URLs, request bodies,
Base64, and raw bytes. Provider errors are bounded and field-specific. GCS and
Drive resolution use the existing service/user identities. Receipt reads are
owner checked; artifact operations remain credit-gated. Binary publication is
create-if-absent and digest verified. No SMS or unrelated user-data path changed.

## Compatibility And Archaeology

The merged Base64 chunk implementation remains only for small old clients. It
is not removed abruptly, but its advertised summary and hard cap now make the
migration explicit. Request-scoped render staging and blind output overwrite are
superseded by digest-addressed objects. Source-descriptor GitHub cache objects
remain valid locations and are adopted by preflight; they need not be recopied.
GitHub Actions quota exhaustion remains a separate retention/storage-policy
failure.

## Known Limitations

- Work Mode host attachment marshalling remains host-owned. Repository and live
  backend publish `settings.gifFrames` from the shared v2 contract, but this
  connected session still advertises a cached old top-level tool schema without
  `settings`. The stable dispatcher is verified; refreshing the host connector
  catalog requires a connector reconnect and cannot be forced by the service.
- A Drive URL still cannot inhabit a host `format: binary` slot. Durable Drive
  and GCS references must use preflight/the stable dispatcher instead of faking
  a host attachment.
- Drive exposes MD5 and byte length, not SHA-256. Preflight reports the
  repository-bound expected SHA and provider MD5 without claiming independent
  provider SHA verification.
- The local Termux runtime lacks ImageMagick `convert`; GIF encode/decode is
  verified in the Cloud Run image, which installs ImageMagick.
- Candidate 001 remains quarantined after transport execution until hosted
  visual Pose-is-God review accepts it.

## Rollback

Rollback uses existing revisions; do not create parallel resources. The immediate
traffic targets are `commandcentermcp-00071-fod`,
`homecentermcp-00140-wax`, and
`command-center-blender-render-00019-vfq`. Use:

`gcloud run services update-traffic SERVICE --to-revisions REVISION=100 --region us-central1 --project home-center-dclar`

A full queue rollback must remove both source-owned resources together after
routing Command Center to the pre-queue revision `commandcentermcp-00069-qin`:

`gcloud functions delete commandCenterRenderWorker --gen2 --region us-central1 --project home-center-dclar`
`gcloud tasks queues delete commandCenterRenderWorker --location us-central1 --project home-center-dclar`

Repository rollback is a normal revert. Existing immutable artifacts and
receipts remain readable; resumable sessions can be explicitly aborted. No
database migration must be reversed.

## Deployment And Live Proof

### Candidate 001

Preflight request `regnet-candidate-001-preflight-c107-ae64-v1` resolved the
GLB and script concurrently from their existing GCS objects: 720,363 bytes
reused, zero transferred. Render request
`regnet-candidate-001-transport-proof-async-v1` returned an accepted queued
receipt in 1.830 seconds with input hash
`e6f4cd4d83ce5969a252baa1a5cf84037b4bba4d190630f7c6cfba8508e2590b`.

The worker completed on execution attempt zero. Blender exit was zero and the
validation manifest preserved the exact source hashes `c1070777...a06b35` and
`ae64b5ae...4bcea`. Cache key:
`5ef0204dff92029110e88e23eb1b48bccb6963427f65d00bda30bb90691ec7c7`.
Evidence includes eight fixed-camera and eight orthogonal renders:

- manifest: `gs://home-center-generated/renders/blender/5ef0204dff92029110e88e23eb1b48bccb6963427f65d00bda30bb90691ec7c7/validation-manifest.json`;
- front: `gs://home-center-generated/renders/blender/5ef0204dff92029110e88e23eb1b48bccb6963427f65d00bda30bb90691ec7c7/fixed/0-locked-k000.png`;
- orthogonal: `gs://home-center-generated/renders/blender/5ef0204dff92029110e88e23eb1b48bccb6963427f65d00bda30bb90691ec7c7/diagnostic/0-orthogonal-k000.png`;
- contact sheet: `gs://home-center-generated/renders/contact-sheets/5ef0204dff92029110e88e23eb1b48bccb6963427f65d00bda30bb90691ec7c7/contact-sheet.png`.

Exact replay returned `attached=true`, the same cache key/input hash, unchanged
accept/start/complete timestamps, and `executionAttempt=0`. Cloud logs between
17:28Z and 17:45Z show one worker POST and one renderer POST only; replay caused
zero additional renderer calls and no binary transfer. Candidate 001 remains
`quarantined-pending-visual-review`; this is transport proof, not animation
acceptance.

### Large Durable Reference

Request `meshy-large-reference-proof-live-v1` resolved the existing
181,652,767-byte Drive ZIP in 270 ms as
`server-side-reference-reuse`: 181,652,767 bytes reused, zero transferred.
Drive byte length and MD5 matched; Drive does not expose SHA-256. Exact replay
returned `attached=true` with the same acceptance timestamp and input hash
`bbb4b85e076570b954f8324b5c4d27b4d6bc42d0bc3edf379505d8eb503c4e7c`.

### Remote Resource Closure

All four intended services have 100% traffic on the revisions listed under
Authorities. Both readiness endpoints are green. The queue is RUNNING. Cloud
Run job count is zero. The post-deploy service count increased only by the
source-owned `commandcenterrenderworker`; no temporary service, job, queue,
bucket, or proof deployment remains. The worker and queue are deployment-script
owned and have paired rollback instructions above.
