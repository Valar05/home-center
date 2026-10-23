# Ritsu Voice Final API: authoritative handoff
**Prepared:** 2026-10-23
**Purpose:** Continue the approved voice integration without repeating the wrong playback or losing prior engineering work.

## USER'S MOST IMPORTANT CORRECTION
The user **already heard and approved a preview of a newly generated Ritsu voice at −1 semitone. It sounded correct.** The later clip with a strange unison/chorus quality was **not** the approved preview and is **not evidence that the user's chosen voice is defective**.

The assistant should have generated/integrated the **new approved voice**. Instead, it played another post-hoc pitch-adjusted clip through the wrong synthesis path. The user explicitly said it was **not Pocket TTS**, and reminded the assistant that the approved −1-semitone preview already existed. This was a failure to follow the request, not a request for another audition.

**Do not spend time on a "failed whisper" from yesterday.** The user explicitly said that is irrelevant. Do not presume the earlier whisper experiment explains the current mismatch.

**Next assistant's first objective:** identify the *exact* user-approved generated preview and recover its generation recipe/source/conditioning settings from the earlier voice-profile chat, associated files and local outputs before touching the audio transformation path. If exact provenance is not confirmed, say so. Do **not** invent or recreate settings from memory and do **not** present a post-processed substitute as an approved voice.

## The user's intent
- A reliable final Ritsu phone voice API that uses the approved voice, with the six emotion profiles: `normal`, `whisper`, `amused`, `happy` (delighted), `upset`, and `somber`.
- **All six are −1 semitone**, as explicitly corrected by user. This numeric configuration is necessary but **not sufficient** to preserve the approved voice's *sound*.
- The user already ended the GPU/ASMR experimentation hours before the cutover request. Do not keep asking whether the previous session has ended, but perform ordinary current-state resource/process checks if necessary for safe activation.
- Do not require more auditioning unless a truly unresolved fidelity question arises. Treat their previously approved preview as the ground truth.
- Preserve the prior functioning phone relay, original Warm baseline for rollback, private tokens, and no false HEARD claims.

## Cloud work VERIFIED
- Home Center repo: `Valar05/home-center`.
- Cloud Run/Functions Node22 Google runtime-image startup blocker (/bin/bash missing) was bypassed by Node24 deployment; release run `39866555671` succeeded.
- Home Center MCP publication run `39873865434` succeeded.
- All-six −1 semitone correction committed to `functions/ritsu_voice_profiles.json` at commit `25d56009408e6ba2db82e0579ec9aeeac126614f`, with regression test added at commit `967fdaa703f5389604ce6e5a251d86d13cf28ce5`.
- Both updated voice endpoint and Home Center MCP re-deployment succeeded in runs `39875644273` and `39875649638`, respectively.
- **Live Home Center API** `ritsu.voice.profiles` returned all six profiles, each `pitchSemitones: -1`, and `normal` as default. Cloud registry thus verified. Other exposed operations: `ritsu.voice.speak`, `ritsu.voice.status`, `ritsu.voice.worker.register`.
- **Cloud registry verified does NOT mean auditory correctness verified**.

## Windows THECAULDRON worker and latest cutover state
- Registered worker ID: `cauldron-ritsu-warm-01`. Private credential was enrolled using `--bootstrap-clipboard` and stored locally (NEVER output tokens).
- Authenticated ticket transport had been tested: `ritsu-worker-maintenance-canary-20261022` transitioned from `queued` to `maintenance` with no audio/relay IDs. This proved worker communication, not HEARD.
- Local paths:
  - Root: `C:\Users\dclar\workspace\ritsu-faster-qwen3-tts`
  - Original/active API script: `ritsu_voice_api_warm_v1.py`
  - Sender: `ritsu_say.py`
  - API bearer token file: `ritsu-api-token.txt`
  - Catalog intended at root: `ritsu_voice_profiles.json`
  - Worker: `C:\Users\dclar\AppData\Local\RitsuWarmTicketWorker\worker.py`
  - Stage: `C:\Users\dclar\AppData\Local\RitsuWarmTicketWorker\staged-repertoire`
  - Safeguard marker: `RITSU_WARM_ASMR_MAINTENANCE` at root.
- Before cutover, Windows process readback found **two old API processes**, PID 3860 and 28476, both running `ritsu_voice_api_warm_v1.py`, and dedicated voice ticket worker PID 25992. The active local API service was bound at 127.0.0.1:19645.
- A scripted backed-up Windows cutover was committed at `tools/campaigns/activate_ritsu_repertoire.ps1`, commit `a5d96f8d47ce23c060019624f90675e9722a2af1`. It was fetched and launched via Windows Computer Hands, receipt `ritsu-cutover-activate-run-20261022`. It created backup directory:
  `C:\Users\dclar\AppData\Local\RitsuWarmTicketWorker\repertoire-backup-20261022-191709`.
