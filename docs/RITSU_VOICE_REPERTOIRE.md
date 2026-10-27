# Ritsu registered voice repertoire, 2026-10-22

## CURRENT SPEECH UNIT AND EARLY AUDIO CONTRACT (2026-10-23, 17:02 CDT)

**The earlier section describing mandatory sentence-level four-job lookahead is historical and no longer reflects the Windows sender.** Actual Windows sender is installed with SHA256 `3DDA464DF8D5E24D29DB471DF7C7B8D70D28741C98866996A980AFE5443C6AD8`: one complete agent-authored text unit -> one Pocket `/v1/speak` job -> one WAV -> canonical `/v1/deliver`. Sender sentence regex splitting OFF. Its previous exact SHA256 `2922EFE848AAD961C96282EB491E4090FCE9DD0891E67CD01FBE1D357AA24B3D` is backed up. No modification to the five approved Pocket clone states, model server, Windows ticket worker, relay or Android receiver during this cutover. Voice profile mapping below remains authoritative for *voice identity*, while this addendum is authoritative for current chunking policy.

Hard live Pocket `/v1/speak` cap = **450 characters per ticket**, fail closed beyond it. No rigid sentence/character splitter, no mid-sentence cuts and no omitted narration. The agent produces multiple complete, ordered, semantically intentional speech units for longer content and submits each separately. To lower first-audio latency, provisional authoring guideline is a 90–140 character first complete thought, followed by naturally completed ~180–300 character thoughts. Benchmarks (Normal voice on actual Windows Pocket CPU, no phone delivery): 112 chars -> 3.62s render, 5.84s audio; 183 -> 5.83s render, 10.08s audio; 289 -> 9.25s render, 13.84s audio. No character-length breakpoint is guaranteed to be optimal. Generator word completeness and end-to-end phone HEARD remain separate gates.

Android v2 receiver playback gaps remain, with 1.445s median phone API interclip boundary in a 58-completion trace. Do not assume no-split sender cutover fixes the phone player or that a proposed silence cutter is live. See `docs/RITSU_PHONE_AUDIO_LAWS.md` and `docs/RITSU_PHONE_GAP_CAMPAIGN_CHECKPOINT_20261023.md`.


## Normal/Warm switch, Desire 02 -1, plus measured sentence-lookahead (2026-10-23)

**Newest selection overrides earlier table:** Normal/Warm is now the approved Desire 02 Ocean Dream **-1 reference-baked Pocket clone** `voice-candidates/fullset-20261023/warm-minus1.safetensors` SHA256 `043D61FCA49B175C88A41734D1A659ED9655D39BDE8BD5FA2038AFC35D7FBB36`; source pre-bake SHA256 `45032B1B34872CBBD671FEAB16431F9BC768BE03582EE0FBC1DBC95DF8905F66`. The Cheesecake no-laugh Warm remains safely archived, not live. Live Pocket server /health verified exact new Warm state. Delighted -1, Amused -1, Somber -1 (shared with Upset), and Whisper -1 are all unchanged, zero active Qwen voice synthesis.

The sentence-level Home Center sender now queues four upcoming complete grammatical sentences with bounded lookahead to the existing **serial CPU Pocket model**, then delivers in FIFO order to the unchanged canonical Tailscale relay. No long multi-sentence Pocket synth call, no sentence truncation, no parallel GPU use. Added per-ticket and per-sentence UTC/monotonic timing logs. Ten-sentence live Home Center test ticket `ritsu-gapfix-live-10sentence-lookahead-20261023` has 10 ordered relay IDs, 10 distinct GET/audio, 10 ACKs, sender transcript hash equal to cloud transcript hash; HEARD pending.

Measured server/transport improvement: pre-fix historical median relay enqueues **5.5s**, post-fix **1.371s**; ten-sentence preflight model generated **25.6s of audio in 17.89s**, confirming synthesis isn't the throughput bottleneck. Remaining measured **phone retrieval interval minus preceding audio duration median 2.68s**, not an exact audible gap. Current Android receiver fetched next WAV only after playing prior one, and is NOT instrumented for playback-start/end or yet modified. Receiver/phone-side prefetch follows only after verified readback/access and owner's audible verdict.

**Operational hard law and exact receipts:** `docs/RITSU_PHONE_AUDIO_LAWS.md` v1.6; source `tools/campaigns/ritsu_pocket_v2_deployed/ritsu_say.py`, `worker.py`, `test_ritsu_say_lookahead.py`; restore backups `PocketTTS/gapfix-desire02-cutover-backups-20261023`. Do not declare gaps eliminated or phone HEARD without user confirmation.

---


## CORRECTION: Delighted is the −1-semitone Pocket clone (2026-10-23, authoritative)

The user explicitly corrected the assistant's misinterpretation of "original": **the official Delighted voice is the clone made by feeding the −1-semitone Happy 00112 reference into Pocket TTS**, not the unshifted Pocket clone and **not any old Qwen/"Quinn" clone**. That adjusted Pocket state **already existed** and its file SHA256, reference SHA256 and source recording have now been verified. No output/post-generation pitch shifting is used.

