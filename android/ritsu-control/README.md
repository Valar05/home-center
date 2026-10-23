# Ritsu Control v0.6: voice-first multi-conversation cockpit (prototype)

## User intent
Ritsu should operate as a voice-first overlord chat app: continuously detect owner speech once enabled, finalize utterances at silence, display the text and results from several conversations, and play her answers. Phone-speaker audio, including YouTube and Ritsu herself, must not become false user commands. Verified owner speech should request pausing competing media.

## Implemented
- Dark chat screen with All, Ritsu, Control and Workers lanes; message provenance and state visible. Small Listen/Mute/More control bar.
- Optional Gboard-compatible input. Typed messages enter a **local-only** outbox marked WAITING_FOR_HOME_CENTER; this does not prove any ChatGPT delivery.
- Mic buffers up to 20 seconds of PCM16 in RAM, with 400ms pre-roll and 700ms silence end-of-utterance detection. Press Listen once; subsequent segments are automatically passed to Android speech recognition, not via another button.
- Android 13+ recognizer can optionally consume captured PCM through its EXTRA_AUDIO_SOURCE file descriptor. Provider support is unverified. May use network processing through system provider.
- Final recognized utterances appear in the Ritsu/All feeds with local outbox status. Interim text is not an executable command.
- The microphone uses VOICE_COMMUNICATION and Android AcousticEchoCanceler where available, but hardware cancellation cannot guarantee rejection of all phone speaker audio.
- Conservative playback guard rejects ambiguous automatic utterances while Android reports active media. This prevents blind YouTube self-transcription, but also blocks genuine barge-in while media plays. The missing near-end speech detector is a gating requirement.
- Advanced explicit media pause control uses Android transient audio focus; third-party players may not pause or resume, and **automatic media pause on verified human speech is not implemented**.

## Check on device
1. Install v0.6 APK (if Android refuses a debug key change, uninstall only the separate Ritsu Control app, never the Termux voice receiver).
2. Open Ritsu, tap Listen once, grant microphone access. Say one sentence and leave one second of silence.
3. If system PCM injection is supported, words should appear in the Ritsu and All views automatically; otherwise an explicit provider status/error should appear under More.
4. Worker tab currently says No verified results because the authenticated Home Center result feed has not yet been connected.
5. Test with phone YouTube playback: ambiguous sound should be rejected, not treated as a command. Headphone behavior also needs testing.
6. Mute physically stops mic capture and recognition. Stop ends session.

## Unmet acceptance
- Real phone support for Google recognition PCM injection and ASR word quality; no automatic continuous Google recognition is guaranteed.
- Echo-cancelled distinction between owner speech and Ritsu/YouTube, real automatic media pause with confirmation, accurate user barge-in and Termux clip-scoped playback cancellation.
- Phone -> Home Center authenticated turn ingest, durable outbox sync, Chromium Throne real ChatGPT reply, multiple worker results, approved Ritsu voice synthesis and canonical Tailscale 19643/Termux playback with audible confirmation.
- Phone lock-screen, permission loss and provider timeout/device runtime testing.

This is **not yet a working two-way voice companion**. Build/test PASS cannot be mistaken for phone runtime, chat delivery, or user-heard playback. Do not fabricate worker results.
