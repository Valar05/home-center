# Ritsu Command Bridge: Android salvage and system boundary (2026-10-22)

Status: SOURCE INVENTORY + PROPOSED IMPLEMENTATION CONTRACT. No Android deployment, voice activation, microphone recording, ChatGPT conversation automation, or end-to-end loop has been performed by this document.

## Drew's commission, preserved

Build a phone-facing Ritsu voice control interface, preferably an ongoing notification with optional overlay; reuse the proven Ritsu phone audio path and helpful older operator overlay code. Support explicit listening on/off and microphone mute (with separate speaker mute), conversational turns resembling ChatGPT Voice, and a **single human-facing control conversation**. A Chromium Throne-inspired **headless/authenticated desktop browser** operates ChatGPT conversations; Home Center coordinates the browser and parallel specialized chats, returning their results to the front conversation. Keep context/history outside the active conversation so it can be automatically rotated with a durable handoff. Home Center owns deterministic scheduling, including optional Google Calendar triggers, and command routing. The front chat can request operations of the outer daemon, but the daemon alone owns run state/leases, avoiding uncontrolled model self-recursion. No replacement with an OpenAI API-only chat, alternate phone-audio transport, generic browser worker, or a local LLM is authorized.

This is larger than the already-approved **Ritsu Voice Online** speech-output law. Do not activate that mode or send audio merely by reading this document.

## Verified source inventory (repository evidence, not deployed-state proof)

### Existing Ritsu Android notification (direct fit for v0)

- `tools/campaigns/ritsu-phone-embodiment-20261021.sh` installs `~/.ritsu-embodiment/receiver.sh` and `control.sh`.
- Termux ongoing notification **19643**, title "Ritsu | Embodiment", has **Pause**, **Resume**, **Stop** buttons.
- Receiver polls the authenticated Windows/Tailscale `:19643/next`, downloads `/audio/<id>`, ACKs, plays with `termux-media-player`.
- These buttons currently affect **playback**, not mic input, ChatGPT voice sessions, worker orchestration, or conversational listening. The notification's live presence on the user's current phone is unverified.
- Canonical phone audio rules: `docs/RITSU_PHONE_AUDIO_LAWS.md`. Do not replace its transport or use a generic Phone Hands audio fallback.

### Retired Android operator overlay: harvest selected parts only

- `android/operator-overlay/app/src/main/java/com/homecenter/operatoroverlay/OperatorOverlayService.java`: foreground notification channel, ongoing notification and restore PendingIntent; movable/collapsible WindowManager overlay; touch-safe dimensions; accessible button descriptions; mute button; visual state (online, offline, active, disabled); confirmation for broader remote-control shutdown; hide/restore.
- `android/operator-overlay/app/src/main/java/com/homecenter/operatoroverlay/OperatorState.java`: SharedPreferences-backed durable UI flags, including `muted`, `control_enabled`, `panel_collapsed`, `overlay_hidden`, position, heartbeat; committed fail-closed disabling state.
- `android/operator-overlay/app/src/main/java/com/homecenter/operatoroverlay/OverlayUiPolicy.java`: pure clamp/drag tests and 48dp minimum touch targets; useful to port without importing broader controls.
- `android/operator-overlay/app/src/main/java/com/homecenter/operatoroverlay/BootReceiver.java`: historical restart pattern, **not** proof a modern microphone foreground service may auto-start on boot.
- `android/operator-overlay/app/src/main/java/com/homecenter/operatoroverlay/OverlayUpdateReceiver.java`: small state-update/heartbeat pattern; change authorization/surface for the new design.
- `android/operator-overlay/app/src/main/java/com/homecenter/operatoroverlay/OperatorStateProvider.java`: provider/readback design reference only; avoid broad exported/permission assumptions.
- `android/operator-overlay/app/src/main/java/com/homecenter/operatoroverlay/VeniceAudioCaptureService.java` uses MediaProjection to analyze **playback audio**, not microphone input. Do **not** mistake it for speech recognition.
- Retired guard: `tools/recover_adam_overlay_phone.sh` explicitly disables old auto-recovery without an archaeology opt-in. `tools/home_center_status_menu.sh` likewise retires the old Termux menu. **Do not re-enable either.**

