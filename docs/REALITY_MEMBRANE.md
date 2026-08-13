# Reality Membrane — Inner Fortress

## Law

Reality may influence Inner Fortress. Inner Fortress may not rewrite reality.

Keep four states separate:

1. real observation
2. derived interpretation
3. fictional transformation
4. Inner Fortress canon consequence

The Reality Membrane owns only (1), plus provenance/history/event mechanics needed to safely derive later layers. It never writes fiction.

## Canonical surface

Target operations:

- `reality.status`
- `reality.observe`
- `reality.history`
- `reality.sources`
- `reality.capabilities`
- optional: `reality.subscribe`, `reality.events`

A default Inner Fortress request should return one compact bounded projection, not raw infrastructure dumps.

## Observation contract

Every observation carries: `observation_type`, `value`, `units`, `observed_at`, `source`, `source_timestamp`, `age_ms`, `freshness`, `confidence`, `location_scope`, `privacy`, `capability_state`, `receipt_id`, `stale`, `unavailable`, and `error`.

Unknown remains unknown. Unavailable values are null. Stale values retain their original timestamp and are never presented as current.

Privacy classes: PUBLIC, DEVICE, PERSONAL, SENSITIVE. Default Inner Fortress projection admits PUBLIC and safe DEVICE observations only. PERSONAL/SENSITIVE require explicit policy.

## Reusable Home Center organs audited at checkpoint

- `time.now`: deployed and callable through `drive_operation`; use as clock truth.
- Phone Hands: deployed `primary-phone` relay with bounded actions, command IDs, terminal receipts, and live device heartbeat.
- Computer Hands: architecture exists but `windows-hands-01` was offline at this checkpoint; do not treat it as callable.
- Venice Nerve: architecture exists but Windows Venice worker was offline; jar emulation was used and labeled as such.
- `context_sync.publish_snapshot`: existing snapshot surface suitable for later compact reality packets.
- Command Center/Phone Hands receipts and Firestore transition records: reuse rather than inventing another receipt substrate.
- Calendar tooling exists, but calendar reality is explicitly opt-in and should derive free/busy without leaking titles/attendees/descriptions by default.
- Existing audio/SFX/voice machinery is not ambient perception. Do not confuse speech/media generation with observed environmental audio.

## Capability matrix

| Sense | First source | State in this checkpoint | Reliability target | Notes |
|---|---|---|---|---|
| local time/timezone/weekday | Home Center runtime clock | implemented in membrane core; existing `time.now` already callable | high | zero-dollar/local |
| daylight | sunrise/sunset adapter | implemented normalizer; source not yet wired | high | coarse locality only |
| current weather | free/public weather adapter | implemented normalizer; source not yet wired | medium-high | weather must carry age/source |
| phone battery/charging | Phone Hands/Android | implemented normalizer; live body exists, observation action not yet wired | high | DEVICE |
| connectivity | Phone Hands/Android | implemented normalizer | high | event-worthy transitions |
| audio route | Phone Hands/Android | implemented normalizer | high | accessibility value high |
| media presence | existing phone/media state | contract slot only | medium | metadata only when authorized |
| calendar free/busy | Google Calendar | deferred opt-in | high | no private titles by default |
| place | coarse known-place policy | deferred | medium | no continuous coordinates |
| microphone environment | local derived events | deferred/research | variable | sensitive; explicit activation only |

## Hunger scoring

Scores are qualitative: H/M/L.

| Candidate | Living world | Accessibility | Impl cost | Battery | Privacy cost | Network | Reliability | Novelty | Creepy risk | Verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| daylight | H | M | L | L | L | L | H | M | L | BUILD |
| rain/weather transitions | H | M | M | L | L | M | H | H | L | BUILD |
| charging/battery transitions | M | H | L | L | L | none | H | M | L | BUILD |
| headphones/audio route | H | H | L | L | L | none | H | H | L | BUILD |
| connectivity changes | M | H | L | L | L | none | H | M | L | BUILD |
| Android Auto/car context | H | H | M | L | M | none | M-H | H | L | NEXT CANDIDATE |
| notification count only | M | H | M | L | M | none | M | M | M | LATER, pressure only |
| nearby known devices | M | M | M | M | M | none | M | M | M | LATER |
| ambient light | M | H | M | M | M | none | M | M | M | LATER |
| microphone sound categories | H | H | H | H | H | none/local | M | H | H | DEFER |
| raw microphone capture | L | L | H | H | H | optional | M | L | H | KILL default |
| precise location history | L | M | H | M | H | optional | M | L | H | KILL default |
| message bodies | L | L | L | L | H | varies | H | L | H | KILL default |

## Event model

Prefer transition events over high-frequency polling. Initial event vocabulary: `weather.changed`, `rain.started`, `sun.risen`, `phone.charging`, `phone.low_battery`, `audio.route_changed`, `media.started`, `connectivity.offline`, `connectivity.restored`, `place.changed`.

Debounce noisy sensors. Event records are reality records, never narrative events.

## History

Keep bounded transition/event history. Do not create an infinite battery-percentage diary. Suggested defaults: 72 hours of transition history plus explicitly pinned scene checkpoints. Longer retention requires a use case.

## Inner Fortress time bridge

Scenes must explicitly track `REAL_NOW`, `SCENE_TIME`, `LAST_SCENE_CHECKPOINT`, `ELAPSED_REAL_TIME`, `ELAPSED_WORLD_TIME`, and one policy: `realtime`, `paused`, `compressed`, `explicitly_advanced`, or `detached`.

Real time is never silently equated to scene time.

## Canary

Acceptance query: “What’s reality right now?”

Required output: actual local time, daylight state, current weather, phone battery/charging if callable, connectivity, audio route if callable; each with timestamp/provenance/staleness. Then Inner Fortress may transform those facts in exactly one scene.

Canary is NOT accepted until the deployed Home Center runtime exposes the membrane and the authorized phone body returns terminal observation receipts. Repository code is implementation evidence only.

## Venice judgment checkpoint

Antagonism found and rejected an initial privacy hole where opaque `media`/`place` extension objects could bypass the default privacy filter. The implementation now filters those groups through the same PUBLIC/DEVICE rule.

Venice checkpoint verdict: continue after this bounded implementation checkpoint; do not merge/deploy until deterministic tests execute on an authorized body and runtime wiring has a callable canary receipt.

## Hunger question after canary

“What single additional real-world sense would make Android 67 feel most embodied?”

Current leading candidate: **audio route / embodied listening context, including Android Auto when legitimately observable**, because it improves roleplay embodiment and accessibility without requiring invasive sensing.
