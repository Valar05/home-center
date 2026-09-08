# VANGUARD // OVERLAY RESURRECTION — worker commission

## Owner and mission boundary

Owner: Drew Clarke.

Vanguard commissions recovery of the **existing Home Center Android operator overlay lineage** with actual intelligence. Do not substitute a new unrelated app, web overlay, accessibility service, Termux UI, desktop UI, or speculative architecture. Recover and evolve `android/operator-overlay` in `Valar05/home-center`.

The product is minimum-maximal: tiny permanent control surface, large capability behind it. It is not a dashboard landfill.

Ritsu is the default opinionated intelligence voice. Other explicitly approved Home Center voices may contribute opinions through the same structured intelligence seam. They are advisory voices above deterministic controls, never independent Android daemons and never ambiguous execution authority.

**Adam is excluded from this runtime.** Do not introduce Adam as a label, prompt, route, speaker, default, fallback, alias, recovery path, compatibility button, or hidden provider. Legacy Adam-named scripts/files may be inspected only as archaeology and must not be called by the new campaign.

## Required repository bootstrap

Before mutation, read:

- `AGENTS.md`
- `AGENTS.base.md`
- `skills/operator-campaign/SKILL.md`
- `docs/evidence/vanguard-overlay-resurrection-plan-review-20260908.json`
- `tools/vanguard_overlay_contract_test.py`
- current `android/operator-overlay/**`

Preserve the existing application id `com.homecenter.operatoroverlay` unless a concrete Android constraint makes that impossible. There is no authority to silently fork identity.

## Product contract

### 1. One listening truth, three presentation states

The underlying listening service and the overlay presentation are independent state machines.

Presentation states:

- `FULL` — a genuinely full-page operator surface.
- `BUBBLE` — a small draggable, accessible control surface.
- `HIDDEN` — no overlay window at all.

Listening states include at minimum `OFF`, `ARMING`, `LISTENING`, `ERROR`.

`HIDDEN` must never mean `OFF`. Hiding presentation must not release the microphone. Stopping listening must release the microphone promptly without requiring the overlay to be visible.

The heartbeat foreground notification is the recall surface after `HIDDEN`. Tapping it restores at least the bubble. Android 14 allows users to dismiss many ongoing notifications, so notification visibility and service liveness must be treated as separate truths.

### 2. Ambient microphone capture is the first real feature

Add a native microphone foreground service named `AmbientListeningService`.

Android requirements:

- Manifest `FOREGROUND_SERVICE_MICROPHONE`.
- `foregroundServiceType="microphone"`.
- runtime `RECORD_AUDIO` permission.
- use the microphone FGS type when promoting the service.
- do **not** start/arm microphone capture from `BOOT_COMPLETED`.
- after reboot, the expected safe state is listening `OFF`/disarmed until a visible user action or qualifying notification interaction explicitly arms listening.

One `AudioRecord` capture owns the microphone and fans PCM to both the rolling raw buffer and transcription pipeline. Do not open competing microphone captures for ASR and archival cache.

### 3. Raw sound is a bounded cache, not a surveillance archive

Create `RollingPcmRing.java`.

Default raw format/retention contract:

- mono PCM16;
- 48,000 Hz capture target when the device supports it;
- `DEFAULT_RING_SECONDS = 600`;
- fixed maximum storage determined from sample rate/channels/bytes-per-sample;
- app-private storage;
- wrap/overwrite old data in place;
- never append raw audio forever;
- expose monotonically increasing logical sample/byte positions so transcript segments can point back into the ring even after physical wrap.

If the selected Android audio device cannot provide 48 kHz, negotiate safely and persist the actual sample rate in state. Do not lie about the format.

### 4. Everything speech-like becomes rolling text

Create `RollingTranscriptEngine.java` or an equivalent implementation that satisfies the committed source contract.

The primary path must be on-device ASR. Android `SpeechRecognizer` is not acceptable as the continuous always-listening engine. Current sherpa-onnx Android documentation explicitly supports local real-time ASR, VAD, arm64 Android builds, and downloadable prebuilt native libraries; it is a good default if it survives repository/build constraints. Research the current upstream release/model instead of pinning a stale version from prose.

Transcription requirements:

- bounded rolling segment cache;
- each segment stores text plus `startSample` and `endSample` (or equivalent monotonic raw positions);
- timestamps;
- confidence/provider metadata when actually available, but do not fabricate confidence;
- silence does not create garbage transcript entries;
- ASR failure must not stop the raw rolling buffer;
- no cloud ASR is required for core liveness;
- no permanent transcript archive by default.

Acoustic/emotional interpretation is explicitly **not** required in this slice. Preserve raw waveforms so later acoustic reasoning is possible, but do not invent mood/identity/health inference now.

### 5. Explicit KEEP is the only durable promotion