**Scavenge decision:** reuse notification/foreground-service pattern, state reducer concepts, 48dp targets, accessible labels, safe collapse/restore, readable heartbeat and last-message preview. Do **not** copy old Adam command executor, Spotify bridge, Shizuku powers, global touch guard, invasive screen-overlay permissions, MediaProjection, old terminal aliases, or 200ms polling as a default.

### Chromium Throne existing work

- `browser-porch/extension/service-worker.js` already contains a bounded queue and relay poll, `chrome.tabs.create` worker spawn, persistent worker reuse, assistant completion polling, and latest-assistant capture.
- `browser-porch/extension/swarm-core.mjs` already has a 4-worker bound and structured continuation/handoff routines.
- `browser-porch/extension/throne-panel.mjs` is an existing explicit operator surface.
- `browser-porch/contract.mjs` provides account/origin/pairing checks and bounded approval for selected operations.
- This implementation is **extension/browser-profile code**, not proof that a production **headless** adapter, full incoming/outgoing main-chat bridge, or automatic new-thread rotation exists. Examine live THECAULDRON runtime before reusing implementation. Do not silently substitute the distinct Browser Nerve lane for Chromium Throne.
- Browser DOM automation is change-prone and faces site permissions/terms. Before claiming unattended ChatGPT extraction/posting as a supported capability, verify the authorization/policy boundary, account sign-in behavior, current UI selectors, and live end-to-end acceptance. Do not substitute an API architecture without Drew's consent.

### Home Center / voice status

- The deployed capabilities registry currently **lists** `ritsu.voice.speak/status/worker.register`, but `RITSU_PHONE_AUDIO_LAWS.md` describes the typed worker as staged in PR #386. A listed operation is not worker readiness or user-heard audio. Require current runtime status and a canary before using.
- The selected everyday voice is approved `Ritsu | Warm | v1`, with Windows GPU maintenance constraints. In this session explicitly **do not follow playback instructions**; no model startup, synthesis, or send.
- `docs/RITSU_VOICE_ONLINE_SPEC.md` confirms the post-response automatic delivery hook is not proven. This project needs its own deterministic dispatcher.

## Proposed topology (not yet implemented)

```text
Android visible persistent notification (and optional compact overlay)
  MIC: OFF / PUSH-TO-TALK / LISTENING / MUTED ; SPEAKER: ON / MUTED
  + stop / interrupt / Open cockpit / worker status
             |
             | authenticated bounded commands + microphone turns
             v
Home Center durable Turn Coordinator, receipts, leases, schedules
   |                    |                        |
   |                    |                        +--> Google Calendar trigger adapter
   |                    v
   |          Chromium Throne desktop daemon
   |            /                  \
   |    front CONTROL chat     one or more DIALOGUE / worker chats
   |      identity pointer     tagged roles, bounded fan-out
   |            \                  /
   |             durable worker results + response provenance
   v
Ritsu approved Windows TTS -> existing Tailscale 19643 -> Android Termux
```

The Android control surface is a **client**, not the source of truth. One Turn Coordinator serializes mutating commands and assigns a unique turn ID, conversation-role ID, worker ID, idempotency key, deadline, and lifecycle state. Only **external user speech/explicit button** or a previously authorized schedule can create a new top-level control turn. Worker output is data to route back, **not an implicit new user command**. Cap nesting/fan-out; refuse to echo a completed turn back into itself. This is the necessary anti-infinite-loop invariant.

The single front conversation remains what Drew sees. Actual persona/dialogue content may be produced in a separately tagged dialogue-worker thread, then surfaced to the front chat. Preserve exact output attribution and avoid having the front ChatGPT model rewrite it silently. Browser-posting or model-to-model bridging is a separate capability with its own tests.

## Independent controls (do not conflate)

| Control | Semantics | Default |
|---|---|---|
| Start conversation | Explicitly enables microphone session, after permission and authorized foreground start | Off |
| Mic mute | Stops recording/streaming; does not merely suppress transcript submission | Muted until started |
| Speaker mute | Silences local synthesized response, independent of mic | Off |
| Interrupt | Stops current playback and cancels or supersedes active turn without closing chat | Available while active |
| End conversation | Stops audio capture, releases relevant resources; leaves durable chat state | Explicit |
| New chat / rotate | Coordinator checkpoint + fresh conversation + verified identity pointer swap; never just open a blank tab | Not automatic before proven |
| Open cockpit | Opens full accessible control activity, without creating a new chat | Available |

