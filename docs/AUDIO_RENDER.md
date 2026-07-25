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

The operation uploads every output to Drive, reads it back, verifies byte count and SHA-256, records source and output metadata, and returns a structured MCP `audio` block for the primary audio output so ChatGPT can play it inline.
