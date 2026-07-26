# Home Center Audio Render

`audio.render` is a direct Home Center MCP provider operation exposed through the existing `drive_operation` dispatcher. It exists so ChatGPT can render deterministic sound effects, beds, stems, waveform PNGs, spectrogram PNGs, and verified audio artifacts without a connector schema refresh.

Runtime boundary:

```text
ChatGPT
  -> Home Center MCP drive_operation(operation="audio.render")
  -> accepted receipt with requestId/inputSha256/statusOperation
  -> Home Center async audio worker
  -> verified GCS artifacts
  -> optional Drive publish step only when publishToDrive is true or policy requests publication
```

The renderer must not create Command Center jobs, Codex executions, LLM prompts, GitHub Actions renders, or Termux runtime processes. Long-form work is tracked as a Home Center audio render job with audit state, lease/heartbeat metadata, progress checkpoints, and status polling. The submitted `scriptText` is a declarative JSON audio recipe. It is not Python or JavaScript, and it cannot import modules, call the shell, open network sockets, read credentials, or access arbitrary filesystem paths.

The first production renderer is `home-center-deterministic-audio-v1`, implemented in `functions/audio_render_service.js`. It uses fixed in-process DSP primitives for synthesis, layering, timeline placement, analysis, waveform PNGs, and spectrogram PNGs. Encoded OGG/MP3/FLAC exports use the pinned production dependency `ffmpeg-static` via argument-array process invocation; dependencies are installed at deployment/build time, not during a render.

Speech is a recipe source, not a separate worker path. A `speech` node calls the existing Home Center Cartesia provider directly, resolves canonical character profiles such as Isaac/Clyde when requested, forwards structured Cartesia `generation_config` controls for supported emotion, speed, and volume, then applies the existing tempo-preserving Cartesia pitch processor before returning an ordinary clip for trimming, layering, effects, stems, and export. An `audition` node creates separate Cartesia generation contexts for each requested emotion and registers each take as an individually exportable clip.

Supported Cartesia speech controls in recipes: `text`, `character` or explicit `voiceName`/`voiceId`, `modelId`, `emotion`, `speed`, `volume`, `pitchSemitones`, optional `label`, and optional take naming. Isaac resolves to `Clyde - Calm Narrator`, voice id `98a34ef2-2140-4c28-9c71-663dc4dd7022`, model `sonic-3.5`, speed `0.97`, and pitch `-1.5` semitones unless a call-level override is supplied. Emotional controls are provider requests and remain subject to human listening judgment; Home Center records what was requested and what artifact was returned, but does not claim a perceived emotion.

The operation uploads every output to `gs://home-center-generated` first, reads it back, verifies byte count and SHA-256, records source, speech, take, and output metadata, then publishes a Drive copy when requested or needed for existing ChatGPT resource-link clients. `audio.render_artifacts` can verify canonical `gs://` refs and legacy published `drive://` refs, including server-side decode checks through the deployed FFmpeg runtime for encoded audio.

## Long-Form Speech Sequences

Use `speech_sequence` for attributed audiobook/dialogue passages that must remain one mastered artifact:

```json
{
  "operation": "audio.render",
  "args": {
    "requestId": "scene-longform-v1",
    "returnInlineAudio": false,
    "settings": {"speechConcurrency": 3, "timeoutMs": 600000},
    "scriptText": "{\"sampleRate\":24000,\"graph\":[{\"id\":\"scene\",\"op\":\"speech_sequence\",\"pauseMs\":120,\"master\":{\"limitDb\":-1},\"segments\":[{\"speaker\":\"Stasya\",\"character\":\"Stasya\",\"text\":\"Exact text.\"},{\"speaker\":\"Isaac\",\"character\":\"Isaac\",\"emotion\":\"hurt\",\"text\":\"Exact reply.\"}]}],\"final\":\"scene\",\"outputs\":[{\"name\":\"scene.ogg\",\"format\":\"ogg\",\"clip\":\"scene\"}]}"
  }
}
```

`speech_sequence` preserves submitted order and speaker ownership exactly. It does not infer, combine, reassign, summarize, or simplify speakers. Each segment must provide `speaker` plus either `character` or explicit `voiceId`/`voiceName`; unresolved ownership fails before rendering. The renderer records per-segment provenance including index, speaker, character, resolved voice, model, requested emotion, speed, volume, pitch, submitted and normalized character counts, provider byte count, provider timing, and resulting duration.

Canonical profiles resolve aliases case-insensitively:

| Character | Voice | Voice ID | Model | Speed | Pitch | Direction |
| --- | --- | --- | --- | ---: | ---: | --- |
| Stasya | Milena - Composed Clarifier | `b66b3a19-31b3-401f-8b08-40d46a61e4f1` | `sonic-3.5` | 1.08 | 0 | Cultivated, intimate, dry, playful, capable of hard authority; not a heavy Bond-style Russian accent. |
| Isaac | Clyde - Calm Narrator | `98a34ef2-2140-4c28-9c71-663dc4dd7022` | `sonic-3.5` | 0.97 | -1.5 | Controlled American mentor; technical, dry, protective; deep without gravel. |
| Eve | Jacqueline - Reassuring Agent | `9626c31c-bec5-4cca-baa8-f8ba9e84c8bc` | `sonic-3.5` | 1.0 | 0 | Warm and composed, observant restraint, emotionally aware without becoming syrupy. |

