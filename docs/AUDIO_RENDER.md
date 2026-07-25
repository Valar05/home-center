# Home Center Audio Render

`audio.render` is a direct Home Center MCP provider operation exposed through the existing `drive_operation` dispatcher. It exists so ChatGPT can render deterministic sound effects, beds, stems, waveform PNGs, spectrogram PNGs, and verified audio artifacts without a connector schema refresh.

Runtime boundary:

```text
ChatGPT
  -> Home Center MCP drive_operation(operation="audio.render")
  -> Home Center deterministic audio renderer
  -> verified Drive artifacts plus structured MCP audio content
```

The renderer must not create Command Center jobs, Codex executions, LLM prompts, worker leases, GitHub Actions renders, or Termux runtime processes. The submitted `scriptText` is a declarative JSON audio recipe. It is not Python or JavaScript, and it cannot import modules, call the shell, open network sockets, read credentials, or access arbitrary filesystem paths.

The first production renderer is `home-center-deterministic-audio-v1`, implemented in `functions/audio_render_service.js`. It uses fixed in-process DSP primitives for synthesis, layering, timeline placement, analysis, waveform PNGs, and spectrogram PNGs. Encoded OGG/MP3/FLAC exports use the pinned production dependency `ffmpeg-static` via argument-array process invocation; dependencies are installed at deployment/build time, not during a render.

Speech is a recipe source, not a separate worker path. A `speech` node calls the existing Home Center Cartesia provider directly, resolves canonical character profiles such as Isaac/Clyde when requested, forwards structured Cartesia `generation_config` controls for supported emotion, speed, and volume, then applies the existing tempo-preserving Cartesia pitch processor before returning an ordinary clip for trimming, layering, effects, stems, and export. An `audition` node creates separate Cartesia generation contexts for each requested emotion and registers each take as an individually exportable clip.

Supported Cartesia speech controls in recipes: `text`, `character` or explicit `voiceName`/`voiceId`, `modelId`, `emotion`, `speed`, `volume`, `pitchSemitones`, optional `label`, and optional take naming. Isaac resolves to `Clyde - Calm Narrator`, voice id `98a34ef2-2140-4c28-9c71-663dc4dd7022`, model `sonic-3.5`, speed `0.97`, and pitch `-1.5` semitones unless a call-level override is supplied. Emotional controls are provider requests and remain subject to human listening judgment; Home Center records what was requested and what artifact was returned, but does not claim a perceived emotion.

The operation uploads every output to Drive, reads it back, verifies byte count and SHA-256, records source, speech, take, and output metadata, and returns a structured MCP `audio` block for the primary audio output so ChatGPT can play it inline. `audio.render_artifacts` can also perform a server-side decode check using the authorized Drive readback path and the deployed FFmpeg runtime for encoded audio.

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

`audio.render` persists a `running` audit state before provider calls begin and writes completion before constructing optional inline content. If a client times out or rejects optional inline media, call `drive_operation(operation="audio.render_status", args={"requestId":"..."})` or retry the exact same `audio.render` request. The same request ID with identical normalized input returns the completed receipt without invoking Cartesia or writing Drive again. Reusing the request ID with different normalized input fails as an idempotency conflict.

`speech_sequence` applies a documented mastering default: peak limiting at about -1 dB with no tempo change. Callers may override `master.limitDb`, but the default exists so raw stitched speech does not clip by accident. Numeric peak, LUFS, and clipping metrics are verification data only; human listening remains the authority for casting and emotional performance.
