# Ritsu registered voice repertoire, 2026-10-22

## Authority and scope

Home Center voice identity is versioned in `functions/ritsu_voice_profiles.json`. The catalog was reconstructed from the actual Windows `C:\Users\dclar\workspace\ritsu-voice-repertoire\repertoire-manifest.json` plus `emotion-batch.py` used to produce the upset and somber auditions. Local voice reference WAVs remain exclusively on THECAULDRON, not in GitHub or Firebase. A worker must use the registered IDs and reference texts, not discover or invent settings.

The cloud operation `ritsu.voice.profiles` lists profile names, pitch shifts and approval statuses; `ritsu.voice.speak({requestId,text,voice:'warm-v1',delivery:'phone',profile})` carries the selected profile on each ticket. Default profile is `normal` (approved -1 semitone). `profile` is selected independently of `voice` so the transport and engine contract remain immutable.

| Profile | Qwen reference | Pitch (semitones) | Status |
| --- | --- | ---: | --- |
| normal | ex04_happy_00085.wav | -1 | approved; everyday default |
| whisper | ex04_whisper_00059.wav | -1 | approved whisper audition, lowered candidate |
| amused | ex04_laughing_00044.wav | -1 | approved amusing reference chosen in final audition |
| happy | ex04_happy_00112.wav | -1 | approved delighted option 2 |
| upset | ex04_confused_00043.wav | -1 | provisional, user asked to include |
| somber | ex04_sad_00037.wav | -1 | rework later, user asked to include |

The original `warm` local reference remains as rollback. Do not remove it or replace its files. No new voice is silently generated or trained.

## Artifact mapping

- **Cloud catalog:** `functions/ritsu_voice_profiles.json`
- **Cloud ticket API:** `functions/ritsu_voice_api.js`
- **Cloud tests:** `functions/ritsu_voice_api.test.js`
- **Windows worker source:** `workers/ritsu_warm_ticket_worker.py` (currently installed worker may still be the earlier in-memory code)
- **Staged repertoire-aware API:** `tools/campaigns/ritsu_voice_api_repertoire_v1.py`
- **Staged sender:** `tools/campaigns/ritsu_say_repertoire_v1.py`
- **Local stage directory:** `%LOCALAPPDATA%\RitsuWarmTicketWorker\staged-repertoire`

## Activation gates

The ASMR session owns the GPU until explicit clearance. Keep `RITSU_WARM_ASMR_MAINTENANCE` in place. Never auto-start Qwen, change the current running model or overwrite the active `ritsu_voice_api_warm_v1.py` while ASMR is working.

Before audible activation: verify cloud deployment and `ritsu.voice.profiles` capability readback; confirm staged source SHA/compilation and presence of all six reference WAVs; back up active API and sender; install both staged scripts together while voice worker is paused; ensure exactly one API listener and worker, and choose explicit restart only with user clearance; send short tagged sample, check relay ACK and get user HEARD confirmation. Worker queues and Windows reboot persistence still need separate verification. MAINTENANCE is a successful silent gate, not proof of audio playback.

## Revision notes

The repertoire includes upset and somber at user request despite their unfinished quality. Approval status is metadata, not a prohibition: the caller may deliberately choose either profile.

## Cloud deployment blocker, confirmed at 2026-10-22 22:18 UTC

**Source registration is complete; live rollout is not.** The compiled six-profile cloud contract cannot yet be advertised by the currently running Home Center MCP because the updated `ritsuVoice` Cloud Function fails its Google Cloud Run startup check. The old healthy `ritsuvoice-00001-moy` continues to serve the pre-repertoire typed API. Do **not** claim `ritsu.voice.profiles` live or clear the ASMR safeguard. Re-running the current deploy workflow without addressing the buildpack incompatibility is not useful.