Explicit segment settings override canonical profile values and are recorded in the manifest. Isaac's pitch is applied by the existing tempo-preserving post-Cartesia pitch processor.

## Long-Form Limits And Recovery

Production defaults support at least 900 seconds per final clip and up to 240 `speech_sequence` segments. A ten-minute mono 24 kHz render is roughly 28.8 MB of PCM before encoding. OGG is the recommended long-form delivery format; WAV uses a separate 64 MB safety ceiling while encoded outputs use a 24 MB ceiling. Inline audio content is size-bounded and skipped above the inline limit, so long-form callers should set `returnInlineAudio: false` and treat the textual receipt plus `resource_link` and Drive readback verification as authoritative.

Speech sequence synthesis uses bounded Cartesia concurrency. `settings.speechConcurrency` or `speech_sequence.concurrency` may tune it, with a conservative default of 3 and a hard cap of 8. Provider calls may complete out of order, but the final clip and segment provenance are stitched in submitted order. Any required segment failure fails the whole sequence; Home Center does not upload a partial final artifact as success.

`audio.render` now returns promptly with an accepted receipt instead of holding the connector request open for long synthesis or encoding. The receipt includes `requestId`, `idempotencyKey`, `inputSha256`, current `status`, progress, lease metadata when available, and `statusOperation: {operation:"audio.render_status", args:{requestId}}`. The async worker performs synthesis, mixing, encoding, verification, and artifact publication outside the connector response path.

The same request ID with the same canonical input hash attaches to the existing queued/running/completed job and must not invoke Cartesia or write artifacts again. The same request ID with a different canonical input hash fails as an idempotency conflict. `publishToDrive:false` is a hard policy boundary: audio outputs, previews, manifests, and compatibility resource links remain GCS-only and are not copied to Drive.

Status may be `queued`, `running`, `completed`, `failed`, or `stalled`. A stale `running` job whose heartbeat expires becomes `stalled`; Home Center does not silently retry paid synthesis after an ambiguous provider failure. Operators must inspect checkpoints and provider evidence before resuming or quarantining affected takes.

`speech_sequence` applies a documented mastering default: peak limiting at about -1 dB with no tempo change. Callers may override `master.limitDb`, but the default exists so raw stitched speech does not clip by accident. Numeric peak, LUFS, and clipping metrics are verification data only; human listening remains the authority for casting and emotional performance.


## Incident: Nine Below 2026-07-25

Production request `fleshpunk-nine-below-final-v1-20260725` for Fleshpunk -- Nine Below timed out at the connector while the deployed synchronous renderer had only written its initial audit row. The deployed audit document records `status=running`, `inputSha256=70bb7f8753bc18b3c33bc29906f22ee212368a852d96a2b71a7e3ff3f67672c1`, no result, no affected Drive file ids, and no affected GCS refs. No matching `gs://home-center-generated` object was found for the final request id during reconciliation. Because that old lane did not persist per-take provider checkpoints, the charge-safe classification is stalled/quarantined until provider-side evidence is reviewed; do not resubmit the 187-take production request under a new idempotency key.


## Canonical Source Reuse Doctrine

A verified generated artifact must be reusable directly from its canonical `gs://home-center-generated/...` durable ref. Deterministic downstream work must not detour through a Drive publication copy merely because Drive is convenient for human playback.

Rules:

- GCS is the canonical render store; Drive publication is a delivery surface, not a render cache.
- A source-backed render binds the exact durable ref and expected SHA-256. Only the configured generated-artifact bucket is readable through `audio.render`; arbitrary buckets and network URLs remain forbidden.
- Paid or accepted speech is checkpointed as an immutable source artifact. Mixing, encoding, publication, indexing, and recovery reuse that artifact and must never resynthesize speech to repair a downstream failure.
- Long source materialization and deterministic recipe rendering must emit lease heartbeats and progress. A static phase label without a current heartbeat is not evidence of healthy work.
- A stale or ambiguous request is quarantined under its original idempotency key. Recovery uses a new deterministic source-only request only after proving that no paid provider operation can be repeated.
- Long-form speed comes from bounded speech concurrency, larger truth-preserving scene boundaries, canonical source reuse, and memory-bounded mix graphs—not from duplicate submissions or continuous ambience wallpaper.

This doctrine was promoted after the Chapter 1 Scenes Five–Six production exposed a 40.8 MB Drive-source materialization detour. The accepted speech completed quickly and remained valid; only deterministic post-production required repair.

### Production evidence and next throughput boundary

The first live canonical-source recovery, `vacation-day1-scenes5-6-coastal-road-through-royal-cove-soundscape-v2-20260726`, reused the verified 40,772,934-byte narration WAV by its allowlisted GCS ref and expected SHA-256. Canonical materialization completed in about 24 seconds, the lease remained current throughout deterministic rendering, and the final 14:09.435 stereo OGG published with matching GCS/Drive hashes and successful independent decode checks. The recipe contained zero speech nodes, so recovery could not incur a second Cartesia charge.

That run also established the next honest performance boundary: a 14:09 timeline required about 16:03 end to end even after source transfer was repaired. The in-memory mix graph, encoding, and publication path—not speech synthesis or canonical retrieval—now dominate long-form latency. The next renderer optimization should therefore be a bounded block/streaming mixer with phase timing in the manifest. Artifact publication must also renew the lease or emit explicit sub-phase checkpoints; a completed render sitting in `publishing_artifacts` must not become operationally ambiguous.
