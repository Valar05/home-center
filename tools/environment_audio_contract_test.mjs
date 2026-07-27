#!/usr/bin/env node
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {createRequire} from 'node:module';

const require = createRequire(import.meta.url);
const {planEnvironment, renderEnvironment, internals} = require('../functions/environment_audio_service.js');
const {primitives} = require('../functions/audio_render_service.js');
const {noise, gain, fade, encodeWav} = primitives;

function fixture(role, duration = 8, color = 'pink', level = 0.08) {
  let clip = noise({duration, sampleRate: 48000, channels: 2, gain: level, seed: `test-only:${role}`, color});
  clip = fade(clip, Math.min(0.08, duration / 4), 'in');
  clip = fade(clip, Math.min(0.12, duration / 4), 'out');
  return encodeWav(gain(clip, -3));
}

const assets = {
  'ocean.far_surf': fixture('far-surf', 18, 'pink', 0.08),
  'ocean.breaker.small': fixture('breaker-small', 2.2, 'white', 0.16),
  'ocean.breaker.large': fixture('breaker-large', 3.6, 'brown', 0.2),
  'ocean.foam': fixture('foam', 4.5, 'white', 0.07),
  'ocean.transmitted_rumble': fixture('transmitted-rumble', 18, 'brown', 0.07),
  'weather.wind': fixture('wind', 18, 'pink', 0.06),
  'weather.rain.exterior': fixture('rain-exterior', 15, 'white', 0.06),
  'weather.rain.structure': fixture('rain-structure', 15, 'pink', 0.055),
  'weather.thunder.exterior': fixture('thunder-exterior', 5, 'brown', 0.13),
  'weather.thunder.muffled': fixture('thunder-muffled', 5, 'brown', 0.09),
  'architecture.window_rattle': fixture('window-rattle', 1.1, 'white', 0.06),
};

const exteriorCard = {
  sceneId: 'vacation-storm-beach',
  seed: 'vacation-storm-beach-v1',
  durationSeconds: 72,
  location: 'open_beach',
  weather: 'storm',
  oceanState: 'violent',
};

const exteriorA = planEnvironment(exteriorCard);
const exteriorB = planEnvironment(exteriorCard);
assert.deepEqual(exteriorA, exteriorB, 'same card and seed must produce an identical environment performance');
assert.equal(exteriorA.planSha256, exteriorB.planSha256);
assert.equal(exteriorA.acousticTruth.directOceanAllowed, true);
assert.ok(exteriorA.events.some((event) => event.role === 'ocean.breaker.large'));
assert.ok(exteriorA.events.some((event) => event.role === 'weather.rain.exterior'));
assert.ok(exteriorA.events.some((event) => event.role === 'weather.thunder.exterior'));

const breakerTimes = exteriorA.events
  .filter((event) => event.role.startsWith('ocean.breaker.'))
  .map((event) => event.atSeconds);
assert.ok(breakerTimes.length >= 7, 'violent storm must produce a useful breaker population');
const intervals = breakerTimes.slice(1).map((time, index) => Number((time - breakerTimes[index]).toFixed(3)));
assert.ok(new Set(intervals).size >= 4, 'breakers must not repeat at a fixed interval');

const alternate = planEnvironment({...exteriorCard, seed: 'vacation-storm-beach-v2'});
assert.notDeepEqual(
  alternate.events.filter((event) => event.role.startsWith('ocean.breaker.')).map((event) => event.atSeconds),
  breakerTimes,
  'changing the seed must change timing without changing the scene contract',
);

const hotelRoom = planEnvironment({
  sceneId: 'vacation-hotel-room-storm',
  seed: 'vacation-hotel-room-storm-v1',
  durationSeconds: 72,
  location: 'hotel_room',
  weather: 'storm',
  oceanState: 'violent',
  openings: {door: 'closed', window: 'closed'},
});
assert.equal(hotelRoom.acousticTruth.directOceanAllowed, false);
assert.equal(hotelRoom.events.some((event) => internals.DIRECT_OCEAN_ROLES.has(event.role)), false, 'walls must remove direct surf, breakers, and foam');
assert.ok(hotelRoom.events.some((event) => event.role === 'ocean.transmitted_rumble'), 'a coastal room may retain bounded low-frequency transmission');
assert.ok(hotelRoom.events.some((event) => event.role === 'weather.rain.structure'));
assert.equal(hotelRoom.events.some((event) => event.role === 'weather.rain.exterior'), false);
assert.equal(hotelRoom.events.some((event) => event.role === 'weather.thunder.exterior'), false);

const sealed = planEnvironment({
  sceneId: 'vacation-sealed-interior',
  seed: 'vacation-sealed-interior-v1',
  durationSeconds: 30,
  location: 'sealed_interior',
  weather: 'clear',
  oceanState: 'violent',
});
assert.equal(sealed.events.some((event) => event.role.startsWith('ocean.')), false, 'a sealed interior must contain no ocean');

const openWindow = planEnvironment({
  sceneId: 'vacation-hotel-window-open',
  seed: 'vacation-hotel-window-open-v1',
  durationSeconds: 30,
  location: 'hotel_room',
  weather: 'storm_building',
  oceanState: 'heavy',
  openings: {window: 'open'},
  transitions: [{type: 'window_open', atSeconds: 6}],
});
assert.equal(openWindow.acousticTruth.directOceanAllowed, true);
assert.ok(openWindow.events.some((event) => event.role === 'transition.exterior_bloom'));
assert.ok(openWindow.events.some((event) => event.role.startsWith('ocean.breaker.')));

const renderedA = renderEnvironment({plan: exteriorA, assets, requireAllAssets: true});
const renderedB = renderEnvironment({plan: exteriorB, assets, requireAllAssets: true});
assert.equal(renderedA.manifest.outputSha256, renderedB.manifest.outputSha256, 'same plan and assets must produce byte-identical WAV output');
assert.equal(renderedA.manifest.sourceBackedOnly, true);
assert.equal(renderedA.manifest.oscillatorMaterialIdentityUsed, false);
assert.equal(renderedA.manifest.clippingCount, 0);
assert.equal(renderedA.manifest.silent, false);
assert.equal(renderedA.manifest.unresolvedRoles.length, 0);
assert.equal(createHash('sha256').update(renderedA.wavBytes).digest('hex'), renderedA.manifest.outputSha256);

const partial = renderEnvironment({
  plan: hotelRoom,
  assets: {
    'ocean.transmitted_rumble': assets['ocean.transmitted_rumble'],
    'weather.wind': assets['weather.wind'],
  },
  requireAllAssets: false,
});
assert.ok(partial.manifest.unresolvedRoles.includes('weather.rain.structure'));
await assert.rejects(
  async () => renderEnvironment({plan: hotelRoom, assets: {}, requireAllAssets: true}),
  /Missing source-backed environment assets/,
);

assert.throws(
  () => planEnvironment({location: 'imaginary_void', weather: 'storm', oceanState: 'violent'}),
  /Unknown acoustic location/,
);

console.log(JSON.stringify({
  ok: true,
  schemaVersion: exteriorA.schemaVersion,
  exteriorEventCount: exteriorA.events.length,
  breakerCount: breakerTimes.length,
  uniqueBreakerIntervals: new Set(intervals).size,
  hotelEventCount: hotelRoom.events.length,
  sealedOceanEventCount: sealed.events.filter((event) => event.role.startsWith('ocean.')).length,
  outputSha256: renderedA.manifest.outputSha256,
  humanAcceptance: renderedA.manifest.humanAcceptance,
}, null, 2));