Root cause was reproduced by pulling the *actual failed container image*. New Google Node22 buildpack image uses a distroless runtime without `/bin/bash`, while its generated CNB web process explicitly tries to execute `/bin/bash`; its exec.d helper also has a bash shebang. Docker exits 82 before the Ritsu application starts. CPU, RAM, declaring Functions Framework, and an exec.d helper-only patch did not resolve this base/process mismatch. GitHub issue [#389](https://github.com/Valar05/home-center/issues/389) contains run links and a detailed continuation plan. Source and Windows stage are safe and passing; cloud publication awaits a reproducible runtime fix.

## Global pitch correction, 2026-10-22

User explicitly set **all six registered voices to -1 semitone**, including amused, happy, upset, and somber. The authoritative catalog must hold -1 for each and Windows activation must copy the catalog into the Qwen API root before launching the repertoire API. The original warm rollback sample remains unchanged. This revision supersedes the earlier table and any Windows staging manifest with old pitch values.

## Whisper phase-artifact repair and live canary, 2026-10-22

User reports whisper generated by the deployed repertoire had an unwanted doubled/unison character despite a clean previously approved -1 semitone preview. Investigation isolated the discrepancy: prior repertoire code used `librosa.effects.pitch_shift` on finished audio, unlike the approved preview produced by FFmpeg Rubber Band with `formant=preserved`.

The approved Windows audition `ex04-whisper-v1-lower-1st-20261022.wav` was compared against reprocessing its pristine source `ex04-whisper-qwen-trial-20261022.wav` with FFmpeg `rubberband=pitch=0.9438743126816935:formant=preserved`. At 24 kHz with 72,961 samples, waveform correlation was **0.999997**, RMSE **0.0001529**. This experimentally recovers the actual approved processing technique.

The repertoire Qwen local API source now implements that FFmpeg Rubber Band stage, not librosa phase-vocoder shift. A local code readback confirmed the running source contains `formant=preserved` and that librosa pitch shift occurs only in an explanatory comment. The API was restarted after pausing its worker; `/v1/health` returned `model:loaded` with no error; `/v1/voices` returned all six profiles at -1 semitone. ASMR maintenance was cleared after the user confirmed the experiment ended.

Exact whisper end-to-end ticket: `ritsu-whisper-rubberband-approved-test-20261022`, text `Hey, sweetheart. I'm right here.`, profile `whisper`. Home Center status reached `enqueued`, relay ID `eeb01561de1a6ddef6ec6e10`. **Phone HEARD remains unverified until user confirms.** Do not assert audible delivery or subjective sound quality from enqueue alone. Keep original audition WAVs untouched and preserve the backed-up API sources in `%LOCALAPPDATA%\\RitsuWarmTicketWorker\\repertoire-backup-20261022-191709`.

## Baked minus-one references (2026-10-23)

User corrected the architecture: a previous clean -1-semitone preview existed, and recurrent post-processing of generated dialogue introduced an objectionable doubled/unison whisper. This is not evidence that every -1 pitch operation sounds bad. The explicit current design is to **prepare each reference WAV once** with FFmpeg `rubberband=pitch=0.943874312682:formant=preserved`, never modify original audition WAVs, and stop post-processing generated dialogue. Do not silently reinstate per-generation `librosa.effects.pitch_shift` or FFmpeg filters.

- One-time baker: `tools/campaigns/ritsu_bake_voice_references.py`
- Local baked WAVs: `C:\Users\dclar\workspace\ritsu-faster-qwen3-tts\ritsu-pitched-references\<referenceFile>`
- Manifest with original and baked SHA256: `ritsu-pitched-references/bake-manifest.json`
- Runtime API: `tools/campaigns/ritsu_voice_api_repertoire_v1.py` now reads baked samples directly and writes generated audio without pitch postprocessing
- Computer Hands receipt: `ritsu-bake-ref-run-20261023` exit 0, `BAKED_SIX_REFERENCES_OK 6`; originals preserved
- Windows activation receipt: `activation-report.json` reached `activated` at 2026-10-23 06:15 local with backup `repertoire-backup-20261023-061154`; registration worker started, no HEARD assertion
- A dedicated whisper test was submitted as `ritsu-baked-whisper-audition-20261023-01` but remained queued at last verification. The result must be checked and the user must audition before declaring the whisper fixed.
- Baking pitch into a reference changes voice-cloning conditioning; it is not necessarily acoustically identical to pitch shifting the finalized output. Compare with the user's approved earlier preview.
