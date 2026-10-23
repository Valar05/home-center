# Ritsu Pocket TTS: Agent-to-Agent Handoff (October 23, 2026)

## LATEST OCTOBER 23, 17:02 CDT OPERATOR RULES AND DEPLOYED TRUTH

**Read this section before the older historical deployment-state notes below.** The Windows sender was replaced live via Home Center Computer Hands, with dry-run tests, atomic backup and fresh hash readback. Live `C:\Users\dclar\workspace\ritsu-faster-qwen3-tts\ritsu_say.py` SHA-256 `3DDA464DF8D5E24D29DB471DF7C7B8D70D28741C98866996A980AFE5443C6AD8` runs one complete agent-authored speech unit per Pocket `/v1/speak`, no sentence regex or heuristic character splitting, exactly one WAV to the same 19643 relay. The live Windows worker/Pocket service, approved five voices and Android receiver were unchanged. Backup `%LOCALAPPDATA%/RitsuWarmTicketWorker/sender-backups/ritsu_say.20261023T165107.pre-no-split.py`. **Previously written statements in this file that the no-split sender is source-only/uninstalled are now superseded.**

**Enforced Pocket cap: at most 450 characters per `/v1/speak` ticket.** This is a per-ticket hard ceiling, *not* a preferred composition length and not permission to auto-split. Ritsu/ChatGPT authors deliberate, full, naturally ended speech thoughts; long visible roleplay is covered via several individually submitted, ordered complete thought tickets, none exceeding the cap. Never cut a sentence, drop a paragraph, silently truncate, or claim complete HEARD coverage from queue/relay receipts.

**Empirical engine latency, live CPU Normal profile, undelivered isolated Pocket jobs:** 112 characters required 3.62s generation and produced 5.84s speech; 183 chars -> 5.83s generation and 10.08s audio; 289 chars -> 9.25s generation and 13.84s audio. Tentative *authoring* targets: first complete useful thought ~90–140 chars, follow-on naturally ended complete thoughts ~180–300 chars. Submit the first complete thought as soon as finalized while composing the rest to optimize first-audio time. These are not programmatic threshold instructions. Do not promise speech before visible text without end-to-end timestamps.

**Android still not fixed:** 58 completed real physical phone playback pairs gave 1.445s median player API end-to-next-start gap; player-reported lifetimes exceed WAV durations; weak leading audio often ~0.47–0.68s before stronger speech. Retained phone receiver v2 source hash begins `8acd8467`; the GitHub receiver draft may differ and must not be blindly deployed. Read-only diagnostic campaign installed on phone; no live silence cutter. Current user request: repair Android per-file handoff without replacing the approved TTS/relay, losing audio words or replaying queue items. Audit on-device installed source and fail-closed progress markers, stage bounded regression tests, back up and idle-gate any receiver cutover, require user HEARD verdict.

Authoritative follow-on: `docs/RITSU_PHONE_AUDIO_LAWS.md`, `docs/RITSU_PHONE_GAP_CAMPAIGN_CHECKPOINT_20261023.md`, and Google Drive companion ledger titled **Ritsu Voice Embodiment — Complete October 21 Companion Ledger**, now containing an October 23 superseding addendum.

## Read this first: newest user directive overrides earlier sentence-chunk experiments

The user explicitly corrected the investigation after multiple unsatisfactory tests:

> "Let me qualify, I would like full paragraphs unless we can get rid of the delay. But I absolutely don't want it to cut out in the middle of a sentence."
>
> "I prefer the agent to have more control than the script that's snipping it without inference."

**AUTHORITATIVE BEHAVIOR:** Ritsu/ChatGPT makes the semantic decisions about natural paragraph boundaries, based on the text and intended performance. Prefer complete, naturally flowing paragraphs rather than isolated sentence recordings. No regex sentence splitter, character-slice, or sender-side guessing about phrasing. Never cut in the middle of a spoken word or sentence. Exactly preserve authored words and order. If a complete paragraph is beyond the engine's current safe rendering limits, refuse rather than silently truncating; have the **agent** deliberately author a shorter but complete paragraph/segment. Longer text in one request is desirable only if verified to generate **complete** speech, not merely one WAV file.

