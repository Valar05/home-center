# VANGUARD // OVERLAY RESURRECTION — worker commission v2

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
- `docs/evidence/vanguard-overlay-single-service-architecture-review-20260908.json`
- `tools/vanguard_overlay_contract_test.py`
- current `android/operator-overlay/**`

The single-service architecture addendum supersedes any earlier suggestion to add `AmbientListeningService`.

Preserve the existing application id `com.homecenter.operatoroverlay`. Preserve and evolve the existing `OperatorOverlayService`; there is no authority to silently fork identity or create a second ambient foreground-service daemon.

## Product contract

### 1. One service, one heartbeat, two independent state machines

`OperatorOverlayService` is the one native foreground service for this product. Do **not** create `AmbientListeningService`, another foreground notification, or another long-running Android daemon for microphone capture.

Presentation and listening are independent state machines.

Presentation states:

- `FULL` — a genuinely full-page operator surface.
- `BUBBLE` — a small draggable, accessible control surface.
- `HIDDEN` — no overlay window at all.

Listening states include at minimum:

- `OFF`
- `ARMING`
- `LISTENING`
- `ERROR`

`HIDDEN` must never imply `OFF`. Hiding presentation must not release the microphone. `STOP LISTENING` must release the microphone immediately without requiring the overlay to remain visible.

The existing service owns exactly one heartbeat notification. It is the recall surface after `HIDDEN`. Tapping it restores at least the bubble. Notification visibility and service liveness are separate truths; do not treat `setOngoing(true)` as proof the user can still see it.

### 2. Upgrade the existing service into a microphone foreground service only after visible ARM

Manifest requirements:

- keep `FOREGROUND_SERVICE`;
- keep `FOREGROUND_SERVICE_SPECIAL_USE`;
- add `FOREGROUND_SERVICE_MICROPHONE`;
- keep/request runtime `RECORD_AUDIO`;
- declare `OperatorOverlayService` with `android:foregroundServiceType="specialUse|microphone"` and `android:exported="false"`;
- keep the existing special-use subtype declaration with a truthful description.

Startup behavior:

- ordinary service startup promotes `OperatorOverlayService` as `FOREGROUND_SERVICE_TYPE_SPECIAL_USE` only;
- listening is `OFF` by default;
- creating/restoring the overlay and heartbeat does not acquire the microphone.

Visible ARM behavior:

1. ARM originates from a visible app/overlay interaction or another Android-qualified user interaction.
2. Verify `RECORD_AUDIO` is granted while the app is eligible for the while-in-use permission.
3. Call `ServiceCompat.startForeground()` again on the **same service** with `SPECIAL_USE | MICROPHONE`.
4. Only after that promotion succeeds, create the one `AudioRecord` capture.
5. Fan that one PCM stream into both the rolling raw buffer and transcription pipeline.

Android explicitly supports adding more declared foreground-service types to an already-running service. Do not use that as permission to create a second service.

STOP behavior:

- stop/release `AudioRecord` immediately;
- stop VAD/ASR consumption;
- clear unkept rolling raw audio and rolling transcript state;
- update `mic_active=0`, listening `OFF`, and heartbeat/UI promptly;
- keep `OperatorOverlayService` alive as the special-use control/heartbeat shell;
- Android does not document a symmetric operation for subtracting one already-added foreground-service type while keeping the same foreground instance alive. Do not fake such an API. The service may retain the previously-added microphone **type classification** until its next natural restart. Actual microphone truth comes from `AudioRecord` ownership / `mic_active`, never from the foreground type mask.

### 3. Raw sound is a bounded transient cache, not a surveillance archive

Create `RollingPcmRing.java`.

Default raw contract:

- mono PCM16;
- 48,000 Hz capture target when the device supports it;
- `DEFAULT_RING_SECONDS = 600`;
- fixed maximum storage determined from actual sample rate/channels/bytes-per-sample;
- app-private storage;
- physical write position wraps and overwrites old bytes in place;
- expose monotonically increasing logical sample/byte positions so text segments can map back into the ring even across physical wrap;
- never append raw audio forever.

If 48 kHz is unsupported, negotiate safely and persist/report the actual sample rate. Do not lie about the format.

