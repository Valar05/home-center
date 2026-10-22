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