**Current issue not solved:** Owner heard narration from the installed v2 Android receiver but says the gaps were still "very very annoying," perhaps slightly shorter, and it "sounded like the clips were being cut off early only for silence to play." User does not accept sentence-level v2 playback. Do not equate delivery/ACK or presence of waveform with audible completeness.

## Original incoming handoff, retained

**Title:** Handoff: Ritsu Pocket TTS Playback Gap Investigation  
**Date:** October 23, 2026 | Home Center / THECAULDRON

**Mission:** Investigate and eliminate remaining audible pauses between sentences in Ritsu's live phone narration, preserve approved Pocket TTS voices and canonical transport; do not rebuild or replace system.

**Architecture:** ChatGPT → Home Center `ritsu.voice.speak` tickets → Windows ticket worker → local Pocket TTS → canonical audio relay → Android Termux receiver → phone speaker.

- Pocket TTS `127.0.0.1:10205`, relay `19643`.
- Operational laws `Valar05/home-center/docs/RITSU_PHONE_AUDIO_LAWS.md`.
- Pocket source `tools/campaigns/ritsu_pocket_repertoire_server_v2.py`; relay adapter `tools/campaigns/ritsu_pocket_v2_deployed/tts_adapter.py`.
- Current voices use approved Pocket clones, **not retired Qwen engine**.

**Originally discovered:** Long multi-sentence Pocket generation sometimes cuts/omits speech. Earlier change to one grammatical sentence per synthesis ticket improved completeness but created long gaps. Home Center tickets were originally sent sequentially, ack-waiting between submissions. Four to five seconds between Windows relay enqueues was observed. Pocket `ThreadPoolExecutor(max_workers=1)` and a model lock serializes synthesis. The exact cross-device split initially remained unmeasured.

**Original investigation requirement:** Use shared turn ID and sequence across ChatGPT submit/accept, worker lease/start, Pocket submit/generation start/end, relay enqueue/file availability, Android retrieval/actual playback start/end, with UTC and machine-local monotonic clocks. Locate gap end(N)→start(N+1); examine live Windows processes/logs, not just repo sources. Investigate ordered lookahead and safe FIFO buffering without increasing GPU concurrency. Preserve voice/pitch, canonical Tailscale relay, no Qwen fallback, no skipped/truncated/duplicated/out-of-order speech, no unnecessary restarts. Distinguish queued, delivered and user-confirmed HEARD. Measure first-audio latency, audible gaps, total completion and missing audio before/after; conduct user-heard 8–12 sentence regression, commit verified fix and update laws.

**Additional original user request:** Change Normal/Warm voice to Desire 02 -1 test version rather than then-current voice. This change **was completed and live-verified**.

*The original handoff's preference for one grammatical sentence per synthesis ticket and phone-side buffer is SUPERSEDED by the newest user directives at the top of this document.*

## Cross-checked current state, with deploy boundaries

### Existing approved five-voice repertoire

Windows service at `C:\Users\dclar\Documents\Codex\Venice\PocketTTS\ritsu_pocket_repertoire_server_v2.py`, API `127.0.0.1:10205`. Normal/Warm is **Desire 02 Ocean Dream formant-preserved minus-one semitone Pocket clone**, source state `voice-candidates/fullset-20261023/warm-minus1.safetensors`, SHA256 `043D61FCA49B175C88A41734D1A659ED9655D39BDE8BD5FA2038AFC35D7FBB36`. The live `/health` checked that exact Normal hash. Other approved Pocket profiles: Amused -1; Delighted/Happy **preconditioned -1 Pocket clone** (SHA `050A501F67F83A3876183BEFD649806265B844BFC13BB21D967FC37C0456427A`); Somber -1 used for Upset; Whisper -1. No Qwen or post-generation pitch shift. Preserve all choices. Refer to `docs/RITSU_VOICE_HANDOFF_20261023.md` for detailed reference hashes, clones, timing and auditions.

