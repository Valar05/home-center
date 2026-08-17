# Heartbeat Persisted Poll Contact

## Purpose
Keep the existing Operator Overlay's fast persisted-heartbeat poll loop honest and cheap without creating another owner. Distinguish **waiting for first contact** from **storage contact disappeared after last-good contact**, avoid repeating decode/hash/parse/scene work when projection inputs did not change, and keep one poll observation internally coherent.

## Ownership boundary
The sole poll owner remains the existing `OperatorOverlayService`. This skill owns no SharedPreferences writer, renderer, service lifecycle, transport, queue, Phone Hands ticket, primary-phone execution, recovery daemon, P0 coordinator, deployment, delivery, or acceptance lane.

The authorized composition chain is:

`OperatorState persisted heartbeat transaction -> HeartbeatPersistedSnapshotReader one-map observation -> HeartbeatPersistedPollPolicy -> existing Base64/integrity/parser/scene pipeline -> HeartbeatOverlayRefreshPlan -> existing OperatorOverlayService`

Do not create a neighboring polling service, cache controller, overlay owner, or recovery path.

## Four poll decisions
`HeartbeatPersistedPollPolicy` exposes four decisions:

- `WAITING`: the canonical persisted store is fully absent and no visible last-good heartbeat exists yet. This is not a fault and must not manufacture one.
- `PROJECT`: an input that can change storage verification or semantic projection changed. Run the existing Base64/integrity/parser/scene chain.
- `PRESERVE_MISSING_CONTACT`: the store became fully absent after visible last-good contact existed. Preserve that contact through the existing fail-closed scene organ and expose `MISSING_AFTER_CONTACT_BOUNDARY`; do not silently leave the old heartbeat looking current.
- `SKIP_UNCHANGED`: the last processed projection inputs are semantically identical. Do not decode, hash, parse, rebuild, refresh, announce, or animate merely because the 200 ms poll ran again.

## Projection identity
Persisted projection equivalence includes exact stored Base64 payload text, declared byte count, declared SHA-256 after the same trim normalization already used by persisted projection, and the **validity class** of the update timestamp (`updatedMs > 0` versus missing).

The magnitude of a positive wall-clock timestamp is observation metadata, not semantic identity. A new positive timestamp with identical payload/byte/SHA inputs does not earn another semantic projection. If the timestamp changes from missing/non-positive to positive, projection must run because storage acceptance can change.

Do not use timestamp ordering as a replay sequence. Do not weaken byte/SHA verification to make dedupe easier.

## One poll = one storage observation
The heartbeat writer commits payload, byte count, SHA, and update metadata in one SharedPreferences editor transaction. Reading those keys through four independent getter calls can still straddle two committed maps if a writer lands between getters, manufacturing a transient byte/SHA mismatch that looks like a real storage-integrity wound.

`HeartbeatPersistedSnapshotReader.read(...)` now supplies the existing owner with all four fields from one `SharedPreferences.getAll()` observation. `fromValues(...)` remains the pure regression-testable extraction seam. Missing keys keep canonical defaults; a present key with the wrong stored type is rejected rather than rewritten into fake absence.

**Current capability truth:** coherent one-map reader source **YES**; existing `OperatorOverlayService` coherent-reader source consumption **YES**; Android execution/runtime observation **NO**.

## Coherent-read failure
A coherent storage read may fail because SharedPreferences access aborts or because a present heartbeat key has an unexpected stored type. That is not `WAITING`, not `PRESERVE_MISSING_CONTACT`, and not permission to erase or advance processed identity.

The existing owner catches a bounded `RuntimeException` at the reader boundary, preserves the last-good frame through `HeartbeatSceneGraph.preserveRejectedRefresh(...)` using `STORAGE_READ_FAILURE_BOUNDARY`, and deliberately **does not advance `heartbeatProcessedPersistedSnapshot`**. The next 200 ms poll therefore retries the read. Repeated identical read wounds may recompute the fail-closed plan, but render/announcement identities must prevent repeated native rebuild, speech, or Christmas twitch.

Do not echo raw exception text into TalkBack/operator-facing prose. The exact exception remains implementation evidence, not display semantics.

## Contact preservation
A fully absent persisted store has history-sensitive meaning:

- before first accepted/preserved visible contact: `WAITING`;
- after visible last-good contact: one explicit storage-contact wound, then `SKIP_UNCHANGED` while the same absence persists.

Use `HeartbeatPersistedPollPolicy.hasVisibleLastGoodContact(frame)` rather than inventing a node-count predicate. The source predicate is **non-empty accepted/preserved `visiblePulseId`**. A valid complete pulse can contain zero material lights and still be the last visible heartbeat contact; `frame.nodes.isEmpty()` therefore does not mean "no contact."

