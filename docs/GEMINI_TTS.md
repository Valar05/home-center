# Gemini Flash TTS provider

Home Center exposes `gemini-3.1-flash-tts-preview` through the existing `drive_operation` names `tts.voices`, `tts.synthesize`, and `audio.render`. It does not add a top-level MCP tool.

The authorized live lane is:

```text
ChatGPT -> Home Center MCP -> tts.synthesize/audio.render -> Gemini API
        -> Home Center deterministic PCM16 processor -> verified durable artifact
```

Gemini calls are synchronous inside the authenticated Home Center MCP request. They never enter Command Center, a Codex worker, the audio-render queue, a lease, GitHub Actions, an OpenAI API call, or a substitute browser/runtime lane. Existing Cartesia calls retain their prior route. `provider:"auto"` keeps Cartesia as the compatibility default and selects Gemini only when Gemini-only direction or expressive-tag features are declared. No provider failure silently changes providers.

`tts.voices` accepts `provider:"gemini"`, `provider:"cartesia"`, or `provider:"auto"`. Gemini returns the official named-voice catalog plus a live model availability probe. Cache output always includes TTL, age, `cacheState`, and `stale`; a failed refresh returns visibly stale data and its stable error code.

`tts.synthesize` accepts exact `text`, `voiceName`, natural-language `direction`, `speaker`, `segments`, `pauseMs`, `format`, and a stable `requestId`. Supported expressive tags are returned by `tts.voices`; unknown bracket tags fail closed. Gemini PCM is accepted only as mono signed 16-bit little-endian at 24 kHz and is rejected when empty, odd-length, too short, or silent. Home Center creates deterministic PCM silence, stitching, and WAV headers, then verifies every checkpoint and final Drive artifact by byte count and SHA-256 readback.

Each Gemini sequence segment uses a stable content hash and produces a verified checkpoint receipt before the next segment. A final sequence is published only after every segment and final byte validation succeeds. Audit receipts include exact transcript and transcript hash, provider/model/voice, direction hash, expressive tags, duration, latency/retry attempts, provider usage when supplied, public-price cost estimate, deterministic processor identity, checkpoint references, and excluded-lane flags. Infrastructure summaries omit dialogue and secrets.

Provider automation is bounded by request size, sequence count, provider concurrency, request timeout, transient-only retry with bounded exponential backoff and `Retry-After`, a Firestore daily soft-budget reservation, and a Firestore circuit opened only by real transient synthesis outcomes. Missing secret, quota/budget refusal, provider refusal, malformed audio, silence, or any readback mismatch fails closed.

Gemini `audio.render` recipes set `provider:"gemini"` on `speech` or `speech_sequence` nodes. These recipes bypass the legacy asynchronous audio queue and execute directly without a lease. Deterministic DSP and canonical artifact/readback/Reader registration remain unchanged.

Failure receipts use stable codes and plain fields for what failed, preserved progress, possible provider usage, whether a retry is sensible, recovery reference, and one safe next action. Retry with the same request ID; never invent a new ID to bypass ambiguous billing state.
