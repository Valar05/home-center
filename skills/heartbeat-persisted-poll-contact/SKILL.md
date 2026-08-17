# Heartbeat Persisted Poll Contact

## Purpose
Keep the existing Operator Overlay's fast persisted-heartbeat poll loop honest and cheap without creating another owner. Distinguish **waiting for first contact** from **storage contact disappeared after last-good contact**, and avoid repeating decode/hash/parse/scene work when the inputs that can affect projection did not change.

## Ownership boundary
This skill is source policy only until the existing `OperatorOverlayService` consumes it. It owns no SharedPreferences writer, renderer, service lifecycle, transport, queue, Phone Hands ticket, primary-phone execution, recovery daemon, P0 coordinator, deployment, delivery, or acceptance lane.

The only authorized composition target is the existing chain:

`OperatorState persisted heartbeat fields -> HeartbeatPersistedPollPolicy -> existing Base64/integrity/parser/scene pipeline -> HeartbeatOverlayRefreshPlan -> existing OperatorOverlayService`

Do not create a neighboring polling service or cache controller.

## Four poll decisions
`HeartbeatPersistedPollPolicy` exposes four source decisions:

- `WAITING`: the canonical persisted store is fully absent and no visible last-good heartbeat exists yet. This is not a fault and must not manufacture one.
- `PROJECT`: an input that can change storage verification or semantic projection changed. Run the existing Base64/integrity/parser/scene chain.
- `PRESERVE_MISSING_CONTACT`: the store became fully absent after visible last-good contact existed. Preserve that contact through the existing fail-closed scene organ and expose `MISSING_AFTER_CONTACT_BOUNDARY`; do not silently leave the old heartbeat looking current.
- `SKIP_UNCHANGED`: the last processed projection inputs are equivalent. Do not decode, hash, parse, rebuild, refresh, announce, or animate merely because the 200 ms poll ran again.

## Projection identity
Persisted projection equivalence includes:

- exact stored Base64 payload text;
- declared byte count;
- declared SHA-256 after the same trim normalization already used by persisted projection;
- the **validity class** of the update timestamp (`updatedMs > 0` versus missing).

The magnitude of a positive wall-clock timestamp is observation metadata, not semantic identity. A new positive timestamp with identical payload/byte/SHA inputs does not earn another semantic projection. If the timestamp changes from missing/non-positive to positive, projection must run because storage acceptance can change.

Do not use timestamp ordering as a replay sequence. Do not weaken byte/SHA verification to make dedupe easier.

## Contact preservation
A fully absent persisted store has history-sensitive meaning:

- before first accepted/preserved visible contact: `WAITING`;
- after visible last-good contact: one explicit storage-contact wound, then `SKIP_UNCHANGED` while the same absence persists.

Use `HeartbeatPersistedPollPolicy.hasVisibleLastGoodContact(frame)` rather than inventing a node-count predicate. The source predicate is **non-empty accepted/preserved `visiblePulseId`**. A valid complete pulse can contain zero material lights and still be the last visible heartbeat contact; `frame.nodes.isEmpty()` therefore does not mean "no contact."

The wound must reuse `HeartbeatSceneGraph.preserveRejectedRefresh(...)` when owner wiring lands, so last-good controls remain visible, discarded attempted state stays absent, and frame/node one-shot motion remains clamped.

A repeated identical absence must not repeatedly rebuild, speak, or twitch.

## Accessibility and touch
Silent stale contact is an accessibility defect: a TalkBack user must not hear or touch an old heartbeat as though storage contact were still current. The missing-after-contact state therefore needs the same bounded interruption semantics as other fail-closed wounds.

Poll dedupe is also accessibility protection. Re-running projection on every fast poll must not be used as an excuse to recreate native controls, churn focus, re-announce summaries, or blink Christmas lights.

## Regression source
At minimum cover:

- canonical fully absent store + no visible contact -> `WAITING`;
- **accepted zero-material pulse still counts as visible last-good contact**;
- fully absent store after visible contact -> `PRESERVE_MISSING_CONTACT` once;
- repeated identical absence after that processed wound -> `SKIP_UNCHANGED`;
- identical payload/byte/SHA with a different positive timestamp -> `SKIP_UNCHANGED`;
- timestamp validity class change -> `PROJECT`;
- payload, byte count, or SHA change -> `PROJECT`;
- inconsistent empty payload with non-empty metadata -> `PROJECT`, never `WAITING`;
- null observation fails closed to missing contact only when last-good contact exists.

A regression file is source only until an authorized runner executes it.

## Existing-owner wiring contract
When wiring the existing service, retain the last **processed** snapshot only after the chosen decision has been applied. If an unexpected internal projection exception aborts work, keep the older processed snapshot so the next poll retries instead of falsely deduplicating failed work.

Owner wiring must pass the current `HeartbeatSceneGraph.Frame` into the scene-bound decision overload, not manufacture a weaker boolean from child count. For `PRESERVE_MISSING_CONTACT`, compose the existing preservation organ and then retain the empty processed snapshot; the next identical empty poll may become `SKIP_UNCHANGED`.

Owner wiring must not consume Phone Hands, the primary-phone execution surface, queue/relay prerequisites, or P0 recovery owners. It is ordinary source composition inside the existing overlay service.

## Evidence membrane
Keep these states separate:

`requested -> policy source -> regression source -> existing-owner source wired -> tested -> runtime observed -> TalkBack exercised -> deployed -> callable -> executed -> delivered -> accepted`

GitHub readback proves durable source only. This skill existing does not prove the 200 ms service poll consumes it, that Android tests ran, or that any phone changed.

## Done for one source pulse
This skill may light only when persisted-poll classification, missing-contact truth, projection dedupe, owner composition, regression source, or runtime evidence materially changes. Another unchanged poll or another unchanged CI failure stays dark.
