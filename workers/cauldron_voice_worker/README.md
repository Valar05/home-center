# THECAULDRON local voice worker — fixed-voice pilot

This package is the outbound-only Windows worker for Home Center issue #185. It installs Kokoro-ONNX in a user-owned directory, verifies model and voice bytes by SHA-256, and renders only the fixed `af_heart` utility voice. It is not Venice and cloning is disabled.

## Proven boundary

- Helm Center creates owner-scoped immutable tickets and verifies every returned artifact.
- THECAULDRON polls one configured Helm Center HTTPS origin and opens no inbound port.
- Each render is split losslessly and checkpointed in order.
- A restarted worker downloads any server-verified checkpoint missing from its local cache.
- Cloud speech fallback is forbidden.
- Final WAV completion requires GCS byte/hash readback, authenticated Audio Reader discovery, and a bounded playback header probe.
- Installation creates no service or scheduled task. Persistence waits for the real canary, pause/resume, thermal, responsiveness, and human listening gates.
- Discord remains downstream transport. DAVE outbound playback and microphone receive are separate unproved gates.

## Helm Center preparation

Through the stable `drive_operation` dispatcher:

1. Call `local_voice.worker.register` with a stable `requestId` and `workerId=cauldron-voice-01`.
2. Call `local_voice.ticket.create` for the exact canary text `Fortress interface ready.`.
3. Keep the returned one-time bootstrap code private. It expires after ten minutes and cannot be reused.

## Install and register on THECAULDRON

From a checkout of the reviewed PR commit, run PowerShell as Drew's ordinary Windows user:

```powershell
.\workers\cauldron_voice_worker\bootstrap.ps1 -BootstrapCode "<one-time-code>"
```

The bootstrap:

- installs under `%LOCALAPPDATA%\Ferravine\VoiceWorker\v1`;
- creates a Python 3.12 virtual environment;
- downloads only the pinned Kokoro model files;
- verifies both model hashes;
- exchanges the one-time code directly with Helm Center;
- ACL-locks the resulting worker token;
- performs `worker.py --verify`;
- creates no service, scheduled task, inbound listener, cloud fallback, or clone profile.

## Run the audible canary

After the ticket exists:

```powershell
& "$env:LOCALAPPDATA\Ferravine\VoiceWorker\v1\run-once.ps1"
```

Then call `local_voice.ticket.status`. Completion is proved only when the response contains:

- `status=completed`;
- provider `local_cauldron`, engine `kokoro-onnx`;
- matching final WAV byte count and SHA-256 readback;
- authenticated Reader discovery;
- `playback.ok=true`;
- `humanAcceptance=unreviewed`.

## Fixed canary pack

1. `Fortress interface ready.`
2. One ordinary dialogue line.
3. One long input that forces multiple segments and exact ordered stitching.
4. Kill/restart during a multi-segment render and verify the worker downloads completed checkpoints instead of resynthesizing them.

Venice auditions begin only after a separate consent/provenance profile exists and Drew accepts an actual candidate performance.

## Primary evidence

- Kokoro-ONNX: https://github.com/thewh1teagle/kokoro-onnx
- Kokoro model: https://github.com/hexgrad/kokoro
- Discord DAVE: https://discord.com/blog/bringing-dave-to-all-discord-platforms
- Pycord 2.8: https://github.com/Pycord-Development/pycord/releases/tag/v2.8.0
