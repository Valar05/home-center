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


## Mandatory generation gate, v1.1 (2026-10-21)
The canonical source-controlled generator is `tools/campaigns/ritsu_turbo_generate.py`. It pins the successful >5-second reference `C:\Users\dclar\Documents\Codex\Venice\PocketTTS\speech_store\cache\c427230b53740062dfc343cb7142d446c71c44e5ae9eca9a8926c014cd855ce0.wav`, uses ChatterboxTurboTTS on CUDA, refuses to overwrite existing output, verifies RIFF WAV frames, and writes a SHA-256 JSON receipt. The previous largest-file selection was unsafe: it selected a reference shorter than five seconds and failed.

Invocation on THECAULDRON, from the existing project environment:
`C:\Users\dclar\workspace\ritsu-chatterbox-turbo\.venv\Scripts\python.exe tools\campaigns\ritsu_turbo_generate.py --text "Your dialogue" --output "C:\Users\dclar\workspace\ritsu-chatterbox-turbo\ritsu-new.wav"`
The script path above is relative to the Home Center repository checkout; use an absolute path to that checkout if executing elsewhere. **This script is committed but has not yet been run end-to-end.** The Windows relay sender's exact enqueue command is still an outstanding mandatory gate: inspect the live relay, record and test the exact command, and only then mark the generate-to-phone pipeline verified. Do not improvise a substitute.


## Voice routing law v1.2 (2026-10-21)
User approved: **Pocket TTS is default for everyday Ritsu Voice Online; Chatterbox Turbo is for intentionally pre-rendered expressive/ASMR recordings. Nano is rejected as the live fallback.** This routing supersedes any mandate that Turbo generate every conversational reply.