- **Last confirmed local activation report** from `activation-report.json`: `phase: installed`, `detail: Repertoire files installed; starting API`, timestamp 2026-10-22 19:17:22 CDT. A subsequent local `/v1/health` returned `{"ok":true,"model":"loading","error":null,"queue":0}`. **There was no later confirmed `api_ready` or `activated` report, no confirmed successful completion of the cutover, no proven phone HEARD, and no reboot proof.**
- Before any new cutover/restart, **read the actual current report, API health, running processes, maintenance marker and backups**. Do not assume either installation succeeded fully or rollback occurred.

## Exact known audio implementation discrepancy
The staged local repertoire API source is `tools/campaigns/ritsu_voice_api_repertoire_v1.py`. In the reviewed snapshot, it:
1. Loads Qwen3-TTS 0.6B Base and a profile's `referenceFile` and `referenceText`.
2. Calls `model.generate_voice_clone(...)`.
3. **After synthesis**, if `pitchSemitones` is set, applies `librosa.effects.pitch_shift(..., n_steps=shift)` to the generated samples.
4. Saves the resulting WAV and sends it via the existing phone relay.
This post-generation pitch shifting is an identified **potential reason the final API differs from the approved preview**; it must not be treated as the approved recipe merely because the JSON pitch is −1. The user's observation about the unnatural unison sound is actionable evidence about fidelity, not an invitation to argue about earlier whisper experiments.

The sender source is `tools/campaigns/ritsu_say_repertoire_v1.py`. It requests each profile with `--profile` and enqueues the resulting WAV via the authorized local relay on 127.0.0.1:19643, then phone over Tailscale/Termux. One enqueued ticket is NOT proof of audible playback.

## Source profile map (current registered names)
- normal: `ex04_happy_00085.wav`, approved
- whisper: `ex04_whisper_00059.wav`, approved audition pitch candidate
- amused: `ex04_laughing_00044.wav`, approved
- happy: `ex04_happy_00112.wav`, approved
- upset: `ex04_confused_00043.wav`, provisional but explicitly included
- somber: `ex04_sad_00037.wav`, rework-later but explicitly included
All six cloud metadata pitch values are **−1 semitone**. These files were reported present on THECAULDRON in the earlier Windows preflight, but exact correspondence to the specific approved preview has **not yet been established**.

## Handoff procedure
1. **Begin with the user's correction**, not a whisper diagnosis. Acknowledge the user-approved −1 preview is the source of truth.
2. Locate the exact approved preview and generation method from the voice-profiles thread/artifacts. Pin its source file, settings and checksum. Recover the role of Pocket TTS versus Qwen clone and whether pitch was changed in conditioning versus after rendering. Do not assume.
3. Read the current local activation-report.json, local voice server health and process owners. Safely reconcile partial activation/rollback; preserve timestamped backups and only one API listener/worker.
4. Replace/repair the audio path to replicate the approved voice *without arbitrary after-the-fact pitch stretching* unless this is provably how the approved preview was produced. Keep the cloud profile names, −1 requirements and deterministic fixed dispatch contract.
5. Run a short phone canary **using that exact correct voice-generation route**, inspect ordered relay receipts, and ask user if actually HEARD and whether it matches the approved preview. Do not play unrelated transformed clips.
6. Then verify all six profiles, persistence/restart, local listener ownership and phone receiver reliability. Update `docs/RITSU_PHONE_AUDIO_LAWS.md` and `docs/RITSU_VOICE_REPERTOIRE.md` with final receipts and remaining gaps.

**Do not claim the final API is ready to use until the audio user hears is the already approved sound.**

## Working references
- `functions/ritsu_voice_profiles.json`
- `functions/ritsu_voice_api.js`
- `functions/ritsu_voice_api.test.js`
- `workers/ritsu_warm_ticket_worker.py`
- `tools/campaigns/ritsu_voice_api_repertoire_v1.py`
- `tools/campaigns/ritsu_say_repertoire_v1.py`
- `tools/campaigns/activate_ritsu_repertoire.ps1`
- `docs/RITSU_PHONE_AUDIO_LAWS.md`
- `docs/RITSU_VOICE_REPERTOIRE.md`

**Suggested new-thread instruction:** “Fortress Online. Read docs/RITSU_VOICE_HANDOFF_20261023.md and RITSU_PHONE_AUDIO_LAWS.md. Recover the exact previously approved newly generated −1-semitone Ritsu preview. Do not substitute post-processed audio or revisit yesterday's whisper. Verify the partially activated Windows API, correct the path, and only then test actual phone playback.”