The wound must reuse `HeartbeatSceneGraph.preserveRejectedRefresh(...)` so last-good controls remain visible, discarded attempted state stays absent, and frame/node one-shot motion remains clamped. A repeated identical absence must not repeatedly rebuild, speak, or twitch.

A coherent-read failure before first contact must not invent a visible pulse identity. Its interruption description may report that no complete heartbeat is available; that is different from claiming visible contact existed.

## Interruption chrome truth
Visible interruption chrome must be derived from the same accepted/preserved contact predicate as scene recovery. Do not let the Android owner re-derive `CONTACT HELD` from `refreshInterrupted` or control count alone.

`HeartbeatOverlayViewModel.Model.summaryVisibleLabel()` is the canonical compact label:

- pre-contact interrupted refresh -> `HEARTBEAT • REFRESH BLOCKED`;
- interrupted refresh with non-empty accepted/preserved `visiblePulseId` and zero controls -> `HEARTBEAT • CONTACT HELD`;
- interrupted refresh with visible controls -> count plus `CONTACT HELD`;
- non-interrupted zero-control model -> `HEARTBEAT • waiting`.

`interruptionDetailContentDescription()` applies the same truth to detail prose. Before contact it says the refresh was blocked before any heartbeat contact was accepted. With accepted/preserved contact it may say the last-good heartbeat contact is preserved. Never claim a held contact that the scene does not actually retain.

**Current capability truth:** model summary/detail truth source **YES**; existing `OperatorOverlayService.applyHeartbeatModelChrome(...)` consumes both helpers **YES**; Android/TalkBack runtime observation **NO**.

## Accessibility and touch
Silent stale contact is an accessibility defect: a TalkBack user must not hear or touch an old heartbeat as though storage contact were still current. The missing-after-contact and coherent-read-failure states therefore use bounded interruption semantics.

Poll dedupe is also accessibility protection. Re-running projection on every fast poll must not recreate native controls, churn focus, re-announce summaries, or blink Christmas lights. Likewise, a torn multi-getter storage read must not generate a false wound when one coherent preference-map observation can avoid it.

## Regression source
At minimum cover canonical empty waiting, accepted zero-material contact, missing-after-contact once, repeated missing skip, project→skip→wound→skip→recovery lifecycle, failed-project retry when the owner retains the prior processed snapshot, positive-timestamp-only skip, timestamp validity-class project, payload/byte/SHA project, inconsistent empty metadata project, null observation semantics, one-map extraction/defaults/type drift, coherent-read failure preserving last-good contact/no motion, read failure before first contact inventing no visible pulse, repeated read failure preserving equivalent contact, recovery remaining `PROJECT` when the failed read did not advance processed identity, and summary/detail chrome distinguishing pre-contact `REFRESH BLOCKED` from genuine last-good `CONTACT HELD` including zero-material accepted contact.

A regression file is source only until an authorized runner executes it.

## Existing-owner wiring contract
`OperatorOverlayService` consumes `HeartbeatPersistedSnapshotReader`, `HeartbeatPersistedPollPolicy`, and the model-owned summary/detail chrome source. It reads one current map snapshot, classifies that observation against the last processed snapshot and current scene, skips unchanged projection, preserves missing-after-contact through the existing scene organ, retains the current snapshot only after the chosen decision is applied, and renders interruption chrome from the accepted/preserved model instead of duplicating contact inference in Android view code.

Expected invalid persisted payload data may be retained after its preserved wound is applied so identical corruption does not burn the 200 ms loop forever. A **reader/storage failure is different**: no coherent current observation exists, so the owner preserves a bounded read wound and keeps the older processed snapshot; the next poll retries.

Owner wiring must not consume Phone Hands, the primary-phone execution surface, queue/relay prerequisites, or P0 recovery owners.

## Evidence membrane
Keep these states separate:

`requested -> policy source -> coherent reader source -> existing-owner coherent-reader source wired -> model chrome truth source -> existing-owner chrome source wired -> regression source -> tested -> runtime observed -> TalkBack exercised -> deployed -> callable -> executed -> delivered -> accepted`

GitHub readback proves durable source only. None of these source artifacts prove Android tests ran or that any phone changed.

## Done for one source pulse
This skill may light only when persisted-poll classification, missing-contact truth, projection dedupe, coherent storage observation, owner composition, interruption chrome truth, regression source, or runtime evidence materially changes. Another unchanged poll or another unchanged CI failure stays dark.
