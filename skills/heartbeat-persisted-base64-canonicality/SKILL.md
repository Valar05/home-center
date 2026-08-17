# Heartbeat Persisted Base64 Canonicality

## Purpose
Keep one persisted heartbeat payload byte identity from wearing multiple textual Base64 costumes. The existing writer emits standard padded Android Base64 with `NO_WRAP`; the existing overlay owner decodes the stored declaration before byte-count/SHA verification. Decoded bytes and their SHA prove payload content, but by themselves do not prove that the stored Base64 declaration is the exact writer encoding.

This skill lights only when the persisted Base64 declaration contract, its source verification, its owner composition, or evidence for that composition materially changes.

## Ownership boundary
The sole Android owner remains `OperatorOverlayService`. This skill creates no decoder service, poller, renderer, state store, queue, Phone Hands ticket, primary-phone execution, recovery daemon, P0 coordinator, deployment lane, or delivery lane.

The authorized chain is:

`OperatorState canonical Base64 writer -> HeartbeatPersistedSnapshotReader exact raw declaration -> existing Android Base64 decode -> canonical writer-equivalent re-encode -> HeartbeatPersistedBase64Canonicality exact comparison -> existing byte-count/SHA/UTF-8/parser/scene chain`

No neighboring architecture is permitted.

## Canonical declaration rule
`OperatorState.updateHeartbeatLights(...)` is the writer authority. It emits `Base64.encodeToString(payloadBytes, Base64.NO_WRAP)`.

A reader may use the existing platform decoder, but decoder acceptance is not declaration acceptance. A raw persisted string is canonical only when all of the following are true:

1. the existing decoder produces bytes;
2. those bytes are re-encoded with the exact writer flags;
3. the raw persisted declaration is character-for-character identical to that canonical re-encoding.

Do **not** trim whitespace, strip ignored characters, repair missing padding, normalize pad bits, case-fold, or otherwise rewrite a stored declaration into acceptance.

`HeartbeatPersistedBase64Canonicality.matchesCanonicalRoundTrip(...)` deliberately owns only this exact comparison. The existing owner remains responsible for platform decode/re-encode and for routing rejection through the existing scene-preservation organ.

## Why SHA is not enough
Byte count and SHA-256 prove the decoded payload bytes. A tolerant Base64 decoder may accept distinct textual declarations that produce the same bytes. Therefore a successful byte-count/SHA check can coexist with a non-canonical stored Base64 declaration.

The canonicality gate must run after successful decode and canonical re-encode but before semantic projection is trusted. A mismatch is a persisted-evidence wound, not a reason to alter the decoded payload into a new accepted identity.

## Fail-closed consequence
A non-canonical declaration must use the existing contact-preservation path:

- preserve last-good visible heartbeat contact when one exists;
- expose a bounded deterministic boundary, never raw exception prose;
- clamp frame and node transition motion;
- do not rebuild/speak/twitch repeatedly for the same unchanged wound once owner dedupe is wired;
- do not advance any claim to runtime, deployment, phone execution, delivery, or acceptance merely because source policy exists.

The pure boundary is `HeartbeatPersistedBase64Canonicality.NON_CANONICAL_BOUNDARY`.

## Accessibility and touch
Silent normalization is an accessibility defect because operator-visible/TalkBack state can look continuously accepted while persisted evidence has changed shape. The repair must make the wound semantically available through the existing heartbeat scene/model without manufacturing a second UI owner. A Base64 declaration mismatch earns no decorative Christmas motion.

The corresponding source art must remain non-raster and touch/keyboard semantic if operated in DOM. Source art is never Android runtime proof.

## Regression source
At minimum pin:

- canonical padded writer encoding accepted by exact comparison;
- ignored-whitespace alias rejected;
- unpadded alias rejected when canonical writer encoding contains padding;
- non-canonical pad-bit alias rejected even when a permissive decoder can map it to the same bytes;
- null/empty declarations not promoted into canonical payload identity.

Regression source is not TESTED until an authorized runner executes it.

## Existing-owner wiring state
Current source truth at creation:

- exact comparison policy source: **YES**;
- hostile regression source: **YES**;
- existing `OperatorOverlayService` performs platform decode: **YES**;
- existing owner canonical re-encode + exact raw declaration comparison: **NO**;
- fail-closed owner routing for this new boundary: **NO**;
- Android tests executed: **NO / blocked by existing Actions-budget boundary**;
- runtime UI observed: **NO**;
- runtime TalkBack exercised: **NO**;
- deployed/callable/executed/delivered/accepted: **NO**.

Do not report the policy as owner wiring.

## P0 / phone firewall
This skill never consumes Phone Hands, the primary-phone execution surface, queue/relay prerequisites, Nightcore, Pocket TTS, Chromium, Context Organs, P0 recovery, or physical acceptance. Fresh P0 evidence remains read-only here.

## Done for one source pulse
This skill may yield after durable policy, regression source, doctrine/art synchronization, and bounded review receipts exist with exact owner/runtime boundaries. The next heartbeat must either wire the existing owner through an authorized repository lane or find a materially different independent wound; do not keep relighting this skill because blocked CI remains blocked.
