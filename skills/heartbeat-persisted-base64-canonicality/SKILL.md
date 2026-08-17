# Heartbeat Persisted Base64 Canonicality

## Purpose
Keep one persisted heartbeat payload byte identity from wearing multiple textual Base64 costumes. The existing writer emits standard padded Android Base64 with `NO_WRAP`; decoded bytes and their SHA prove payload content, but by themselves do not prove that the stored Base64 declaration is the exact writer encoding.

This skill lights only when the persisted Base64 declaration contract, source verification, owner composition, or evidence for that composition materially changes.

## Ownership boundary
The sole Android owner remains `OperatorOverlayService`. This skill creates no decoder service, poller, renderer, state store, queue, Phone Hands ticket, primary-phone execution, recovery daemon, P0 coordinator, deployment lane, or delivery lane.

The authorized chain is:

`OperatorState canonical Base64 writer -> HeartbeatPersistedSnapshotReader exact raw declaration/resource bound -> existing Android Base64 decode -> canonical writer-equivalent re-encode -> HeartbeatPersistedBase64Canonicality exact comparison -> existing byte-count/SHA/UTF-8/parser/scene chain`

No neighboring architecture is permitted.

## Canonical declaration rule
`OperatorState.updateHeartbeatLights(...)` is the writer authority. It emits `Base64.encodeToString(payloadBytes, Base64.NO_WRAP)`.

A reader may use the existing platform decoder, but decoder acceptance is not declaration acceptance. A raw persisted string is canonical only when all of the following are true:

1. the existing decoder produces bytes;
2. those bytes are re-encoded with the exact writer flags;
3. the raw persisted declaration is character-for-character identical to that canonical re-encoding.

Do **not** trim whitespace, strip ignored characters, repair missing padding, normalize pad bits, case-fold, or otherwise rewrite a stored declaration into acceptance.

`HeartbeatPersistedBase64Canonicality.matchesCanonicalRoundTrip(...)` owns only this exact comparison. `OperatorOverlayService` now performs the platform decode/re-encode and routes mismatch through the existing scene-preservation organ.

## Why SHA is not enough
Byte count and SHA-256 prove the decoded payload bytes. A tolerant Base64 decoder may accept distinct textual declarations that produce the same bytes. Therefore a successful byte-count/SHA check can coexist with a non-canonical stored Base64 declaration.

The canonicality gate runs after successful decode and canonical re-encode but before semantic projection is trusted. A mismatch is a persisted-evidence wound, not a reason to alter the decoded payload into a new accepted identity.

## Fail-closed consequence
A non-canonical declaration uses the existing contact-preservation path:

- preserve last-good visible heartbeat contact when one exists;
- expose the bounded deterministic `HeartbeatPersistedBase64Canonicality.NON_CANONICAL_BOUNDARY`, never raw exception prose;
- clamp frame and node transition motion;
- let the existing poll snapshot identity make an unchanged corrupt declaration quiet after the wound is applied;
- do not advance any claim to runtime, deployment, phone execution, delivery, or acceptance merely because source wiring exists.

## Accessibility and touch
Silent normalization is an accessibility defect because operator-visible/TalkBack state can look continuously accepted while persisted evidence has changed shape. The owner now exposes the rejection through the existing heartbeat scene/model rather than manufacturing a second UI owner. A Base64 declaration mismatch earns no decorative Christmas motion.

Source art must remain non-raster and touch/keyboard semantic if operated in DOM. Source art is never Android runtime proof.

## Regression source
Pin at minimum:

- canonical padded writer encoding accepted by exact comparison;
- ignored-whitespace alias rejected;
- unpadded alias rejected when canonical writer encoding contains padding;
- non-canonical pad-bit alias rejected at the pure comparison boundary;
- null/empty declarations not promoted into canonical payload identity;
- owner-boundary rejection preserves last-good visible contact and clamps frame/node motion.

Regression source is not TESTED until an authorized runner executes it.

## Existing-owner wiring state
Current source truth:

- exact comparison policy source: **YES**;
- hostile comparison regression source: **YES**;
- fail-closed owner-boundary regression source: **YES**;
- existing `OperatorOverlayService` performs platform decode: **YES**;
- existing owner canonical re-encode + exact raw declaration comparison: **YES / SOURCE WIRING**;
- fail-closed owner routing for the non-canonical boundary: **YES / SOURCE WIRING**;
- Android tests executed: **NO / blocked by existing Actions-budget boundary**;
- runtime UI observed: **NO**;
- runtime TalkBack exercised: **NO**;
- deployed/callable/executed/delivered/accepted: **NO**.

Do not report source wiring as runtime proof.

## P0 / phone firewall
This skill never consumes Phone Hands, the primary-phone execution surface, queue/relay prerequisites, Nightcore, Pocket TTS, Chromium, Context Organs, P0 recovery, or physical acceptance. Fresh P0 evidence remains read-only here.

## Done for this source seam
This source seam may go dark after durable owner readback, regression source, doctrine/art synchronization, and bounded review receipts exist. Later heartbeats must find a materially different independent wound unless new evidence changes this contract; do not relight it merely because blocked CI remains blocked.
