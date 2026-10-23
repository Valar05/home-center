# Ritsu Pocket phone gap campaign: continuation checkpoint (2026-10-23)

## Mission and preserved boundaries

Commissioned by Drew to consolidate the unresolved Ritsu Pocket TTS audible-gap investigation into a governed Home Center script campaign, then continue as far as the authorized runtime permits. **Success = natural, complete audible narration with acceptable continuous pacing, explicitly confirmed by the owner.** This checkpoint is NOT success.

The sole speech path remains: ChatGPT -> Home Center `ritsu.voice.speak` -> THECAULDRON Windows worker -> Pocket TTS localhost 10205 -> canonical Tailscale 19643 relay -> Termux Android receiver. No Qwen, other voices, replacement relay, alternate playback app, silent sentence regex, clipping, or arbitrary text length slicing.

Authoritative user correction: agent deliberately authors complete paragraphs with natural sentence boundaries; no automated sentence/word truncation. Preserve current approved Pocket voice repertoire, including Normal/Warm Desire 02 minus-one clone hash beginning 043D61. Any true repair requires source tests, authorized runtime deployment, readback, and explicit owner HEARD acceptance.

## Canonical campaign etiquette read

- `skills/operator-campaign/SKILL.md` (stable entrypoint, durable history, status/stop/resume, failure receipts, process isolation, clipboard receipts, checkpoint continuation).
- `skills/venice-governed-campaign/SKILL.md` (mission, review, evidence, stop rule).
- `skills/chatgpt-phone-ingress/SKILL.md` and `docs/PHONE_HANDS_CHATGPT_RELAY.md` (Home Center Phone Hands primary route, no Drew-as-transport substitution).
- `.continue/rules/00-judgement-jar-mission-boundary.md` and `20-judgement-jar-repository-truth.md` (no tool substitution; deployed truth requires device evidence).
- `docs/RITSU_PHONE_AUDIO_LAWS.md` and `docs/RITSU_PHONE_GAP_HANDOFF_20261023_AGENT_CONTINUATION.md` (audio-specific authority and historical receipts).

## Source artifacts, not yet installed

- `tools/campaigns/ritsu_phone_gap_campaign.py`, source latest commit `9fbc3cfbb6ecd29009e2f07dac9b4348462112cb`.
  - Android Termux read-only trace/WAV/source-hash collector; stable `run/resume/status/receipts/follow/stop/recover`, bounded isolated child, durable JSON receipts, clipboard status; no voice/relay mutation.
  - Explicitly marks absent, corrupt or truncated playback evidence `inspection-incomplete` and exits nonzero; never gap-free or HEARD.
  - Source is not itself an installed operator notification/menu. Do not claim full Operator Campaign acceptance without runtime install/canaries.
- `tools/campaigns/test_ritsu_phone_gap_campaign.py`, source commit `1ce21be41ac40483943dc4b03070793e3711ddde`. Offline fixtures for gap arithmetic, trace absence/corruption, and event integrity. **Tests authored, not reported as run on phone.**

## Real Home Center ingress receipts

- Direct Home Center `command_center.phone_hands.devices` succeeded and returned `primary-phone` and `primary-phone-rescue-v1`, but their reported last-seen timestamps are stale. Device registration is not liveness.
- `command_center.phone_hands.enqueue` successfully accepted idempotent read-only `phone_shell` command `ritsu-gap-readonly-audit-20261023-v1`, targeting `primary-phone` and only reading the already existing `~/.ritsu-embodiment/receiver-v2/trace.jsonl`. `phone_hands.get` repeatedly returned **queued / no execution result**; no playback times were retrieved. It has a 45s TTL, though status may continue showing queued past expiry.
- `computer_hands.worker.status` on `windows-hands-01` returned **online=true, idle**, fresh heartbeat, with other active lanes. This disproves a blanket Home Center/Windows-control outage.
- `computer_hands.request.create` accepted read-only `process.list` ticket `ritsu-gap-windows-process-audit-20261023-v1` through the authorized Home Center Windows worker. `computer_hands.request.status` confirmed **completed** with 300 process records; Windows Python PID 33012 appears, matching the prior documented Ritsu worker PID, but the action did not verify command line, sender SHA or audio quality.