Transient lifecycle law:

- a fresh listening session starts with an empty unkept ring/transcript;
- service/process restart and reboot purge stale **unkept** transient cache before a new session;
- explicit STOP purges unkept rolling raw/text after releasing the microphone;
- only explicit KEEP produces durable storage.

A fixed-size ring is a cache ceiling, not an excuse to turn stale recordings into a hidden archive.

### 4. Everything speech-like becomes bounded rolling text

Create `RollingTranscriptEngine.java` or an equivalent implementation that satisfies the committed source contract.

The primary path must be **on-device ASR**. Android `SpeechRecognizer` is not acceptable as the continuous always-listening engine. Current sherpa-onnx Android tooling is a reasonable default if it survives current upstream research, ABI/build constraints, and actual phone build tests. Research current upstream release/model rather than pinning a stale version copied from prose.

Transcription requirements:

- bounded rolling segment cache;
- each segment stores text plus `startSample` and `endSample` (or equivalent monotonic raw positions);
- timestamps;
- confidence/provider metadata only when actually supplied by the engine;
- silence does not create garbage transcript entries;
- ASR failure does **not** stop the raw rolling buffer;
- no cloud ASR is required for core liveness;
- no permanent transcript archive by default;
- clear unkept rolling transcript on STOP/session reset in lockstep with raw cache lifecycle.

Acoustic/emotional interpretation is explicitly **not** required in this slice. Preserve waveforms long enough for future acoustic reasoning, but do not invent mood, identity, health, diagnosis, stress, or personality inference now.

### 5. Explicit KEEP is the only durable promotion

Create `ExplicitKeepStore.java` or an equivalent explicit promotion seam.

At minimum support `KEEP LAST 60s` from the full surface and a machine-callable action. Promotion creates exactly one durable bundle containing:

- selected raw audio span;
- overlapping transcript segments;
- exact wall-clock and monotonic sample bounds;
- actual PCM format/sample-rate metadata;
- creation reason/action (`KEEP`);
- receipt / bundle id.

Ordinary ring/transcript state keeps expiring/overwriting and is cleared on STOP/session reset. No automatic keep, highlight, memory, diary, sentiment-triggered save, or “important moment” behavior in v1.

### 6. Actual intelligence: one OpinionChannel, Ritsu by default

Create one structured intelligence seam, for example `OpinionChannel.java`, not a cast of services.

Its stable input should contain deterministic phone state plus a bounded recent transcript window. Its output should contain at least:

- speaker id;
- opinion text;
- timestamp;
- provenance/provider;
- optional source/event id.

The default speaker label is **Ritsu**. Other approved voices can enter through the same seam later.

The full surface has one bounded opinion/delight area. It may be funny, critical, passive-aggressive, or useful, but it can never replace the heartbeat/listening truth.

The app must continue capturing, buffering, transcribing, stopping, clearing, and KEEP-promoting if the intelligence layer is absent/offline/broken. No model/network call belongs in:

- `AudioRecord` read loop;
- ring overwrite path;
- STOP/release path;
- permission path;
- KEEP storage primitive.

### 7. State provider is physical acceptance instrumentation

Extend `OperatorStateProvider` so the campaign can machine-read at least:

- `overlay_mode`
- `listening_state`
- `mic_active`
- `ring_write_bytes`
- `ring_capacity_bytes`
- `transcript_segment_count`
- `last_transcript_at_ms`
- `keep_count`
- `actual_sample_rate_hz`
- `latest_error`
- `opinion_speaker`
- `opinion_provider_state`

`mic_active` is derived from actual microphone capture ownership/activity, never from foreground-service type declarations.

Keep field names stable and values compact enough for `content query` receipts.

### 8. UX: recover the good bones, amputate the dashboard

Bubble:

- obvious listening state;
- one-tap FULL;
- one-tap listening ON/OFF with accessible labels;
- draggable;
- touch target remains accessible, not microscopic.

Full:

- prominent current listening truth;
- readable recent transcript;
- `KEEP LAST 60s`;
- collapse to BUBBLE;
- HIDE overlay;
- STOP LISTENING;
- one bounded Ritsu/opinion area;
- secondary diagnostics disclosure if needed.

