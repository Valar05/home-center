#!/usr/bin/env node
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
const require = createRequire(import.meta.url);
const r = require('../functions/reality_membrane');

const NOW = Date.parse('2026-08-13T10:30:00.000Z');

const time = r.timeObservations({nowMs: NOW, timeZone: 'America/Chicago'});
assert.equal(time.now.observation_type, 'time.local');
assert.equal(time.now.value, '2026-08-13T05:30:00-05:00');
assert.equal(time.timezone.value, 'America/Chicago');
assert.equal(time.date.value, '2026-08-13');
assert.equal(time.weekday.value, 'Thursday');
assert.equal(time.now.stale, false);
assert.ok(time.now.receipt_id.startsWith('reality_'));

const fresh = r.observation({
  observation_type: 'weather.temperature_f',
  value: 78,
  units: 'F',
  observed_at: '2026-08-13T10:20:00.000Z',
  source: 'test',
  max_age_ms: 20 * 60 * 1000,
}, NOW);
assert.equal(fresh.stale, false);
assert.equal(fresh.age_ms, 10 * 60 * 1000);
const stale = r.observation({
  observation_type: 'weather.temperature_f',
  value: 78,
  units: 'F',
  observed_at: '2026-08-13T09:00:00.000Z',
  source: 'test',
  max_age_ms: 20 * 60 * 1000,
}, NOW);
assert.equal(stale.stale, true);
assert.equal(stale.freshness, 'stale');
assert.equal(r.staleObservation(fresh, 'network_down', NOW).capability_state, 'degraded');

const unknown = r.observation({
  observation_type: 'phone.audio_route',
  unavailable: true,
  capability_state: r.CAPABILITY.UNAVAILABLE,
  source: 'phone_hands',
  privacy: r.PRIVACY.DEVICE,
  error: 'not_observed',
}, NOW);
assert.equal(unknown.value, null);
assert.equal(unknown.unavailable, true);
assert.equal(unknown.capability_state, 'unavailable');

const weather = r.weatherObservations({
  condition: 'Light rain',
  weather_code: 61,
  temperature_f: 78,
  feels_like_f: 80,
  precipitation: 'rain',
  precipitation_inches: 0.02,
  precipitation_probability_pct: 70,
  humidity_pct: 84,
  wind_mph: 4,
  severe_alerts: [],
}, {nowMs: NOW, observedAt: NOW - 5 * 60 * 1000, source: 'fixture.free_weather'});
assert.equal(weather.temperature_f.value, 78);
assert.equal(weather.temperature_f.privacy, 'PUBLIC');
assert.deepEqual(weather.severe_alerts.value, []);
const missingWeather = r.weatherObservations({}, {nowMs: NOW, source: 'fixture.free_weather'});
assert.equal(missingWeather.temperature_f.unavailable, true);
assert.equal(missingWeather.precipitation.unavailable, true);

const phone = r.phoneObservations({
  battery_pct: 61,
  charging: true,
  power_source: 'usb',
  connectivity: 'home_center_relay_online',
  audio_route: 'headphones',
}, {nowMs: NOW, observedAt: NOW - 30 * 1000, source: 'fixture.phone_hands', receiptId: 'phc_test'});
assert.equal(phone.battery_pct.value, 61);
assert.equal(phone.battery_pct.receipt_id, 'phc_test');
const missingPhone = r.phoneObservations({}, {nowMs: NOW, source: 'fixture.phone_hands'});
assert.equal(missingPhone.battery_pct.unavailable, true);
assert.equal(missingPhone.charging.unavailable, true);
assert.equal(missingPhone.audio_route.unavailable, true);

const daylight = r.daylightObservation({
  sunrise: Date.parse('2026-08-13T11:30:00.000Z'),
  sunset: Date.parse('2026-08-14T01:00:00.000Z'),
  nowMs: NOW,
  receiptId: 'weather_receipt',
});
assert.equal(daylight.value, 'dark_before_sunrise');
assert.equal(daylight.receipt_id, 'weather_receipt');
assert.equal(r.daylightObservation({nowMs: NOW}).unavailable, true);

const projection = r.compactProjection({nowMs: NOW, time, daylight, weather, phone, unavailable: ['media.current']});
assert.equal(projection.observed_at, '2026-08-13T10:30:00.000Z');
assert.equal(projection.device.battery_pct.value, 61);
assert.equal(projection.environment.precipitation.value, 'rain');
assert.equal(projection.unavailable[0], 'media.current');
assert.equal(projection.device.battery_pct.privacy, 'DEVICE');
assert.equal(projection.device.battery_pct.receipt_id, 'phc_test');

const sensitive = r.observation({observation_type: 'calendar.description', value: 'private', privacy: r.PRIVACY.SENSITIVE, source: 'calendar'}, NOW);
const filtered = r.compactProjection({nowMs: NOW, media: {forbidden: sensitive}, place: {also_forbidden: sensitive}, time: {now: sensitive}});
assert.equal(filtered.media.forbidden, undefined);
assert.equal(filtered.place.also_forbidden, undefined);
assert.equal(filtered.time.now, null);
assert.ok(!JSON.stringify(filtered).includes('private'));

const events = r.transitionEvents(
  {precipitation: 'none', daylight: 'dark_before_sunrise', charging: false, audio_route: 'speaker', connectivity: 'offline', battery_pct: 30},
  {precipitation: 'rain', daylight: 'daylight', charging: true, audio_route: 'headphones', connectivity: 'home_center_relay_online', battery_pct: 20},
  '2026-08-13T10:30:00.000Z',
  ['weather_receipt', 'phc_test'],
);
assert.deepEqual(events.map((event) => event.event_type), [
  'rain.started',
  'sun.risen',
  'phone.charging',
  'audio.route_changed',
  'connectivity.restored',
  'phone.low_battery',
]);
assert.deepEqual(events[0].source_receipts, ['weather_receipt', 'phc_test']);

const checkpoint = {real_time: NOW - 60 * 60 * 1000, scene_time: NOW - 2 * 60 * 60 * 1000};
const compressed = r.timeBridge({realNow: NOW, sceneTime: NOW, lastSceneCheckpoint: checkpoint, policy: 'compressed', compressionRatio: 3});
assert.equal(compressed.ELAPSED_REAL_TIME_MS, 60 * 60 * 1000);
assert.equal(compressed.ELAPSED_WORLD_TIME_MS, 3 * 60 * 60 * 1000);
assert.equal(r.timeBridge({realNow: NOW, lastSceneCheckpoint: checkpoint, policy: 'paused'}).ELAPSED_WORLD_TIME_MS, 0);
assert.equal(r.timeBridge({realNow: NOW, policy: 'detached'}).ELAPSED_WORLD_TIME_MS, null);

const summary = r.accessibilitySummary(projection);
assert.match(summary, /^Reality: 5:30 AM\./);
assert.match(summary, /Still dark/);
assert.match(summary, /78 degrees/);
assert.match(summary, /Phone charging at 61 percent/);
assert.match(summary, /headphones audio/);

const capabilities = r.realityCapabilities({callableOperations: ['reality.status', 'reality.observe']});
assert.equal(capabilities.unknown_policy, 'unknown-remains-unknown');
assert.equal(capabilities.cost_policy, 'zero-dollar-default');
assert.ok(capabilities.target_operations.includes('reality.history'));
assert.deepEqual(capabilities.callable_operations, ['reality.status', 'reality.observe']);
assert.deepEqual(capabilities.layer_policy, ['real_observation', 'derived_interpretation', 'fictional_transformation', 'inner_fortress_canon']);

console.log('Reality Membrane contract tests passed');