## Open phase and next authorized action

**Current phase: INSPECTION_INCOMPLETE; live audio repair NOT DEPLOYED.**

1. Restore or observe fresh Android Home Center Phone Hands heartbeat by the authorized device recovery path. Do not treat an enqueue receipt as phone execution or reuse an expired command as success. Do not blindly rebootstrap a registered device.
2. Only when actual device execution is available, invoke the committed campaign through Home Center on Android; verify its installed source identity, isolated controls, trace pairs and resulting device-local receipts. Keep no more than one active read-only inspection command per lane.
3. Compare Android end(N)->start(N+1), WAV-leading and tail silence, playback duration vs file duration, and Windows generation/relay timing. This separates player restart overhead, host generation stalls, and phoneme completeness without assuming a fix.
4. Prepare minimum repair against the proven bottleneck. Promote only after a separate authorized deployment gate with backups and readback; do not route around platform safety blocks.
5. Real phone listening confirms continuity and full word/paragraph coverage. Keep `HEARD` false/unverified until owner confirms.

No new speech canary, Android receiver restart, approved voice replacement, or live Windows sender cutover occurred during this campaign slice. Prior staged paragraph sender remains source-only and Android v2 prefetch receiver is the previously installed runtime.


## 16:18–16:20 CDT retry and authorized operator fallback

Owner correction: Ritsu's **voice receiver has continued working**; do not conflate that with the distinct Home Center Phone Hands command-control receiver. The Tailscale speech relay may be healthy even while `android_phone_home_center_relay.py` has a stale heartbeat.

Retried from ChatGPT via real Home Center `command_center.phone_hands.enqueue`:
- `ritsu-gap-primary-trace-20261023-1618-cdt-v2` on `primary-phone`, read-only `phone_shell`, TTL 120 seconds, accepted as **queued**.
- `ritsu-gap-rescue-trace-20261023-1618-cdt-v2` on `primary-phone-rescue-v1`, same read-only diagnostics, TTL 60 seconds, accepted as **queued**.
- Both `phone_hands.get` readbacks at 21:20:41 UTC remain **queued**, with no lease owner, no stdout, and no execution receipt, after their TTL. This proves Home Center cloud enqueue works, not phone-local execution. No voice service changed.

Owner expressly volunteered to run on-phone recovery manually if required. Because both authorized phone control lanes were tried and not executing, preserve a one-time, bounded operator handoff. Committed guarded install source `tools/campaigns/install_ritsu_phone_gap_campaign.sh` commit `7dfd8bbea6eac9cd89fe995f4faa55b124b43dc2`. It pins the read-only campaign to `9fbc3cfbb6ecd29009e2f07dac9b4348462112cb`, downloads source and offline tests, compiles and runs tests before installing into Termux private app storage, preserves changed existing files, exposes stable `ritsu-gap` run/status/receipts/follow/stop/recover and clipboard receipt. **This installer is committed, NOT installed, NOT tested on Android.** It must not be counted as a phone repair until owner returns an actual device receipt; campaign itself only diagnoses gaps and does not repair audio.

Next live evidence must be actual Termux receiver-v2 `trace.jsonl` event deltas, followed by measured minimal fix. No speculative rewriting of Pocket engine or phone transport.


## 21:22:30 UTC owner-supplied real phone playback report

The owner executed the read-only Termux campaign manually and pasted the full report from `~/.ritsu-embodiment/gap-campaign/result-20261023T212230Z.json`. **This is fresh physical Android trace evidence**, not a new Home Center Phone Hands result. Campaign receipt: `PHASE=inspection-complete`, `WORKER_ALIVE=False`, source `ANDROID_TERMUX`, `traceHealth=OK`, `traceEventCount=232`, `completedPairs=58`, `startedCount=58`, `finishedCount=58`, no trace anomalies, `receiverSourceSha256=8acd84673b91420dddac5705829e17997ca9dfcde87e5f3d3f35b872f219322f`. No audio pipeline changes.

