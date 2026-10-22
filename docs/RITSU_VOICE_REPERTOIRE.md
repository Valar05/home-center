# Ritsu registered voice repertoire, 2026-10-22

## Authority and scope

Home Center voice identity is versioned in `functions/ritsu_voice_profiles.json`. The catalog was reconstructed from the actual Windows `C:\Users\dclar\workspace\ritsu-voice-repertoire\repertoire-manifest.json` plus `emotion-batch.py` used to produce the upset and somber auditions. Local voice reference WAVs remain exclusively on THECAULDRON, not in GitHub or Firebase. A worker must use the registered IDs and reference texts, not discover or invent settings.

The cloud operation `ritsu.voice.profiles` lists profile names, pitch shifts and approval statuses; `ritsu.voice.speak({requestId,text,voice:'warm-v1',delivery:'phone',profile})` carries the selected profile on each ticket. Default profile is `normal` (approved -1 semitone). `profile` is selected independently of `voice` so the transport and engine contract remain immutable.

| Profile | Qwen reference | Pitch (semitones) | Status |
| --- | --- | ---: | --- |
| normal | ex04_happy_00085.wav | -1 | approved; everyday default |
| whisper | ex04_whisper_00059.wav | -1 | approved whisper audition, lowered candidate |
| amused | ex04_laughing_00044.wav | 0 | approved amusing reference chosen in final audition |
| happy | ex04_happy_00112.wav | 0 | approved delighted option 2 |
| upset | ex04_confused_00043.wav | 0 | provisional, user asked to include |
| somber | ex04_sad_00037.wav | 0 | rework later, user asked to include |

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
