# Ritsu Control v0.5: fix invisible speech-recognition results

## V4 fault diagnosis
A confirmed owner report from their phone: speech into the installed V4 produced no visible text and no Ritsu spoken reply. Source inspection revealed two concrete UI/flow errors:
- V4 required **Start local listening** followed by an independent **Use Google speech recognition** tap. The first control only launched AudioRecord's **energy detector** and never generated words.
- Even a successful `SpeechRecognizer.onResults` wrote a static field, and the editable Gboard text box was only populated by a further **Load recognized transcript** tap. Normal UI refresh didn't pull in the results.
- V4 had no phone->Home Center->ChatGPT->Ritsu TTS transport, so speech output was not implementable from that app. It cannot be called a voice companion.

## V5 repairs
- One **Talk to Google recognizer (one phrase)** button requests RECORD_AUDIO from the visible activity and then starts mic/ASR handoff in one operation, rather than quietly enabling energy VAD only.
- The visible Activity updates status and transcript every 300ms **while visible**, with callbacks stopped when paused. No background screen polling.
- The recognizer's partial results are displayed as interim words immediately when Google returns them, and a final result automatically replaces the preview in the Gboard-compatible editable field.
- Speech errors, timeouts, busy provider, permission and network errors have **human-readable** diagnostic status (and no false text).
- All recognized text is local/ephemeral, never automatically treated as a ChatGPT command or routed through a model. The system provider may separately use online recognition.
- Independent **Start local listening** still runs only the local energy detector and is labeled as such.

## Expected test
1. Install debug V5 (may need uninstalling only old Ritsu Control if CI ephemeral debug signature differs).
2. Open Ritsu Control and tap **Talk to Google recognizer (one phrase)** just once. Approve mic permission if asked.
3. Say a short sentence. Watch interim or final words appear directly in the text field. An explanatory provider error should appear in live status if the recognizer fails. The provider may produce only final results.
4. Open Gboard in the field to use your normal editing/autocorrect suggestions.
5. This still does **not** cause Ritsu's voice to speak back. The certified voice-response path requires the authenticated Home Center and Chromium Throne bridge, an existing Ritsu voice worker, and the canonical Windows/Tailscale :19643 -> Termux playback. It must not be simulated with generic Android TTS.

## Verification boundaries
CI pass == compiled APK + pure-state and manifest/flow contract checks. It is **not** device recognition proof, ChatGPT command delivery proof, or audible feedback proof. The owner must verify phone behavior. The speech provider API is not intended for indefinite continuous recognition, so this button remains single-phrase; full-duplex live voice/barging remains unaccepted.
