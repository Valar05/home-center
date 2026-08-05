# THECAULDRON local voice farm preflight

This directory implements the reversible on-machine preflight for Home Center issue
[#185](https://github.com/Valar05/home-center/issues/185). It does **not** install a
service, expose a port, register a Home Center provider, or change voice tiers.

The preflight benchmarks three candidate lanes:

- Kokoro-ONNX on CPU for fixed-voice utility and accessibility speech;
- Chatterbox Nano on CPU for consented reference-voice speech;
- Chatterbox Turbo as an explicit single-owner CUDA feasibility test.

F5-TTS remains research-only. Every render makes its own split plan, preserves ordered
segments, writes immutable hashes and metrics, and leaves human listening approval to
Drew. Chatterbox refuses to load without a reference file plus an exact-hash consent
record permitting `local_tts_clone`.

## Cauldron commands

```powershell
./local/cauldron_voice_farm/install.ps1
./local/cauldron_voice_farm/control.ps1 status
./local/cauldron_voice_farm/run_canaries.ps1
```

Consented Nano or Turbo trials add `-ReferenceAudio`, `-ConsentRecord`, and either
`-IncludeNano` or `-IncludeTurbo`. Turbo is never selected implicitly.

```json
{
  "schemaVersion": "home-center.voice-consent.v1",
  "speakerOwner": "Represented adult",
  "consentAuthority": "Consenting authority",
  "permittedUses": ["local_tts_clone"],
  "referenceSha256": "lowercase sha256 of the reference WAV"
}
```

Pause, recovery, and guarded removal:

```powershell
./local/cauldron_voice_farm/control.ps1 pause
./local/cauldron_voice_farm/control.ps1 resume
./local/cauldron_voice_farm/control.ps1 uninstall -Approved
```

All environments, models, caches, receipts, and outputs remain beneath
`%LOCALAPPDATA%\HelmCenter\cauldron-voice-farm`. No public or LAN listener is created.
The next phase may connect an accepted engine to Home Center; this preflight does not
claim implementation of that provider or deployment on THECAULDRON.