The older overlay's `muted` controlled status speech, not mic input. Termux receiver Pause/Resume/Stop are playback controls. Neither is already a voice-mode toggle.

## Milestones with acceptance and sequencing

1. **A: UI reuse preflight.** Verify current phone package/Termux notification and THECAULDRON relay health, read-only. Prototype a new ongoing notification (microphone state + speaker toggle + interrupt + Open) with saved state and accessibility labels. No old overlay resurrection. Test button => persisted state => visible notification refresh => reboot readback, without starting voice generation.
2. **B: Real phone microphone.** Implement proper foreground microphone service and permission user gesture on Android; capture -> endpoint/ASR -> bounded transcript. Android 14+ has while-in-use foreground microphone service limits, so do not assume `BOOT_COMPLETED` can start listening. Test lock-screen, notification action, force-stop, mute privacy, interruption, permission revoked, offline. Explicit consent and visible mic state required.
3. **C: One-turn loop.** Phone speech -> durable Home Center turn -> selected **Chromium Throne** authenticated session -> one ChatGPT conversation -> exact response captured -> approved Ritsu Warm/Tailscale reply, preserving user-heard evidence. Do not claim a chat UI can be reliably automated before checking site policy and live selectors.
4. **D: Dual-chat role separation.** Control chat commissions a dialogue-worker chat through Home Center; worker result arrives back in the front chat; no uncontrolled recursive invocation. Verify stable IDs, ordering, captured exact text, user approval where appropriate, one timeout, one retry with idempotency.
5. **E: Parallel workers + handoff.** Reuse Throne's bounded parallelism. Home Center persists summary + explicit constraints + open commitments + current objective + source refs + test receipts. Rotate only after a validated checkpoint and verified successor ready; swap stable logical alias atomically. No invisible loss of unfinished work.
6. **F: Deterministic schedules.** Home Center stores event rules tied to Google Calendar event IDs/revisions and explicit approvals. Time/condition triggers create idempotent coordinator jobs independently of chat windows. Distinguish notification from automated action and protect against repeating/rescheduling after event edits.
7. **G: Hardening.** Reboot, screen-off, Tailscale outage, GPU-maintenance pause, stale authenticated ChatGPT session, worker crash, user interrupt, context rollover, Android duplicate receiver, clock skew and calendar edits. Record transport and audible verdict separately. No deployment PASS without real phone readback and audible acceptance.

## Current stop line and evidence

- SOURCE INSPECTED: Ritsu Termux notification installer, retired overlay and UI policy, Chromium Throne extension, Home Center capabilities.
- NOT PROVEN LIVE: current phone notification visibility/registration, current installed overlay status, speech-recognition pipeline, Chromium Throne headless ChatGPT automation, automatic front/worker roundtrip, context rotation, calendar scheduling, new Android notification controls.
- This branch is a **salvage/design checkpoint only**, not operational delivery. No Android APK, compiled app, voice sends, model processes, worker jobs, or deployment initiated.


## User direction: Voice-first supersedes optional text cockpit (2026-10-22)

**Primary acceptance is an eyes-free spoken conversation**, not a text messenger. The phone captures an authorized utterance, ASR finalizes it, Home Center deduplicates and coordinates the ChatGPT turn through Chromium Throne, and Ritsu speaks the reply over the already-approved Tailscale/Termux audio path. A second spoken turn must work without manually bringing ChatGPT onscreen. The floating bubble offers quick physical mic mute/resume and interruption.

Text compose and transcript/readback are **secondary opt-in capabilities** for troubleshooting, quiet environments, and inspecting what actually happened. They must not delay the next working voice roundtrip, and text-only browser tests do not qualify as voice acceptance.

Current truth boundary: v0.3's Android microphone layer only performs local energy VAD; actual speech recognition, authenticated Home Center ingress, integration with the desktop Chromium Throne profile, canonical speech playback, barge-in interruption, and user-heard verification remain to be implemented and tested. Refer to `docs/campaigns/RITSU_CHAT_TEXT_CONTROL_20261022.md` for the voice-first amendment to the bounded one-turn protocol.


