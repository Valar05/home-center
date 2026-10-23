# Ritsu Control v0.7: visible chat footer and live Google speech fix

## Owner's phone feedback on v0.6 (FAIL)
- Footer buttons were drawn under Android's gesture navigation/home controls.
- When Gboard opened, it obscured the composer and bottom controls.
- Speech produced no text.

## Corrective changes
- Native Android 15+/SDK35 edge-to-edge layout now consumes real `WindowInsets.Type.systemBars()`, `displayCutout()` and `ime()`. The entire vertical chat column is padded by the larger of the navigation and keyboard bottom insets. Keyboard resize mode is requested. The composer and fixed Listen/Mute/More controls should remain accessible above system UI.
- The More control opens a modal Android dialog rather than expanding a tall panel below the footer.
- A small live recognized-words preview appears above the composer, and returned final recognized speech enters the Ritsu/All feed.
- The app now calls `SpeechRecognizer.startListening()` directly with the provider owning the **live microphone**. V0.6 used `RecognizerIntent.EXTRA_AUDIO_SOURCE` with already-recorded PCM. Android documents that the provider **may ignore** the extra, causing silent/nonworking results. That experimental default route is removed.
- Google's recognizer handles its own speech-ending/silence endpoint. It reports `onResults` or `onError`; the service only requests another bounded session **after** that callback, with 450ms or 1800ms pacing, a 45s watchdog, and a four-consecutive-error fail-closed circuit breaker. This is not a guaranteed continuous Google speech service, which Android's docs discourage for long-running use; battery and real-device stability still need verification.
- If Android reports phone media playback during any part of a recognition session, the transcript is rejected rather than being accidentally treated as an owner command. This conservative, best-effort protection may also reject the owner's own speech while watching YouTube and is not a proven acoustic origin classifier.
- The chat interface still stores only genuine recognized/typed text locally as `WAITING_FOR_HOME_CENTER`, never a fictional worker reply. The Android package still has no INTERNET permission; system recognition provider may perform remote processing under its own permissions.

## Suggested phone test
1. Install v0.7 APK, opening Ritsu Control with mic permission. If a debug signature differs, uninstall **only Ritsu Control**, not the separate Termux receiver.
2. Open Gboard in the composer: both its text field and Listen/Mute/More footer must be visible above the keyboard, including with gesture navigation.
3. Close Gboard, tap Listen once, speak a simple sentence and stop. The recognizer should return final text as a Ritsu/All chat item. Interim words, if exposed by the provider, appear above the composer.
4. If nothing appears, the header and More -> Status and recognition errors should reveal whether Android returns no speech, permission denial, provider busy or network issues.
5. Mute must cancel the active recognizer and stop future listening. Resume restarts the live provider. The phone's microphone privacy indicator is another independent check.
6. Test phone media playback separately. The active-media guard may block transcripts, including real speech over music; do not interpret that as reliable full-duplex echo cancellation.

## Still not implemented
- An authenticated phone-to-Home Center-to-Chromium Throne multi-conversation roundtrip, receiving worker results, and Ritsu speaking her approved voice through the canonical Tailscale :19643/Termux receiver.
- True human speech-vs-phone playback separation and reliable automatic YouTube pause and barge-in.
- Verified Pixel screen-off, Gboard IME resize, recognition quality and Android provider restart behavior.

Passing CI unit tests or generating an APK does **not** validate the owner's runtime experience. No claim of audible Ritsu replies or actual ChatGPT delivery is made.
