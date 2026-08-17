# Heartbeat Pre-Decode Resource Budget

## Purpose
Keep corrupt persisted heartbeat declarations from consuming unbounded decode/allocation work before the existing integrity pipeline can reject them.

The canonical writer caps the UTF-8 payload at `OperatorState.MAX_HEARTBEAT_LIGHTS_BYTES`. Standard padded Base64 can therefore require at most:

`4 * ceil(MAX_HEARTBEAT_LIGHTS_BYTES / 3)` characters.

`HeartbeatPersistedSnapshotReader.MAX_PAYLOAD_BASE64_CHARS` derives that ceiling from the existing byte constant. The coherent reader rejects a longer stored declaration before `OperatorOverlayService` calls Android Base64 decode.

## Ownership
This skill owns a source-level resource bound only. It does not own a decoder, poll loop, cache, renderer, overlay controller, transport, Phone Hands ticket, primary-phone command, P0 recovery action, deployment, or acceptance lane. The sole runtime owner remains the existing `OperatorOverlayService`; the canonical writer remains `OperatorState.updateHeartbeatLights(...)`.

Do not create a second decoder or a second heartbeat reader to enforce this rule.

## Evidence separation
The pre-decode length ceiling is not Base64 canonicality and is not payload integrity.

- declaration length within the ceiling: merely eligible for the existing decode/canonicality/integrity/parser chain;
- declaration length above the ceiling: coherent-read failure before decode;
- exact Base64 writer representation: separate `HeartbeatPersistedBase64Canonicality` concern;
- decoded byte count/SHA/UTF-8/semantic acceptance: existing downstream concerns.

Never report `length <= max` as valid Base64, accepted payload, rendered UI, or runtime delivery.

## Accessibility and contact preservation
An oversized declaration is a storage wound, not operator prose. The existing service catches the reader failure at the coherent-read boundary and projects the bounded `STORAGE_READ_FAILURE_BOUNDARY`; raw declaration contents and raw exception text must not be announced through TalkBack.

If last-good heartbeat contact exists, preserve it through the existing fail-closed scene organ and clamp one-shot motion. Before first contact, do not invent `CONTACT HELD`.

## Regression source
Pin at least:

- exact canonical maximum declaration length is accepted by the reader;
- maximum + 1 is rejected before any owner decode;
- exact SHA metadata text remains byte-for-character unchanged by the reader;
- wrong stored types remain read failures rather than fake absence;
- regression source existence is not TESTED evidence.

## Capability membrane
Keep these states distinct:

`requested -> reader bound source -> regression source -> exact GitHub readback -> tested -> runtime decode avoided -> runtime UI observed -> TalkBack exercised -> deployed -> callable -> executed -> delivered -> accepted`

Current source state: reader bound **YES**; regression source **YES**; exact GitHub readback **YES**; tested/runtime/deployed/callable/executed/delivered/accepted **NO** until separate evidence exists.

## P0 firewall
This skill must never wake, queue, retask, probe, or consume Phone Ingress, Phone Hands, Nightcore, Pocket TTS, Chromium Control, Context Organs, or their physical acceptance chain. A repository-source resource bound is independent of P0 recovery.