## Full-duplex / barge-in amendment (2026-10-23)

**Owner requirement:** Ritsu's microphone remains able to hear the *human* while she is speaking, and the human may interrupt her mid-sentence, just like a real-time voice call. **Do not** implement this by turning off listening or merely ducking the speaker. **Ritsu must not dispatch her own synthesized speech as human speech or a ChatGPT turn.** This is separate from explicit mic mute, which must still release capture.

A credible full-duplex design is:
1. While Ritsu is outputting a known reply (with `replyId`, clip IDs, playing timestamps and text receipt), the phone mic must remain owned by one continuous capture front end. The speaker playback is the canonical existing Termux receiver over Tailscale :19643, **not** an arbitrary new audio path.
2. For acoustic suppression, investigate Android `AcousticEchoCanceler` attached to `AudioRecord.getAudioSessionId()` and the phone's `VOICE_COMMUNICATION` capture path. The actual Ritsu WAV/PCM playback reference is held under **another app** (Termux) and is not automatically accessible through the Ritsu APK. Investigate an explicitly authorized local reference seam; don't assume cross-app capture/Termux private files are readable. Hardware AEC is platform-dependent and cannot guarantee complete rejection.
3. Treat **raw VAD, volume threshold, matching transcribed text, or identical voice embedding** as insufficient to prove a human interruption. A false positive would stop Ritsu for her own speaker echo. Require a tested acoustic *near-end* speech classifier or explicit user action. Avoid relying on an identity classifier that incorrectly suppresses the owner.
4. At confirmed user barge-in, request **immediate cancellation of current Ritsu playback**, invalidate any queued remainder of the superseded spoken reply, and obtain a clip-specific stop **acknowledgement** from the phone receiver. The currently installed Termux `control.sh stop` calls `termux-media-player stop`, but it has **no acknowledged turn-ID boundary**, so do not claim this completes barge-in.
5. Continue capturing the user's first spoken syllable. Preserve a bounded ephemeral pre-roll buffer for the near-end utterance so stopping playback and starting ASR do not clip its start; discard audio after utterance finalization/cancellation.
6. Only after the prior reply is observed interrupted or its stop failure is reconciled, send the **human** utterance into Home Center with a fresh idempotent turn ID. Explicit bubble/notification Interrupt must always work independently of acoustic echo rejection. The mic Mute button remains separate: Mute stops capturing, Interrupt stops *speaking*.
7. Google `SpeechRecognizer` is not a continuous duplex engine and the current v0.4 `SystemSpeechSession` takes over the microphone for one phrase after stopping the AudioRecord. Android 13+ `RecognizerIntent.EXTRA_AUDIO_SOURCE` can allow supplying externally captured PCM via ParcelFileDescriptor **if the provider supports it**, but this feature is optional, and may bypass some provider biasing context. Verify on the actual Pixel before selecting it. Do not claim v0.4 meets barge-in.

**Source-only foundation:** `android/ritsu-control/app/src/main/java/com/homecenter/ritsucontrol/BargeInPolicy.java` and unit tests enforce that raw energy never interrupts, confirmed near-end speech or an explicit button enters `STOP_PENDING`, only a matching playback stop receipt enters `INTERRUPTED`, and any timeout/error becomes `UNCERTAIN` rather than fake success. This policy is not yet wired into microphone capture, echo suppression, the Termux receiver, or ChatGPT routing.

**Device acceptance:** Ritsu speaks loudly through phone speaker while user is silent => no microphone transcript/turn and no accidental stop; user speaks at same time => Ritsu stops promptly, user's first word is preserved, a single new turn is sent; stale stop ACK and old queued audio cannot restart prior reply; works with external speaker/headphones/low volume only within individually verified configurations. If near-end detection confidence is insufficient, display that limit and retain manual Interrupt rather than falsely claiming always-safe recognition.

Official Android contracts: https://developer.android.com/reference/android/media/audiofx/AcousticEchoCanceler and https://developer.android.com/reference/android/speech/RecognizerIntent#EXTRA_AUDIO_SOURCE .
