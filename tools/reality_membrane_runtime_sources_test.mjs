#!/usr/bin/env node
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {createRequire} from 'node:module';
const require=createRequire(import.meta.url);
const runtime=require('../functions/reality_membrane_runtime');
const reality=require('../functions/reality_membrane');

const NOW=Date.parse('2026-08-13T10:30:00.000Z');
const region=runtime.regionConfig({});
assert.equal(region.id,'central_arkansas');
assert.equal(region.locationScope,'coarse_locality');
assert.equal(region.configuredBy,'bounded_owner_default');
assert.ok(!JSON.stringify({id:region.id,label:region.label,scope:region.locationScope}).includes(String(region.latitude)));

const openMeteo={
  current:{time:'2026-08-13T10:30:00.000Z',temperature_2m:77.4,apparent_temperature:79.1,precipitation:0.02,rain:0.02,relative_humidity_2m:88,wind_speed_10m:4.2,weather_code:61},
  hourly:{time:['2026-08-13T09:00:00.000Z','2026-08-13T10:00:00.000Z','2026-08-13T11:00:00.000Z'],precipitation_probability:[20,70,80]},
  daily:{sunrise:['2026-08-13T11:29:00.000Z'],sunset:['2026-08-14T00:58:00.000Z']},
};
const parsed=runtime.parseOpenMeteo(openMeteo,{nowMs:NOW,region});
assert.equal(parsed.weather.temperature_f.value,77.4);
assert.equal(parsed.weather.precipitation.value,'rain');
assert.equal(parsed.weather.precipitation_probability_pct.value,70);
assert.equal(parsed.weather.humidity_pct.value,88);
assert.equal(parsed.weather.wind_mph.value,4.2);
assert.equal(parsed.daylight.value,'dark_before_dawn');
assert.equal(parsed.weather.temperature_f.location_scope,'coarse_locality');
assert.equal(parsed.source.cost,'zero');
assert.equal(parsed.source.region_label,undefined);
assert.ok(!JSON.stringify(parsed.source).includes(region.label));
assert.ok(!JSON.stringify(parsed.source).includes(String(region.latitude)));
assert.ok(parsed.source.receipt_id.startsWith('weather_open_meteo_'));

assert.equal(runtime.weatherCodeKind(95),'thunderstorm');
assert.equal(runtime.weatherCodeKind(73),'snow');
assert.equal(runtime.weatherCodeKind(45),'fog');
assert.equal(runtime.weatherCodeKind(0),'none');

const alerts=runtime.parseNwsAlerts({features:[
  {properties:{event:'Flood Warning',severity:'Severe',urgency:'Immediate',headline:'Flooding expected',sent:'2026-08-13T10:00:00Z',expires:'2026-08-13T14:00:00Z',instruction:'private full instructions omitted'}},
  {properties:{event:'Heat Advisory',severity:'Moderate',urgency:'Expected',headline:'Heat advisory',sent:'2026-08-13T09:00:00Z',expires:'2026-08-14T01:00:00Z'}},
]});
assert.equal(alerts.active,true);
assert.equal(alerts.count,2);
assert.equal(alerts.highest_severity,'Severe');
assert.equal(alerts.events[0].event,'Flood Warning');
assert.ok(!JSON.stringify(alerts).includes('private full instructions'));
assert.deepEqual(runtime.parseNwsAlerts({features:[]}),{active:false,count:0,highest_severity:'none',events:[]});

const responses=new Map([
  [runtime.openMeteoUrl(region),openMeteo],
  [runtime.nwsAlertsUrl(region),{features:[]}],
]);
const fetchImpl=async (url,options={})=>{
  if (String(url).startsWith('https://api.weather.gov/')) {
    assert.ok(options.headers && options.headers['User-Agent']);
    assert.ok(!options.headers['User-Agent'].includes('@'));
  }
  return {ok:true,status:200,text:async()=>JSON.stringify(responses.get(String(url))),headers:options.headers || {}};
};
const environment=await runtime.fetchPublicEnvironment({nowMs:NOW,env:{},fetchImpl});
assert.equal(environment.weather.temperature_f.value,77.4);
assert.equal(environment.weather.alert.value.active,false);
assert.equal(environment.region.privacy,'PERSONAL');
assert.equal(environment.region.location_scope,'coarse_locality');
assert.ok(!JSON.stringify(environment.weather).includes(String(region.latitude)));
assert.ok(!JSON.stringify(environment.source).includes(region.label));

