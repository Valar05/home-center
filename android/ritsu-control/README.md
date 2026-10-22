# Ritsu Control v0.3: local listening and floating mute bubble

## What it really does
- Opt-in continuous **microphone** capture on Android (AudioRecord, PCM16, mono, 16 kHz), local energy-based voice activity detection only.
- A deterministic `OFF -> LISTENING -> MUTED -> LISTENING -> OFF` state machine with a bounded local metadata receipt ledger (`sessionId`, `seq`, transitions, reason, monotonic timestamp).
- Actual **Mute microphone** stops and releases AudioRecord *before* showing MUTED. Resume must successfully restart capture before showing LISTENING.
- Optional 56dp draggable **Ritsu overlay bubble**: tap to expand Mute/Resume, Stop session, Hide bubble. Tap again to collapse. Drag by the R circle.
- User-managed Android Quick Settings tile and Ritsu Activity reopen bubble after hiding it or Android dismissing the notification.
- No microphone start on device boot or process restart; explicit visible app start with RECORD_AUDIO permission.
- No automatic file recording, transcript, ASR, wake phrase, remote command, Home Center upload, TTS or network interface. User's separate voice relay is unmodified.

## Running on Android
1. Install the new **v0.3** debug APK. If Android rejects it because its ephemeral debug signing key differs from v0.2, uninstall only the standalone Ritsu Control application and install v0.3; the separate Termux audio receiver is unaffected.
2. Open **Ritsu | Listening control**, tap **Start local listening**, grant microphone permission.
3. Tap **Enable floating Ritsu bubble**. Android opens **Display over other apps** approval. Allow *Ritsu Control*. Return to the app; the bubble appears.
4. Tap the bubble. **Mute microphone** stops the real recorder and updates the local mode. **Resume microphone** restarts the capture. **Hide bubble** removes the overlay without modifying microphone mode; **Stop session** ends everything.
5. To restore a hidden bubble, open the Ritsu Control app from its Quick Settings tile or launcher and tap **Enable floating Ritsu bubble**.
6. Observe Android's microphone privacy dot as an independent indicator. An external app or OS policy may interrupt or silence mic capture; device acceptance must still verify actual app behavior. The UI status can be refreshed.

## Security / truth gates
- Overlay permission (`SYSTEM_ALERT_WINDOW`) is **optional** and independently user-controlled. No full-screen touch interceptor, screen guard, Shizuku, rooted device, UI automation or background-start exploit.
- `RECORD_AUDIO` is requested only on the visible activity. Service declares `FOREGROUND_SERVICE_MICROPHONE`, `microphone|specialUse`, and uses `START_NOT_STICKY`. Mic is never restored from a saved requested flag.
- The service still holds its foreground service session after mute so a user-triggered notification or bubble action can resume capture, but no audio is read while MUTED.
- Audio buffers live in the AudioRecord worker and are reused; the app has no INTERNET permission, so source cannot send audio to remote services.
- Voice activity detection is threshold/hysteresis, **not** a speech-recognizer. It cannot identify speakers, wake words, language, or commands.
- Small system foreground notifications remain swipe-dismissable on Android 14+. Quick Settings tile and optional overlay are separate reentry paths.
- Unit tests validate transition legality, silence/voice hysteresis and fail-closed stop. CI proves compile/test, not Android mic permission/runtime semantics. Accept only after actual phone receipts and an Android microphone privacy-indicator test.

## Intended deterministic bridge next
- Assign immutable turn identifiers only to explicitly recognized and confirmed utterances after implementing a proper ASR/wake-word engine.
- Serialize commands through Home Center: envelope id, source, session, sequence, scope, expiry, idempotency key and explicit user authorization.
- Complete dialogue/worker ChatGPT session rotations using Chromium Throne separately from phone capture.
- Never treat arbitrary assistant/worker text as an executable command, never inject audio into Ritsu phone transport except through the previously approved route.
