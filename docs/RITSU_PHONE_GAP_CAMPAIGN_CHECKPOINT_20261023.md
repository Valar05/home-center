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
