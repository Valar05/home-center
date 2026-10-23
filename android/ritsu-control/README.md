# Ritsu Control v0.4: Android speech recognition + Gboard editing (prototype)

## What changed
- The app now uses Android's **default system speech recognition service** for **one explicitly requested utterance** at a time. If the Google service is configured as the default, that is the provider used.
- The existing v0.3 local continuous mic/VAD service remains. Tapping **Use Google speech recognition (one phrase)** releases AudioRecord *first* and hands mic ownership to SpeechRecognizer. After the provider finishes or times out, the app tries to restart VAD, unless the user explicitly muted or stopped. Recognition mode is its own state, never mislabeled "AudioRecord active".
- The recognizer receives supported Android 13+ context biasing hints for Ritsu, Serin, Chromium Throne and other proper names. A provider may ignore them.
- A **Gboard-compatible editable transcript field** allows Gboard dictation, your keyboard's suggestions, autocorrection and user correction exactly as they work normally in an Android text field.
- **See Android spelling suggestions** asks the configured Android system spell checker for optional alternatives. It cannot read Gboard's private learned suggestions; changes are always user-selected, never silently applied.
- Latest speech transcript is ephemeral display state only, not stored to files, not submitted to ChatGPT, and not injected into its existing remote audio relay.
- **Privacy:** default speech-recognition services may use cloud processing, independently of Ritsu's no-INTERNET manifest. Do not assume all recognition is on-device.

## How to test the actual Android recognizer
1. Install v0.4. If it will not update v0.3 due to different debug signing keys, uninstall only the separate **Ritsu Control** app, then install the new APK. The Termux audio receiver is a different app and remains unaffected.
2. Open Ritsu Control, select **Start local listening** and grant Android microphone permission.
3. Tap **Use Google speech recognition (one phrase)** and speak when its status says "Speak now". This is **bounded provider dictation**; do not assume it will automatically recognize later phrases. If no provider is available, the failure appears in the app.
4. Tap **Refresh live status** then **Load recognized transcript** to place recognized words in an Android editable text field.
5. Focus the field to use the actual installed Gboard keyboard, dictate or manually correct the transcript, or tap **See Android spelling suggestions** to inspect optional suggestions from the system spellchecker.
6. Confirm **Mute microphone** and **Stop entire session** cancel current recognition and release the microphone. The floating bubble remains an optional overlay, subject to Android's separate permission rules.

## Implemented versus still unverified
- Source implements Android system SpeechRecognizer, proper microphone handoff, 45-second time limit, local transcript, Gboard editing and spell-checker suggestions.
- CI compilation/tests establish syntactic and pure-state correctness only. Actual microphone capture handoff, default provider quality, Android privacy indicator, suggestions and locked-screen behavior all require human device verification.
- Neither Google ASR nor Gboard autocomplete means Ritsu now controls ChatGPT: **authenticated phone -> Home Center ingress**, and real voice-response return through the canonical Tailscale/Termux relay, remain unimplemented.
- This is **not** continuous Google dictation. The separate continuous local VAD detects energy but cannot hear words; Android SpeechRecognizer explicitly discourages uninterrupted continuous recognition.
- The source cannot reconstruct the old keyboard from another phone and does not claim to access Gboard's private personalized model.

## Security / architecture
- No automatic microphone start on boot, no Phone Hands audio transport, no change to the approved Windows/Tailscale 19643 receiver.
- No Android INTERNET permission or transcript upload in the Ritsu app. The system ASR provider may communicate with Google's services according to phone settings and its own permissions.
- Mic + foreground service, Quick Settings reentry and optional overlay follow the same v0.3 permissions; no global touch interception.
- Muting is physical release of AudioRecord **and** cancellation of an in-progress recognition session, without rearming after an explicit mute.
- Turn submission and external command execution are forbidden for raw/unreviewed transcript strings until Home Center's authenticated deterministic coordinator is connected.
