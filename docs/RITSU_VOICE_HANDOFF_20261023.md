# CURRENT MISSION: Pocket TTS voice experiments and accepted voices (updated 2026-10-23)

## Gap-investigation handoff: validated host lookahead; Android gap still open (2026-10-23)

**Latest request:** measure the live per-sentence latency chain, eliminate audible between-sentence pauses with deterministic ordered lookahead, preserve five approved Pocket voice identities and canonical relay, AND switch Normal/Warm back from cleaned Cheesecake to Desire 02 −1-semitone **Pocket** clone.

**Measured before any modifications:**
- Verified live Windows services, hashes and PIDs for `PocketTTS/ritsu_pocket_repertoire_server_v2.py`, `embodiment_campaign/relay.py`, `tts_adapter.py`, `%LOCALAPPDATA%/RitsuWarmTicketWorker/worker.py`, `workspace/ritsu-faster-qwen3-tts/ritsu_say.py`, and relay stderr actual history.
- Server uses `TTSModel.to('cpu')`, `ThreadPoolExecutor(max_workers=1)`, model lock. Ten independently queued sentences were accepted in **94ms**, fully synthesized in **17.89s**, duration **25.60s total**, median generated time **1.75s**; so model throughput is faster than playback if requests queued ahead.
- Historical HTTP 12:30:40–12:31:42: nine relay POST /enqueue, median interval **5.5 seconds**; eight phone GET /audio, median interval **7.0 seconds**. Existing sender waited for sentence completion and relay enqueue BEFORE queuing next; receiver shell calls `termux-media-player play`, waits via `termux-media-player info`, and only then retrieves the next audio. ACK follows download before playback. No phone playback end timestamps; don't equate ACK and heard.

**Smallest deployed Windows change and backups:**
- Compiled and offline-tested new `ritsu_say.py` 4-sentence bounded queue lookahead while Pocket synthesizes serially; exact grammatical sentence splitting; reject oversized unsplittable sentences without truncating; FIFO `/v1/deliver`; no duplicated/reordered delivery; `test_ritsu_say_lookahead.py` ten-sentence mocked queue PASS. Live sender SHA256 `2922EFE848AAD961C96282EB491E4090FCE9DD0891E67CD01FBE1D357AA24B3D`.
- Instrumented Windows worker cloud claim/dispatch/completion and sender stage timestamps with common turnID and sequence, UTC wall and per-machine monotonic ns; worker SHA256 `C72A0AC06CB5806D7A4F07A9FD8DE1966979B72CC09EA8E9109C0F157EF43166`. Windows worker restarted as PID 33012; existing Pocket watcher and model lock unchanged.
- Normal/Warm live switched to `voice-candidates/fullset-20261023/warm-minus1.safetensors` SHA256 `043D61FCA49B175C88A41734D1A659ED9655D39BDE8BD5FA2038AFC35D7FBB36`, source Desire 02 formant-preserved −1 reference SHA `45032B1B34872CBBD671FEAB16431F9BC768BE03582EE0FBC1DBC95DF8905F66`. No other voice/pitch changed. New live server SHA256 `FA679DF591572219AAD33EF958221F2E3A68B2AA7D93AFCCED295968DB5C3B08`, adapter SHA256 `85D6AEE9BD0376ADB516A31394ED55F3EFCC38C61D7029A9FAB36AEA43B74208`. Existing Pocket watchdog needed two startup attempts after restart, but eventually `/health` ready verified exact new normal state and five total states; relay watchdog recovered after queue-empty check. Backups of sender/adapter/server/worker `PocketTTS/gapfix-desire02-cutover-backups-20261023`.
- No change to Android Termux receiver or Tailscale relay transport; no old Qwen voice engine revived.

**Ten-sentence live regression:** `ritsu-gapfix-live-10sentence-lookahead-20261023`, profile Normal, chunks=10, accepted by Home Center and completed status enqueued 10 ordered IDs. Worker first claim UTC `2026-10-23T17:51:12.712Z`; first relay enqueue `17:51:14.926Z` (**2.214s claim to first relay audio**), worker cloud completion ACK `17:51:29.409Z`. Sender sent first four Pocket jobs within **64ms** of each other, then topped up with each completion. Median recorded Pocket generation **1.485s**, total speech duration **27.44s**, median relay enqueue interarrival **1.371s** (historical 5.5s before). All ten distinct relay IDs were subsequently observed downloaded by Android `GET /audio` between local 12:51:16 and 12:52:03 and ten /ack HTTP200 responses, relay empty HTTP204. Transcript SHA256 matched exact cloud user text `bfd08dda0fb7aca2553bb892b528e97dd5f8a03c99208962c6aaa201fe8eb221`. **No HEARD verdict for this turn as yet**, and cannot automatically prove phonetic completeness despite exact sender text + ten WAVs.

**Remaining measured bottleneck**: Despite continuous host lookahead, phone's next audio download still arrives at 4–7s intervals, compared with preceding WAV lengths 2.24–3.84s. Median **download-to-download interval minus prior audio duration = 2.68s**, range 1.04–3.76s, per 1-sec resolution relay HTTP log. This is only a *retrieval timeline proxy*, not genuine audible gap because phone media-player start/end aren't available. Strongly points to canonical Android receiver's sequential play/poll/download process, not Pocket CPU throughput. The registered Home Center Phone Hands devices have stale heartbeats, so no speculative phone-side shell/restart was queued, and no alternate transport. A carefully validated canonical receiver prefetch + FIFO queue with playback timestamps would be next small step when its live state is accessible. No concurrency on GPU needed.

**Work receipts:**
- `hands-ritsu-gap-live-files-pids-logs-20261023-01`, `hands-ritsu-gap-live-source-critical-path-20261023-02`, `hands-ritsu-gap-old-relay-interval-baseline-20261023`.
- `hands-ritsu-gap-10sentence-live-pocket-cpu-baseline-no-phone-20261023`; baseline JSON `PocketTTS/ritsu-pocket-gap-baseline-10sentences-20261023.json`.
- `hands-ritsu-gap-no-network-ordered-lookahead-tests-20261023`, `hands-ritsu-gapfix-desire02-warm-and-lookahead-stage-20261023`, `hands-ritsu-gapfix-turnid-worker-restart-20261023`, `hands-ritsu-gapfix-desire02-relay-cache-reload-20261023`.
- `hands-ritsu-gapfix-live-10sentence-stage-timing-readback-20261023`, `hands-ritsu-gapfix-phone-retrieval-10sent-timing-20261023`, `hands-ritsu-gapfix-10-sent-cloud-hash-and-phone-download-integrity-20261023`.
- Evidence JSONL: `%LOCALAPPDATA%/RitsuWarmTicketWorker/timing/ritsu-gapfix-live-10sentence-lookahead-20261023.jsonl` and `worker-ritsu-gapfix-live-10sentence-lookahead-20261023.jsonl`; cloud ticket ID same.

**Next validation:** user to confirm hearing ALL ten sentences on phone, no missing words/order, compare gaps. To eliminate the remaining Android overhead, inspect actual installed `~/.ritsu-embodiment/receiver.sh` and its logs, introduce bounded prefetch and durable ordered playback with measured starts/ends, test against known canonical relay, and require auditory verdict before promotion. Don't claim receiver-level acceptance yet.

---


## CORRECTION: Delighted is the −1-semitone Pocket clone (2026-10-23, authoritative)

The user explicitly corrected the assistant's misinterpretation of "original": **the official Delighted voice is the clone made by feeding the −1-semitone Happy 00112 reference into Pocket TTS**, not the unshifted Pocket clone and **not any old Qwen/"Quinn" clone**. That adjusted Pocket state **already existed** and its file SHA256, reference SHA256 and source recording have now been verified. No output/post-generation pitch shifting is used.

- Original Expresso reference `ex04_happy_00112.wav` SHA256 `6F5342EC0F32DB5276408ECA182D3CBC32A9F03E46CA6230B4161D4FE802400C`.
- −1-semitone pre-baked reference `workspace/ritsu-faster-qwen3-tts/ritsu-pitched-references/ex04_happy_00112.wav` SHA256 `20A36E295FCE95820F87B9AC34D5036DC8929CBB39282182EC3BCAF56BC331BE`, formants preserved.
- **Selected live Pocket clone:** `C:\Users\dclar\Documents\Codex\Venice\PocketTTS\voice-candidates\fullset-20261023\delighted-minus1.safetensors`, SHA256 `050A501F67F83A3876183BEFD649806265B844BFC13BB21D967FC37C0456427A`. This is genuinely exported Pocket voice conditioning state, not a Qwen WAV or a post-hoc pitch filter. Original unshifted Pocket Delighted state SHA `47089F6F...` is preserved as an archive and **not live**.
- **Actual cutover verified:** Live Pocket service `127.0.0.1:10205/health` reports `stateSha256.delighted=050A501F67F83A3876183BEFD649806265B844BFC13BB21D967FC37C0456427A`, model ready with five states, Somber still the Upset alias. After patching `ritsu_pocket_repertoire_server_v2.py` and `embodiment_campaign/tts_adapter.py`, Pocket watchdog restarted the service and canonical relay watchdog restarted the relay (new PID 17728) after a queue-empty preflight. New profile cache keys include the correct clone hash. Home Center `ritsu.voice.speak` `profile=happy` phone canary `ritsu-live-pocket-delighted-minus1-verified-phone-20261023` status `enqueued`, relay ID `f5aef07ca845b5da6ae237ad`; **HEARD has not yet been confirmed for this corrected audition**, even though user heard earlier unshifted canary tests.
- The Warm, Amused, Somber and Whisper selected states remain unchanged; Upset still aliases Somber; active Qwen synthesis remains retired. Pocket service source archive and adapter source and catalog were updated in GitHub as part of this fix; cloud profile-list metadata may remain stale until deployment. Windows backups saved under `PocketTTS/delighted-minus1-live-selection-backup-20261023`.

