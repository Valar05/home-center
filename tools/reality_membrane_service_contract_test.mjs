#!/usr/bin/env node
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
const require = createRequire(import.meta.url);
const service = require('../functions/reality_membrane_service');

const NOW = Date.parse('2026-08-13T10:45:00.000Z');

const coarse = service.coarseLocation({location: {latitude: 35.1234, longitude: -92.4567, label: 'central_arkansas'}});
assert.deepEqual(coarse, {
  configured: true,
  latitude: 35.1,
  longitude: -92.5,
  label: 'central_arkansas',
  scope: 'coarse_0.1_degree',
});
assert.equal(service.coarseLocation({}).configured, false);
assert.equal(service.weatherCodeLabel(61), 'Rain');
assert.equal(service.precipitationKind({rain: 0.02}), 'rain');
assert.equal(service.nearestHourlyProbability({time: [100, 200, 300], precipitation_probability: [10, 20, 30]}, 190), 20);
const url = service.openMeteoUrl(coarse);
assert.match(url, /latitude=35.1/);
assert.match(url, /longitude=-92.5/);
assert.match(url, /current=temperature_2m/);
assert.ok(!url.includes('apikey'));

const weatherPayload = {
  current: {
    time: Math.floor((NOW - 60_000) / 1000),
    temperature_2m: 77.8,
    relative_humidity_2m: 84,
    apparent_temperature: 80.1,
    precipitation: 0.02,
    rain: 0.02,
    showers: 0,
    snowfall: 0,
    weather_code: 61,
    wind_speed_10m: 4.2,
    is_day: 0,
  },
  hourly: {
    time: [Math.floor((NOW - 60_000) / 1000), Math.floor((NOW + 59 * 60_000) / 1000)],
    precipitation_probability: [70, 65],
  },
  daily: {
    sunrise: [Math.floor(Date.parse('2026-08-13T11:30:00.000Z') / 1000)],
    sunset: [Math.floor(Date.parse('2026-08-14T01:00:00.000Z') / 1000)],
  },
  timezone: 'America/Chicago',
};
const alertPayload = {
  features: [{
    id: 'urn:oid:test-alert',
    properties: {
      event: 'Severe Thunderstorm Warning',
      severity: 'Severe',
      certainty: 'Observed',
      urgency: 'Immediate',
      onset: '2026-08-13T10:40:00Z',
      expires: '2026-08-13T11:15:00Z',
      senderName: 'NWS Little Rock AR',
    },
  }],
};
let fetchCount = 0;
const fetchImpl = async (requestUrl, options = {}) => {
  fetchCount += 1;
  const isAlerts = String(requestUrl).includes('api.weather.gov');
  if (isAlerts) assert.match(options.headers['User-Agent'], /HomeCenter-RealityMembrane/);
  const payload = isAlerts ? alertPayload : weatherPayload;
  return {ok: true, status: 200, text: async () => JSON.stringify(payload)};
};
const bundle = await service.fetchWeatherBundle(coarse, {fetchImpl, nowMs: NOW});
assert.equal(fetchCount, 2);
assert.equal(bundle.ok, true);
assert.equal(bundle.payload.temperature_f, 77.8);
assert.equal(bundle.payload.precipitation, 'rain');
assert.equal(bundle.payload.precipitation_probability_pct, 70);
assert.equal(bundle.payload.severe_alerts[0].event, 'Severe Thunderstorm Warning');
assert.equal(bundle.sunriseMs, Date.parse('2026-08-13T11:30:00.000Z'));
assert.equal(bundle.sunsetMs, Date.parse('2026-08-14T01:00:00.000Z'));
assert.ok(bundle.receiptId.startsWith('reality_'));

