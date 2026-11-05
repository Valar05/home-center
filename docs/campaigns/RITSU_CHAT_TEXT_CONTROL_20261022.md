# Ritsu Chat Control Transport: Stage C1 (secondary text fallback)

## Gboard transcription and personalized correction preference (2026-10-22)
The owner reports that **Gboard's built-in dictation works very well**, and wants to preserve its familiar autocorrection/personalized vocabulary rather than replace it with a noticeably worse recognizer.

- **Visible text/inspection mode:** use a normal Android editable text input that invokes the user's existing **Gboard** keyboard. The Gboard microphone, autocorrect, corrections and vocabulary remain under Gboard's control, not a hand-rolled Ritsu keyboard.
- **Hands-free primary mode:** do **not** promise that an app can silently commandeer Gboard voice typing behind the lock screen. Gboard dictation is an IME feature for an editable focused UI; it is not a supported always-on background microphone API.
- For eyes-free listening, investigate Android's supported speech-recognition facilities with **on-device availability checked at runtime** and VAD-triggered bounded utterances, without asserting equivalence to Gboard's personalized correction. Android's `SpeechRecognizer` documentation says it is not intended for unbounded continuous recognition; do not run endless recognition calls.
- Preserve exact ASR text in receipts and keep corrected text distinct if a later explicit correction stage is implemented. Do not silently rewrite proper names, commands, addresses, or personal vocabulary using a generic language model.
- Device acceptance compares **Gboard dictation quality** with the chosen heads-free ASR on actual frequently used names/terms; ask for fixes only if evidence shows a gap. Gboard stays available as a user-controlled fallback.

## Google recognizer reuse and correction surface decision (2026-10-22)
The owner asks to reuse Google's existing speech recognition and Gboard's intelligent autocomplete. Implement the **supported** portion directly:

- Default recognizer: `SpeechRecognizer.createSpeechRecognizer(context)` after `isRecognitionAvailable(context)` and declared `<queries><intent><action android:name="android.speech.RecognitionService" /></intent></queries>`. Where supported, `createOnDeviceSpeechRecognizer(context)` may be selectable. Inspect the actual provider and runtime behavior; do not assert it is the exact Gboard/Assistant voice-typing model.
- Prioritize speaker-specific vocabulary by passing `RecognizerIntent.EXTRA_BIASING_STRINGS` (API 33+) and optionally `EXTRA_ENABLE_BIASING_DEVICE_CONTEXT`. Both are **hints, not guarantees**; feature/provider support must be checked.
- **Existing user precedent:** Drew built a *new keyboard for June* that successfully reused the same autocorrect preferences. Treat this as a real prior working observation, not a hypothetical claim that needs to be argued away. Locate/recover the implementation before assuming we need a new language model or private vocabulary store.
- **Critical Android API distinction:** a custom Android IME or spellchecker may use the shared `android.provider.UserDictionary` and the enabled spellchecking service. Official `UserDictionary` docs say that starting with API 23, user dictionary access is restricted to IMEs and spellcheckers; an ordinary background service has different access. `TextServicesManager` / `SpellCheckerSession.getSentenceSuggestions` offers system-service suggestions to eligible clients. This can explain how a brand-new keyboard picked up settings without copying a Gboard private database. Which exact route June's keyboard used is **not yet verified from its source**.
- Gboard's private internal ranking and any unexposed learned state are not themselves a documented public API, but **do not conflate that with lack of access to shared system dictionary and suggestions**. Test reuse of system settings first, and distinguish observed behavior from implementation assumptions.
- First attempt to reuse the same **shared autocorrect settings and suggestion mechanisms that June's keyboard used**. A visible transcript field can also invoke Gboard directly. If the keyboard project used a custom IME adapter, test that approach without replacing Ritsu's foreground-service microphone or pretending an IME can run unattended dictation.
- Google `SpeechRecognizer` may use network/cloud audio processing and is **not intended for unbounded continuous sessions**. Keep the user-consented microphone foreground session distinct from individual bounded ASR utterances triggered by local VAD; only allow one microphone owner at a time. Where the recognition provider opens its own mic, release/pause the app's AudioRecord first and reacquire after completion; explicit mute/stop cancels both layers. Test screen-off, Android privacy indicator, service lifetime, provider silence and battery on-device.
- Preserve raw transcript and accepted corrections separately with turn ID, do not silently overwrite a personal name. The contract is not accepted until Google recognition on this specific phone returns actual text and a user confirms its quality.

Official Android references: https://developer.android.com/reference/android/speech/SpeechRecognizer ; https://developer.android.com/reference/android/speech/RecognizerIntent ; https://developer.android.com/reference/android/view/textservice/SpellCheckerSession ; https://developer.android.com/reference/android/provider/UserDictionary ; https://developer.android.com/reference/android/view/textservice/TextServicesManager .

## Voice-first product directive (user-confirmed 2026-10-22)
**Voice is the PRIMARY user interaction.** The phone should function as an eyes-free Ritsu conversation with optional minimized floating mute/interrupt controls, while ChatGPT/browser work occurs off-screen. Text input is a fallback/debugging/quiet-mode control, and returned transcripts are optionally inspectable, not an attention-demanding chat inbox.

