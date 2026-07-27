# SFX source ingestion

Home Center preserves original Foley and other sound-source recordings through the existing `drive_operation` entry point. This is acquisition and provenance, not sound generation or artistic acceptance.

## Operation

Call `audio.ingest_drive` with `approved: true`, a stable `requestId` and `batchId`, and `stage: "sources"`.

Source-stage ingestion additionally requires:

- `sourceKind`: `foley_recording`, `generated`, `licensed`, `public_domain`, or `unknown`
- `creator`: the source creator or recorder
- `rightsBasis`: `self_recorded`, `commissioned`, `licensed`, `public_domain`, or `unknown`

Optional capture and annotation fields are `captureDevice`, `captureApp`, `recordedAt`, `annotationStatus`, `semanticAuthority`, and `sourceNotes`.

For recordings that contain spoken slate labels, use:

```json
{
  "operation": "audio.ingest_drive",
  "args": {
    "approved": true,
    "fileId": "<drive-file-id>",
    "requestId": "<stable-request-id>",
    "batchId": "<stable-batch-id>",
    "project": "sfx-armory",
    "stage": "sources",
    "sourceKind": "foley_recording",
    "creator": "<recorder>",
    "rightsBasis": "self_recorded",
    "annotationStatus": "embedded_spoken_labels_unparsed",
    "semanticAuthority": "source_audio"
  }
}
```

## Contract

The operation streams the Drive object to temporary GCS storage, hashes it while streaming, verifies the staging readback, creates an immutable canonical `audio/.../sources/...` object, verifies the canonical readback, and writes immutable by-Drive-ID, catalog, and batch-item indexes. The Drive source is never changed.

A source-stage index uses `home-center.audio-index.v2` and binds the declared provenance and annotation state into the immutable identity. Identical replay attaches. Conflicting provenance for the same canonical source fails closed.

`semanticAuthority: "source_audio"` means later segmentation must listen to and transcribe the recording rather than inventing the event order from chat memory. `annotationStatus: "embedded_spoken_labels_unparsed"` means the labels exist in the recording but have not yet been converted into an event manifest.

Call `audio.finalize_ingest_batch` after every expected item is verified. Sealing proves bytes and inventory only; it does not grant playback, quality, or human artistic acceptance.

## Boundaries

- Original source bytes remain immutable.
- Cleanup, trimming, denoising, decomposition, and generation create descendants; they never replace the source.
- Source ownership and license evidence are catalog data, not inferred from filenames.
- Human acceptance remains separate from mechanical verification.