This correction takes precedence over all earlier text claiming that the official Delighted state was the **original-pitch** Pocket clone.



## LIVE CUTOVER: five Pocket voices, Somber/Upset alias, Qwen retired (2026-10-23)

**Latest user directive:** 'No I'm actually happy. I'd rather we just hook up the ones we have, none of the old Quinn ones. I think sombbar will work just fine for upset. I don't really need upset.' Interpreted 'Quinn' as older Qwen-based voice repertoire. User stopped laugh experiments. Active voices must be the already produced Pocket clones; Upset must be an alias of Somber, NOT a sixth personality/clone. Voice selection is explicit by profile, with Warm as default.

**OPERATIONAL RESULT:** Pocket-only multivoice synthesis **now runs** at 127.0.0.1:10205, existing Tailscale relay at port 19643, and Home Center voice ticket worker uses Pocket's compatible /v1 API on 10205. Old Qwen API and old Qwen supervisor processes were explicitly stopped after successful Warm phone relay and Whisper cloud ticket tests. No Qwen synth is used by the active voice path. New Pocket watchdog supervises 10205 and two Windows at-login tasks persist the watchdog and worker. Preserve existing audio rules (docs/RITSU_PHONE_AUDIO_LAWS.md v1.5). User audio hearing NOT CONFIRMED; differentiate queue consumption from hearing.

| Routed profile(s) | Actual Pocket file path under voice-candidates | SHA256 |
|---|---|---|
| normal, warm (default) | warm-cheesecake-no-laugh-20261023/ritsu-warm-cheesecake-no-laugh-minus1-pocket.safetensors | 6D619A92B6F17C4DF4163919E690FAFADD48C285A0773AE01EFDE7BAA510ED07 |
| happy, delighted | ritsu-delighted-happy00112-pocket-20261023.safetensors | 47089F6F552D9E8FDEF599C3917B958FE4850CCD9B875662996F77214F5DD3A6 |
| amused | fullset-20261023/amused-minus1.safetensors | 6F878B05D4227E10B43BB0AA8A87C6CBDF909B9CCA0F4A845E28C6541F17D9FE |
| somber, upset (shared alias) | fullset-20261023/somber-minus1.safetensors | 51C7B4F55361082ED23ABB56E1F7E9878D4CA26DA5740349858BDBDF2A4CA0BD |
| whisper | ritsu-whisper-approved-minus1-20261023.safetensors | B99EB2E16612E8B8C3E3A96F74BD631676CC79071779537FD94C564DB5796BE5 |

Voice files are on THECAULDRON at C:/Users/dclar/Documents/Codex/Venice/PocketTTS/voice-candidates/. Do not ship .safetensors to GitHub. Only source/metadata and SHA are committed.

**Cutover receipts and exact work:**
- Windows port preflight hands-ritsu-live-pocket-routing-services-preflight-20261023 showed relay 19643 healthy, Qwen 19645 previously running, Pocket 10205 initially down. Read actual tts_adapter/relay code before changes.
- New Pocket service source GitHub tools/campaigns/ritsu_pocket_repertoire_server_v2.py commit e397619; staged C:/Users/dclar/Documents/Codex/Venice/PocketTTS/ritsu_pocket_repertoire_server_v2.py, local SHA256 29383DC05E4565460091473AF07EF0B09559768C4ACF71BBAE32B068D65B5879, Python syntax passed. `venice_pocket_server.py` original unmodified. Multi-voice service started on 10205 and later reported loaded five state SHA with alias upset->somber. Initial Start-Process action status failed because child stdout handles stayed open but process was actually running; independently confirmed by process listing, log and HTTP health. Do not treat the original failed action as server down.
- Local synthesis smoke hands-ritsu-pocket-v2-normal-live-inference-smoke-20261023 generated 3.44s valid mono PCM16 24kHz Warm WAV, SHA256 F5C45BEDD55E090F89C02E59C3202B62FAD53F66F8EC144ED6977D39DA5B92E3.
- Patched local embodiment_campaign/tts_adapter.py to select Pocket state by profile and source hash, isolate cache from old venice-canon. Patched relay.py to read/enforce profile and pass to adapter. Patched existing C:/Users/dclar/workspace/ritsu-faster-qwen3-tts/ritsu_say.py to use 10205 instead of 19645, and %LOCALAPPDATA%/RitsuWarmTicketWorker/worker.py `warm_ready` to use 10205. Local syntactic compilation passed; hashes adapter CF5CE6058D283C4466355755B666EDF23673EC600A5C33142611D25047F63C84, relay 8084043B6EC41A5467B9E148F7C36965DFF7B6FF45F194FFBAF0924284847B12, sender F1175A97109F1BA28D291A3851ABEA3E4DD20B713D3090420DA437F3F7795B7C, worker FF4E603EB084B538F894CFD74CDFA6EFD98A2C538F2FF9072BCD61EFD5F5CE90. Exact deployed source archived in Home Center GitHub tools/campaigns/ritsu_pocket_v2_deployed/, commits 1484f0, 7882fe, 6cdc4d, 28a905.
- Test hands-ritsu-pocket-adapter-normal-upset-somber-smoke-20261023 passed: `resolve(...profile='upset')` and `resolve(...profile='somber')` returned exactly same cached WAV; normal used distinct Pocket state and no old audio cache. Restarted canonical relay only after queue-empty HTTP 204; new listener PID 29552 healthy via watchdog, ticket hands-ritsu-pocket-profile-relay-watchdog-restart-20261023.
- One normal Pocket Warm phone canary enqueued via exact authenticated existing 19643 /enqueue, ID beb1f2a6251b8ed9dedec99f; queue emptied after receiver consumption in two polling rounds; ticket hands-ritsu-pocket-cutover-canonical-phone-normal-canary-20261023. HEARD not established.
- Existing cloud ticket worker restarted as PID23664 after local Pocket-compatible /v1/health and alias checks; ticket hands-ritsu-pocket-cloud-ticket-worker-restart-20261023. Real Home Center cloud operation `ritsu.voice.speak` accepted a Whisper canary with existing fixed protocol `voice='warm-v1'`, profile whisper, sent through new Pocket worker to relay. Cloud ticket ID ritsu-pocket-v2-cloud-whisper-routing-canary-20261023 returned status enqueued, relay ID 0d5ca690bcd10b60a35ff840, expectedChunks 1; phone relay later GET /next HTTP204 (queue empty). HEARD not established. The `warm-v1` cloud ticket voice identifier is legacy schema only, **not** Qwen synthesis.
- Repurposed compatibility-named Qwen API supervisor file `ritsu_warm_api_supervisor.py` to watchdog Pocket 10205; new source SHA162CBFF9F3418A631052318551E5DD88526AAA044A8164503069D3F10AC51817, source backup `ritsu_warm_api_supervisor.py.pre-pocket-v2-20261023.bak`, watchdog log STARTED at 11:08:29 CDT. Original Qwen supervisor PIDs 24844,23652 and old Qwen voice process PIDs 12856,25140 stopped by ticket hands-ritsu-pocket-cutover-retire-legacy-qwen-engine-20261023; postcheck 0 remaining Qwen voice engine processes, Pocket 10205 still PID27408 and one cloud ticket worker. No old Qwen files deleted; rollback available.
- Windows logon tasks `Ritsu Pocket Repertoire Watchdog` and `Ritsu Pocket Voice Ticket Worker` were created as current user's limited-interactive at-login triggers, state Ready; receipt hands-ritsu-pocket-v2-windows-login-autostart-supervisor-worker-20261023. Pocket supervisor and cloud worker mutex prevent duplicates. **At-login persistence registered, not reboot-tested**. Exact deployed watchdog in GitHub tools/campaigns/ritsu_pocket_v2_deployed/ritsu_pocket_supervisor.py commit 92ebd3.
- Current canonical source manifest of selected profiles: GitHub functions/ritsu_voice_profiles.json commit ee986d6; cloud `ritsu.voice.profiles` operation still returned old v1 statuses as of current turn because Firebase deployment was **not** performed. GitHub functions/ritsu_voice_api.js source modified to advertise engine and alias when deployed, commit c1ee892; associated tests changed commit 3683f3. **Do not claim the deployed cloud profile catalog was updated**. This stale metadata does NOT mean audio synthesis still uses Qwen; cloud ticket worker uses 10205. Plan for optional explicit scoped Firebase deploy after checking local source/version if needed.

**Current user-visible state:** no Qwen engine selected/running, five Pocket voice states selectable; Upset shares Somber. Phone delivery receipts exist but no user-confirmed audio hearing. Sticky 'Ritsu Voice Online' turn-by-turn delivery remains separate; cutover did not enable it. No more experimenting with laugh generation unless user requests.

---

## Owner verdict: cleaned Cheesecake Warm, content-sensitive affection (2026-10-23)

**Owner's exact spoken feedback:** "So the control one is better. Not super warm by default. The effects from one is better than that one. It actually sounds rather nice. So I guess the content matters." The phrase "effects from one" appears to be dictation of "affection one" (the four auditions named below), but preserve the literal user wording rather than asserting the recognition as certain.