**Measured playback API timing:** median interval from `playback_finished(N)` to `playback_started(N+1)` = **1.445 seconds**. Routine transitions mostly **1.09–1.84 seconds**, independent of exceptional 30.876s (30→31), 848.34s (36→37), 108.88s (41→42), 151.566s (50→51), and max 2737.353s likely separate requests/idle. These extreme interruptions must not be blended into the same-session gap estimate. All routine pauses are unacceptably long for sentence-level narration, and this measurement confirms the Android per-file boundary is a major latency source.

**Player elapsed vs actual WAV duration:** phone retained WAVs 51..58 are 24,000 Hz mono 16-bit and lengths 1.92, 1.52, 2.48, 4.96, 2.96, 1.76, 3.44, 4.08 seconds. Matching player elapsed timings are 2.973, 2.021, 3.416, 6.240, 3.490, 3.156, 4.140, 4.490 seconds. Thus per-clip player lifetime exceeds WAV duration by 0.41–1.396 seconds (not all necessarily audible). Example sequence 56: elapsed 3.156 seconds for 1.76s WAV; then API-to-API gap 56→57 is 1.445s. This may produce **more than 2 seconds** of perceived pause, before any WAV leading silence. Confirm by listening; player timestamps are not acoustic sample clocks.

**Important distinctions:** This evidence does NOT establish whether clip-end phonemes are intact or if Pocket clipped any words. It does NOT establish generation starvation across paragraphs, and it does not prove the installed Android receiver source equals repo staged `ritsu_phone_receiver_prefetch_v2.sh` (live installed sha8acd differs from staged file). The report shows last eight clips are only 1.52–4.96s long, supporting the previously documented per-sentence output. Most direct next improvement is to **remove unapproved automatic sentence segmentation at the Windows sender and deliver deliberately authored, complete paragraphs as one WAV each**, as already staged but uninstalled. That reduces interclip restarts per paragraph; it does not guarantee gapless between paragraphs. Do not mechanically concatenate, trim phonemes, raise Pocket token limits, or replace Termux playback without controlled evidence. Agent-authored paragraphs still need the Pocket 450-character enforced limit and completeness listening check.

## Revised next gates

- Inspect fresh Windows sender and worker active file hashes, current queue, and Pocket server health through existing authenticated Home Center Windows lane (read-only first). Preserve historical source-only vs runtime distinction.
- Validate isolated full paragraph WAV for exact spoken text, words and tail, especially Pocket's internal `split_into_best_sentences` tokenizer. No audio canary unless user consents to hearing it.
- If tests pass, deploy the minimally changed staged paragraph sender/worker through the authorized runtime lane with backups, idle gate and rollback, and readback. No changes to approved voices or canonical relay.
- Measure whether clip count per response and meaningful pause shrink, then user HEARD acceptance.


## Follow-on: Owner reports approximately five-second perceived pauses and requests silence cutter

Real Android 58-clip trace captured earlier gave median player API interval 1.445s, not acoustic end-to-next-speech-onset. WAVs 51..58 sum 23.12s of samples; their player elapsed sums 29.926s and the intervening seven start/end API intervals sum 9.942s, yielding 39.868s overall API player span for 23.12s of sampled audio. The remaining 16.748s are not independently verified as acoustic silence. Earlier ten Windows source WAVs had low-energy lead 0.02–0.75s, so perceived 5s may reflect player overhead plus padding plus request starvation. Do not claim exact five seconds acoustically measured.

