# Artifact Bucket Architecture

Home Center uses Cloud Storage as the canonical store for generated machine artifacts. Google Drive remains the curated human library for Holocrons, documentation, approvals, canon, and intentionally published files.

## Ownership

- Source code belongs in Git.
- Knowledge belongs in Drive.
- Generated artifacts belong in `gs://home-center-generated`.
- Drive is a publishing destination, not a render cache.
- Generated artifacts should be reproducible from source whenever practical.

## Bucket

Canonical bucket: `gs://home-center-generated`

Provision with `tools/setup_generated_artifact_bucket.sh`. The script enables Storage, creates the bucket when missing, and enforces:

- versioning enabled;
- uniform bucket-level access;
- public access prevention;
- lifecycle rules;
- object metadata preservation;
- per-object hashes in metadata and receipts.

Cloud Storage already stores object checksums. Home Center also records SHA-256 in custom metadata and verifies readback hashes for generated artifacts.

## Layout

```text
home-center-generated/
  audio/
    drew/
      narration/
      voice-tests/
      characters/
      final/
    june/
      narration/
      voice-tests/
      characters/
      final/
    shared/
  renders/
    blender/
    contact-sheets/
    gifs/
  images/
  glb/
  video/
  logs/
  temp/
```

Temporary render inputs and staging files use `temp/`. Blender logs use `logs/`. Rendered frames and bundle manifests use `renders/blender/`; contact sheets and GIFs use their own render subtrees.

## Lifecycle

Bucket lifecycle is automatic. Do not manually clean temporary render caches.

- `temp/`: delete after 7 days.
- `audio/drew/voice-tests/`, `audio/june/voice-tests/`, `audio/shared/voice-tests/`: delete after 30 days.
- `logs/`: delete after 14 days.
- `final/`: retained.

## Metadata Contract

Every generated artifact must include custom metadata with this shape or a strict superset:

```json
{
  "owner": "authenticated@example.com",
  "ownerEmail": "authenticated@example.com",
  "project": "fleshpunk",
  "stage": "review",
  "engine": "cartesia",
  "createdBy": "home-center-mcp",
  "jobId": "...",
  "commit": "...",
  "timestamp": "...",
  "executionAuthorized": "true",
  "authorizationState": "owner_scoped",
  "humanAcceptance": "unreviewed",
  "sha256": "...",
  "byteCount": "..."
}
```

Workflow state must not live only in filenames. Filenames may be human-readable, but receipts, manifests, and object metadata are the durable authority.

## Publishing Flow

```text
request
  -> Home Center or Command Center
  -> Cloud Storage generated bucket
  -> validation and readback hash check
  -> register owner-scoped review artifacts in the authenticated Reader
  -> keep human acceptance separate as unreviewed until a verdict exists
  -> if explicitly requested: publish a Drive copy
  -> return GCS identity plus private Reader delivery evidence
```

Renderers and audio generators must not write directly to Drive as their primary output. Drive upload is a publish step after Cloud Storage readback succeeds.

For backward compatibility, `audio.render` can still return a Drive `resource_link` when explicitly requested, but its canonical identity is the `gs://` object and its completion gate is private Audio Reader registration, discovery, and playback.

## Permissions

- Drew: bucket administration.
- Home Center and Command Center service accounts: scoped object write/read needed for generation and verification.
- Workers/renderers: scoped object write/read for their execution lane.
- Public: no access.

Do not make generated artifact buckets public. Human consumption should use Drive-published artifacts or explicitly authorized download flows.

## Implementation Owners

- `functions/artifact_bucket.js`: canonical GCS upload, metadata, readback verification, and Drive publish helper.
- `functions/audio_render_service.js`: audio artifacts write to GCS first and complete only after Reader registration.
- `functions/audio_catalog_service.js`: receipt-only, owner-scoped Audio Reader registration, byte-preserving metadata repair, discovery, and playback probes.
- `functions/home_center_mcp.js`: top-level render file staging uses the generated bucket.
- `functions/command_center_mcp.js`: Command Center render upload staging uses the generated bucket.
- `cloud-render/src/render_bundle.mjs`: Blender bundles, frames, contact sheets, GIFs, logs, GLBs, manifests, and hashes write to the generated bucket layout.
- `tools/setup_generated_artifact_bucket.sh`: live bucket creation and lifecycle configuration.

Digest-addressed immutable render inputs use `artifacts/sha256/<sha256>/<filename>`. Request-scoped `temp/render-inputs` paths are legacy cache locations only; new host staging reuses exact bytes by digest.
