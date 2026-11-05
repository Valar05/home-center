# Ritsu Control v0.8: Gboard-inspired thinking pauses

## Owner observation from v0.7
The system recognizer auto-ended phrases too aggressively. The owner naturally pauses between words while thinking and is accustomed to Gboard's more forgiving dictation cadence. A provider-level onResults callback does **not** establish that the human has finished speaking.

## Changes
- Added pure Java SpokenTurnBuffer. Android recognized final fragments are held as one *draft* turn until **3.2 seconds of quiet following the most recent finalized fragment** rather than being inserted into chat immediately.
- Starting another speech phrase cancels the scheduled commit. New final fragment extends the same draft and resets the timer. This creates one message across pauses when Google's recognizer ends a session early.
- After the full quiet interval, or after an explicit user Mute/Stop, one bounded local outbox message is created and shown in the chat. No duplicate provisional messages are sent.
- The default 3.2s delay is a **tunable approximation of the Gboard feeling**, not a reverse-engineered Gboard internal setting. In **More → Speech pause timing**, choose Quick 2s, Natural 3.2s (default), or Thoughtful 5s. The preference is persisted on the phone and changing it does not instantly submit old drafts.
- Optionally pass Android recognizer 1350/2300ms possible/complete silence hints. Android warns recognition providers may ignore these or behave unexpectedly; the independent application draft buffer is the authoritative commit gate.
- Live UI shows **Composing: ...** while speech is held back. The completed message appears once in the All/Ritsu feed only when the draft is committed. Other conversation channels and Home Center transport semantics are unchanged.
- On recognizer no-match during a continuation attempt, allow quiet timer to elapse rather than losing an already-transcribed earlier fragment. Audio-source rejection still applies before buffering.

## Acceptance test on device
1. Tap Listen and say “I think...” then pause about 1.5 seconds, then “we should make her wait longer.”
2. Expect ONE final chat message, not two. During the pause, see an unfinished composing preview.
3. After speaking ends, wait 3.2s for the single message to enter the local feed. Repeat with Thoughtful (5s) if naturally deliberative speech is still split.
4. Mute after a partial draft: recognized final fragments should be committed locally once, and recording stops. Try speaking for longer than the configured gap to intentionally create two messages.
5. Compare the subjective cadence with Gboard typing on the same phone. Device/provider timing remains subject to Google's own end-of-speech and start-listening gaps.

## Not established
This is **not** a synchronized clone of Gboard's private timing, nor a guarantee that Google will capture every syllable during its restart gap. Real phone behavior remains unverified. The underlying app still does not send to Home Center or retrieve ChatGPT replies, and Ritsu audio responses are not integrated in this APK.
