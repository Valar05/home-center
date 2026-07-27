# Vacation Environmental Audio

Status: candidate implementation, human listening review pending.

This renderer exists to fix two production failures in the current Vacation soundscape:

1. ocean events repeated at visibly regular intervals;
2. exterior ocean remained audible when the scene moved into an interior.

The electronic interface boops and bleeps are outside this system and must remain unchanged.

## Authority order

1. Location and openings.
2. Weather.
3. Ocean state.
4. Dramatic intensity.

The ocean may perform as a dangerous, unstable presence. It may build, cluster, and storm. It may not pass through sealed walls because the story wants emphasis.

## Environment card

```json
{
  "sceneId": "vacation-day-three-beach-storm",
  "seed": "vacation-day-three-beach-storm-v1",
  "durationSeconds": 72,
  "location": "open_beach",
  "weather": "storm",
  "oceanState": "violent",
  "dialogueSafe": true
}
```

Interior example:

```json
{
  "sceneId": "vacation-day-three-hotel-room",
  "seed": "vacation-day-three-hotel-room-v1",
  "durationSeconds": 72,
  "location": "hotel_room",
  "weather": "storm",
  "oceanState": "violent",
  "openings": {
    "door": "closed",
    "window": "closed"
  }
}
```

The hotel-room card removes direct surf, breakers, and foam. It may retain bounded low-frequency ocean transmission, rain striking the structure, muffled thunder, and occasional window rattle.

A fully sealed interior uses `location: "sealed_interior"` and contains no ocean events.

## Supported locations

- `open_beach`
- `shoreline`
- `dock`
- `covered_balcony`
- `covered_patio`
- `hotel_lobby`
- `hotel_room`
- `hotel_hallway`
- `bathroom`
- `vehicle`
- `sealed_interior`

## Weather states

- `clear`
- `windy`
- `storm_building`
- `storm`
- `storm_passing`
- `after_storm`

## Ocean states

- `absent`
- `calm`
- `rolling`
- `active`
- `heavy`
- `violent`

## Required source roles

The planner emits roles rather than fabricating material. Production must provide real, rights-cleared source recordings for the roles a scene uses.

Ocean:

- `ocean.far_surf`
- `ocean.breaker.small`
- `ocean.breaker.large`
- `ocean.foam`
- `ocean.transmitted_rumble`

Weather and structure:

- `weather.wind`
- `weather.rain.exterior`
- `weather.rain.structure`
- `weather.thunder.exterior`
- `weather.thunder.muffled`
- `architecture.window_rattle`

The renderer reports unresolved roles. With `requireAllAssets: true`, it fails closed instead of substituting a generic noise or oscillator.

## JavaScript use

```js
const {
  planEnvironment,
  renderEnvironment,
} = require('./functions/environment_audio_service');

const plan = planEnvironment(environmentCard);
const result = renderEnvironment({
  plan,
  assets: {
    'ocean.far_surf': farSurfWavBuffer,
    'ocean.breaker.small': smallBreakerWavBuffer,
    'ocean.breaker.large': largeBreakerWavBuffer,
    'ocean.foam': foamWavBuffer,
    'weather.wind': windWavBuffer,
    'weather.rain.exterior': rainWavBuffer,
    'weather.thunder.exterior': thunderWavBuffer,
  },
  requireAllAssets: true,
  ceilingDb: -1,
});

await fs.writeFile('vacation-environment.wav', result.wavBytes);
await fs.writeFile(
  'vacation-environment-manifest.json',
  JSON.stringify(result.manifest, null, 2),
);
```

## Timing contract

- Breaker timing uses deterministic seeded variation.
- Violent water may form short clusters, followed by longer gaps.
- Foam follows a breaker with bounded variation instead of sharing its exact onset.
- Continuous beds are built from overlapping, offset source excerpts.
- Reusing the same card and seed reproduces byte-identical output when source assets are identical.
- Changing the seed changes the performance while preserving location and weather truth.

## Transitions

Cards may include transition markers:

```json
{
  "transitions": [
    {"type": "window_open", "atSeconds": 6},
    {"type": "window_close", "atSeconds": 24}
  ]
}
```

Supported markers currently create explicit transition events:

- `door_open`
- `door_close`
- `window_open`
- `window_close`
- `enter_interior`

These markers are evidence for the final scene mixer. They do not override the card's physical location state.

## Acceptance boundaries

Mechanical acceptance:

- deterministic plan and output;
- no clipping;
- no fixed-interval breaker loop;
- no direct ocean in a sealed interior;
- no synthetic replacement for absent production assets;
- exact output hash in the manifest.

Human acceptance remains separate:

- Does the storm feel alive rather than busy?
- Does the ocean stop at the correct narrative threshold?
- Is transmitted interior rumble restrained enough for dialogue?
- Are breakers and thunder timed to the scene rather than merely randomized?

No deployment or merge is authorized by this document.