New repository artifacts (source-only):
- `tools/campaigns/ritsu_pcm_silence_guard.py`, commit `35cedfe35b258edc69b0a6fb73f9aeb1349e08bc`, PCM16 24k mono read-only onset inspector, separately authored non-overwriting candidate writer. Keeps 200ms guard, caps cut at 800ms, never trims tails or touches source.
- `tools/campaigns/test_ritsu_pcm_silence_guard.py`, commit `dc289df33dbe34407b3ed5cb9172390f4e94cf19`, five synthetic offline tests: suffix/tail intact, soft initial onset, all-silent/short refuse, max cap, unsupported format fail closed. Equivalent local tests were run successfully; GitHub committed test sources not claimed as phone-tested yet.
- Existing `ritsu_phone_gap_campaign.py` updated at commit `00ab7f1f453847c09f88b830f1259edd8b1c1be3` with `ritsu-gap silence`, which probes up to eight retained real Android WAVs and prints/copies onset metrics only, writing independent JSON receipt and leaving prior gap report and audio untouched.
- Guarded in-place Termux upgrade `tools/campaigns/upgrade_ritsu_gap_silence_probe.sh`, commit `8ae5f3d73700896e0060cf112c686950147d036c`; pinned sources, compares installed old files to prior approved version, backs up originals, compiles/runs both offline test files, and invokes existing `ritsu-gap silence`. **Not installed or run on actual phone yet.**
- `docs/RITSU_PHONE_AUDIO_LAWS.md` addendum commit `b1510c51f6b34cc59a1179e9d8e24668984698b8` records owner authorization and speech-integrity gates.

**No live changes:** Do not wire cutter into Pocket, relay, receiver, or sender until actual phone PCM probe and careful listening prove no words or soft syllable onset is cut. Prior downstream MediaPlayer per-file overhead and unapproved upstream sentence splitter remain independent problems. NEXT: obtain `ritsu-gap silence` receipt from actual Termux; compare leading quiet against measured 1.445s phone handoff; prepare minimal opt-in cut/agent-authored-paragraph fix with test/rollback and owner-heard acceptance.


## Read-only silence probe real installation and zero-onset correction

Owner ran the guarded Termux upgrade on October 23 and returned:
`RITSU_SILENCE_PROBE_INSTALLED=1`;
backup `~/.local/share/ritsu-phone-gap/backups/silence-20261023T213755Z`;
read-only probe WAV seq 90–97 all `leading_quiet_ms=0`, `candidate_cut_ms=0`, report `~/.ritsu-embodiment/gap-campaign/silence-20261023T213755Z.json`, and `AUDIO_UNCHANGED=1`.

**Interpretation correction:** 0ms at existing very-low thresholds (PEAK >96 / RMS >32 in signed 16-bit samples over first 10ms) does NOT imply immediate speech or that the previous Windows 0.02–0.75s low-energy padding findings were false. Even background digital noise, room tone, or pre-utterance energy can exceed these thresholds. The old cutter deliberately proposed no cuts to avoid phoneme damage. These newer WAVs are different from seq51–58 and require per-clip comparison.

New source-only refinement: `ritsu_pcm_silence_guard.py` commit `2d3285d2e39a7afaa6102e848433db31c90c0a77` adds read-only first-frame dBFS, leading 100/250ms envelope peaks, and five-consecutive-10ms threshold crossing candidates at -50/-40/-30dBFS and adaptive relative envelope threshold, explicitly NO AUTO CUT. `ritsu_phone_gap_campaign.py` commit `8a11a5237161839c44d67002d361e9d24af0dd99` correlates onset estimates to actual per-sequence preceding playback API gap and player elapsed vs WAV duration. `test_ritsu_pcm_silence_guard.py` commit `589f2ff13ee030297c12a149a090cc4cdaf396ee` adds synthetic low-level pre-speech PCM and immediate-onset controls.

The guarded, pinned in-place installer `tools/campaigns/upgrade_ritsu_gap_energy_profile.sh` commit `8c3e8d5115663851dfc8befb3a480dd88a2562ba` checks exact prior source against installed files, runs offline tests, backups before replace, and finally invokes the unchanged `ritsu-gap silence` command. This later upgrade is **not yet run** on Android and should never be labeled accepted until its device receipt exists. No Pocket model, voices, relay, receiver script, or playback process changed.

Priority: interpret actual dBFS envelope and phone timing together. A threshold crossing is not word onset and never by itself authorizes PCM trimming. Retain earlier owner directive for complete agent-authored paragraphs without source-based sentence splitting.

## 16:51 CDT: historical Pocket comparison, real benchmarks, and verified live repair