const normalizedPhone = service.normalizePhoneReceipt({
  commandId: 'phc_test',
  status: 'completed',
  result: {
    ok: true,
    timestamp: NOW / 1000,
    battery: {'level': '61', 'status': '2', 'USB powered': 'true', 'AC powered': 'false', 'Wireless powered': 'false'},
  },
}, NOW);
assert.equal(normalizedPhone.ok, true);
assert.deepEqual(normalizedPhone.payload, {
  battery_pct: 61,
  charging: true,
  power_source: 'usb',
  connectivity: 'home_center_relay_online',
  audio_route: undefined,
  screen_state: undefined,
  thermal_state: undefined,
});

let clock = NOW;
let getCalls = 0;
const callCommandCenter = async (operation, args) => {
  if (operation === 'phone_hands.enqueue') return {commandId: args.commandId, status: 'queued'};
  assert.equal(operation, 'phone_hands.get');
  getCalls += 1;
  if (getCalls === 1) return {commandId: args.commandId, status: 'leased'};
  return {
    commandId: args.commandId,
    status: 'completed',
    result: {
      ok: true,
      timestamp: clock / 1000,
      battery: {'level': '61', 'status': '2', 'USB powered': 'true'},
    },
  };
};
const phone = await service.observePhone({
  callCommandCenter,
  requestId: 'service-contract-test',
  timeoutMs: 4000,
  now: () => clock,
  sleep: async (ms) => { clock += ms; },
});
assert.equal(phone.ok, true);
assert.equal(phone.payload.battery_pct, 61);
assert.equal(phone.payload.connectivity, 'home_center_relay_online');
assert.ok(phone.commandId.startsWith('reality_'));

clock = NOW;
getCalls = 0;
fetchCount = 0;
const packet = await service.runOperation({
  operation: 'reality.observe',
  admin: null,
  user: {email: 'owner@example.invalid'},
  args: {
    requestId: 'packet-contract-test',
    timeZone: 'America/Chicago',
    location: {latitude: 35.1234, longitude: -92.4567, label: 'central_arkansas'},
    scene: {
      sceneTime: NOW,
      lastSceneCheckpoint: {real_time: NOW - 60_000, scene_time: NOW - 120_000},
      policy: 'compressed',
      compressionRatio: 2,
    },
  },
  callCommandCenter,
  fetchImpl,
  now: () => clock,
  sleep: async (ms) => { clock += ms; },
});
assert.equal(packet.contract, 'home-center.reality.v1');
assert.equal(packet.layer, 'real_observation');
assert.equal(packet.fiction_generated, false);
assert.equal(packet.paid_service_activated, false);
assert.equal(packet.location.scope, 'coarse_0.1_degree');
assert.equal(packet.projection.environment.temperature_f.value, 77.8);
assert.equal(packet.projection.environment.severe_alerts.value[0].severity, 'Severe');
assert.equal(packet.projection.environment.severe_alerts.source, 'weather.gov.alerts');
assert.equal(packet.projection.device.battery_pct.value, 61);
assert.equal(packet.projection.device.connectivity.value, 'home_center_relay_online');
assert.equal(packet.projection.device.audio_route.unavailable, true);
assert.equal(packet.projection.time_bridge.ELAPSED_WORLD_TIME_MS, 120_000);
assert.match(packet.summary, /^Reality:/);
assert.ok(!JSON.stringify(packet).includes('35.1'));
assert.ok(!JSON.stringify(packet).includes('-92.5'));
assert.ok(!JSON.stringify(packet).includes('owner@example.invalid'));

const capabilities = await service.runOperation({operation: 'reality.capabilities'});
assert.deepEqual(capabilities.callable_operations, [
  'reality.status',
  'reality.observe',
  'reality.history',
  'reality.sources',
  'reality.capabilities',
]);
assert.equal(capabilities.unknown_policy, 'unknown-remains-unknown');
const noHistory = await service.runOperation({operation: 'reality.history', admin: null, user: {}});
assert.equal(noHistory.unavailable, true);
assert.deepEqual(noHistory.events, []);

console.log('Reality Membrane service contract tests passed');
