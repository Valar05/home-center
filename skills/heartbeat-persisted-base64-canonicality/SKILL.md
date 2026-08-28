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
3. both declarations fit the canonical persisted Base64 text ceiling before equality work;
4. the raw persisted declaration is character-for-character identical to that canonical re-encoding.

Do **not** trim whitespace, strip ignored characters, repair missing padding, normalize pad bits, case-fold, truncate, or otherwise rewrite a stored declaration into acceptance.

`HeartbeatPersistedBase64Canonicality.matchesCanonicalRoundTrip(...)` owns the exact comparison and now also reuses `HeartbeatPersistedPollPolicy.MAX_PAYLOAD_B64_CHARS` as its direct/package-call source-work throat before `String.equals(...)`. Safe composition already arrives bounded through persisted custody, but direct helper callers do not inherit that proof merely because the canonical owner is safe.

## Why SHA is not enough
Byte count and SHA-256 prove the decoded payload bytes. A tolerant Base64 decoder may accept distinct textual declarations that produce the same bytes. Therefore a successful byte-count/SHA check can coexist with a non-canonical stored Base64 declaration.

The canonicality gate runs after successful decode and canonical re-encode but before semantic projection is trusted. A mismatch is a persisted-evidence wound, not a reason to alter the decoded payload into a new accepted identity.

## Fail-closed consequence
A non-canonical or over-ceiling declaration uses the existing contact-preservation path:

- preserve last-good visible heartbeat contact when one exists;
- expose the bounded deterministic `HeartbeatPersistedBase64Canonicality.NON_CANONICAL_BOUNDARY`, never raw exception prose;
- clamp frame and node transition motion;
- let the existing poll snapshot identity make an unchanged corrupt declaration quiet after the wound is applied;
- do not advance any claim to runtime, deployment, phone execution, delivery, or acceptance merely because source wiring exists.

## Accessibility and touch
Silent normalization is an accessibility defect because operator-visible/TalkBack state can look continuously accepted while persisted evidence has changed shape. The owner exposes rejection through the existing heartbeat scene/model rather than manufacturing a second UI owner. A Base64 declaration mismatch earns no decorative Christmas motion.

Source art must remain non-raster and touch/keyboard semantic if operated in DOM. Source art is never Android runtime proof.

## Resource law — 2026-08-27 14:02 source checkpoint
A bounded caller does not make a reusable helper intrinsically bounded. The pure exact-comparison helper now refuses either direct declaration above `MAX_PAYLOAD_B64_CHARS` before equality work. Exact-at-ceiling text remains admitted; max+1 is rejected. Oversized evidence is neither truncated nor normalized into a plausible canonical declaration.

## Regression source
Pin at minimum:

- canonical padded writer encoding accepted by exact comparison;
- ignored-whitespace alias rejected;
- unpadded alias rejected when canonical writer encoding contains padding;
- non-canonical pad-bit alias rejected at the pure comparison boundary;
- null/empty declarations not promoted into canonical payload identity;
- exact-at-ceiling direct comparison accepted when identical;
- max+1 on either side rejected before equality work;
- owner-boundary rejection preserves last-good visible contact and clamps frame/node motion.

Regression source is not TESTED until an authorized runner executes it.

## Existing-owner wiring state
Current source truth:

- exact comparison policy source: **YES**;
- direct comparison finite-source throat: **YES / SOURCE_WIRED**;
- hostile comparison regression source: **YES / UNEXECUTED**;
- fail-closed owner-boundary regression source: **YES / UNEXECUTED**;
- existing `OperatorOverlayService` performs platform decode: **YES**;
- existing owner canonical re-encode + exact raw declaration comparison: **YES / SOURCE_WIRING**;
- fail-closed owner routing for the non-canonical boundary: **YES / SOURCE_WIRING**;
- Android tests executed: **NO unless fresh exact-head evidence proves otherwise**;
- runtime UI observed: **NO**;
- runtime TalkBack exercised: **NO**;
- deployed/callable/executed/delivered/accepted: **NO**.

Do not report source wiring as runtime proof.

## P0 / phone firewall
This skill never consumes Phone Hands, the primary-phone execution surface, queue/relay prerequisites, Nightcore, Pocket TTS, Chromium, Context Organs, P0 recovery, or physical acceptance. Fresh P0 evidence remains read-only here.

## Done for this source seam
This seam may go dark after durable owner readback, regression source, doctrine synchronization, and bounded review receipts exist. Later heartbeats must find a materially different independent wound unless new evidence changes this contract; blocked CI alone is not permission to relight it.