User authorized killing Windows sender sentence splitting, asked for adaptive complete-thought lengths and why original Pocket felt better.

History: first archived Pocket sender at GitHub commit 6cdc4d23 bundled text to 350-character chunks, not per-sentence WAVs. Commit 0f7288e4 on October 23 required one sentence per speech unit. Commit d08f2e18 added four-job lookahead but retained one WAV per grammatical sentence, multiplying the phone playback overhead. Later source at f04ad636 and d3ece78c provided a no-split one-input-one-WAV sender capped to the real 450-character Pocket /v1/speak ceiling; that source remained uninstalled until this campaign.

Actual Pocket 10205 NORMAL voice /v1/speak benchmark on idle Windows host, ticket ritsu-pocket-render-size-benchmark-20261023-001: 112 chars -> 3.62s generation, 5.84s WAV; 183 chars -> 5.83s, 10.08s WAV; 289 chars -> 9.25s, 13.84s WAV. All completed, NONE delivered to phone. Tentative 0.032s-per-char generation slope for these samples only. Provisional agent-first opening thought 90-140 chars and subsequent natural complete thoughts 180-300 chars, never script-side splitting and never mandatory character slices. Dispatch first finalized useful spoken thought before composing all later paragraphs when safe.

Live Windows audit ticket ritsu-voice-live-readonly-audit-20261023-001 established old active sender SHA256=2922EFE848AAD961C96282EB491E4090FCE9DD0891E67CD01FBE1D357AA24B3D, worker SHA256=C72A0AC06CB5806D7A4F07A9FD8DE1966979B72CC09EA8E9109C0F157EF43166, Pocket SHA256=FA679DF591572219AAD33EF958221F2E3A68B2AA7D93AFCCED295968DB5C3B08. Regex sentence splitting was TRUE, WINDOW=4 TRUE. Audit output exited nonzero only on subsequent optional process-name formatting; read-only file-hash receipts are still valid.

GUARDED LIVE SENDER CUTOVER INSTALLED: Source deployment script tools/campaigns/ritsu_no_split_sender_cutover.ps1 committed 022b08171cf1f2c405b27af698f75625702a9cc2. Windows Computer Hands dry-run ticket ritsu-no-split-windows-dryrun-20261023-001 completed with no-network whole-text contract test PASS, hashes expected, model loaded and queue=0. Then install ticket ritsu-no-split-windows-install-20261023-001 successfully replaced only Windows sender file atomically with verified SHA256=3DDA464DF8D5E24D29DB471DF7C7B8D70D28741C98866996A980AFE5443C6AD8. Old sender exact backup at %LOCALAPPDATA%/RitsuWarmTicketWorker/sender-backups/ritsu_say.20261023T165107.pre-no-split.py. No worker/Pocket/relay/phone receiver restart or modifications. Post-readback ticket ritsu-no-split-windows-postreadback-20261023-001 confirmed whole=True, regex_sentence=False, max_450=True, worker hash unchanged, Pocket loaded queue0.

IMPORTANT: This is true runtime source deployment, NOT user-HEARD quality acceptance. Sender now refuses any single ticket text over 450 characters instead of splitting or dropping words. Agent must compose and issue ordered complete thought tickets itself, preserving all substantive visible content. Long Pocket internally chunked generation may still omit words and must be heard/verified; no phone canary or trim was sent during cutover. The Android API boundary and player overhead remain independently unfixed. User's recollection of speech arriving before visible text remains a latency regression to investigate, not proven caused by a particular commit.

Canonical audio law update commit 651978ca64094c55bb5ff598911cd6b262be09a2.


## 17:02+ CDT: Drive, GitHub rule synchronization and Android receiver v3 candidate

Drive native Doc **Ritsu Voice Embodiment — Complete October 21 Companion Ledger** `https://docs.google.com/document/d/1okcl-v7CcaEnZruG10n5as-3UjgPpqrdb8ZBS5c30mk/edit` updated in place via authenticated Google Drive Docs API with revision guard and verified readback. Superseding Oct 23 entry: approved live Pocket 10205/relay 19643, complete agent-authored speech units, hard **450-character limit per ticket**, provisional agent-authored ~90–140-character first useful thought and ~180–300-character later complete thoughts, never software slicing, and delivered vs HEARD distinction. Historical Qwen/Turbo is no longer active guidance.

