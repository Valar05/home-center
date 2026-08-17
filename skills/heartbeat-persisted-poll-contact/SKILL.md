# Heartbeat Persisted Poll Contact

## Purpose
Keep the existing Operator Overlay's fast persisted-heartbeat poll loop honest and cheap without creating another owner. Distinguish **waiting for first contact** from **storage contact disappeared after last-good contact**, avoid repeating decode/hash/parse/scene work when projection inputs did not change, and keep one poll observation internally coherent.

## Ownership boundary
The sole poll owner remains the existing `OperatorOverlayService`. This skill owns no SharedPreferences writer, renderer, service lifecycle, transport, queue, Phone Hands ticket, primary-phone execution, recovery daemon, P0 coordinator, deployment, delivery, or acceptance lane.

The authorized composition chain is:

`OperatorState persisted heartbeat transaction -> one persisted observation -> HeartbeatPersistedPollPolicy -> existing Base64/integrity/parser/scene pipeline -> HeartbeatOverlayRefreshPlan -> existing OperatorOverlayService`

Do not create a neighboring polling service, cache controller, overlay owner, or recovery path.

## Four poll decisions
`HeartbeatPersistedPollPolicy` exposes four decisions:

- `WAITING`: the canonical persisted store is fully absent and no visible last-good heartbeat exists yet. This is not a fault and must not manufacture one.
- `PROJECT`: an input that can change storage verification or semantic projection changed. Run the existing Base64/integrity/parser/scene chain.
- `PRESERVE_MISSING_CONTACT`: the store became fully absent after visible last-good contact existed. Preserve that contact through the existing fail-closed scene organ and expose `MISSING_AFTER_CONTACT_BOUNDARY`; do not silently leave the old heartbeat looking current.
- `SKIP_UNCHANGED`: the last processed projection inputs are equivalent. Do not decode, hash, parse, rebuild, refresh, announce, or animate merely because the 200 ms poll ran again.

## Projection identity
Persisted projection equivalence includes exact stored Base64 payload text, declared byte count, declared SHA-256 after the same trim normalization already used by persisted projection, and the **validity class** of the update timestamp (`updatedMs > 0` versus missing).

The magnitude of a positive wall-clock timestamp is observation metadata, not semantic identity. A new positive timestamp with identical payload/byte/SHA inputs does not earn another semantic projection. If the timestamp changes from missing/non-positive to positive, projection must run because storage acceptance can change.

Do not use timestamp ordering as a replay sequence. Do not weaken byte/SHA verification to make dedupe easier.

## One poll = one storage observation
The heartbeat writer commits payload, byte count, SHA, and update metadata in one SharedPreferences editor transaction. Reading those keys through four independent getter calls can still straddle two committed maps if a writer lands between getters, manufacturing a transient byte/SHA mismatch that looks like a real storage-integrity wound.

`HeartbeatPersistedSnapshotReader` therefore exists as a source helper that extracts all four heartbeat fields from one `SharedPreferences.getAll()` observation. It owns no poll loop or cache. `fromValues(...)` is pure regression-testable extraction.

**Current capability truth:** the reader source exists and has regression source, but `OperatorOverlayService` does **not yet consume the one-map reader**. Until that owner wiring lands, source classification/dedupe is wired but coherent single-map observation remains an explicit source gap. Do not call that gap runtime-tested merely because the helper exists.

## Contact preservation
A fully absent persisted store has history-sensitive meaning:

- before first accepted/preserved visible contact: `WAITING`;
- after visible last-good contact: one explicit storage-contact wound, then `SKIP_UNCHANGED` while the same absence persists.

Use `HeartbeatPersistedPollPolicy.hasVisibleLastGoodContact(frame)` rather than inventing a node-count predicate. The source predicate is **non-empty accepted/preserved `visiblePulseId`**. A valid complete pulse can contain zero material lights and still be the last visible heartbeat contact; `frame.nodes.isEmpty()` therefore does not mean "no contact."

The wound must reuse `HeartbeatSceneGraph.preserveRejectedRefresh(...)` so last-good controls remain visible, discarded attempted state stays absent, and frame/node one-shot motion remains clamped. A repeated identical absence must not repeatedly rebuild, speak, or twitch.

## Accessibility and touch
Silent stale contact is an accessibility defect: a TalkBack user must not hear or touch an old heartbeat as though storage contact were still current. The missing-after-contact state therefore uses the same bounded interruption semantics as other fail-closed wounds.

Poll dedupe is also accessibility protection. Re-running projection on every fast poll must not recreate native controls, churn focus, re-announce summaries, or blink Christmas lights. Likewise, a torn multi-getter storage read must not generate a false wound if one coherent preference-map observation can avoid it.

## Regression source
At minimum cover canonical empty waiting, accepted zero-material contact, missing-after-contact once, repeated missing skip, project→skip→wound→skip→recovery lifecycle, failed-project retry when the owner retains the prior processed snapshot, positive-timestamp-only skip, timestamp validity-class project, payload/byte/SHA project, inconsistent empty metadata project, null observation semantics, and one-map field extraction/default behavior.

A regression file is source only until an authorized runner executes it.

## Existing-owner wiring contract
`OperatorOverlayService` now consumes `HeartbeatPersistedPollPolicy` source: it classifies one current snapshot against the last processed snapshot and current scene, skips unchanged projection, preserves missing-after-contact through the existing scene organ, and retains the current snapshot only after the chosen decision is applied. Expected invalid persisted data may be retained after its preserved wound is applied so identical corruption does not burn the 200 ms loop forever; unexpected internal aborts must leave the older processed snapshot so the next poll retries.

The remaining source seam is narrower: replace the four independent heartbeat preference getters with the existing one-map `HeartbeatPersistedSnapshotReader.read(...)` helper. This is still composition inside the existing owner, not permission to create another polling owner.

Owner wiring must not consume Phone Hands, the primary-phone execution surface, queue/relay prerequisites, or P0 recovery owners.

## Evidence membrane
Keep these states separate:

`requested -> policy source -> owner classification source wired -> coherent one-map reader source -> owner coherent-reader source wired -> regression source -> tested -> runtime observed -> TalkBack exercised -> deployed -> callable -> executed -> delivered -> accepted`

GitHub readback proves durable source only. None of these source artifacts prove Android tests ran or that any phone changed.

## Done for one source pulse
This skill may light only when persisted-poll classification, missing-contact truth, projection dedupe, coherent storage observation, owner composition, regression source, or runtime evidence materially changes. Another unchanged poll or another unchanged CI failure stays dark.
