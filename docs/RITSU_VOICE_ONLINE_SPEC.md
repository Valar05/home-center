# Ritsu Voice Online: sticky conversation-mode specification v0.1
Status: DESIGN ONLY. Not deployed or validated. Extends docs/RITSU_PHONE_AUDIO_LAWS.md; that law takes precedence.

## Commands
- `Ritsu Voice Online`: latch voice for the current chat, until explicit `Ritsu Voice Offline`.
- `Ritsu Voice Offline`: unlatch for this chat only.
- Fortress Online and Clock Mode are independent and do not reset the latch.

## Required behavior
For every assistant-visible response after activation, enqueue its speakable text through the **existing, proven** Tailscale Ritsu relay, never Phone Hands or alternate Android execution. Split at sentence boundaries, target 1–3 sentences per chunk with bounded text/latency. Preserve sequence IDs, turn IDs, and chunk indices. Single active playback stream, ordered delivery, no overlap. Exclude code blocks, URLs, citations, and secrets from speech by deterministic documented rules; visible text remains complete. Explicitly report omitted speech segments. Support interruption/cancellation on newer turns and offline command.

## Architecture gate
A chat instruction alone cannot intercept all generated tokens or automatically call MCP after every response. A runtime-level post-response dispatcher or streaming hook MUST exist and must preserve per-chat latch state durably. If unavailable, this feature is NOT operational; per-turn manual MCP dispatch is only a separately approved degraded mode. Do not assert streaming if only after-turn synthesis is supported.

## Canonical audio path
Follow RITSU_PHONE_AUDIO_LAWS.md exactly. Inspect live Windows relay sender syntax, receiver, and health before implementing. Use existing short host-side enqueue. No Phone Hands, ADB, Drive-link, new relay, Android shell payload, or guessed endpoint.

## Delivery receipts and acceptance
Track CREATED -> SYNTHESIZED -> ENQUEUED -> RECEIVED/ACKED -> HEARD (user-confirmed). Never equate ACK with audible playback. Test 3 short consecutive chunks, long response, interrupted turn, chat restart within same conversation, separate chat isolation, offline command, and relay outage fail-closed. Capture commit, runtime deployment, and actual audible verdict before marking complete.


## Status amendment v0.2 (2026-10-22): warm voice runtime deployed, reply hook still not deployed

The earlier `DESIGN ONLY` status is superseded for the **Windows synthesis-to-phone transport**, not for the automatic per-ChatGPT-reply latch/dispatcher.

- DEFAULT speaker: `Ritsu | Warm | v1`, user-approved Qwen3-TTS 0.6B Base full-reference clone, source/engine/file hashes and immutable constraints in `docs/RITSU_PHONE_AUDIO_LAWS.md` v1.4+.
- Windows API `C:\Users\dclar\workspace\ritsu-faster-qwen3-tts\ritsu_voice_api_warm_v1.py`, loopback port 19645, bearer token from local file, `/v1/speak` -> poll `/v1/jobs/<id>` -> `/v1/deliver` -> existing Tailscale relay port 19643 -> Termux Android receiver. Never expose bearer tokens.
- Windows login Startup launcher `RitsuWarmVoiceAPI.vbs` invokes the Warm API silently with `pythonw.exe`; Python headless stdout/stderr are redirected to local log files by the program. API now queues `__boot_prewarm__` on startup so model and CUDA graphs can warm before chat requests. Verified after simulated startup launch: `/v1/health` 200 with `model=loaded`, `__boot_prewarm__` completed. Actual reboot persistence and crash-restart watchdog not yet independently verified.
- One-call bounded speech client `C:\Users\dclar\workspace\ritsu-faster-qwen3-tts\ritsu_say.py`, supports `--text` or `--text-file`, serially submits ordered ~350-character chunks, awaits each job completion, and enqueues to the phone relay, reporting ENQUEUED not HEARD. Validated short warm clip, 4.72 sec audio in 3.094 sec, relay id `1b68001f0fc151cde03df337`. Receiver audible confirmation for that sample still pending.
- Custom-instructions reference to canonical law remains valid without changing the snippet. The prompt keyword **does not itself create an automatic post-response event handler**. No claim of automatic whole-ChatGPT-message speech on every turn is allowed until the post-response/streaming bridge is implemented and tested. Manual dispatch through the connected Windows controller remains the current supported path. Per-turn reply parity, longer multi-chunk test, interruption, chat restart, concurrent streams and phone audible confirmation remain explicit gates.
