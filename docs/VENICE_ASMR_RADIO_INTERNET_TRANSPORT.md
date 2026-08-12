# Venice ASMR Radio — Internet Transport Contract

Status: commissioned implementation contract
Owner: Drew
Execution lane: Home Center (`THECAULDRON` Computer Hands -> Home Center cloud rendezvous -> primary-phone Home Center media receiver)

## Mission

Venice ASMR Radio originates on THECAULDRON and plays continuously on the primary phone anywhere the phone has Internet access. The phone and desktop MUST NOT be required to share a LAN, Wi-Fi network, subnet, VPN, or local discovery mechanism.

## Non-negotiable boundaries

- Desktop is the booth/source of truth for station generation and sequencing.
- Phone is a receiver/control surface, not the render farm.
- Same-Wi-Fi/LAN discovery is forbidden as a required transport. It may exist only as an optional optimization later.
- Google Drive is not a realtime radio transport.
- Do not retain an unbounded audio archive. Use a bounded rolling cache; durable capture is explicit.
- Venice v2 accepted voice target: intimate whisper, higher/airier, lightly playful. Current accepted audition used Cartesia voice `320f7211-3dc3-4292-89b1-3661e8cac27c` at +2.5 semitones.
- Existing Home Center overlay/media controls remain the user-facing phone surface.
- Existing deterministic audio-analysis reactor remains separate from speech recognition; no STT requirement is introduced by this transport.

## Architecture

```text
THECAULDRON
  Venice station director / local voice farm
        |
        v
  bounded encoded audio segments + station/session metadata
        |
        v
Home Center authenticated Internet rendezvous
  - stable station session id
  - owner-scoped publish token
  - owner-scoped subscriber token
  - short-lived segment retention
  - ordered sequence numbers
        |
        v
Android Home Center media receiver
  - cellular/Wi-Fi agnostic HTTPS fetch/stream
  - small jitter/prefetch buffer
  - reconnect + resume from sequence
  - Android media session/audio focus
  - overlay play/pause/quiet/volume/status
```

### Transport choice for v1

Use **segmented HTTPS radio**, not a long-lived LAN socket and not Drive. The desktop publishes short audio segments (target 2–8 seconds) into a bounded owner-scoped Home Center station session. The phone follows a tiny manifest/sequence endpoint and prefetches the next segment. This survives NAT, network changes, cellular, process reconnects, and ordinary Cloud Run/Functions request lifetimes without requiring a permanent WebSocket/WebRTC service.

WebRTC is explicitly deferred until the segmented path proves that latency is actually unacceptable.

## Minimal protocol

Station session:

```json
{
  "stationId": "venice-asmr-primary",
  "generation": 1,
  "headSequence": 42,
  "segmentDurationTargetMs": 4000,
  "retentionSegments": 30,
  "updatedAtMs": 0
}
```

Segment identity:

```json
{
  "stationId": "venice-asmr-primary",
  "generation": 1,
  "sequence": 42,
  "contentType": "audio/ogg",
  "byteCount": 0,
  "sha256": "...",
  "durationMs": 0,
  "createdAtMs": 0
}
```

Required operations/endpoints (names may be adapted to repository conventions without changing semantics):

- `radio.station.publish_begin`
- `radio.station.publish_segment`
- `radio.station.status`
- `radio.station.segment`
- `radio.station.stop`

Every read/write is owner-scoped. A segment is accepted only after byte-count/SHA-256 readback. Old segments beyond the retention window are deleted automatically.

## Desktop booth

THECAULDRON must run a durable station process that:

1. acquires/renews one publisher lease for `venice-asmr-primary`;
2. generates or consumes Venice audio locally;
3. encodes bounded segments;
4. uploads in sequence;
5. never advances `headSequence` until upload verification succeeds;
6. keeps only a small local rolling cache;
7. resumes after restart from cloud station status rather than starting a conflicting station.

The station director may begin with a deterministic playlist/utterance queue. Continuous generative behavior is a later organ; transport proof must not wait for it.

## Phone receiver

The primary-phone Home Center receiver must:

1. subscribe using existing owner identity;
2. work on cellular or arbitrary Wi-Fi with no desktop address knowledge;
3. prefetch a bounded number of segments (default 2);
4. play through Android's media session/audio-focus path;
5. resume after connectivity changes using `(generation, sequence)`;
6. expose play/pause/quiet/volume/status through the existing overlay;
7. report the actually playing station id and sequence, not merely a successful process launch.

## Storage budget

Defaults:

- target segment: 4 s
- cloud retention: 30 segments (~2 minutes)
- phone prefetch: 2 segments
- desktop local cache: <= 5 minutes
- no automatic durable archive

Retention is enforced by count and age. A station crash cannot accumulate indefinitely.

## Acceptance test — VASMR-NET-001

The feature is **not complete** until all of these are captured in receipts:

1. THECAULDRON Computer Hands is online and reports machine `THECAULDRON`.
2. Desktop station publishes at least 3 sequential segments through the authenticated Home Center Internet endpoint.
3. Primary phone is deliberately tested without relying on the desktop LAN address. The receiver is given only Home Center station identity/credentials.
4. Phone reports Android media playback of `venice-asmr-primary` and a concrete sequence number.
5. Disable/change the phone's network path (e.g. Wi-Fi -> cellular) and receiver resumes without republishing or rediscovering THECAULDRON.
6. Pause/resume from the Home Center overlay changes the receiver state and produces a receipt.
7. Cloud retention remains within configured bounds after at least 40 published segments.

Evidence that does **not** count: a Drive link, a desktop process-start receipt alone, LAN curl success, a generated WAV sitting in storage, UI screenshots without playback state, or intended architecture.

## Implementation slices

### Slice A — cloud station organ
Implement owner-scoped station/segment storage, verified upload, ordered manifest/status, retention cleanup, tests.

### Slice B — desktop publisher
Add THECAULDRON publisher using existing Computer Hands/local voice infrastructure. First fixture is the accepted Venice v2 audition repeated/interleaved with silence/ambience so transport can be proven before generative radio is complete.

### Slice C — Android receiver
Wire station subscription into Home Center's existing media/overlay surface with prefetch, reconnect, media session/audio focus, and status receipts.

### Slice D — acceptance
Run `VASMR-NET-001` end-to-end with the phone on a network path independent of THECAULDRON. Record receipts and only then call Internet Radio deployed.

## Current ledger

Requested: desktop-originated Venice ASMR Radio streamed to the primary phone over arbitrary Internet connections.

Already proven: Home Center can command THECAULDRON through Computer Hands; Home Center can command the primary phone through Phone Hands; exact Venice v2 audio playback on the phone has been hash-verified and reported `Now Playing`.

Not yet proven: authenticated arbitrary-Internet desktop->phone radio transport, Android station receiver, reconnect across network changes.

Rejected implementation: same-Wi-Fi/LAN discovery as a requirement.