The **default experience** is:
1. The user explicitly enables a visible, permissioned continuous listening session on Android.
2. A real ASR pipeline detects completed utterances and generates a bounded transcript. Existing energy VAD alone is **not** ASR, wake-word recognition, or a working conversation.
3. The deterministic Home Center coordinator assigns a turn ID, gates one authorized user intent, and sends the bounded turn through **Chromium Throne** without requiring the ChatGPT window to be foregrounded.
4. The exact ChatGPT answer is captured and mapped to the same turn ID, with channel and conversation identity.
5. Approved Ritsu Warm speech output follows the canonical existing Windows/Tailscale `19643` -> Android Termux path per `docs/RITSU_PHONE_AUDIO_LAWS.md`. Never invent an audio alternative.
6. When playback ends, the listening session remains able to capture another user utterance, subject to explicit mic mute, interrupt, stop, permission revocation, and privacy state.
7. Only when deliberately opened, an optional text surface shows transcripts, worker results, delivery receipts, and manual text entry.

**Acceptance criterion:** an eyes-free sequence **speak -> ChatGPT responds -> user hears Ritsu -> speak again** succeeds without opening ChatGPT or typing; the user can interrupt or physically mute the capture using the bubble/notification. Passing text-only transport tests does **not** establish product acceptance.

**Engineering priority after Stage C1:** ASR / utterance finalization and identity-bound authenticated phone<->Home Center ingress, followed by actual Ritsu voice delivery and interruption. A nice text cockpit is lower priority until a complete voice roundtrip is demonstrated.

## Commission and architectural decision
Commissioned 2026-10-22: make a **real ChatGPT control** loop available while voice synthesis and UI overlay are under development. Evaluate Android-hosted versus THECAULDRON-hosted browser. The selected initial host is **Chromium Throne on THECAULDRON**, leaving Ritsu's Android phone as the user-facing cockpit and Home Center as the deterministic, authenticated coordinator.

This choice does **not** mean the phone must display ChatGPT or the desktop worker tab must be foregrounded. Existing Throne creates separate Chrome worker tabs with `active: false`. It does mean the dedicated Chromium Throne profile/extension/relay must be live on desktop.

## Implemented in feature branch
- `browser-porch/ritsu-turn-protocol.mjs` strictly validates stable `sessionId`, `turnId`, `channel` (control/dialogue) and bounded prompt; commandID is derived from turnId, not from a guessed timestamp.
- Existing Chromium Throne localhost relay `browser-porch/relay.mjs` now accepts `action:'chat.turn'` in addition to unchanged swarm actions, requires existing bearer capability and extension-origin lease, and exposes bearer-only `GET /v1/throne/result?commandId=...`.
- A turn can be delivered to Chrome **once**. Duplicates with identical commandId and text are idempotent; conflicting text rejects with 409. A lease expiry becomes `uncertain` and does not automatically replay a potentially already-submitted prompt. In-memory relay dedupe alone is NOT durable across process restart, so authoritative Home Center durability remains a separate unaccepted boundary.
- Extension `browser-porch/extension/service-worker.js` handles `chat.turn` without `BOOT_ENVELOPE` and without invoking the automatic swarm continuation loop, opens a dedicated nonforeground Chrome tab per (sessionId, channel), reuses it for later turns, and persists a pre-send attempt receipt to avoid double submission on ambiguous errors.
- The extension reads an actual new assistant DOM response after the prior assistant baseline. It returns text + matching session/turn IDs and tab ID. A later human accepts or rejects content; `verifiedTurn:true` never implies self-acceptance.
- Protocol and authenticated relay integration tests in `browser-porch/ritsu-turn-protocol.test.mjs` and `browser-porch/ritsu-chat-relay.test.mjs`.
- GitHub Actions workflow `ritsu-chat-control-contract.yml` exercises these tests + existing Chromium Throne relay/extension core regressions.

## Crucial deployment boundary
THIS IS A BRANCH-TESTED TRANSPORT IMPLEMENTATION, **NOT** YET ANDROID TEXT-CONTROL OR A LIVE CHATGPT ROUNDTRIP.
- New Chrome extension and relay source must be packaged/deployed to the exact **Chromium Throne** dedicated profile on THECAULDRON and verified, not Browser Nerve or generic Chrome.
- A secure **Home Center ingress** is still required for the Android Ritsu app to enqueue authenticated text turns and fetch durable replies. Do NOT expose the existing localhost Throne capability directly to a public or LAN socket or put Throne bearer in an APK. It currently listens on `127.0.0.1:9234` for a reason.
- Android must first provide speech-to-text utterance finalization and an authenticated inbound turn path to Home Center, plus canonical Ritsu speech playback and real microphone interruption. Text input, manual send, and response readback are optional inspection/fallback UI, not the next release's defining capability.
- A canary is only externally accepted if same-session ChatGPT submission, browser-confirmed assistant reply, Home Center receipt/readback, phone delivery, and the user's visible confirmation all match by `turnId`.
- No automatic browser wake-from-sleep is proven; background tabs may operate while Chrome is running, but not after computer shutdown/hibernation.

## Why not host Chromium Throne on phone first?
Standard Chrome Android has no Chrome desktop-extension support; the existing Throne extension cannot simply be moved. The authenticated profile already exists on desktop, whereas experimental Android automation often depends on ADB/awake-device semantics and more fragile background scheduling. Future browser adapters may provide a phone-local option behind **the same** Home Center turn schema. This is a swappable actuator, not an Android-vs-desktop religious war.

## No-op / failure truth table
- command queued: not yet sent to ChatGPT
- command leased: extension owns lease, still not proof submitted
- uncertain: browser may have submitted; **never blind resend**
- failed: exact error/receipt required
- completed: DOM observed reply tied to turn, NOT yet delivered to phone or accepted by owner
- home-center delivered: only after cloud/phone routing implemented, authenticated, and verified
- owner accepted: after owner confirmation