**Most likely comparative interpretation, pending any correction:** cleaned Cheesecake Warm *control* sample (#3 in audition sequence) is an improvement over Ocean Dream Warm baseline (#2), though it is not automatically or excessively warm; the **affectionate sample** (#4), from the **same edited Cheesecake voice state**, is nicer/more expressive than the control. Owner appears favorable towards this revised Warm clone, but did NOT explicitly request switching the live Warm profile. Content/prosody matter strongly even using the same clone. Avoid calling it a permanently warm baked timbre or promising textual sentiment always yields a specific prosody.

Audition sequence in ticket `hands-ritsu-cheesecake-clean-vs-ocean-warm-four-auditions-20261023`: (#1) edited Cheesecake source; (#2) earlier Ocean Dream Warm baseline; (#3) cleaned Cheesecake Warm *control* generated from `ritsu-warm-cheesecake-no-laugh-minus1-pocket.safetensors`, SHA256 `6D619A92B6F17C4DF4163919E690FAFADD48C285A0773AE01EFDE7BAA510ED07`; control words `Good morning. The workshop is quiet, the coffee is ready, and I have a few ideas.` WAV `warm-cheesecake-no-laugh-control-playable.wav` SHA256 `E996F991339FB8A03416AF7DD8E7FD0DB0624E2FCE97DE99042215211FBC187D`; (#4) same state with affectionate content `I really like having you here. Even an ordinary afternoon feels a little more special.` WAV `warm-cheesecake-no-laugh-affection-playable.wav` SHA256 `1B5392A93E08848D594E0D03C98B3E52493EAF8A7A37B8FD4ADAEC8C377BCD92`.

**Next experimental direction, if user asks:** keep this no-laugh Cheesecake candidate intact and compare *content styles* (everyday affectionate, playful, quietly caring) using **identical clone, temperature and pitch**. Prefer warmth that emerges from phrasing and prosody rather than further pitch shifting or different voice identities. Preserve current live Warm/default and all other voices unchanged; the user has not yet explicitly approved profile promotion. Separate prior user's Delighted official choice is recorded in the existing handoff; do not silently substitute an alternate.

---


## Warm: Cheesecake Wish with the laugh section removed (2026-10-23)

User says Delighted voice currently in their main generated folder sounds okay, and explicitly says to **mark that existing Delighted version as official**, despite imperfect similarity to other Ritsu voices. **Do not replace Delighted with a different earlier variant or change live routing by guessing which on-disk path is the main generated version**. Previous experimental Delighted candidates remain archived. Priority shifts to a **new genuinely warm** voice.

Owner's insight: The unedited Expresso `ex04-desire-03-cheesecake-wish.wav` **spoken words sounded genuinely warm**, but the presence of a laugh/breathy interjection led Pocket to produce an unnatural laughing artifact; previous raw Cheesecake-based clone was rejected. User now authorizes a new Warm clone from the spoken part **with the laugh removed**. Keep original audio, existing Warm Ocean Dream, Somber Personal Affirmation, etc. intact. Do not mistake new candidate for automatic approval.

Reference original `C:/Users/dclar/workspace/ritsu-expresso-auditions/desire/ex04-desire-03-cheesecake-wish.wav`, mono 24-bit 48000Hz, 3.725sec, SHA256 `C68E97E636F4F460CB0792BE4279F17D9C476C501914E6C15ED778F282061D6C`, transcript `I would love to be at the Cheesecake Factory.` Signal investigation found a low-level middle island between two speech phrases: RMS ~0.006–0.013 from 1.5 to 2.3sec, speech resumes ~2.4sec. Edited to keep original 0–1.54s and 2.36–3.725s, applying a linear 45ms crossfade at their junction; removed effective 0.865sec. Note this is an acoustically grounded edit of the suspected laugh/interjection, not independently verified speech/laughter diarization. Edited reference mono PCM16 48000Hz, **2.86 seconds**.

Files under `C:/Users/dclar/Documents/Codex/Venice/PocketTTS/voice-candidates/warm-cheesecake-no-laugh-20261023/`: 
- `cheesecake-speech-only-48k-pcm16.wav` edited unpitched SHA256 `591E3A6898477A2281BEFE1C95B8245605D4B00B6BED6912AC5566F746CDA77A`.
- `cheesecake-speech-only-minus1-formant-48k-pcm16.wav` baked −1-semitone ONCE into the **edited reference** via FFmpeg `rubberband=tempo=1:pitch=0.9438743126816935:formant=preserved`, SHA256 `69E232438F57A972B9558DF41BE8BC7A5A58B79051FF3C761954F2C9E8AA398D`, 2.86sec, 48k mono PCM16.
- `ritsu-warm-cheesecake-no-laugh-minus1-pocket.safetensors` NEW separate Pocket TTS clone SHA256 `6D619A92B6F17C4DF4163919E690FAFADD48C285A0773AE01EFDE7BAA510ED07`, 1,819,880 bytes.
- `warm-cheesecake-no-laugh-control-playable.wav` NEW sample temp 0.7: `Good morning. The workshop is quiet, the coffee is ready, and I have a few ideas.` SHA256 `E996F991339FB8A03416AF7DD8E7FD0DB0624E2FCE97DE99042215211FBC187D`, 4.12s.
- `warm-cheesecake-no-laugh-affection-playable.wav` NEW sample temp 0.7: `I really like having you here. Even an ordinary afternoon feels a little more special.` SHA256 `1B5392A93E08848D594E0D03C98B3E52493EAF8A7A37B8FD4ADAEC8C377BCD92`, 4.44s.
- Source edit details recorded in `cheesecake-source-edit.json` under same directory.

After voice export generated 2 new samples with Pocket TTS at `--temperature 0.7 --language english --device cpu`. Generated audio WAV headers repaired by canonical finalizer, PCM samples verified byte-identical. No pitch applied after generation. Signal QA `hands-ritsu-cheesecake-no-laugh-warm-audition-signal-qa-20261023` exit 0, no clipping or static-like start for the new clips.

**Desktop playback completed in four ordered clips, 3sec gaps, interactive session 1**: (1) edited −1 Cheesecake speech-only reference, (2) previous Ocean Dream Warm −1 baseline, (3) new Cheesecake Warm standard sentence, (4) new Cheesecake Warm affectionate sentence. One-shot ticket `hands-ritsu-cheesecake-clean-vs-ocean-warm-four-auditions-20261023`, all FFplay exit 0, 10:34:48–10:35:16 CDT. **USER HAS NOT YET CONFIRMED whether these clips were heard or whether any new Warm is accepted**. Do not infer from FFplay exit. No existing settings or stored states overwritten; prior Cheesecake clone rejection still applies to its **unedited** source, not to this new cleaned experiment.

Other receipts: `hands-ritsu-cheesecake-laugh-segment-forensics-20261023` 10ms audio RMS analysis, `hands-ritsu-cheesecake-speech-laugh-cut-first-20261023` waveform edit, `hands-ritsu-cheesecake-clean-speech-minus1-reference-20261023` pitch bake, `hands-ritsu-warm-clean-cheesecake-clone-20261023` clone export, `hands-ritsu-cheesecake-warm-no-laugh-two-tests-20261023` synthesis.

Next: listen to user's verdict on whether edited source still contains laughter or abrupt join, and whether new Pocket Warm voice is genuinely more affectionate, without unnatural laughter. If laughs persist, inspect edited source further and refine cut; otherwise consider promoting only after explicit user approval.

---


## New Delighted reference experiment, avoiding pitch-only fixes (2026-10-23)

**Owner verdict on prior −1/−2 Delighted pitch comparison:** Delighted still feels like a different person/voice relative to the rest of Ritsu's repertoire, and an additional −1 reference semitone to −2 did **not** improve identity. So **do NOT promote the −2 happy_00112 Delighted state**. A different source performance is more plausible than further pitch adjustment. Owner says other voices mostly sound similar; the Warm/Desire voice still lacks a certain amount of tenderness but is otherwise acceptable at −1. Upset could be reserved for roleplay, not required as everyday personality.

New targeted Delighted candidate from **different** `ex04_happy_00111.wav`, already owner-auditioned earlier as too exuberant/friendly for Warm, therefore plausibly appropriate to Delighted while better anchoring vocal identity. Kept same base pitch: reference −1 semitone via Rubberband formant-preserved directly on ORIGINAL, tempo=1, pitch=0.9438743126816935, output PCM16 mono 48kHz. NO extra/output pitch shift. No original state changed, no live promotion.

Original source: `C:/Users/dclar/workspace/ritsu-expresso-auditions/ex04_happy_00111.wav`, SHA256 `D1A4811384DC02990DC1A931D78B2EC2598730ED70988959E44143CF352B7921`.
New artifacts under `C:/Users/dclar/Documents/Codex/Venice/PocketTTS/voice-candidates/delighted-alternate-happy00111-20261023/`: (1) `ex04-happy00111-minus1-formant-pcm16.wav` SHA256 `B5E005AA4F5DAE71E8F89FE9425BF36F2DC9D0F3202C838B45B60C53428C33E1`, 3.071292s; (2) `ritsu-delighted-alternate-happy00111-minus1.safetensors` SHA256 `F0136C7AF7424314B3BC51F5234CCE63A95B210372C3D43591E6E6DE207F17C5`; (3) `ritsu-delighted-alternate-happy00111-minus1-test-playable.wav` SHA256 `4385A1261F3F80D1F51DDFB7244255062185339F2D96D60F22916FE32C041155`, 3.16s. Pocket temp=0.7, generated sentence **exactly** `Oh, that's wonderful! I'm so glad it worked out.`. WAV finalizer changed only headers, PCM sample data verified byte-identical.

Waveform QA receipt `hands-ritsu-new-delighted-happy111-threeway-signal-qa-20261023`, exit 0: compare Warm −1 4.84s, previous Delighted happy00112 −1 3.72s, NEW Delighted happy00111 −1 3.16s; new RMS −26.89dBFS, zcr .096, peak .355, no clipping/no noise-like intro.

Desktop auditory comparison played one shot with 3s gaps, *in order*: (1) Warm Ocean Dream −1 baseline, (2) Delighted original source happy00112 −1, (3) **new alternate Delighted happy00111 −1**, on THECAULDRON interactive session 1 at 10:24:05–10:24:24 CDT; each FFplay exit=0. Receipt `hands-ritsu-delighted-happy111-compare-old-and-warm-playonce-20261023`. Owner has **not yet confirmed hearing or new alternate Delighted verdict**, do not mark accepted. Existing prior accepted original-pitch happy00112 Delighted preserved; later shifted happy00112 variants are not automatically approved.

Reference prep receipt `hands-ritsu-delighted-alt-happy111-minus1-prep-20261023`, export `hands-ritsu-delighted-alt-happy111-minus1-export-20261023`, generation `hands-ritsu-delighted-alt-happy111-minus1-synthesis-20261023`. Do not solve identity mismatch by blindly shifting further. Next get owner hearing verdict on new source and compare timbre similarity vs Warm/Amused; if it still sounds dissimilar, try using Warm as common identity anchor or alternative multi-utterance concatenated reference with carefully controlled emotion, but don't overwrite defaults.

---


## Owner correction: −2 experiment is DELIGHTED, not Desire (2026-10-23)

**Explicit newest user correction:** 'Whoops. Not desire, delighted, desire was fine though it is lacking a certain amount of warmth.' This supersedes the previous ambiguous request to shift 'the desire voice' one more semitone. Thus **only DELIGHTED needs the new -2 semitone experiment**, while **Desire/Ocean Dream Warm remains at -1 semitone**. Its warmth/voice-identity concerns should be explored through source/performance selection, not assumed to be solvable with lowering pitch. Upset can remain a roleplay-special-purpose candidate, not ordinary conversation.

An earlier -2 warm Ocean Dream experiment was generated before the correction. Its original source SHA256 `08364A79C54F806F0714F05A8CCA22A3724AA54B06CCA168657B269ADDA1B40E` -> -2 48kHz PCM16 formant-preserved reference `voice-candidates/minus2-experiment-20261023/warm-desire02-minus2-formant-pcm16-48k.wav` SHA `FE8A813C36F19F956A93187F28E6D20AC060B8173A6389CFC40ECE4A487A1DC1`; clone `ritsu-warm-ocean-minus2-pocket.safetensors` SHA `516C6B8DF40F128854F1DA16C605326FB20995CA187EFEA8F3FD77E15B2C3BDC`; generated WAV `ritsu-warm-ocean-minus2-comparison-playable.wav` SHA `582613B1B4F053157919CE9F4CCB3EDE7CD7F150E736EB82833F4FECBA7AB488`. This unwanted target had already been played compared to the -1 Warm at 10:06:22–10:06:35 CDT with successful FFplay, receipt `hands-ritsu-ocean-warm-minus1-minus2-compare-playonce-20261023`. **Do not promote the -2 Warm experiment; leave existing -1 Warm candidate unchanged.**

**Corrected DELIGHTED −2 candidate** regenerated from **original, unshifted** `workspace/ritsu-expresso-auditions/ex04_happy_00112.wav` SHA256 `6F5342EC0F32DB5276408ECA182D3CBC32A9F03E46CA6230B4161D4FE802400C`, with FFmpeg Rubberband `tempo=1:pitch=0.8908987181403393:formant=preserved` directly applied ONCE to the reference, encoding mono 48kHz PCM16. Do not shift the already −1 source to avoid multiple resampling rounds, and do not post-shift Pocket generated WAV.

- Prepared −2 reference: `C:/Users/dclar/Documents/Codex/Venice/PocketTTS/voice-candidates/minus2-delighted-experiment-20261023/ex04-happy00112-minus2-formant-pcm16-48k.wav`, SHA256 `FEF76A4CEEEEFDDD789276BCD9F39A598370F295CDBFACE67A7E09B5137DB4E2`, duration 3.103271s.
- Separate new Pocket clone: `.../minus2-delighted-experiment-20261023/ritsu-delighted-happy00112-minus2-pocket.safetensors`, SHA256 `44C282D2DFD95C20D98564320F170B9B09E0800600A091F58AF01A8BF48ADDD1`, 1,967,336 bytes.
- New audition text exactly matching −1 preview: `Oh, that's wonderful! I'm so glad it worked out.` Pocket temp 0.7, language English, CPU. Playable WAV: `.../minus2-delighted-experiment-20261023/ritsu-delighted-happy00112-minus2-test-playable.wav`, SHA256 `E896D27DE214AA619E653AE8A2C027ED50764F261A9F19128E1096BE56850E3B`, duration 3.64s. Header-only finalize verified all PCM sample bytes identical before/after. Signal QA RMS -29.97dBFS, peak .275, opening zero-cross .081, no static flags.
- Compared preexisting −1 Delighted preview from `voice-candidates/fullset-20261023/delighted-playable.wav`, SHA256 `950BC2D36E1125B2163830411BEC6866202CE370EC6F33757BF3B63A1B571B48` (3.72s) to new −2 Delighted above. Played in that order, with 3s pause, interactive desktop Windows session 1, 10:10:40–10:10:51 CDT, both exit 0, guarded one-shot `hands-ritsu-delighted-minus1-minus2-desktop-compare-20261023`.
- Receipts: reference bake `hands-ritsu-delighted-minus2-original-reference-bake-20261023`, clone `hands-ritsu-delighted-minus2-pocket-clone-20261023`, generation `hands-ritsu-delighted-minus2-generate-audition-20261023`, signal QA `hands-ritsu-delighted-minus1-minus2-QA-20261023`, audition `hands-ritsu-delighted-minus1-minus2-desktop-compare-20261023`. All completed exit 0. **User has not yet provided subjective verdict on new −2 Delighted.**

No live profile switches or phone relay activation occurred. Previous accepted Delighted −1/original-pitch states, Warm −1, Somber, Amused, Whisper, Upset remain saved. Do not confuse Delighted source label `happy_00112` with Desire source `ocean-dream`.

---


## Complete six-voice Pocket rebuild, minus-one references (2026-10-23)

User explicitly requested fresh clone exports and a single sequential desktop audition of the full voice set including already pitch-adjusted Whisper and Amused.
All six are freshly exported from the EXACT verified pitch-lowered conditioning references, with no pitch processing applied to generated speech. Only the WAV header finalizer touched output containers, not their sample data. Temperature 0.7 on CPU for all.
All six separate new voice states and preview WAVs are under C:/Users/dclar/Documents/Codex/Venice/PocketTTS/voice-candidates/fullset-20261023. State name is ROLE-minus1.safetensors; preview name ROLE-playable.wav.

| Playback order | Role | Reference SHA256 | Fresh state SHA256 | Fresh WAV SHA256 | Seconds |
|---|---|---|---|---|---|
| 1 | Warm / Normal (Ocean Dream) | 45032B1B34872CBBD671FEAB16431F9BC768BE03582EE0FBC1DBC95DF8905F66 | 043D61FCA49B175C88A41734D1A659ED9655D39BDE8BD5FA2038AFC35D7FBB36 | 551E50374E86A85351BC0CD53109E97F95BB2E2DC4F53DA40B08EA493D7D326E | 4.84 |
| 2 | Delighted (happy_00112, no laugh) | 20A36E295FCE95820F87B9AC34D5036DC8929CBB39282182EC3BCAF56BC331BE | 050A501F67F83A3876183BEFD649806265B844BFC13BB21D967FC37C0456427A | 950BC2D36E1125B2163830411BEC6866202CE370EC6F33757BF3B63A1B571B48 | 3.72 |
| 3 | Amused (laughing_00044) | A66971D3C28B7B63EB805F2CFEE90B0F1FB5FBA8AFCC4DE225419578C66D3DCA | 6F878B05D4227E10B43BB0AA8A87C6CBDF909B9CCA0F4A845E28C6541F17D9FE | A786C67404F0A7B447F778B8A4B29BFBB9A8FE1B4E324B9579A1D0E60E03B454 | 3.24 |
| 4 | Somber (Personal Affirmation, not Cheesecake) | 3CE376A8EC112B1803D9A61C3C0F706E013FDED4BCB39C9A5EFF81F3D3C936C4 | 51C7B4F55361082ED23ABB56E1F7E9878D4CA26DA5740349858BDBDF2A4CA0BD | 50992DE6DA1E6209634B01AB133FA8A69091E804E436EB70EA1E3E764CF35A59 | 4.52 |
| 5 | Whisper (original approved pitched Qwen output) | 673F2A3EB7119F91E58CAABBE188237AE677B27DFB40A39D44A225A3E891DC3C | B99EB2E16612E8B8C3E3A96F74BD631676CC79071779537FD94C564DB5796BE5 | 1BA1788CA34B161C98F63A6C2631441860144366EB97AA89EBF3A38D10866A9D | 4.20 |
| 6 | Upset (confused_00043) | 8D4398610B3041A523ADCEBC0B98174C13E0E58D1660C3059BD50323C7ECED9C | 4A90D110D178B12B91A485265C7DD77828EF3647FDF8592F37DC44A5395F8E87 | 86584B51F53894FB3C0F758365062EA27F84F11826E1BA7BE6A16430AF215E74 | 3.80 |

Verified actual conditioning references: Warm voice-candidates/minus1-prepared-20261023/warm-desire02-minus1-formant-pcm16-48k.wav; Delighted workspace/ritsu-faster-qwen3-tts/ritsu-pitched-references/ex04_happy_00112.wav; Amused same prepared directory/ex04_laughing_00044.wav; Somber voice-candidates/minus1-prepared-20261023/somber-desire01-minus1-formant-pcm16-48k.wav; Whisper workspace/ritsu-faster-qwen3-tts/ex04-whisper-v1-lower-1st-20261022.wav; Upset workspace/ritsu-faster-qwen3-tts/ritsu-pitched-references/ex04_confused_00043.wav.
IMPORTANT: Whisper's existing accepted Pocket state was cloned from the -1 lowered Qwen whisper WAV (24kHz), NOT the raw ex04 whisper file or its prepared Expresso form. Rebuilt Whisper state SHA256 matches its earlier approved minus-one voice state. Other five previously built states also reproduced their state hashes where applicable. Upset had no Pocket state previously and was exported as a new distinct voice.

Test scripts: Warm and Somber 'Good morning. The workshop is quiet, the coffee is ready, and I have a few ideas.'; Delighted 'Oh, that's wonderful! I'm so glad it worked out.'; Amused 'Well, look at you! Someone's feeling clever today.'; Whisper 'I'm right here, darling. Everything is quiet tonight.'; Upset 'Wait, what happened? I thought we had this working.'
Preflight receipts hands-ritsu-full-repertoire-pocket-state-inventory-20261023, hands-ritsu-full-repertoire-whisper-upset-provenance-20261023, hands-ritsu-fullset-whisper-real-source-check-20261023.
Clone+generation receipts: hands-ritsu-fullset-rebuild-warm-20261023, hands-ritsu-fullset-rebuild-delighted-20261023, hands-ritsu-fullset-rebuild-amused-20261023, hands-ritsu-fullset-rebuild-somber-20261023, hands-ritsu-fullset-rebuild-whisper-20261023, hands-ritsu-fullset-rebuild-upset-20261023. All completed exit 0.
Signal QA receipt hands-ritsu-full-repertoire-six-preview-signal-qa-20261023, completed exit 0. All PCM16 mono 24000 Hz, reasonable RMS and zero crossing, no detected high noise or clipping. Machine-readable output hashes and QA are in fullset-20261023/fullset-manifest.json.
Playback receipt hands-ritsu-fullset-20261023-six-voices-sequential-desktop-playonce, completed exit 0, Windows interactive desktop session 1, direct guarded FFplay -loop 1, 3-second gaps, 09:55:11 to 09:55:53 CDT, each six player exit codes 0.
User HEARD verdict on this fresh complete set is not yet returned. Do not infer emotional approval from playback. Existing accepted reference previews, previous states and live API settings are untouched; no phone audio claim. Continue respecting Warm=Ocean Dream, Somber=Personal Affirmation, Cheesecake rejected, no laughs in Delighted.

---


## Pocket −1 semitone alignment: Delighted, Warm, Somber (2026-10-23)

Owner requested: "redo the delighted clip and any others that didn't get caught" after noticing mixed semitone-pitched voice tests. Audited all approved/current Pocket variants before changes.

**Audit:** The original Oct 23 Pocket Delighted, Ocean Dream Warm, and Personal Affirmation Somber candidate had been created at **original pitch**, without the intended −1 semitone reference transformation. **Amused** already uses canonical `ex04_laughing_00044.wav` −1-prebaked source, and the accepted **Whisper** state `ritsu-whisper-approved-minus1-20261023.safetensors` SHA256 `B99EB2E16612E8B8C3E3A96F74BD631676CC79071779537FD94C564DB5796BE5` is already a minus-one version. Do not double-shift these. Older original-pitch versions remain immutable for comparison.

Applied canonical pitch transformation **once to the *reference***: FFmpeg `rubberband=tempo=1:pitch=0.9438743126816935:formant=preserved` with 48 kHz mono, PCM16 output. For Delighted, reused **already existing** baked prepared reference; for Warm and Somber, created and SHA256-verified their own references from original Expresso 24-bit sources. This also avoids Pocket's historical PCM24 decoding bug; a separate decoder patch was previously installed/tested. Do NOT shift the generated output again.

| Emotion | Baked −1 reference / SHA256 | NEW separate Pocket clone / SHA256 | NEW playable audition WAV / SHA256 | Result |
|---|---|---|---|---|
| **Delighted** (no laughs) | existing `C:\Users\dclar\workspace\ritsu-faster-qwen3-tts\ritsu-pitched-references\ex04_happy_00112.wav` / `20A36E295FCE95820F87B9AC34D5036DC8929CBB39282182EC3BCAF56BC331BE` | `ritsu-delighted-happy00112-minus1-pocket-20261023.safetensors` / `050A501F67F83A3876183BEFD649806265B844BFC13BB21D967FC37C0456427A` | `ritsu-delighted-happy00112-minus1-test-20261023-playable.wav` / `6FA980FAA33FDD879FF453CE0CFE7702B6D342347B50BA20DDDD02771C02E65F` | 3.32s, nonstatic, FFplay completed |
| **Warm** (Ocean Dream) | `minus1-prepared-20261023/warm-desire02-minus1-formant-pcm16-48k.wav` / `45032B1B34872CBBD671FEAB16431F9BC768BE03582EE0FBC1DBC95DF8905F66` | `ritsu-warm-desire02-minus1-pocket-20261023.safetensors` / `043D61FCA49B175C88A41734D1A659ED9655D39BDE8BD5FA2038AFC35D7FBB36` | `ritsu-warm-desire02-minus1-test-20261023-playable.wav` / `E1908BDE3554F633E8BA37CF8F06452C173D9DC9E20DD1086A384C1F6C1235DF` | 4.12s, nonstatic, FFplay completed |
| **Somber** (Personal Affirmation, *not* Cheesecake) | `minus1-prepared-20261023/somber-desire01-minus1-formant-pcm16-48k.wav` / `3CE376A8EC112B1803D9A61C3C0F706E013FDED4BCB39C9A5EFF81F3D3C936C4` | `ritsu-somber-desire01-minus1-pocket-20261023.safetensors` / `51C7B4F55361082ED23ABB56E1F7E9878D4CA26DA5740349858BDBDF2A4CA0BD` | `ritsu-somber-desire01-minus1-test-20261023-playable.wav` / `5AE8CE88590DA742011C460D2EF42B86AACE3F22615E8F76967EE4ED0F573885` | 4.28s, nonstatic, FFplay completed |

All NEW states/audio live in `C:\Users\dclar\Documents\Codex\Venice\PocketTTS\voice-candidates\` on THECAULDRON; relative `minus1-prepared-20261023` is inside that directory. Testing used Pocket temperature `0.7`, CPU, one state/export per voice, header-only WAV finalizer preserving sample bytes. Delighted test text `Oh, that's wonderful! I'm so glad it worked out.` Warm and Somber both use `Good morning. The workshop is quiet, the coffee is ready, and I have a few ideas.`

**Preflight receipt** `hands-ritsu-voice-minus1-audit-simple-20261023`; reference bake `hands-ritsu-minus1-warm-somber-reference-bake-20261023`; clone exports `hands-ritsu-delighted-minus1-voice-export-20261023-retry`, `hands-ritsu-minus1-warm-export-20261023`, `hands-ritsu-minus1-somber-export-20261023`; synthesis `hands-ritsu-delighted-minus1-synthesis-20261023`, `hands-ritsu-warm-minus1-synthesis-20261023`, `hands-ritsu-somber-minus1-synthesis-20261023`; QA `hands-ritsu-minus1-three-clips-no-static-signal-check-20261023`, completed exit 0 for all clips. Signal QA: RMS dBFS −29/−26.7/−31, zero-crossing .081/.083/.071 respectively.

**Desktop playback receipt** `hands-ritsu-minus1-delighted-warm-somber-play-three-20261023`, completed exit 0, interactive Windows session 1, direct guarded FFplay sequential one-shot with 3s pauses: Delighted 09:40:29–09:40:34 CDT, Warm 09:40:37–09:40:41 CDT, Somber 09:40:45–09:40:49 CDT. The user has **NOT YET** reported hearing/quality verdict for these newly lowered samples; previous favorable feedback applies to the earlier original-pitch versions. **No live API profile, default, Qwen, Whisper or phone routing updated**.

**Next:** await owner subjective comparison before promoting any corrected state; distinguish source pitch correction from exact output pitch (conditioning with a lowered reference can influence pitch but does not prove every generated syllable is exactly −1 semitone). Never overwrite the previously approved Delighted original-pitch clone. Preserve Cheesecake rejection and Somber = Personal Affirmation.



## Amused Pocket minus-one-semitone audition and pitch clarification (2026-10-23)

- Owner noticed recently generated Pocket Delighted sounded higher than the prior carefully chosen Ritsu pitch and explicitly asked whether we were still applying the **−1 semitone** adjustment. **We were not:** the Oct-23 Pocket Warm, Somber, and Delighted auditions cloned raw source/reference recordings at their original pitch. Do not claim the prior -1 was retained. Their delivery-quality verdicts remain as recorded, but pitch is not yet aligned to prior repertoire.
- The **existing canonical pipeline** baked −1 semitone **exactly once** into prepared reference WAVs, using FFmpeg Rubberband with **formant preserved**; source metadata `C:\Users\dclar\workspace\ritsu-faster-qwen3-tts\ritsu-pitched-references\bake-manifest.json`, with prepared files for normal, whisper, amused, happy, upset, somber. Specifically:
  - Original Amused reference: `C:\Users\dclar\workspace\ritsu-expresso-auditions\ex04_laughing_00044.wav`, SHA256 `CE3C953433BA90A82E05B5E0058230A92F510738F8DB91E3090860B88BD7C6FE`.
  - Baked **−1** Amused reference: `C:\Users\dclar\workspace\ritsu-faster-qwen3-tts\ritsu-pitched-references\ex04_laughing_00044.wav`, SHA256 `A66971D3C28B7B63EB805F2CFEE90B0F1FB5FBA8AFCC4DE225419578C66D3DCA`, manifestation `pitchSemitonesBaked=-1`, `rubberbandFormant=preserved`.
  - Delighted `ex04_happy_00112.wav` has an existing baked **−1** source in the same prepared folder, SHA256 `20A36E295FCE95820F87B9AC34D5036DC8929CBB39282182EC3BCaf56BC331BE` (case-insensitive). The Pocket Delighted state that the owner liked was cloned from the **unshifted** reference instead. Preserve it unchanged and do not claim pitch is corrected until owner approves a different preview.
- Owner authorized **laughter experiments only for Amused**, not Delighted. Exported new **separate Pocket Amused clone from the already baked −1 Amused reference**, with no second pitch-shift stage: `C:\Users\dclar\Documents\Codex\Venice\PocketTTS\voice-candidates\ritsu-amused-laughing00044-minus1-pocket-20261023.safetensors`, SHA256 `6F878B05D4227E10B43BB0AA8A87C6CBDF909B9CCA0F4A845E28C6541F17D9FE`; Windows ticket `hands-ritsu-amused-00044-baked-minus1-pocket-clone-20261023-0934` completed exit 0.
- Generated at Pocket temp 0.7: `Well, look at you! Someone's feeling clever today.` New playable WAV `ritsu-amused-laughing00044-minus1-test-20261023-playable.wav`, SHA256 `7CCDB6C15341202AFD23A44D2B884947ADCCFA33B1426550F03DBC95911F5048`, 3.48 sec, PCM16/24 kHz, waveform nonstatic RMS −23.61 dBFS, ZCR .083, peak .559; test ticket `hands-ritsu-amused-laughing00044-minus1-synth-qa-20261023-0935` completed exit 0.
- Desktop one-shot FFplay in Windows interactive session 1, started 09:31:35 CDT, ended 09:31:39, exit 0, ticket `hands-ritsu-amused-laughing00044-minus1-playonce-20261023-0936`. **OWNER AUDITORY VERDICT PENDING**, do not claim HEARD or approved.
- No live voice routing, Qwen state, accepted Delighted, Warm, Somber, or Whisper voices changed. Keep exact pitch-source vs output provenance; never double-apply pitch.



## Approved Pocket Delighted voice and next Amused experiment (2026-10-23)

- Owner **approved the new Pocket Delighted audition** with the exact words **"That will do very well!"** This is an auditory acceptance, distinct from earlier FFplay-completed receipt. Reference: existing `C:\Users\dclar\workspace\ritsu-expresso-auditions\ex04_happy_00112.wav`, SHA256 `6F5342EC0F32DB5276408ECA182D3CBC32A9F03E46CA6230B4161D4FE802400C`; it also powered the previously owner-approved Qwen Delighted Option 2. Pocket state: `C:\Users\dclar\Documents\Codex\Venice\PocketTTS\voice-candidates\ritsu-delighted-happy00112-pocket-20261023.safetensors`, SHA256 `47089F6F552D9E8FDEF599C3917B958FE4850CCD9B875662996F77214F5DD3A6`. Generated Pocket test words `Oh, that's wonderful! I'm so glad it worked out.` at temperature 0.7; playable WAV `ritsu-delighted-happy00112-test-20261023-playable.wav` SHA256 `C247EE991760DF7760910355CE293079C120C811C354CB3DBF62D5FD99B36423`, 3.72 seconds, nonstatic pass; desktop ticket `hands-ritsu-delighted-happy00112-pocket-playonce-20261023-0950` completed exit 0. Mark **voice accepted/keeper** but **not yet promoted into the live API nor verified on phone**.
- Owner specifically says **do not add laughter to Delighted**. New separate instruction: **experiment with laughing/Amused Ritsu using the previously approved Amused reference**. Earlier repertoire manifest points at `C:\Users\dclar\workspace\ritsu-expresso-auditions\ex04_laughing_00044.wav`, SHA256 `CE3C953433BA90A82E05B5E0058230A92F510738F8DB91E3090860B88BD7C6FE`; originally approved Qwen amused words: `I did actually! the kids were watching "Animaniacs" over the weekend. I still love that show!`; source original audio in mono PCM16 48kHz, ~7.05 seconds. One new Pocket Amused candidate should be tested independently, with careful laughter quality check and no profile default changes. User is willing to experiment on Amused, not on Delighted.



## FINAL USER VERDICT: Pocket Desire clone auditions (2026-10-23)

**Authoritative owner correction: Ocean Dream = Warm, Personal Affirmation = Somber candidate, Cheesecake Wish = REJECTED. This supersedes any earlier swapped descriptions and "verdict pending" text.** The user's numbering here refers to the order in which the three *Pocket clone* candidates were heard, **not** the numbering of the original Expresso source samples. Preserve both numbering systems:

| Pocket audition order | Source Expresso sample | Pocket clone file (THECAULDRON voice-candidates) | User verdict |
|---|---|---|---|
| **First** | **Original source #2**, `ex04-desire-02-ocean-dream.wav` | `ritsu-warm-desire02-pcm16-fixed-20261023.safetensors` SHA256 `2832900AC63E746E1FE5BDA1CC66B37472E190982C7401176C2A72C00C8A04DB` | **BEST / preferred affectionate Warm candidate.** Sounds nice and acceptable, natural attentiveness rather than theatrical happiness. Keep as the selected *candidate*; do not silently change live API default. |
| **Second** | **Original source #3**, `ex04-desire-03-cheesecake-wish.wav` | `ritsu-warm-desire03-pcm24-corrected-20261023.safetensors` SHA256 `062900A9C3AC5F778BA75E6324ED1C45EA83AAF4F577005D0703A427689F9194` | **REJECTED.** Owner found an unnatural interpretation of the laugh; do not use for Warm, Somber, or the everyday profile. |
| **Third** | **Original source #1**, `ex04-desire-01-personal-affirmation.wav` | `ritsu-warm-desire01-pcm24-corrected-20261023.safetensors` SHA256 `9B413ADAD2A126B9BD06AFD950BC15B9B6CEAE1CFF598132266035E0F01BFF90` | **Candidate for SOMBER, not Warm.** User says the Personal Affirmation Pocket clone sounded somber and could be used in that role. Preserve as a candidate; do not change live profile without explicit acceptance. |

Technical details:
- Before fixing the input, original source #2 was 24-bit WAV, but installed Pocket `audio_read` unconditionally treated bytes as 16-bit, creating horrifying loud static and a male voice. Bad state `ritsu-warm-desire02-pocket-20261023.safetensors`, SHA256 `50EBEF7D0A9600318BFECCB7B44713A84AB7E937E69ECB494E8DC14B90ED641F`, is **quarantined/rejected**; NEVER restore it. The old generated 9.32s WAV `ritsu-warm-desire02-pocket-test-20261023-playable.wav`, SHA256 `3904E2C841005B24E18A2B2556FB13D15864E8E63D3A332441FF791B73AD9539`, contains harsh noise.
- The properly converted, waveform-verified reference #2 `C:\Users\dclar\workspace\ritsu-expresso-auditions\desire\ex04-desire-02-ocean-dream-pocket-pcm16-48k.wav`, SHA256 `E79302AE3C58E11E84836DFFF0DFCDDA4673C9D6D3328CF1590E385AFE9A2ECE`, produced the preferred Pocket Warm clone. Test WAV `ritsu-warm-desire02-pcm16-fixed-test-20261023-playable.wav`, SHA256 `F68C2CA43ABB50D48317D8D23C331D4523D1D2C6B41825A4F2A0ECE3549A5DFA`, ~5.0s. Desktop session 1 playback ticket `hands-ritsu-desire02-16bit-repaired-desktop-playonce-20261023-0849`, exit 0, user **HEARD** and said "That sounded nice, I can live with it." Warm ranking reconfirmed after subsequent auditions.
- Patched installed `C:\Users\dclar\Documents\Codex\Venice\PocketTTS\.venv\Lib\site-packages\pocket_tts\data\audio.py` to decode PCM byte widths 1/2/3/4 correctly; patched SHA256 `ABF314557B64A41DD85204F9653A09609BA2992E417A451BC332CEFAC2C87606`, backup `audio.py.pre-20261023-pcm24-fix.bak` SHA256 `A51EF79C94C0F72C3C4F8B496CA9E0F2B903D17C5F9F720D9C71D2BCF64D22BF`. Fixed decoder regression checked 24-bit vs PCM16 every sample: max delta ~3.04e-5, edge-value sample tests passed, ticket `hands-ritsu-pocket-install-pcm24-decoder-regression-20261023-0850`, exit 0. Preserve this fix in reproducible repo tooling, or use converted 16-bit conditioning references; pip upgrades may overwrite local site-packages modification.
- Source #3 corrected clone generated test WAV `ritsu-warm-desire03-pcm24-corrected-test-20261023-playable.wav` SHA256 `8CEB5836D6F78A7929CE96D07ED21D643D66984EDBC96321038519CDC942FD5D`, 4.84s, low-noise precheck succeeded. Owner heard this version and **rejected it for an unnatural laugh interpretation**; no FFplay ticket from this executor was logged for #3 but owner confirmed auditioning it. Do not claim remote FFplay success without receipt. Do not claim remote FFplay success without receipt.
- Source #1 corrected clone generated test WAV `ritsu-warm-desire01-pcm24-corrected-test-20261023-playable.wav` SHA256 `509587741ACD77F2FFA696EB50C77F110A815893DFF5C142150DCCD236B74D0B`, 4.2s, passed non-noise signal precheck. Desktop playback `hands-ritsu-desire01-corrected-desktop-playonce-20261023-0858` completed exit 0. Owner says **this** (Personal Affirmation) clone is the **Somber candidate**, not Warm; do not classify it as rejected.
- All experiments use Pocket default temperature `0.7` and same comparison sentence: "Good morning. The workshop is quiet, the coffee is ready, and I have a few ideas." Original records / other voice states remain unchanged; **no voice profile has been promoted in the live API, and phone delivery has not been verified.**

**Next action**: preserve best Warm = corrected Desire Ocean Dream clone. Somber candidate = corrected Desire Personal Affirmation clone (SOURCE #1 / THIRD Pocket audition); validate it as Somber before any live-profile reassignment. Corrected Desire Cheesecake Wish clone (SOURCE #3 / SECOND Pocket audition) is REJECTED due to unnatural laugh. Do not mistakenly use original source #1 for Warm because user said "one remains the best": that refers to the **first auditioned Pocket clone** (based on source #2), not source WAV #1.



## Desire source auditions retrieved and played (2026-10-23)

- User wants intimate/flirty loving Ritsu rather than exuberant friendly. Desire is preferred style; owner must audition original ex04 recordings **before** any Pocket cloning. Existing voice states remain unchanged.
- THECAULDRON Windows Hands recovered online. The dataset server's /filter requests timed out and bulk /rows requests caused HTTP 429; bypassed both using HTTP byte ranges on Hugging Face CDN Parquet shard train-00014.parquet in nytopop/expresso-conversational. Installed pyarrow 23.0.1 in isolated PocketTTS/.desire-audition-deps (Windows Python 3.13). Only approx. 47 MB transferred from a 14.8 GB dataset. Attribution-NonCommercial 4.0 license.
- Source files saved on THECAULDRON in C:/Users/dclar/workspace/ritsu-expresso-auditions/desire; provenance manifest ex04-desire-audition-20261023.json. All original mono WAV 48kHz, speaker_id=ex04, style=desire; no effects or synthesis.
- **1** ex04-desire-01-personal-affirmation.wav, 5.325 sec, SHA256 2665C713138D4E51FF6158EA58314C3B984313431685C72D0F53075689A35524; Parquet shard 14 row group 19 row 13. Transcript: “In the end, I wouldn't have thought about it like that, but I really, yeah, I really like it when you put it that way.”
- **2** ex04-desire-02-ocean-dream.wav, 7.965 sec, SHA256 08364A79C54F806F0714F05A8CCA22A3724AA54B06CCA168657B269ADDA1B40E; Parquet shard 14 row group 5 row 5. Transcript: “And because I've never been to Maine and I would love to be on the coast like that, somewhere by the ocean, with the house overlooking everything.”
- **3** ex04-desire-03-cheesecake-wish.wav, 3.725 sec, SHA256 C68E97E636F4F460CB0792BE4279F17D9C476C501914E6C15ED778F282061D6C; Parquet shard 14 row group 4 row 8. Transcript: “I would love to be at the Cheesecake Factory.”
- Extraction receipt: hands-ritsu-expresso-desire-extract-three-20261023, completed, exit 0. Desktop playback receipt: hands-ritsu-expresso-desire-three-source-auditions-20261023, completed, exit 0; interactive Windows session 1, each FFplay -loop 1 with guard and three-second pause, times 08:34:20–08:34:46 CDT. User HEARD and emotional verdict PENDING; one-shot execution receipt is not ear confirmation.
- Next step is owner selects 1, 2, 3 or neither. Only after choice, run Pocket export-voice and a new generated audition. Do not modify existing Qwen, Warm Pocket, Whisper Pocket or phone routing.


## Pocket Warm affection audition: user-selected reference 2 (2026-10-23)

- Owner preferred **reference 2** among two unmodified original Expresso recordings replayed once each: reference 1 `ex04_happy_00083.wav` (1.53s) vs reference 2 `C:\\Users\\dclar\\workspace\\ritsu-expresso-auditions\\ex04_happy_00111.wav` (3.07s); source 2 SHA-256 `D1A4811384DC02990DC1A931D78B2EC2598730ED70988959E44143CF352B7921`. Chose reference **before** Pocket cloning as owner requested. No new Qwen synthesis, pitch shift or WAV changes to the original.
- Windows Computer Hands `hands-ritsu-choice2-pocket-clone-20261023-0801`: installed Pocket CLI `export-voice` from exact verified source to new independent `C:\\Users\\dclar\\Documents\\Codex\\Venice\\PocketTTS\\voice-candidates\\ritsu-warm-affection-choice2-20261023.safetensors`, 1967336 bytes, SHA-256 `680A6132AF7A076CFB32F60F25AF26565977E1B80D0A34CBD3246304BFC2871E`. Export completed exit 0; prior warm, whisper and venice-canon voice states untouched.
- Windows Computer Hands `hands-ritsu-choice2-pocket-audition-generate-20261023-0802`: generated comparison sentence `Good morning. The workshop is quiet, the coffee is ready, and I have a few ideas.` through Pocket CLI at default **temperature 0.7** using new choice-2 voice state. Raw `ritsu-warm-affection-choice2-test-20261023-raw.wav`, size 259244 bytes SHA-256 `DD1C23E3C77C5D633A43696E62ADE229C6541C630505E3D85B70E32449EB7EB3`. Header-only finalized playable `ritsu-warm-affection-choice2-test-20261023-playable.wav`, size 259244 bytes SHA-256 `7AA2D6DA64ACB1657CDB618D20DB82857342DC4040B60EBFE7F2A60493EEAE7F`. Sample stream unchanged, 129600 mono PCM16 frames at 24kHz = 5.4 sec.
- Windows Computer Hands `hands-ritsu-choice2-pocket-audition-playonce-20261023-0803`: FFplay direct THECAULDRON interactive session 1, one-shot guard, explicit `-loop 1`, started 08:03:33 CDT ended 08:03:39 CDT, exit code 0. **Do not assert HEARD:** owner subjective quality verdict pending. Do not switch live voice until owner confirms this new clone meets desired affection and tone.



## Pocket TTS Warm v1 clone: separate audition (2026-10-23)

- Owner requested cloning the approved **Warm** voice into Pocket TTS, with the possibility of re-audition if the existing Warm personality was too over-the-top. This is **not** the whisper clone and does **not** authorize changing either the Pocket whisper or Qwen live voice default.
- Audio reference **actually verified on THECAULDRON**: `C:\\Users\\dclar\\workspace\\ritsu-faster-qwen3-tts\\ritsu-maxwarm-fullclone-20261022.wav`, 265004 bytes, SHA-256 `B323EC729AD54E907F22425AF275E89ECB35FB7AFFCFA3BAD6763CD29896A3CB`. This is the previously approved Qwen Warm v1 generated sample, not the raw exaggerated Turbo reference. No pitch shift or effects added.
- Installed Pocket TTS `export-voice` generated a **new separate clone** at `C:\\Users\\dclar\\Documents\\Codex\\Venice\\PocketTTS\\voice-candidates\\ritsu-warm-v1-pocket-20261023.safetensors`, 3441904 bytes, SHA-256 `74D30028529D3E23831E849A6ADC5FB3BE32498A946375DC8D41C172221AB269`; Windows Computer Hands ticket `hands-ritsu-warm-pocket-export-20261023-0742` completed exit 0. Existing `venice-canon.safetensors` and `ritsu-whisper-approved-minus1-20261023.safetensors` untouched.
- Pocket-generated **new utterance**, exact text: “Good morning. The workshop is quiet, the coffee is ready, and I have a few ideas.” Ticket `hands-ritsu-warm-pocket-audition-generate-20261023-0743`, exit 0. Raw WAV `ritsu-warm-pocket-audition-20261023-raw.wav` SHA-256 `10683B764293D40A6FB675F5A5FCFCFB754682C35301FE1CA19FE2B793E91943`, size 247724 bytes. Header-only-normalized playable WAV `ritsu-warm-pocket-audition-20261023-playable.wav`, SHA-256 `866CB9A6F68FA130B359BF3F1C0F16394A7F23D9BB707397793E0C9C877D0403`, same size, 247680 PCM bytes (5.16 seconds), audio samples unmodified.
- Played corrected WAV **directly on Windows desktop**, same successful FFplay method, interactive console session 1 at 07:43:53–07:43:58 CDT, exit 0, ticket `hands-ritsu-pocket-warm-desktop-audition-20261023-0744`. **Owner confirmed HEARD**: Pocket dialed down warmth versus the Qwen Warm reference, is acceptable but potentially a bit less warm than desired. Owner would like to explore a **small** increase, with no regression in artifacting. **Owner also reported hearing the clip twice.** Cloud Computer Hands shows only one recorded command submission with one FFplay run (about 5.8 seconds); that is insufficient to explain or deny duplicate audible playback. Duplication root cause remains OPEN, and no repeat audition is authorized until it is investigated; do not declare single-play reliability. Voice cloning does not supply a calibrated "warmth" knob. Test controlled generation settings (e.g. modest variation in temperature) or a better clean expressive reference as *candidate comparisons*, not a guaranteed warmth effect; preserve current state as-is and do not silently postprocess pitch.
- Until owner approves the new Warm candidate, preserve both prior Warm Qwen and Pocket whisper as rollback/comparison; do not deploy this candidate to everyday Pocket/API or phone on this evidence alone.

# PRIOR MISSION: Pocket TTS clone from approved whisper (owner correction, 2026-10-23)

**This section supersedes all conflicting Qwen cutover instructions below.** The actual commissioned outcome is to use the user's **already-approved newly generated −1-semitone whisper WAV as conditioning for a Pocket TTS voice clone**, not to continue deploying the six-profile Qwen repertoire as the final voice. Qwen voice metadata/activation is historical context only, NOT an acceptance test for this Pocket task. Never replace the approved whisper with the raw Expresso whisper or apply an after-generation pitch effect and call it the approved clone.

## Live THECAULDRON execution receipts, 2026-10-23

- **Authoritative approved source WAV:** `C:\Users\dclar\workspace\ritsu-faster-qwen3-tts\ex04-whisper-v1-lower-1st-20261022.wav`, size 146000 bytes, SHA-256 `673F2A3EB7119F91E58CAABBE188237AE677B27DFB40A39D44A225A3E891DC3C`. This is the previously approved lowered Qwen-generated whisper **recording**, used strictly as input to Pocket TTS cloning. The unlowered trial `ex04-whisper-qwen-trial-20261022.wav` and raw `ex04_whisper_00059.wav` are not substitutes.
- **Pocket clone produced on THECAULDRON:** `C:\Users\dclar\Documents\Codex\Venice\PocketTTS\voice-candidates\ritsu-whisper-approved-minus1-20261023.safetensors`, size 1967336 bytes, SHA-256 `B99EB2E16612E8B8C3E3A96F74BD631676CC79071779537FD94C564DB5796BE5`. Exported using the **existing installed Pocket TTS** `export-voice` operation. The original `venice-canon.safetensors` was not replaced.
- **Actual Pocket TTS synthesis test PASSED:** loaded that exported safetensors with installed `pocket-tts generate`, text `Hey, sweetheart. I'm right here, and I'm listening.`, producing `PocketTTS\voice-candidates\ritsu-whisper-pocket-canary-20261023.wav`, 259244 bytes, SHA-256 `D6A532640D86E6645C412D55D15DB2D41666F8415697EA202118EA5B22AF3653`. Engine reported 5.2 seconds of generated audio in 3.625 seconds. These are real **Windows Computer Hands** execution results, not ChatGPT-local simulations.
- **Existing canonical phone relay preflight:** authenticated `127.0.0.1:19643/health` returned `{"ok":true}`; test WAV header verified RIFF/WAVE. The attempt to submit it to the existing relay was **blocked by tool safety checks**. No enqueue or phone ACK receipt was obtained. **User hearing and fidelity remain unverified.**
- No Qwen default routing, existing Pocket `venice-canon` state, phone receiver or token configuration was changed for this clone. No substitution transport permitted. Do not infer that this new Pocket voice is automatically live in the API.
- **Next acceptance gate:** preserve the proven Pocket clone, use the existing authorized phone delivery route when accessible, obtain user audible verdict comparing it with the approved whisper, then and only then select it in the existing Pocket TTS API. After confirmation, verify single-listener status, startup persistence, complete-response speech and phone ACK/HEARD, with explicit receipts.

## Pocket TTS user audition and WAV-header findings (2026-10-23)

- User confirmed **HEARD** on THECAULDRON using the approved-whisper-conditioned **Pocket TTS** clone, not Qwen: “That was good! A little different from the other one but good. No. Artifacting.” Further user comparison: Pocket was **equally good** in voice quality; Qwen (“Quinn”) more often had audible artifacting, and Pocket felt faster; overall Pocket is the preferred candidate with no observed downside in this audition. Do not erase nuanced preference by claiming identical timbre, or claim zero future artifacts.
- Voice state `ritsu-whisper-approved-minus1-20261023.safetensors` remains distinct from the existing Pocket `venice-canon.safetensors`; no live API default was changed solely by desktop playback.
- Original Pocket-generated test `ritsu-whisper-pocket-canary-20261023.wav` 259244 bytes SHA-256 `D6A532640D86E6645C412D55D15DB2D41666F8415697EA202118EA5B22AF3653` used a streaming RIFF/WAV header declaring **2,000,000,000 bytes** of data, though it contained 129600 actual PCM16 frames (mono, 24 kHz, 5.4 seconds). Unmodified PCM SHA-256 `EC1E4BEDF5DB5FEF0A9FCA1EA97BCB8655BD5C6E0E138B6F00D14E1B47046599`.
- Rewritten header-only playback copy `voice-candidates/ritsu-whisper-pocket-canary-20261023-playback-fixed.wav`, SHA-256 `0FD61EFEBA8D1E8E725573B0F85AD16BAB93F51720AB5F93325151C195B28AE1`, has identical PCM. On 2026-10-23 at 07:24 CDT, interactive Windows session 1 used installed FFplay and default Surface Omnisonic Speakers at 64% unmuted; FFplay exit 0, Computer Hands receipt `hands-ritsu-pocket-fixed-desktop-playback-20261023-0728`; user confirmed HEARD and good quality. Earlier SoundPlayer returned 0 but user heard nothing: not a successful audible test.
- **Recurrent header defect confirmed**: earlier Pocket-generated WAVs `venice-pocket-canary-cold.wav`, `venice-pocket-stream-run1.wav`, `chatgpt-desktop-speech-canary.wav` also carry the 2-billion-byte placeholder. Pocket streaming writer `stream_audio_chunks` emits unknown-length headers; existing `embodiment_campaign/tts_adapter.py` / `pocket_audio_cache.py` currently persist streamed bytes without finalizing headers. Correct after capture and before cache/standalone WAV playback without changing PCM; leave low-latency streaming untouched.
- Voice acceptance: candidate acceptable and preferred to Qwen in user's comparative listening. Further API selection/integration and phone transport verification are separate gates. Preserve original voice assets and rollback.

### Saved WAV cache fix installed and Windows-tested (2026-10-23 07:33 CDT)

- Root cause: Pocket `stream_audio_chunks` uses a 2,000,000,000-byte streaming data sentinel; existing `pocket_audio_cache.py:Store.put()` had copied that header unchanged into persistent saved WAVs. This affects WAV metadata and some playback readers, **not the synthesized PCM**.
- Versioned, limited-losslessness repair module committed at `tools/campaigns/ritsu_pocket_wav_finalize.py` and regression tests at `tools/campaigns/test_ritsu_pocket_wav_finalize.py`. Module only repairs the known standard 44-byte PCM RIFF sentinel, verifies layout and alignment, and changes only RIFF/data size fields. Unexpected layouts pass through, invalid known-sentinel PCM is rejected. No synthesis or live streaming behavior changed.
- Actual Windows Pocket root `C:\Users\dclar\Documents\Codex\Venice\PocketTTS`: installed that finalizer and modified existing `pocket_audio_cache.py` to call `finalize_wav_bytes(source.read_bytes())` inside `Store.put`, before writing cache bytes and recording SHA-256. Original cache source backed up as `pocket_audio_cache.py.pre-20261023-voice-wav-size.bak`. Windows finalizer SHA-256 `9A6E891EEE0E653AA0691BDEB5B102AD7B15C4801A1888AB1DB82489612F6CC8`; patched cache SHA-256 `31C2E02060EF798C732975DBB953E0F3D16ADC37E00E95A87504E6EAA7B0983E`.
- Windows Computer Hands: initial test wrapper incorrectly treated Python unittest's normal stderr as PowerShell error (not a code failure). Re-run `python -m unittest test_ritsu_pocket_wav_finalize test_pocket_audio_cache -v` returned **exit 0, 7/7 tests passed**. An independent integration test passed the **real malformed Pocket canary** through `Store.put` with temporary cache, then verified corrected headers (data length 259200), byte-identical PCM, and successful cache `get`. Ticket `hands-ritsu-pocket-cache-regression-and-integration-test-20261023-0733`, **completed, exit 0**.
- Boundaries: The fix is installed and verified for **new saved/cached Pocket WAVs through Store.put**. Existing stored WAVs are left untouched; standalone Pocket CLI output remains streaming-sentinel unless separately finalized. The new approved whisper voice state is not yet selected in the live TTS service. No phone HEARD proof for new clone.


---

**Historical handoff follows. Conflicting instructions below are superseded by the Pocket clone mission above.**

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
