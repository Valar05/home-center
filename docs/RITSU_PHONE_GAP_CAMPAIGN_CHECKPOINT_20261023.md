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
