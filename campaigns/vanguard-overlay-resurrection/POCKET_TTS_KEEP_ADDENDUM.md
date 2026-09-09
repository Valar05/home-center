# VANGUARD // OVERLAY RESURRECTION — Pocket TTS Keep Addendum

Date: 2026-09-09
Owner: Drew Clarke
Status: BINDING COMMISSION ADDENDUM

## Correction preserved

The resurrected Home Center operator overlay is the **user-facing Pocket TTS surface**. Do not substitute the Home Center main app, a new launcher activity, a web UI, a Termux UI, or ChatGPT read-aloud as the product surface.

The existing `com.dclar.homecenter/.PocketTtsPlaybackActivity` remains an allowed **plumbing component** because it is already the proven Android playback organ. Its existence does not make the Home Center main app the user-facing product.

## Canonical voice lane — no substitutions

Pocket speech must preserve the already-proven mechanism:

`overlay request -> Home Center phone relay -> fortress-read -> pocket-tts-phone -> shizuku/rish -> com.dclar.homecenter/.PocketTtsPlaybackActivity -> completion receipt`

Required identity:

- provider: `pocket-home-center`
- engine: `pocket-tts-phone`
- playback transport: `shizuku-rish`
- output component: `com.dclar.homecenter/.PocketTtsPlaybackActivity`
- system fallback: forbidden
- cloud TTS fallback: forbidden
- Cartesia fallback: forbidden
- browser/ChatGPT read-aloud fallback: forbidden

Do not embed Torch/PocketTTS into the overlay APK. Do not create a second TTS implementation. Do not make a localhost HTTP TTS daemon the default architecture. The reviewed `fortress-read` adapter already owns synthesis, WAV repair, Android launch, log verification, cleanup, and the distinction between rendered audio and completed physical playback.

## Overlay speech request contract

The overlay must expose a small durable request/receipt seam separate from deterministic listening/KEEP state. At minimum the state provider must be able to report:

- `pocket_speech_request_id`
- `pocket_speech_text_b64`
- `pocket_speech_text_sha256`
- `pocket_speech_status` — `IDLE`, `PENDING`, `RUNNING`, `COMPLETED`, `FAILED`, or `MUTED`
- `pocket_speech_receipt_b64`
- `pocket_speech_updated_ms`
- `pocket_speech_fault`

The text payload is bounded UTF-8. The SHA-256 covers the exact decoded bytes. A request ID may never be silently rebound to different bytes.

The phone relay consumes the request locally. It must persist the highest terminally handled request identity outside the overlay process before acknowledging completion, so relay restart cannot replay a completed paragraph. A `PENDING` request may survive relay downtime. A terminal request must not speak twice merely because the relay or overlay restarts.

The relay invokes the canonical `fortress-read` entrypoint and stores its exact machine receipt back into overlay-visible state. `COMPLETED` is legal only when that receipt proves `playbackVerified=true`, `playStartObserved=true`, and `playCompletedObserved=true`. Synthesis-only output is not completion.

If the overlay's speech mute is active when a pending request is claimed, record `MUTED` without invoking another engine. Unmuting does not automatically replay an old muted request; a fresh request is required.

## User-facing overlay behavior

The primary UI remains minimum-maximal.

### BUBBLE

Keep the existing commissioned listening truth and recall behavior. Add only a compact Pocket speech state affordance when useful; do not turn the bubble into a dashboard.

### FULL

In addition to the existing resurrection commission, include:

- one bounded text field for an explicit Pocket utterance;
- one large accessible `SPEAK` action;
- the existing speech mute control, now authoritative for Pocket speech as well;
- visible state `ready / pending / speaking / completed / failed / muted`;
- a compact receipt/fault disclosure rather than a wall of diagnostics;
- the Ritsu opinion area may offer its current text to the same Pocket request seam. It does not get a separate TTS engine or daemon.

Do not restore the legacy TERM / CHAT / CONT / VLAD / RADIO wall, Spotify wall, Adam labels, or the old dashboard clutter merely to obtain an input box.

## Home Center / ChatGPT delivery

Home Center remains the control authority underneath the overlay. A connected ChatGPT carrier may place text on the overlay and request Pocket speech through the same bounded seam. The visible overlay and its mute/status controls remain the user-owned acceptance surface.

A generic `phone_shell` call that speaks without updating/obeying the overlay may be used for doctor/canary repair, but it does not satisfy the final overlay-product delivery claim.

## Independence from ambient listening

Pocket speech output must not become a dependency of microphone capture, rolling PCM, ASR, STOP, transient clearing, or explicit KEEP. A broken/missing Pocket voice may produce a voice fault while the deterministic overlay safety controls continue working.

Likewise, the ambient-listening commission is not permission to auto-speak every transcript or opinion. Speech occurs from an explicit overlay request or an explicitly authorized Home Center/Ritsu output event and always obeys mute.

## Evidence gates

Keep these states distinct:

1. source requested
2. source implemented
3. static contract passed
4. Android built
5. overlay deployed
6. Pocket doctor passed on the physical phone
7. overlay request consumed
8. Pocket synthesis succeeded
9. playback Activity launch acknowledged
10. `play_start` observed
11. `play_finish reason=completed` observed
12. overlay receipt readback reports completed
13. Drew accepts what he actually heard

No earlier state may be rounded up into a later one.

## One-script campaign law

Drew authorized at most one manual campaign script. If the Home Center phone relay cannot consume commands, the only manual handoff for this combined Pocket/overlay campaign must be one durable repository bootstrap invoked by one short command. That bootstrap must recover the relay first, then hand control back to Home Center and resume the Vanguard overlay campaign. Do not emit additional repair scripts afterward; subsequent repair must flow through the restored Home Center lane.

## Compact law

**OVERLAY IS THE FACE. HOME CENTER IS THE AUTHORITY. FORTRESS-READ IS THE THROAT. POCKET-TTS-PHONE IS THE ENGINE. THE EXISTING HOME CENTER PLAYBACK ACTIVITY IS PLUMBING. ONE REQUEST ID, ONE SPEECH EFFECT, ONE RECEIPT. NO FALLBACK. NO SECOND TTS STACK. NO SECOND MANUAL SCRIPT.**
