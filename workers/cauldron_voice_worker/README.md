# Cauldron local voice worker — fixed-voice pilot

This package is the outbound-only Windows worker for Home Center issue #185. The pilot installs Kokoro-ONNX in a user-owned directory, verifies the model and voice bundle by SHA-256, and renders only the fixed `af_heart` utility voice. It does **not** claim to be Venice and does not enable cloning.

## Boundary

- Home Center creates and verifies immutable tickets and artifacts.
- Cauldron polls one configured Home Center HTTPS origin; it opens no inbound port.
- Every render is losslessly split, checkpointed in order, and bound to the input hash.
- Cloud speech fallback is forbidden.
- Worker installation does not create an always-on service. Persistence waits for the real canary, pause/resume, thermal, responsiveness, and human listening gates.
- Discord is downstream transport. Pycord 2.8+ is the candidate outbound DAVE lane; microphone receive is a separate unproved gate.

## Install and verify on Cauldron

Run `bootstrap.ps1` from a checked-out reviewed commit. Then set `HOME_CENTER_LOCAL_VOICE_ORIGIN` and `HOME_CENTER_LOCAL_VOICE_TOKEN` in the launching shell and run:

```powershell
& "$env:LOCALAPPDATA\Ferravine\VoiceWorker\v1\.venv\Scripts\python.exe" "$env:LOCALAPPDATA\Ferravine\VoiceWorker\v1\worker.py" --verify
```

The verification command proves package/model identity only. A live Helm Center ticket and returned WAV are still required before the worker is callable or delivered.

## Fixed canary pack

1. `Fortress interface ready.`
2. One ordinary dialogue line.
3. One long input that forces multiple segments and exact ordered stitching.

Venice auditions begin only after an allowlisted consent/provenance profile exists and the fixed-voice transport is proven.

## Primary evidence

- Kokoro-ONNX source: https://github.com/thewh1teagle/kokoro-onnx
- Kokoro source/model license: https://github.com/hexgrad/kokoro
- Discord DAVE requirement: https://discord.com/blog/bringing-dave-to-all-discord-platforms
- Pycord 2.8 outbound DAVE release: https://github.com/Pycord-Development/pycord/releases/tag/v2.8.0
