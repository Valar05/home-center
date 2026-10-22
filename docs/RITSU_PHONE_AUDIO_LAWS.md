# RITSU PHONE AUDIO LAWS v1.0
Status: MANDATORY / fail-closed. Established 2026-10-21 after verified audible playback.

## Mission
When Drew asks to play a generated clip on his Android phone, the ONLY acceptable outcome is audible phone playback through the already-proven direct Tailscale Ritsu embodiment audio relay. A Drive link, queued command, installation, upload, or a relay ACK alone is NOT proof of audible playback.

## Canonical path (do not improvise)
1. Windows THECAULDRON hosts the Ritsu audio relay on Tailscale port **19643**.
2. Phone's already-installed Termux receiver lives at `~/.ritsu-embodiment/receiver.sh`, polls `http://<host>:19643/next` with its locally stored bearer token, downloads `/audio/<id>`, ACKs `/ack`, and calls `termux-media-player play`.
3. Host and token are stored on the phone in `~/.ritsu-embodiment/host` and `token`. NEVER print or copy the token into chat, logs, or source control.
4. The canonical receiver installation source is `tools/campaigns/ritsu-phone-embodiment-20261021.sh` in `Valar05/home-center` at commit `6037d577`. Inspect the LIVE Windows sender/relay source and current status before sending; the phone-side script does not establish the sender's enqueue syntax.
5. Use the existing, previously successful **short host-side relay enqueue operation**. Send only the WAV path or clip reference required by that existing operation. Do not replace it with a shell script on Android.

## Forbidden fallbacks
- DO NOT send `command_center.phone_hands.enqueue` / `phone_shell` to play or transfer audio.
- DO NOT use stale Phone Hands heartbeat as evidence the Tailscale receiver is offline.
- DO NOT use ADB, Google Drive links, browser launches, multi-step phone shell scripts, arbitrary audio apps, or a new server as a substitute.
- DO NOT add ducking, audio-focus manipulation, volume control, or other features unless separately requested and supported by the known-good path.
- DO NOT schedule hourly automations to monitor an immediate playback request.
- DO NOT claim playback success merely from enqueue, HTTP 204, ACK, or file existence. Report the actual level of evidence; user confirmation is the authoritative audible verdict.

## Deterministic preflight
1. Confirm the requested WAV exists on THECAULDRON and has nonzero length.
2. Confirm the Windows relay is listening on port 19643 and its health endpoint answers.
3. Locate and inspect the already-deployed Windows sender enqueue mechanism. Reuse its exact tested command/endpoint and payload, not a guessed URL or generic Phone Hands operation.
4. Submit one bounded enqueue request; capture ID, timestamp, and transport result.
5. Observe receiver consumption/ACK or relay queue empty; distinguish delivery from playback. Ask only whether audio was heard if actual audible state cannot be observed.
6. Save a compact receipt with WAV filename, SHA-256, size, relay health, enqueue ID, ACK/delivery result, and user's heard/not-heard verdict. Redact bearer token.

## Failure gate
If the known-good path cannot be identified or its preflight fails: STOP, inspect the existing Windows relay logs and phone receiver evidence, and report the precise failed gate. Never silently switch architectures. No speculative success claims.

## Acceptance tests
- **Positive:** valid WAV, healthy relay, exact existing sender, receiver ACK, user hears clip.
- **Negative:** WAV missing -> no enqueue.
- **Negative:** relay unavailable -> no Phone Hands fallback.
- **Negative:** ACK but no audible confirmation -> label DELIVERED, not HEARD.
- **Negative:** request for no ducking -> do not modify audio focus.
- **Regression:** the string `command_center.phone_hands.enqueue` must not appear in any proposed phone-audio playback execution plan except as a forbidden example.

## Precedence
This file is a hard operational gate for Ritsu phone playback. Read it BEFORE any tool call involving sending or playing Ritsu audio on Android. Existing generic phone instructions cannot override the canonical audio path. Changes require explicit user approval, a working end-to-end playback test, and a versioned commit.