const failingFetch=async()=>({ok:false,status:503,text:async()=>"provider down"});
const failed=await runtime.fetchPublicEnvironment({nowMs:NOW,env:{},fetchImpl:failingFetch});
assert.equal(failed.weather.temperature_f.unavailable,true);
assert.equal(failed.daylight.unavailable,true);
assert.equal(failed.weather.alert.unavailable,true);
assert.ok(failed.unavailable.includes('weather'));
assert.ok(failed.unavailable.includes('weather.alert'));
assert.ok(!JSON.stringify(failed.source).includes(region.label));

const probe=runtime.phoneProbeCommand();
assert.match(probe,/python -c/);
assert.ok(!probe.includes('termux-location'));
assert.ok(!probe.includes('ssid'));
assert.ok(!probe.includes('microphone'));
assert.ok(!probe.includes('notification'));
assert.ok(!probe.includes('message'));

const successfulRecord={commandId:'phc_canary',status:'completed',completedAtMs:NOW,result:{ok:true,exitCode:0,stdout:'{"battery_pct":61,"charging":true,"power_source":"usb","connectivity":"wifi","audio_route":"wired_headphones","screen_state":"on"}',stderr:''}};
const phoneParsed=runtime.parsePhoneShellResult(successfulRecord,NOW);
assert.equal(phoneParsed.payload.battery_pct,61);
assert.equal(phoneParsed.payload.audio_route,'wired_headphones');
assert.equal(phoneParsed.meta.receiptId,'phone_hands:phc_canary');
assert.equal(phoneParsed.command.success,true);
const phoneObservations=reality.phoneObservations(phoneParsed.payload,phoneParsed.meta);
assert.equal(phoneObservations.battery_pct.value,61);
assert.equal(phoneObservations.battery_pct.receipt_id,'phone_hands:phc_canary');

const badRecord={commandId:'phc_bad',status:'completed',completedAtMs:NOW,result:{ok:false,exitCode:1,stdout:'',stderr:'probe failed'}};
const phoneFailed=runtime.parsePhoneShellResult(badRecord,NOW);
assert.equal(phoneFailed.payload.battery_pct,undefined);
assert.equal(phoneFailed.meta.error,'probe failed');
assert.equal(phoneFailed.command.success,false);
assert.equal(reality.phoneObservations(phoneFailed.payload,phoneFailed.meta).battery_pct.unavailable,true);

const invalidRecord={commandId:'phc_invalid',status:'completed',completedAtMs:NOW,result:{ok:true,exitCode:0,stdout:'not-json',stderr:''}};
const invalidParsed=runtime.parsePhoneShellResult(invalidRecord,NOW);
assert.equal(invalidParsed.command.success,false);
assert.equal(invalidParsed.meta.error,'phone_observation_invalid_json');

const state=runtime.projectionState({environment:{precipitation:{value:'rain',unavailable:false}},device:{charging:{value:true,unavailable:false},battery_pct:{value:61,unavailable:false},audio_route:{value:'wired_headphones',unavailable:false},connectivity:{value:'wifi',unavailable:false}},time:{daylight:{value:'dark_before_dawn',unavailable:false}}});
assert.deepEqual(state,{precipitation:'rain',charging:true,battery_pct:61,audio_route:'wired_headphones',connectivity:'wifi',daylight:'dark_before_dawn'});

const runtimeSource=fs.readFileSync(new URL('../functions/reality_membrane_runtime.js',import.meta.url),'utf8');
assert.ok(!runtimeSource.includes('dclarke1005@gmail.com'));

console.log('Reality Membrane runtime source tests passed');
