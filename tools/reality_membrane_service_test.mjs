#!/usr/bin/env node
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
const require=createRequire(import.meta.url);
const service=require('../functions/reality_membrane_service');
const runtime=require('../functions/reality_membrane_runtime');

const NOW=Date.parse('2026-08-13T10:30:00.000Z');
const USER={email:'owner@example.com'};
const openMeteo={current:{time:'2026-08-13T10:30:00.000Z',temperature_2m:77,apparent_temperature:79,precipitation:0.01,rain:0.01,relative_humidity_2m:86,wind_speed_10m:5,weather_code:61},hourly:{time:['2026-08-13T10:00:00.000Z'],precipitation_probability:[70]},daily:{sunrise:['2026-08-13T11:29:00.000Z'],sunset:['2026-08-14T00:58:00.000Z']}};
const region=runtime.regionConfig({});
const responses=new Map([[runtime.openMeteoUrl(region),openMeteo],[runtime.nwsAlertsUrl(region),{features:[]}]]);
const fetchImpl=async (url)=>({ok:true,status:200,text:async()=>JSON.stringify(responses.get(String(url)))});
const phoneCommandRunner=async ({commandId,command,ttlMs})=>{
  assert.ok(commandId.startsWith('phc_reality_'));
  assert.match(command,/python -c/);
  assert.equal(ttlMs,45000);
  return {commandId,status:'completed',completedAtMs:NOW,result:{ok:true,exitCode:0,stdout:'{"battery_pct":61,"charging":true,"power_source":"usb","connectivity":"wifi","audio_route":"wired_headphones","screen_state":"on"}',stderr:''}};
};

const observed=await service.observe({user:USER,phoneCommandRunner,fetchImpl,env:{},args:{nowMs:NOW}});
assert.equal(observed.contract,'home-center.reality.v1');
assert.equal(observed.observed_at,'2026-08-13T10:30:00.000Z');
assert.equal(observed.projection.environment.temperature_f.value,77);
assert.equal(observed.projection.environment.precipitation.value,'rain');
assert.equal(observed.projection.time.daylight.value,'dark_before_dawn');
assert.equal(observed.projection.device.battery_pct.value,61);
assert.equal(observed.projection.device.audio_route.value,'wired_headphones');
assert.equal(observed.sources.phone.state,'available');
assert.equal(observed.provenance.phone_command.terminal,true);
assert.equal(observed.privacy_policy.default.join(','),'PUBLIC,DEVICE');
assert.equal(observed.cost_policy,'zero-dollar-default');
assert.equal(observed.fiction_generated,false);
assert.match(observed.speech_summary,/Reality:/);
assert.match(observed.speech_summary,/77 degrees/);
assert.match(observed.speech_summary,/Phone charging at 61 percent/);
assert.ok(!JSON.stringify(observed.projection).includes('owner@example.com'));
assert.ok(!JSON.stringify(observed.projection).includes(String(region.latitude)));
assert.equal(observed.persistence.persisted,false);

const withoutPhone=await service.observe({user:USER,fetchImpl,env:{},args:{nowMs:NOW,includePhone:false}});
assert.equal(withoutPhone.projection.device.battery_pct.unavailable,true);
assert.ok(withoutPhone.projection.unavailable.includes('device.battery_pct'));
assert.equal(withoutPhone.sources.phone.state,'unavailable');

const previous={environment:{temperature_f:{value:75,units:'F',observed_at:'2026-08-13T09:00:00.000Z',source_timestamp:'2026-08-13T09:00:00.000Z',age_ms:0,freshness:'fresh',confidence:0.9,location_scope:'coarse_locality',privacy:'PUBLIC',capability_state:'available',receipt_id:'weather_old',stale:false,unavailable:false,error:'',source:'old-weather'}},device:{battery_pct:{value:50,units:'%',observed_at:'2026-08-13T09:00:00.000Z',source_timestamp:null,age_ms:0,freshness:'fresh',confidence:1,location_scope:null,privacy:'DEVICE',capability_state:'available',receipt_id:'phone_old',stale:false,unavailable:false,error:'',source:'phone_hands'}}};
const current={environment:{temperature_f:{value:null,unavailable:true,stale:false,source:'new-weather'}},device:{battery_pct:{value:null,unavailable:true,stale:false,source:'phone_hands'}}};
const fallback=service.applyStaleFallback(current,previous,NOW,{environmentError:'weather failed',deviceError:'phone failed'});
assert.equal(fallback.environment.temperature_f.value,75);
assert.equal(fallback.environment.temperature_f.stale,true);
assert.equal(fallback.environment.temperature_f.freshness,'stale');
assert.equal(fallback.environment.temperature_f.capability_state,'degraded');
assert.equal(fallback.environment.temperature_f.error,'weather failed');
assert.equal(fallback.device.battery_pct.value,50);
assert.equal(fallback.device.battery_pct.error,'phone failed');
assert.deepEqual(service.unavailableList(fallback),['environment.temperature_f:stale','device.battery_pct:stale']);

assert.match(service.ownerId(USER),/^owner_[0-9a-f]{32}$/);
assert.notEqual(service.ownerId(USER),USER.email);
assert.throws(()=>service.ownerId({}),/authenticated Home Center owner/);

const sourceCatalog=service.sources();
assert.equal(sourceCatalog.contract,'home-center.reality.v1');
assert.ok(sourceCatalog.sources.some((source)=>source.id==='phone_hands.phone_shell'));
assert.ok(sourceCatalog.excluded_by_default.includes('precise_location'));
assert.ok(sourceCatalog.excluded_by_default.includes('microphone_recording'));
assert.ok(sourceCatalog.excluded_by_default.includes('calendar.details'));

const status=await service.status({user:USER});
assert.equal(status.callable,true);
assert.equal(status.accepted,false);
assert.equal(status.has_current_projection,false);
const history=await service.history({user:USER,args:{limit:500,windowHours:500}});
assert.equal(history.count,0);
assert.equal(history.window_hours,72);
assert.equal(history.persisted,false);

console.log('Reality Membrane observe/history service tests passed');