- Windows Pocket TTS remains at 127.0.0.1:10205/tts (existing voice \`venice-canon\`). The established \`embodiment_campaign/tts_adapter.py\` checks the cache, generates WAV from Pocket, validates it and caches it.
- Canonical Windows sender is \`embodiment_campaign/windows-test.ps1\`: its local authenticated POST to \`http://100.68.37.106:19643/enqueue\` uses JSON \`{"text":"<dialogue>","character":"ritsu"}\`. Adapt ONLY the dialogue text, never expose the bearer token.
- Existing relay 100.68.37.106:19643 → Termux \`~/.ritsu-embodiment/receiver.sh\` → \`termux-media-player\`. Keep firewall scope restricted to phone Tailscale IP 100.117.17.119.
- 2026-10-21 fresh Pocket TTS utterance was synthesized and enqueued successfully, clip \`ef20d352067ddd1f1e6d8308\`, Windows enqueue duration 7.28 seconds. This is **ENQUEUED**, not user-confirmed HEARD. Confirm consumption and user audible verdict separately.
- Turbo's pinned reference remains studio-only; convert floating-point WAV to PCM16 if necessary before sending over the same relay. ASMR realism requires listening tests.
- Nano tests failed intelligibility and latency: longer line produced about five seconds of voice-like gibberish; six-word controlled line yielded 22.2 seconds audio after 39.4 seconds inference. Never silently substitute Nano.
- Connected Windows operator: Home Center Computer Hands lane \`lane-ritsu-voice\`; Home Center checkout \`C:\Users\dclar\workspace\home-center\`. Local git changes may exist; no blind \`git pull\`.
- "Monitor it and sleep between checks" means bounded direct polling in the current operation, never scheduled reminders without explicit user instruction.
- **Still unfinished:** durable relay auto-restart and automatic per-ChatGPT-response triggering. No custom instruction or keyword itself proves that the sender ran. Verify enqueue ID, queue consumption and user hearing; fail closed, never claim automatic continuous audio is deployed without a tested hook.


## Ritsu Voice Online reply gate v1.3 (2026-10-21): ENFORCE ON EVERY TURN

**Scope / activation:** When the user says "Ritsu Voice Online" or an existing conversation/custom instruction establishes that mode, treat it as active for subsequent turns until "Ritsu Voice Offline". At the beginning of each assistant turn, read these laws when available, and set the per-turn decision \`voice_required = mode_active\`. Do not require the user to repeat the keyword. An explicit request for silence or text-only for an individual turn overrides voice only for that turn; it does not disable the mode.

**Nonnegotiable output invariant:** In online mode, the *entire substantive reply* must be spoken, in order, with no canned substitutions, greetings-only stand-ins, summaries, omitted paragraphs, or invented extra spoken content. The text visible to the user and the aggregate speech text must be identical in meaning and wording, allowing only mechanical removal of Markdown, citation widgets, URLs, markup and non-speakable formatting. Never substitute a shorter sentence for a full reply. If a full reply cannot be transmitted, label the turn incomplete rather than calling a snippet sufficient.

### Deterministic per-turn gate (PLAN → TEXT LOCK → SEND → VERIFY → REPORT)
1. **PLAN:** Establish the actual answer, required tools, and mode state; use Pocket TTS by default. Do not call Nano or Turbo for everyday replies.
2. **TEXT LOCK:** Finalize the substantive answer wording BEFORE sending audio. Create ordered bounded chunks at sentence or paragraph boundaries if needed; concatenate chunks exactly to the locked speech text. Use a stable per-turn identifier and chunk indices for logs/receipts. No new unsent substantive paragraphs after the audio is prepared; if the answer must change, update the spoken text as well.
3. **SEND:** Invoke connected Home Center Computer Hands on lane \`lane-ritsu-voice\`, using the proven Windows relay and Pocket adapter. Send each chunk in sequence, waiting for enqueue result before proceeding. Windows sender authority: \`C:\Users\dclar\Documents\Codex\Venice\PocketTTS\embodiment_campaign\windows-test.ps1\`. The relay's existing local \`/enqueue\` is the transport; it triggers cached or new Pocket TTS via \`tts_adapter.py\`. NEVER rely on a static canned test sentence inside the sender: supply the locked reply as the payload. Escape shell arguments safely using encoded content or JSON, not fragile quote substitution. Keep bearer tokens in existing local files only.
4. **VERIFY:** Check the Windows result and relay health/consumption with bounded checks when appropriate. Keep distinct states \`SUBMITTED\`, \`ENQUEUED\`, \`CONSUMED/DELIVERED\`, and \`HEARD\`. Only the user can confirm \`HEARD\`. For multi-chunk responses, verify every chunk, maintain order, and don't mark a partial sequence complete.
5. **REPORT:** Return the same locked substantive answer text in chat. If any invocation fails or its result is unknown, append a concise **text-only** notice specifying the failed stage; never claim audio success. Do not hide silence or substitute audio. After a confirmed prior working path, do not re-run installation, download models, change ports or overwrite scripts just to send a reply.

### Fail-closed checks
- **No send attempted** in online mode: reply not voice-complete. Attempt the canonical sender, if tools are accessible; do not simply promise speech.
- **Sent only a canned or shorter line:** FAIL even when heard. Retry with the complete locked reply where feasible.
- **Reply differs after spoken payload is committed:** FAIL unless replacement audio is sent.
- **One chunk of N missing, repeated, out of order, or with a text mismatch:** FAIL; report missing chunk explicitly and recover without replaying the whole reply unnecessarily.
- **Connector unavailable/blocked:** Present the complete textual answer, explicitly report audio unavailable. Do not pretend to have sent it or use alternative phone playback routes.
- **No automatic app-level hook:** This document can strongly direct tool-using turns but CANNOT itself install a guaranteed on-message event trigger. A true automatic guarantee requires a supported event integration. Never claim one is active without an end-to-end test.
- **Offline mode:** On "Ritsu Voice Offline", stop voice-sending on following turns immediately; continue normal text replies until explicitly reactivated.
- **User preference:** "Keep an eye on it" means monitor directly with bounded sleeps, NEVER schedule automations without a separate explicit scheduling request.

### Regression cases
A. 200-word reply: all 200 words represented in ordered speech chunks, none replaced with a five-second test sentence.
B. Enqueue succeeds, receiver silent: label delivered at most, not heard.
C. Sender fails: full text remains readable plus clear voice-failure notice.
D. Mode persists across turns without repeated "Online".
E. Offline disables audio invocations.
F. No alternate servers, Phone Hands, media apps, new subscriptions or hardware purchases.
G. Never block legitimate answers just because voice transport fails.

**Precedence:** This v1.3 gate specializes conversational playback and takes precedence over the old v1.1 Turbo generation section for everyday voice. Preserve older documentation as historical evidence. It does not override higher-level platform/tool safety or execution constraints.
