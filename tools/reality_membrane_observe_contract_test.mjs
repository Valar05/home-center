#!/usr/bin/env node
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {createRequire} from 'node:module';
const require = createRequire(import.meta.url);
const core = require('../functions/reality_membrane');
const runtime = require('../functions/reality_membrane_runtime');

assert.equal(runtime.precipitationKind({rain:0.1,snowfall:0,precipitation:0.1}),'rain');
assert.equal(runtime.precipitationKind({rain:0,snowfall:0.2,precipitation:0.2}),'snow');
assert.equal(runtime.precipitationKind({rain:0,snowfall:0,precipitation:0}),'none');
assert.equal(runtime.nearTermProbability({time:[100,3700,7300,20000],precipitation_probability:[10,40,80,99]},100),80);

const parsed = runtime.parsePhoneStdout('noise\n{"schema":"home-center.reality.phone-observation.v1","battery_pct":61,"charging":true}\n');
assert.equal(parsed.battery_pct,61);
assert.equal(parsed.charging,true);
assert.equal(runtime.parsePhoneStdout('not json'),null);

const phone = runtime.phoneObservationGroup({payload:{schema:'home-center.reality.phone-observation.v1',observed_at_unix_ms:1000,battery_pct:61,charging:true,connectivity:'wifi'},error:'',command:{commandId:'phc_test',status:'completed'}},2000);
assert.equal(phone.battery_pct.value,61);
assert.equal(phone.charging.value,true);
assert.equal(phone.connectivity.value,'wifi');
assert.equal(phone.audio_route.unavailable,true);
assert.equal(phone.audio_route.value,null);

const time = core.timeObservations({nowMs:Date.parse('2026-08-13T10:00:00Z'),timeZone:'America/Chicago'});
const weather = core.weatherObservations({temperature_f:77,precipitation:'rain'},{nowMs:Date.parse('2026-08-13T10:00:00Z'),observedAt:'2026-08-13T09:59:00Z',source:'fixture'});
const summary = runtime.speechSummary({time,daylight:core.daylightObservation({sunrise:'2026-08-13T11:00:00Z',sunset:'2026-08-14T01:00:00Z',nowMs:Date.parse('2026-08-13T10:00:00Z')}),weather,phone});
assert.ok(summary.startsWith('Reality:'));
assert.ok(summary.includes('still dark'));
assert.ok(summary.includes('77 degrees Fahrenheit'));
assert.ok(summary.includes('61 percent battery'));
assert.ok(summary.includes('charging'));

const bridge = runtime.timeBridge({sceneTime:'1918-04-02T03:00:00Z',timePolicy:'paused',lastSceneCheckpoint:'2026-08-13T09:00:00Z',elapsedWorldTimeMs:1000},time,Date.parse('2026-08-13T10:00:00Z'));
assert.equal(bridge.policy,'paused');
assert.equal(bridge.ELAPSED_REAL_TIME_MS,3600000);
assert.equal(bridge.ELAPSED_WORLD_TIME_MS,1000);
assert.match(bridge.assumption,/not silently equated/);

const sources = runtime.realitySources();
assert.ok(sources.sources.every((source)=>source.cost === 'zero' || source.cost === 'zero_only'));
assert.ok(sources.sources.filter((source)=>source.locationPrecision).every((source)=>source.locationPrecision === 'coarse_0.1_degree'));
assert.ok(sources.excludedByDefault.includes('microphone_recordings'));
assert.ok(sources.excludedByDefault.includes('precise_location_history'));
const capabilities = runtime.realityCapabilities();
assert.equal(capabilities.implemented.observe,true);
assert.equal(capabilities.implemented.subscribe,false);
assert.equal(capabilities.accessibility.speech_summary,true);

const runtimeSource = fs.readFileSync(new URL('../functions/reality_membrane_runtime.js', import.meta.url),'utf8');
assert.ok(!runtimeSource.includes('OPENAI_API_KEY'));
assert.ok(!runtimeSource.includes('CARTESIA_API_KEY'));
assert.ok(!runtimeSource.includes('microphone recording'));
assert.ok(runtimeSource.includes("fiction_generated:false"));
assert.ok(runtimeSource.includes("default:['PUBLIC','DEVICE']"));
console.log('Reality Membrane observe contract tests passed');
