# Pocket TTS local runtime

Pocket TTS is the bounded local speech conductor. It does not replace the already accepted phone Pocket Space reader or the proven THECAULDRON Venice Pocket-TTS stream. It gives those and later approved engines one inspectable product shell.

## Current source slice

- one loopback-only service;
- persistent, separate synthesis and playback worker threads;
- `speak`, `stop`, and `status` control loop;
- deterministic text normalization and lossless sentence-aware chunking;
- playback starts after the first chunk rather than waiting for the full utterance;
- SHA-256-bound WAV cache with atomic per-chunk manifests;
- receipts for TTFA, total time, render time, RTF, cache hits, glitches, worker liveness, and streaming order;
- local Piper and Kokoro-ONNX adapters only;
- no caller-supplied command, hosted voice, cloud fallback, or default cloud mouth.

The implementation also exposes `render`, `pause`, `resume`, `voices`, and `benchmark`, but this slice claims only deterministic source/unit coverage for `speak`, `stop`, `status`, TTFA, offline identity, and cache reuse. Physical playback and pause/resume require their own host receipts.

## Engine policy

1. Piper is the intended utility/fallback tier. No Piper voice is activated until its exact model bytes, model license, source, and SHA-256 enter the registry.
2. Kokoro-ONNX is the expressive companion/narration tier. The current registry reuses the already pinned Kokoro v1 model and voice bank; the entries are not Venice identity claims.
3. RealtimeTTS is an orchestration reference, not a dependency or authority owner.
4. Coqui XTTS remains experimental and is deliberately rejected by the production registry parser.
5. Hosted TTS is never Adam's default mouth. Every accepted profile must be local, licensed, provenance-linked, and hash pinned.

## Run the source candidate

Set `HOME_CENTER_LOCAL_VOICE_ROOT` to the verified Kokoro worker root containing `models/kokoro-v1.0.onnx` and `models/voices-v1.0.bin`, then start the foreground service:

```sh
python tools/pocket_tts_runtime.py serve
```

In another local process:

```sh
python tools/pocket_tts_runtime.py speak --voice companion-kokoro-heart "Fortress interface ready."
python tools/pocket_tts_runtime.py status
python tools/pocket_tts_runtime.py stop
```

The server binds only `127.0.0.1:10206`, mints a mode-0600 bearer token, and accepts a fixed command vocabulary. It has no installer, boot persistence, or remote phone path in this source slice.

## Proof boundary

- Existing Pocket TTS/Pocket Space artifacts and historical receipts prove their exact prior runs only.
- Unit tests use an owned synthetic PCM fixture and prove orchestration behavior without network access.
- Repository source does not prove this new service installed, boot-persistent, physically audible, phone-callable, or human accepted.
- The next gate is an exact-head THECAULDRON canary using the already pinned Kokoro assets, followed separately by a reviewed phone adapter rather than waking or bypassing Phone Hands.
