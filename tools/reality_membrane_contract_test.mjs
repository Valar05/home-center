#!/usr/bin/env node
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
const require = createRequire(import.meta.url);
const r = require('../functions/reality_membrane');

const NOW = Date.parse('2026-08-13T09:30:00.000Z');
const OBSERVED = '2026-08-13T09:30:00.000Z';

const t = r.timeObservations({nowMs:NOW,timeZone:'America/Chicago'});
assert.equal(t.now.observation_type,'time.local');
assert.equal(t.timezone.value,'America/Chicago');
assert.equal(t.date.value,'2026-08-13');
assert.equal(t.weekday.value,'Thursday');
assert.equal(t.now.stale,false);
assert.ok(t.now.receipt_id.startsWith('reality_'));

const fresh = r.observation({observation_type:'weather.temperature_f',value:78,units:'F',observed_at:'2026-08-13T09:20:00.000Z',source:'test',max_age_ms:20*60*1000},NOW);
assert.equal(fresh.stale,false);
assert.equal(fresh.age_ms,10*60*1000);
const stale = r.observation({observation_type:'weather.temperature_f',value:78,units:'F',observed_at:'2026-08-13T08:00:00.000Z',source:'test',max_age_ms:20*60*1000},NOW);
assert.equal(stale.stale,true);
assert.equal(stale.freshness,'stale');

const implicitUnknown = r.observation({observation_type:'phone.audio_route',source:'phone_hands',privacy:r.PRIVACY.DEVICE},NOW);
assert.equal(implicitUnknown.value,null);
assert.equal(implicitUnknown.unavailable,true);
assert.equal(implicitUnknown.capability_state,'unavailable');
const explicitUnknown = r.unavailableObservation('weather.wind_mph',{source:'weather',nowMs:NOW});
assert.equal(explicitUnknown.value,null);
assert.equal(explicitUnknown.error,'not_observed');

const weather = r.weatherObservations({temperature_f:78,feels_like_f:80,precipitation:'rain',precipitation_probability_pct:70,humidity_pct:84,wind_mph:4,alert:'none'},{nowMs:NOW,observedAt:'2026-08-13T09:25:00.000Z',source:'fixture.free_weather',sourceTimestamp:'2026-08-13T09:25:00.000Z'});
assert.equal(weather.temperature_f.value,78);
assert.equal(weather.temperature_f.privacy,'PUBLIC');
assert.equal(weather.temperature_f.source_timestamp,'2026-08-13T09:25:00.000Z');
const partialWeather = r.weatherObservations({temperature_f:78},{nowMs:NOW,source:'fixture.partial'});
assert.equal(partialWeather.wind_mph.unavailable,true);
assert.equal(partialWeather.wind_mph.value,null);

const phone = r.phoneObservations({battery_pct:61,charging:true,connectivity:'wifi',audio_route:'headphones'},{nowMs:NOW,observedAt:'2026-08-13T09:29:30.000Z',source:'fixture.phone_hands',receiptId:'phone_hands:canary'});
assert.equal(phone.battery_pct.value,61);
assert.equal(phone.battery_pct.receipt_id,'phone_hands:canary');
const partialPhone = r.phoneObservations({battery_pct:61},{nowMs:NOW});
assert.equal(partialPhone.audio_route.unavailable,true);

const dark = r.daylightObservation({sunrise:'2026-08-13T11:30:00.000Z',sunset:'2026-08-14T01:00:00.000Z',dawn:'2026-08-13T11:00:00.000Z',dusk:'2026-08-14T01:30:00.000Z',nowMs:NOW});
assert.equal(dark.value,'dark_before_dawn');
assert.equal(r.daylightObservation({nowMs:NOW}).unavailable,true);

const projection = r.compactProjection({observedAt:OBSERVED,time:t,daylight:dark,weather,phone,unavailable:['calendar','place']});
assert.equal(projection.observed_at,OBSERVED);
assert.equal(projection.device.battery_pct.value,61);
assert.equal(projection.environment.precipitation.value,'rain');
assert.equal(projection.environment.temperature_f.privacy,'PUBLIC');
assert.equal(projection.device.battery_pct.privacy,'DEVICE');
assert.equal(projection.unavailable[0],'calendar');
assert.ok(projection.environment.temperature_f.receipt_id);
assert.ok(projection.environment.temperature_f.freshness);

const sensitive = r.observation({observation_type:'calendar.description',value:'private',privacy:r.PRIVACY.SENSITIVE,source:'calendar'},NOW);
const projection2 = r.compactProjection({observedAt:OBSERVED,media:{forbidden:sensitive},place:{also_forbidden:sensitive},time:{now:sensitive}});
assert.equal(projection2.media.forbidden,undefined);
assert.equal(projection2.place.also_forbidden,undefined);
assert.equal(projection2.time.now,null);
assert.ok(!JSON.stringify(projection2).includes('private'));

const events = r.transitionEvents({precipitation:'none',charging:false,battery_pct:16,audio_route:'speaker',connectivity:'wifi',daylight:'dawn'},{precipitation:'rain',charging:true,battery_pct:15,audio_route:'headphones',connectivity:'offline',daylight:'daylight'},OBSERVED);
assert.deepEqual(events.map((event)=>event.event_type),['rain.started','phone.charging','phone.low_battery','audio.route_changed','connectivity.offline','sun.risen']);
assert.ok(events.every((event)=>event.receipt_id.startsWith('reality_')));

const realNow='2026-08-13T09:30:00.000Z';
const checkpoint='2026-08-13T08:30:00.000Z';
assert.equal(r.timeBridge({realNow,lastSceneCheckpoint:checkpoint,policy:'realtime'}).ELAPSED_WORLD_TIME_MS,3600000);
assert.equal(r.timeBridge({realNow,lastSceneCheckpoint:checkpoint,policy:'paused'}).ELAPSED_WORLD_TIME_MS,0);
assert.equal(r.timeBridge({realNow,lastSceneCheckpoint:checkpoint,policy:'compressed',worldRate:4}).ELAPSED_WORLD_TIME_MS,14400000);
assert.equal(r.timeBridge({realNow,sceneTime:'2026-08-13T10:30:00.000Z',lastSceneCheckpoint:checkpoint,policy:'explicitly_advanced'}).ELAPSED_WORLD_TIME_MS,7200000);
assert.equal(r.timeBridge({realNow,lastSceneCheckpoint:checkpoint,policy:'detached'}).ELAPSED_WORLD_TIME_MS,null);
assert.throws(()=>r.timeBridge({policy:'omniscient'}),/Unsupported/);

const spoken = r.speechSummary(projection);
assert.match(spoken,/Reality:/);
assert.match(spoken,/78 degrees/);
assert.match(spoken,/Phone charging at 61 percent/);
assert.match(spoken,/headphones connected/);
assert.ok(!spoken.includes('private'));

const caps = r.realityCapabilities();
assert.equal(caps.unknown_policy,'unknown-remains-unknown');
assert.equal(caps.cost_policy,'zero-dollar-default');
assert.equal(caps.fiction_policy,'observations_only_no_narrative_generation');
assert.ok(caps.operations.includes('reality.observe'));
assert.ok(caps.timePolicies.includes('detached'));

console.log('Reality Membrane contract tests passed');
