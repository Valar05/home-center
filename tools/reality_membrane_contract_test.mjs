#!/usr/bin/env node
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
const require = createRequire(import.meta.url);
const r = require('../functions/reality_membrane');

const NOW = Date.parse('2026-08-13T09:30:00.000Z');

const t = r.timeObservations({nowMs:NOW,timeZone:'America/Chicago'});
assert.equal(t.now.observation_type,'time.local');
assert.equal(t.timezone.value,'America/Chicago');
assert.equal(t.now.stale,false);
assert.ok(t.now.receipt_id.startsWith('reality_'));

const fresh = r.observation({observation_type:'weather.temperature_f',value:78,units:'F',observed_at:'2026-08-13T09:20:00.000Z',source:'test',max_age_ms:20*60*1000},NOW);
assert.equal(fresh.stale,false);
assert.equal(fresh.age_ms,10*60*1000);
const stale = r.observation({observation_type:'weather.temperature_f',value:78,units:'F',observed_at:'2026-08-13T08:00:00.000Z',source:'test',max_age_ms:20*60*1000},NOW);
assert.equal(stale.stale,true);
assert.equal(stale.freshness,'stale');

const unknown = r.observation({observation_type:'phone.audio_route',unavailable:true,capability_state:r.CAPABILITY.UNAVAILABLE,source:'phone_hands',privacy:r.PRIVACY.DEVICE,error:'not_observed'},NOW);
assert.equal(unknown.value,null);
assert.equal(unknown.unavailable,true);
assert.equal(unknown.capability_state,'unavailable');

const weather = r.weatherObservations({temperature_f:78,feels_like_f:80,precipitation:'rain',precipitation_probability_pct:70,humidity_pct:84,wind_mph:4},{nowMs:NOW,observedAt:'2026-08-13T09:25:00.000Z',source:'fixture.free_weather'});
assert.equal(weather.temperature_f.value,78);
assert.equal(weather.temperature_f.privacy,'PUBLIC');

const phone = r.phoneObservations({battery_pct:61,charging:true,connectivity:'wifi',audio_route:'headphones'},{nowMs:NOW,observedAt:'2026-08-13T09:29:30.000Z',source:'fixture.phone_hands'});
const projection = r.compactProjection({time:t,weather,phone,unavailable:['environment.daylight']});
assert.equal(projection.device.battery_pct.value,61);
assert.equal(projection.environment.precipitation.value,'rain');
assert.equal(projection.unavailable[0],'environment.daylight');
assert.ok(!JSON.stringify(projection).includes('calendar title'));

const sensitive = r.observation({observation_type:'calendar.description',value:'private',privacy:r.PRIVACY.SENSITIVE,source:'calendar'},NOW);
const projection2 = r.compactProjection({media:{forbidden:sensitive}});
assert.equal(projection2.media.forbidden.privacy,'SENSITIVE'); // caller-owned opaque extension is not auto-flattened
assert.equal(r.compactProjection({time:{now:sensitive}}).time.now,null); // default membrane slots fail closed

const events = r.transitionEvents({precipitation:'none',charging:false,audio_route:'speaker',connectivity:'wifi'},{precipitation:'rain',charging:true,audio_route:'headphones',connectivity:'offline'},'2026-08-13T09:30:00.000Z');
assert.deepEqual(events.map(e=>e.event_type),['rain.started','phone.charging','audio.route_changed','connectivity.offline']);

const dark = r.daylightObservation({sunrise:'2026-08-13T11:30:00.000Z',sunset:'2026-08-14T01:00:00.000Z',nowMs:NOW});
assert.equal(dark.value,'dark_before_sunrise');
const noSun = r.daylightObservation({nowMs:NOW});
assert.equal(noSun.unavailable,true);

const caps = r.realityCapabilities();
assert.equal(caps.unknown_policy,'unknown-remains-unknown');
assert.equal(caps.cost_policy,'zero-dollar-default');
assert.ok(caps.operations.includes('reality.observe'));

console.log('Reality Membrane contract tests passed');