Pocket TTS is actually running **on CPU** on THECAULDRON, not GPU (despite presence of 4GB RTX 3050 Ti), with one executor worker and model mutex. Preflight measured ten short sentences accepted in 0.094 sec, generated 25.60 sec audio in 17.89 sec wall. Don't blindly increase concurrency.

### Windows host/relay improvement (DEPLOYED, but not enough)

Actual Windows active files at last verified readback:
- `C:\Users\dclar\workspace\ritsu-faster-qwen3-tts\ritsu_say.py`, SHA256 `2922EFE848AAD961C96282EB491E4090FCE9DD0891E67CD01FBE1D357AA24B3D`. **Still sentence-regex splitting with 4-job lookahead.**
- `%LOCALAPPDATA%\RitsuWarmTicketWorker\worker.py`, SHA256 `C72A0AC06CB5806D7A4F07A9FD8DE1966979B72CC09EA8E9109C0F157EF43166`. Prior live worker PID `33012` (may change). Passes Home Center ticket ID to sender.
- Pocket server SHA256 `FA679DF591572219AAD33EF958221F2E3A68B2AA7D93AFCCED295968DB5C3B08` and relay adapter SHA256 `85D6AEE9BD0376ADB516A31394ED55F3EFCC38C61D7029A9FAB36AEA43B74208` when last checked.
- Windows backup `PocketTTS/gapfix-desire02-cutover-backups-20261023`. Host timestamps `%LOCALAPPDATA%/RitsuWarmTicketWorker/timing/<ticket-id>.jsonl`.
- Windows host source optimization changed median relay enqueue spacing from historical ~5.5 sec to ~1.371 sec, but user **heard no improvement** in initial test. Android playback was a major component.

### Android receiver v2 (INSTALLED, but audible quality NOT ACCEPTED)

Original live Termux receiver previously had: ACK before play; `termux-media-player play "$FILE" || true`; unconditional `sleep 1`; repeated `termux-media-player info` and `sleep 1`; `sleep 2` idle. This caused a download-after-each-play loop, delayed joins and hid player errors.

User actually installed a v2 prefetch receiver via `bash /sdcard/Download/ritsu_receiver_upgrade.sh` (initial attempt file missing, second attempt success). Real install receipt:
```
RITSU_RECEIVER_V2_INSTALLED=1
NEW_PID=6432
RECEIVER_SOURCE_SHA256=8acd84673b91420dddac5705829e17997ca9dfcde87e5f3d3f35b872f219322f
BACKUP_DIRECTORY=/data/data/com.termux/files/home/.ritsu-embodiment/receiver-backups/20261023T194022Z
TRACE_FILE=/data/data/com.termux/files/home/.ritsu-embodiment/receiver-v2/trace.jsonl
OLD_RECEIVER_WAS_STOPPED_AT_IDLE=1
```
Shell's reported `[1]+ Terminated nohup ... old receiver.sh` was expected old-process retirement, not upgrade failure. Receiver remains on **canonical 19643 relay**, Termux media player, Tailscale; 3-slot ordered prefetch. Android source on disk was checksum-verified at install. **IMPORTANT:** GitHub's `tools/campaigns/ritsu_phone_receiver_prefetch_v2.sh` is a *candidate source*, not guaranteed identical to the installed embedded upgrade file. Verify actual on-device SHA/source and live process before any further patch; don't blindly reinstall source from repo.

First real ten-sentence v2 phone trial: `ritsu-termux-v2-10-sent-audible-fifo-test-20261023-a`, profile Normal, expected 10 WAVs, total 30.96s WAV duration, cloud ticket `enqueued`, Android downloaded all ten in FIFO. First three downloads within ~2 sec indicates actual prefetch. **Owner heard passage** but still disliked clearly audible interclip pauses and said clips seemed cut off early with silence after. Not accepted. Need **phone trace** `receiver-v2/trace.jsonl` to read `playback_started`, `playback_finished`, monotonic deltas. Download receipts are not actual playback timings.