Referenced GitHub docs also updated at top-of-file with superseding guidance:
- `docs/RITSU_PHONE_GAP_HANDOFF_20261023_AGENT_CONTINUATION.md` commit `0f26f1903d8dc5cef719d832989265637bd2fd26`.
- `docs/RITSU_VOICE_REPERTOIRE.md` commit `6da5f6bd8f954be07010dc82e0442d0d57ca3d84`.
- `docs/RITSU_PHONE_AUDIO_LAWS.md` already has authoritative 450/first-audio/verified sender cutover at commit `651978ca64094c55bb5ff598911cd6b262be09a2` (later versions may extend it).
- Android cause revalidated against upstream Termux project `termux-media-player` command source: it accepts only **one input path per play**, no native command-line playlist. Per-file Android MediaPlayer restarts and API transactions are expected to cost delay; user trace confirms 0.8–1.5s player API handoffs plus leading low-energy PCM.

Android v3 **candidate prepared, NOT installed**:
- `tools/campaigns/ritsu_phone_wav_batch.py`, commit `87a1cfbbcdf94f71b629b25c6230be156487efba`: joins 2–3 ALREADY-prefetched ordered canonical 24k mono PCM16 source WAVs into exactly one WAV using original PCM bytes unchanged. Validates sample-by-sample SHA256 output, source immutable, maximum 90 seconds, at-most-three, contiguous seq identity, new-file-only. No TTS/voice/relay changes, no silence trimming/crossfade.
- `tools/campaigns/test_ritsu_phone_wav_batch.py`, commit `bcb2e852361deab142ad0eca145b454a9eb78ee4`: four offline tests (exact PCM and original preservation, nonconsecutive refusal, single-file refusal, bad format refusal). Real Windows Computer Hands test attempt #003 output `UNIT_TEST_EXIT=0`, four tests passed; its shell syntax step initially failed solely because Windows Bash was given an invalid `C:\...` path, then separate bash -n via stdin completed `BASH_SYNTAX_EXIT=0` for the v3 receiver source.
- `tools/campaigns/ritsu_phone_receiver_prefetch_v3.sh`, commit `9f94c5c5d10524c3ea8f265dbacd8ad9bc4031fc`, derived from staged v2 same three-slot fetch+ack/trace state. For 2–3 ready consecutive WAVs, build one verified batch and call the SAME `termux-media-player play` once; if one ready, play immediately, no wait for more. Always keep FIFO play.seq accounting, crash marker fail-closed, log batch first/last events. **Note:** old installed receiver.sh real hash `8acd84673b91420dddac5705829e17997ca9dfcde87e5f3d3f35b872f219322f`, not necessarily byte-identical to staged v2. Current live v2 unchanged.
- `tools/campaigns/install_ritsu_phone_receiver_v3_next_restart.sh` commit `183666e17a3dcce1355f3f3b2bbccc5f474370bd`. Phone-side guarded installer validates exact old deployed receiver hash and absence of playback marker, downloads pinned candidate/helper/tests, runs `bash -n` and Python offline tests, backs up old receiver under `receiver-backups/v3-source-...`, atomically replaces source and installs helper, **does not stop/restart** active receiver or touch Pocket/relay/player. Its effect is for NEXT receiver launch only and subject to a real Termux receipt. Installer is not yet run.

**Important limitation:** Batching only helps if at least two next clips are already buffered; it will NOT hide a new clip that arrives after the prior one ends, nor guarantee gapless across all speech. A persistent gapless player would need a separately designed Android playback implementation, and is NOT silently substituted. No cutter enabled. Only owner phone listening plus trace proves whether Android batch improvement works. Real runtime needs quiescent cutover and exact on-device source verification before enabling; do not interrupt live playback or claim HEARD.