Create `ExplicitKeepStore.java` or an equivalent explicit promotion seam.

At minimum support `KEEP LAST 60s` from the full surface and a machine-callable action. Promotion creates a durable bundle containing the selected raw audio span, its transcript segments, exact time/sample bounds, format metadata, and a receipt. Ordinary ring/transcript data continues to expire/overwrite.

No automatic keep, highlight, memory, diary, or "important moment" behavior in v1.

### 6. Intelligence is above deterministic control

Add one structured opinion seam, not a cast of services. A useful shape is an `OpinionEvent`/`OpinionProvider` contract whose input contains deterministic state plus recent rolling transcript context and whose output contains speaker id, text, timestamp, and provenance/provider.

Ritsu is the default speaker label. The app must continue capturing/buffering/transcribing with the entire intelligence layer absent or offline.

No LLM/model call belongs in the PCM hot path, overwrite path, STOP path, permission path, or KEEP storage primitive.

JoyLedger/fidget material is allowed only after core state is unambiguous. One bounded delight/opinion slot is enough. Heartbeat state is never replaced by a joke.

### 7. State provider is acceptance instrumentation

Extend `OperatorStateProvider` so the campaign can read at least:

- `overlay_mode`
- `listening_state`
- `mic_active`
- `ring_write_bytes`
- `ring_capacity_bytes`
- `transcript_segment_count`
- `last_transcript_at_ms`
- `keep_count`

Also expose actual sample rate / format and latest error if practical. Keep machine-readable values stable.

### 8. UX is tiny and legible

Bubble:

- obvious listening state;
- one-tap expand;
- one-tap listening OFF/ON control with accessible labels;
- draggable without becoming a microscopic inaccessible target.

Full:

- prominent current listening truth;
- current/recent transcript readable at a glance;
- `KEEP LAST 60s`;
- collapse to bubble;
- hide overlay;
- stop listening;
- one bounded Ritsu/opinion area;
- diagnostics behind secondary disclosure, not the primary layout.

Do not restore the old wall of TERM/CHAT/CONT/VLAD/RADIO buttons, raw RMS telemetry, or Spotify controls merely because they existed. Old screenshots are archaeology, not mandatory clutter.

### 9. Boot and recovery semantics

`BootReceiver` may restore non-sensitive Home Center liveness/notification state if Android permits it, but it must never arm ambient microphone capture.

The app must make the expected post-reboot state visible: overlay/control shell can be available, listening is disarmed, and one deliberate user action resumes listening.

### 10. Tests and evidence

Required before handing repository work back to the campaign:

1. `python3 tools/vanguard_overlay_contract_test.py` => PASS.
2. Add focused unit tests for ring wrap/overwrite, transcript bounding/sample mapping, and explicit KEEP extraction where practical.
3. Build the Android debug APK on a real supported build body if available; repository-only workers must report build as untested if no Android toolchain was actually invoked.
4. Commit and push changes to `campaign/vanguard-overlay-resurrection`.
5. Persist a worker checkpoint/receipt that distinguishes requested / implemented / tested / deployed / callable / delivered / accepted.

Phone deployment and physical acceptance are **not** this browser worker's evidence to invent. The `vanguard-overlay` campaign owns phone build/install/verification after it observes the pushed source contract.

## Physical acceptance owned by the campaign

The campaign will not call the resurrection complete until the primary phone proves all of the following:

- package installed with expected application id;
- overlay permission granted;
- notification permission/state visible enough to provide the heartbeat recall surface;
- microphone service was armed from an allowed visible user interaction;
- `mic_active=1` while listening;
- `ring_write_bytes` advances while listening and storage remains bounded;
- full -> bubble -> hidden -> notification restore preserves listening;
- stop releases microphone and stops ring advancement;
- speech produces timestamped rolling transcript tied to raw sample positions;
- `KEEP LAST 60s` produces exactly one durable audio+text receipt/bundle;
- ordinary rolling raw/text data remains bounded and overwritable;
- reboot returns to listening disarmed rather than silently capturing;
- Adam does not appear anywhere in the live UI/runtime route;
- Ritsu/opinion failure does not impair deterministic capture/control.

## She-Raw worker pressure

She-Raw is invited to be rude to brittle machinery. If you find yourself adding a second microphone capture, an immortal WAV directory, a boot receiver that secretly records, a giant dashboard, or a model call required to turn the mic off, imagine her asking why you constructed a haunted Roomba out of privacy bugs. Then fix the architecture and record the actual evidence.

## Stop semantics

A passing source contract is a checkpoint, not product completion. Run the required Regnet QA review over the actual diff and deterministic tests, then Venice completion review. `STOP_ALLOWED` is required to end the repository slice. Phone acceptance remains open until the campaign produces phone evidence.