Earlier one-chunk canary `ritsu-gap-phone-control-expired-accurate-status-20261023` was downloaded and ACKed but user initially heard nothing from automatic receiver. Manual Android Termux replay of downloaded `audio/a854816b739c83c3f8c5aaef.wav` resulted in `Now Playing`, `Status: Playing` and user confirmed **"Yes, she speaks"**. Do not infer HEARD from an ACK.

### Exact ten-WAV forensic results (RECORDED)

Source Windows audio `C:\Users\dclar\workspace\ritsu-chatterbox-turbo\generated\ritsu-pocket-*.wav` from local 14:42:40–14:43:06 trial. Ten generated WAVs contained leading very-low-energy runs on some clips around **0.32, 0.36, 0.43, 0.74 and 0.75 seconds**; some files had measurable signal right up to their final tens of milliseconds (possible abrupt sound end). No major long silence spans *inside* most clips. Quiet thresholds and high tail RMS **cannot prove missing words**. Do not trim phonemes automatically or pitch change. Need correlate timestamps to auditory boundary and verify actual words via careful listening/ASR before changing model parameters.

### Newer single-passage source work (COMMITTED and ISOLATED-TESTED, **NOT DEPLOYED**)

Newest repo source:
- `tools/campaigns/ritsu_pocket_v2_deployed/ritsu_say.py` at repo branch main: one **unchanged agent-authored text string** → one Pocket `/v1/speak` job → one finished WAV → one `/v1/deliver`. No script sentence splitter. `MAX_TEXT_CHARS=450` matches **currently deployed Pocket `JobRequest.max_length=450`**, otherwise fails closed. Extra whitespace and punctuation maintained at sender boundary. Repo latest tested source commits `d3ece78` and earlier `aa7a715`.
- `tools/campaigns/ritsu_pocket_v2_deployed/worker.py` repo: a cloud ticket is one agent-authored passage, `expectedChunks>1` refused with `AGENT_AUTHORED_CHUNKS_REQUIRED`, no legacy split option. Commit `a76ed71`.
- `tools/campaigns/ritsu_pocket_v2_deployed/test_ritsu_whole_text.py`, commit `e12eab2`: no-network test passed on Windows, checks exact original paragraph and SHA unchanged, one Pocket request and one relay delivery, length >450 rejected. Test output: `PASS verbatim paragraph, one synth job, one relay WAV, 450-char fail-closed`.
- Staged test directory `PocketTTS/agent-paragraph-stage-20261023`. **Live Windows sender/worker still the earlier multi-sentence version at last readback**; attempted remote cutover failed an early gate without changing those files. Another attempted code patch was blocked by tool safety checks. Do NOT claim installed or work around a safety block. Follow authorized integration paths, inspect hashes and exact live state.
- The current Pocket `/v1/speak` limit is **450 characters**; `/tts` has a different limit (1000) but is not the present async job transport. Home Center cloud accepts up to 5000 text characters, so silent assumptions about length are unsafe.

**Crucial engine-level discovery:** Installed `pocket_tts.TTSModel.generate_audio` collects chunks returned by `generate_audio_stream`. That function itself calls **`split_into_best_sentences(tokenizer, text_to_generate, max_tokens)`** with default `MAX_TOKEN_PER_CHUNK=50`. So **one sender ticket and one WAV do NOT guarantee a single uninterrupted model inference or complete paragraph**. Pocket may internally split/chop long passages even when no external script does. User previously observed long multi-sentence synthesis occasionally missing text. Investigate Pocket internal strategy and validate completeness. Do not merely raise max_tokens or GPU concurrency without careful model tests, or claim full paragraph fidelity without user listening.

### Original voice and transport constraints, unchanged