- Original Expresso reference `ex04_happy_00112.wav` SHA256 `6F5342EC0F32DB5276408ECA182D3CBC32A9F03E46CA6230B4161D4FE802400C`.
- −1-semitone pre-baked reference `workspace/ritsu-faster-qwen3-tts/ritsu-pitched-references/ex04_happy_00112.wav` SHA256 `20A36E295FCE95820F87B9AC34D5036DC8929CBB39282182EC3BCAF56BC331BE`, formants preserved.
- **Selected live Pocket clone:** `C:\Users\dclar\Documents\Codex\Venice\PocketTTS\voice-candidates\fullset-20261023\delighted-minus1.safetensors`, SHA256 `050A501F67F83A3876183BEFD649806265B844BFC13BB21D967FC37C0456427A`. This is genuinely exported Pocket voice conditioning state, not a Qwen WAV or a post-hoc pitch filter. Original unshifted Pocket Delighted state SHA `47089F6F...` is preserved as an archive and **not live**.
- **Actual cutover verified:** Live Pocket service `127.0.0.1:10205/health` reports `stateSha256.delighted=050A501F67F83A3876183BEFD649806265B844BFC13BB21D967FC37C0456427A`, model ready with five states, Somber still the Upset alias. After patching `ritsu_pocket_repertoire_server_v2.py` and `embodiment_campaign/tts_adapter.py`, Pocket watchdog restarted the service and canonical relay watchdog restarted the relay (new PID 17728) after a queue-empty preflight. New profile cache keys include the correct clone hash. Home Center `ritsu.voice.speak` `profile=happy` phone canary `ritsu-live-pocket-delighted-minus1-verified-phone-20261023` status `enqueued`, relay ID `f5aef07ca845b5da6ae237ad`; **HEARD has not yet been confirmed for this corrected audition**, even though user heard earlier unshifted canary tests.
- The Warm, Amused, Somber and Whisper selected states remain unchanged; Upset still aliases Somber; active Qwen synthesis remains retired. Pocket service source archive and adapter source and catalog were updated in GitHub as part of this fix; cloud profile-list metadata may remain stale until deployment. Windows backups saved under `PocketTTS/delighted-minus1-live-selection-backup-20261023`.

This correction takes precedence over all earlier text claiming that the official Delighted state was the **original-pitch** Pocket clone.



## Current live Pocket-only repertoire (2026-10-23)

**This section is authoritative over the historical Qwen profile table below.** The user requested that the existing **Pocket TTS clones** be connected to the everyday Ritsu voice path, with **no old Qwen ('Quinn') voices**. A standalone Upset voice is unnecessary: **upset aliases Somber**. The Pocket engine and existing phone relay were wired and tested on THECAULDRON on Oct 23.

| Public profile | Actual engine/state | Pitch preparation | Live status |
|---|---|---|---|
| normal, warm (default) | Pocket edited no-laugh Cheesecake clone; SHA256 6D619A92B6F17C4DF4163919E690FAFADD48C285A0773AE01EFDE7BAA510ED07 | -1 baked into reference | Selected live default |
| happy, delighted | Pocket happy_00112 user-accepted original clone; SHA256 47089F6F552D9E8FDEF599C3917B958FE4850CCD9B875662996F77214F5DD3A6 | Original pitch, no new shift | Official existing Pocket clone |
| amused | Pocket laughing_00044; SHA256 6F878B05D4227E10B43BB0AA8A87C6CBDF909B9CCA0F4A845E28C6541F17D9FE | -1 baked into reference | Selected |
| somber, upset | Pocket Personal Affirmation; SHA256 51C7B4F55361082ED23ABB56E1F7E9878D4CA26DA5740349858BDBDF2A4CA0BD | -1 baked into reference | One shared voice state; Upset alias only |
| whisper | Pocket approved whispered source; SHA256 B99EB2E16612E8B8C3E3A96F74BD631676CC79071779537FD94C564DB5796BE5 | -1 baked into the source | Selected |

**Live API**: 127.0.0.1:10205, Pocket-only /tts and /v1 compatibility routes. Relay: the existing Tailscale 19643 with optional enumerated profile and default normal. Home Center cloud tickets retain fixed compatibility voice ID warm-v1 even though synthesis is Pocket; local ticket worker and sender now route to 10205. Qwen engine port 19645 processes stopped. Profile state SHA is part of the local speech cache key; no stale audio bleed. Source of truth and operational hard gates: docs/RITSU_PHONE_AUDIO_LAWS.md v1.5. Source version control: tools/campaigns/ritsu_pocket_repertoire_server_v2.py and tools/campaigns/ritsu_pocket_v2_deployed/. THECAULDRON at-login scheduled tasks keep the Pocket supervisor and cloud ticket worker available.

**Deployment distinction:** functions/ritsu_voice_profiles.json now reflects this Pocket selection in GitHub. The deployed cloud profile-list operation may still return older labels until the updated Firebase function is deployed. The local cloud ticket worker and relay were verified to synthesize via Pocket, not Qwen. Do not falsely treat a GitHub commit as cloud deployment. User audible HEARD verdict still outstanding for the cutover canaries.

---

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
