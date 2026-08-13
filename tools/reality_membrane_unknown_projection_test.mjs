#!/usr/bin/env node
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
const require = createRequire(import.meta.url);
const core = require('../functions/reality_membrane');
const runtime = require('../functions/reality_membrane_runtime');

const NOW = Date.parse('2026-08-13T10:30:00.000Z');
const weather = core.weatherObservations({temperature_f:null,precipitation:undefined},{nowMs:NOW,observedAt:new Date(NOW).toISOString(),source:'fixture'});
assert.equal(weather.temperature_f.value,null);
assert.equal(weather.temperature_f.unavailable,true);
assert.equal(weather.temperature_f.capability_state,'unavailable');
assert.equal(weather.temperature_f.error,'not_observed');
assert.equal(weather.precipitation.unavailable,true);

const phone = core.phoneObservations({battery_pct:null,charging:null,connectivity:null,audio_route:null},{nowMs:NOW,observedAt:new Date(NOW).toISOString(),source:'fixture'});
for (const observation of Object.values(phone)) {
  assert.equal(observation.value,null);
  assert.equal(observation.unavailable,true);
  assert.equal(observation.capability_state,'unavailable');
}

const full = core.observation({observation_type:'weather.temperature_f',value:77,units:'F',observed_at:'2026-08-13T10:29:00.000Z',source:'fixture',source_timestamp:'2026-08-13T10:28:00.000Z',max_age_ms:120000,confidence:0.9,location_scope:'coarse_test',privacy:core.PRIVACY.PUBLIC},NOW);
const projection = core.compactProjection({weather:{temperature_f:full},phone:{audio_route:phone.audio_route}});
const compact = projection.environment.temperature_f;
for (const key of ['value','units','observed_at','source','source_timestamp','age_ms','freshness','confidence','location_scope','privacy','capability_state','receipt_id','stale','unavailable','error']) assert.ok(Object.hasOwn(compact,key),`compact observation missing ${key}`);
assert.equal(projection.device.audio_route.unavailable,true);
assert.equal(projection.device.audio_route.value,null);

const time = core.timeObservations({nowMs:NOW,timeZone:'America/Chicago'});
const summary = runtime.speechSummary({time,daylight:null,weather:{},phone});
assert.match(summary,/5:30 AM/);
assert.match(summary,/audio route unavailable/);
assert.match(summary,/connectivity unavailable/);
assert.doesNotMatch(summary,/05:30/);

const capabilities = runtime.realityCapabilities();
assert.equal(capabilities.offline.last_weather_stale_reconciliation,true);
assert.equal(capabilities.offline.active_alert_replay,false);
console.log('Reality Membrane unknown/projection/accessibility tests passed');