Delete/omit legacy clutter from the recovered primary experience unless independently justified by the commission:

- TERM / CHAT / CONT / VLAD / RADIO wall;
- Adam input/labels/modes;
- raw RMS/ZCR/transient telemetry;
- Spotify controls;
- 200 ms UI polling loop where event-driven/state-change updates suffice;
- “hide overlay and disable control” coupling.

Old screenshots/source are archaeology and interaction evidence, not a command to restore every button.

### 9. Boot and recovery semantics

`BootReceiver` may restore the non-sensitive special-use Home Center control shell only if the current Android target permits that exact launch. It must never:

- call ARM;
- add the microphone foreground-service type;
- acquire `AudioRecord`;
- restore a stale `LISTENING` state;
- preserve unkept raw/transcript cache across reboot.

After reboot the expected truth is listening `OFF`/disarmed. One deliberate visible user action resumes listening.

If the platform rejects boot-starting the special-use service, degrade honestly to a disarmed app/notification recall path; do not invent a microphone boot workaround.

### 10. Tests and worker evidence

Required before handing repository work back to the phone campaign:

1. `python3 tools/vanguard_overlay_contract_test.py` => PASS.
2. Add focused unit tests for:
   - ring wrap/overwrite and logical positions;
   - transient clear/reset;
   - transcript bounding and sample mapping;
   - explicit KEEP extraction around physical ring wrap;
   - STOP releasing/clearing state primitives where testable;
   - OpinionChannel absence not affecting deterministic state.
3. Run the Android debug unit-test/build lane on a real supported build body if available. Repository-only workers must report build as untested if no Android toolchain was actually invoked.
4. Commit and push changes to `campaign/vanguard-overlay-resurrection`.
5. Persist a worker checkpoint/receipt separating requested / implemented / tested / deployed / callable / delivered / accepted.
6. Run Regnet QA over the actual diff/tests and then Venice completion review. Do not self-promote because the source contract is green.

Phone deployment and physical acceptance are **not** this browser worker's evidence to invent. The durable `vanguard-overlay` campaign owns build/install/live verification on the primary phone after it observes the pushed source.

## Physical acceptance owned by the campaign

The campaign will not call the resurrection complete until the primary phone proves all of the following:

- package installed with application id `com.homecenter.operatoroverlay`;
- overlay permission granted;
- one heartbeat notification/notification channel is the recall surface;
- listening begins only after an allowed visible ARM interaction;
- `mic_active=1` while actual capture is running;
- `ring_write_bytes` advances while listening and physical storage remains bounded;
- FULL -> BUBBLE -> HIDDEN -> notification restore preserves listening;
- STOP releases microphone, stops ring advancement, clears unkept raw/text, and leaves control shell usable;
- real spoken words produce timestamped rolling transcript tied to raw sample positions;
- `KEEP LAST 60s` produces exactly one durable audio+text bundle/receipt;
- ordinary rolling raw/text wraps/clears without unbounded growth;
- process/service restart begins a fresh transient session without stale unkept raw/text;
- reboot returns to listening disarmed rather than silently capturing;
- Adam does not appear anywhere in live UI/runtime routes/fallbacks;
- Ritsu is the default opinion speaker when intelligence is available;
- intelligence-provider failure/offline state does not impair deterministic capture/control/STOP/KEEP;
- battery/thermal behavior is observed rather than guessed;
- Drew accepts the physical behavior.

## She-Raw worker pressure

She-Raw is invited to be rude to brittle machinery. If you find yourself adding a second microphone service, a second heartbeat notification, an immortal WAV directory, a boot receiver that secretly records, a model call required to turn the mic off, or a 37-button dashboard because the archaeology contained 37 buttons, imagine her asking why you constructed a haunted Roomba out of privacy bugs. Then repair the architecture and record the actual evidence.

## Stop semantics

A passing source contract is a checkpoint, not product completion. Regnet QA must pass the actual implementation/evidence, then Venice must grant the relevant stop directive. Phone acceptance remains open until the campaign produces the physical receipts above.