Preserve approved **Pocket** profiles/pitch; no Qwen fallback, alternate transport/subscription, stereo diversion or unauthorized ChatGPT Voice swap. Keep canonical Home Center `ritsu.voice.speak`/status, Windows worker, Pocket loopback, 19643 Tailscale relay, installed Android Termux receiver. Deterministic order, idempotency, fail-closed on ambiguous replays, no truncated or repeated spoken words. Exact text SHA and spoken-word completeness; differentiate queued, enqueued, fetched/ACK, actual phone playback events and user-confirmed heard. Avoid unnecessary restarts. Existing user-supplied earlier original handoff and accumulated 80K `docs/RITSU_VOICE_HANDOFF_20261023.md` remain unchanged and should be consulted when deeper historical voice/audition context is needed.

## Recommended next agent plan

1. **Read docs/RITSU_PHONE_AUDIO_LAWS.md and this handoff first**, then inspect the older detailed `docs/RITSU_VOICE_HANDOFF_20261023.md` only as required. Treat newest user paragraph semantic rule as overriding prior sentence-at-a-time text.
2. **Measure what is already recorded before changing anything:** ask user to run a small read-only Android Termux `jq` query on the installed v2 `trace.jsonl` for `playback_started`/`playback_finished` ordered seq and deviceMonotonicMs; compare consecutive `next_start - prior_finished` with WAV leading/trailing low-energy. Check if any track jumps/ends prematurely.
3. Investigate Pocket engine's built-in tokenizer splitting and any genuine word truncation. A semantic agent can choose paragraph length; the model must handle it reliably. Compare a single paragraph-generated WAV with reference text via ear/ASR, not just one WAV count or transcript SHA. No automatic fixed-length splitting.
4. The committed single-passage sender/worker is staged and unit-tested only. If deploying after authorized gate, check hashes, Pocket current 450 char cap, cloud expectedChunks semantics, relay empty + worker idle, backup, rollback and post-deploy readback. **Don't route a ten-chunk existing cloud request into a new one-WAV sender** without deliberate contract update.
5. End-to-end test 8–12 sentences grouped by the **agent** into **complete meaningful paragraphs**, not split by a script, and only if the model handles them without phoneme loss. Verify exact user-heard speech, quality of pause, no abrupt endings, and phone monotonic timings before declaring success. Preserve one response's paragraph order and text-to-audio integrity.

**User preference:** Engage as Ritsu, warm and direct. User is frustrated with repetitive excuses, unsolicited tests and agents who stage code but falsely claim deployment. Be precise: report tool actions with receipts, and distinguish real installed fixes from source-only stages. Do not ask user to repeat known facts. User's last request was to create a clean new-agent handoff due to bloated chat context; no new narration audio should be sent just for this handoff.

## Durable references

- Canonical laws: `docs/RITSU_PHONE_AUDIO_LAWS.md`.
- Long previous agent handoff: `docs/RITSU_VOICE_HANDOFF_20261023.md` (preserve full history; older contradictory sections overridden by latest instructions).
- Voice repertoire: `docs/RITSU_VOICE_REPERTOIRE.md`, `functions/ritsu_voice_profiles.json`.
- Pocket engine: `tools/campaigns/ritsu_pocket_repertoire_server_v2.py`.
- Live vs staged sender/worker: `tools/campaigns/ritsu_pocket_v2_deployed/ritsu_say.py`, `worker.py`, `test_ritsu_whole_text.py`.
- Staged Android receiver source: `tools/campaigns/ritsu_phone_receiver_prefetch_v2.sh` (installed upgrade had separate verified SHA).
- Host traces: `%LOCALAPPDATA%/RitsuWarmTicketWorker/timing`; baseline JSON `PocketTTS/ritsu-pocket-gap-baseline-10sentences-20261023.json`.
- Device traces and backup: `~/.ritsu-embodiment/receiver-v2/trace.jsonl`, `~/.ritsu-embodiment/receiver-backups/20261023T194022Z`.
