#!/usr/bin/env node
import assert from 'node:assert/strict';
import {buildCanaryScene} from './inner_fortress_reality_canary_scene.mjs';

const receipt = {
  packetReceiptId:'reality_packet_fixture',
  observedAt:'2026-08-13T10:30:00.000Z',
  projection:{
    time:{
      now:{value:'2026-08-13T05:30:00',observed_at:'2026-08-13T10:30:00.000Z',source:'home_center.runtime_clock',receipt_id:'time_receipt',stale:false},
      daylight:{value:'dark_before_sunrise',observed_at:'2026-08-13T10:30:00.000Z',source:'open_meteo.public_forecast',receipt_id:'daylight_receipt',stale:false},
    },
    environment:{
      temperature_f:{value:77,units:'F',observed_at:'2026-08-13T10:29:00.000Z',source:'open_meteo.public_forecast',receipt_id:'temp_receipt',stale:false},
      precipitation:{value:'rain',observed_at:'2026-08-13T10:29:00.000Z',source:'open_meteo.public_forecast',receipt_id:'rain_receipt',stale:false},
    },
    device:{
      battery_pct:{value:61,units:'%',observed_at:'2026-08-13T10:30:00.000Z',source:'phone_hands:fixture',receipt_id:'battery_receipt',stale:false},
      charging:{value:true,observed_at:'2026-08-13T10:30:00.000Z',source:'phone_hands:fixture',receipt_id:'charging_receipt',stale:false},
      connectivity:{value:'wifi',observed_at:'2026-08-13T10:30:00.000Z',source:'phone_hands:fixture',receipt_id:'connectivity_receipt',stale:false},
    },
  },
  unavailable:['phone.audio_route'],
  sourceReceipts:{phone:{commandId:'phc_fixture',status:'completed'},weather:{id:'open_meteo.public_forecast',ok:true}},
};
const output = buildCanaryScene(receipt);
assert.equal(output.layers.OBSERVED.packet_receipt_id,'reality_packet_fixture');
assert.equal(output.layers.FICTIONAL_TRANSFORMATION.layer,'FICTIONAL_TRANSFORMATION');
assert.equal(output.layers.FICTIONAL_TRANSFORMATION.derived_only_from_packet,true);
assert.match(output.layers.FICTIONAL_TRANSFORMATION.scene,/At 5:30 AM/);
assert.match(output.layers.FICTIONAL_TRANSFORMATION.scene,/77 degrees Fahrenheit/);
assert.match(output.layers.FICTIONAL_TRANSFORMATION.scene,/rain/);
assert.match(output.layers.FICTIONAL_TRANSFORMATION.scene,/61 percent/);
assert.match(output.layers.FICTIONAL_TRANSFORMATION.scene,/audio route unknown/);
assert.equal(output.layers.CANON_CONSEQUENCE,null);
assert.equal(output.invariants.home_center_generated_fiction,false);
assert.equal(output.invariants.fiction_wrote_reality,false);
assert.equal(output.invariants.canon_automatic,false);
assert.ok(output.receipt_sha256.length===64);

const unknown = buildCanaryScene({packetReceiptId:'unknowns',observedAt:'2026-08-13T10:30:00Z',projection:{time:{},environment:{},device:{}},unavailable:['phone.battery_pct','phone.charging','phone.connectivity','phone.audio_route'],sourceReceipts:{}});
assert.match(unknown.layers.FICTIONAL_TRANSFORMATION.scene,/weather source remained honestly unavailable/);
assert.match(unknown.layers.FICTIONAL_TRANSFORMATION.scene,/battery unobserved/);
assert.doesNotMatch(unknown.layers.FICTIONAL_TRANSFORMATION.scene,/\b\d{2,3} degrees Fahrenheit\b/);
assert.equal(unknown.layers.CANON_CONSEQUENCE,null);
console.log('Inner Fortress Reality Membrane canary scene tests passed');
