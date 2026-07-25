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

The operation uploads every output to Drive, reads it back, verifies byte count and SHA-256, records source, speech, take, and output metadata, and returns a structured MCP `audio` block for the primary audio output so ChatGPT can play it inline.
