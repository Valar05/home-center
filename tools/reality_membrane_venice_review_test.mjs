#!/usr/bin/env node
import assert from 'node:assert/strict';
import {reviewRealityCanary} from './reality_membrane_venice_review.mjs';

const canary = {
  projection:{
    time:{daylight:{value:'daylight',stale:false},now:{value:'2026-08-13T06:00:00',stale:false}},
    environment:{temperature_f:{value:77,stale:false}},
    device:{battery_pct:{value:61,stale:false},charging:{value:true,stale:false},connectivity:{value:'wifi',stale:false},audio_route:null},
  },
  unavailable:['phone.audio_route'],
  speechSummary:'Reality: 6:00 AM. Daylight. 77 degrees Fahrenheit. 61 percent battery. Charging. Wifi.',
  timeBridge:{policy:'detached'},
  costPolicy:'zero-dollar-default',
  packetByteCount:9000,
  sourceReceipts:{phone:{commandId:'phc_test',status:'completed'},weather:{id:'open_meteo.public_forecast',ok:true}},
  checks:{noSensitiveLeak:true},
};
const scene = {
  layers:{OBSERVED:{},FICTIONAL_TRANSFORMATION:{derived_only_from_packet:true,scene:'Android 67 stood at April’s kitchen window. Reality remained itself.'},CANON_CONSEQUENCE:null},
  invariants:{home_center_generated_fiction:false},
};
const pass = reviewRealityCanary(canary,scene);
assert.equal(pass.verdict,'CHECKPOINT_REACHED');
assert.equal(pass.directive,'CONTINUE_REQUIRED');
assert.deepEqual(pass.failedCriteria,[]);
assert.equal(pass.jars.length,13);

const bad = reviewRealityCanary({...canary,speechSummary:'',costPolicy:'billable',packetByteCount:90000,projection:{...canary.projection,environment:{temperature_f:{value:77,stale:true}}},checks:{noSensitiveLeak:false}},
  {layers:{OBSERVED:{},FICTIONAL_TRANSFORMATION:{derived_only_from_packet:false,scene:'Drew knows every private message.'},CANON_CONSEQUENCE:{automatic:true}},invariants:{home_center_generated_fiction:true}});
assert.equal(bad.verdict,'FAIL');
assert.equal(bad.directive,'REPLAN_REQUIRED');
for (const expected of ['narrator_omniscience','privacy_leakage','api_cloud_dependence','inaccessible_controls','stale_as_current','real_people_vs_characters','telemetry_fetish','reality_fiction_boundary']) {
  assert.ok(bad.failedCriteria.includes(expected),`expected ${expected}`);
}
console.log('Venice Reality Membrane review tests passed');
