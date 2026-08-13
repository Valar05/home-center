#!/usr/bin/env node
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
const require = createRequire(import.meta.url);
const core = require('../functions/reality_membrane');
const runtime = require('../functions/reality_membrane_runtime');

const NOW = Date.parse('2026-08-13T11:00:00.000Z');
const previous = {
  receiptId:'reality_packet_previous',
  projection:{
    time:{daylight:{value:'dark_before_sunrise',observed_at:'2026-08-13T10:00:00.000Z',source:'open_meteo.public_forecast',receipt_id:'daylight_prior',stale:false}},
    environment:{
      temperature_f:{value:77,units:'F',observed_at:'2026-08-13T10:00:00.000Z',source:'open_meteo.public_forecast',receipt_id:'temp_prior',stale:false},
      feels_like_f:{value:79,units:'F',observed_at:'2026-08-13T10:00:00.000Z',source:'open_meteo.public_forecast',receipt_id:'feels_prior',stale:false},
      precipitation:{value:'rain',observed_at:'2026-08-13T10:00:00.000Z',source:'open_meteo.public_forecast',receipt_id:'rain_prior',stale:false},
      humidity_pct:{value:88,units:'%',observed_at:'2026-08-13T10:00:00.000Z',source:'open_meteo.public_forecast',receipt_id:'humidity_prior',stale:false},
      wind_mph:{value:4,units:'mph',observed_at:'2026-08-13T10:00:00.000Z',source:'open_meteo.public_forecast',receipt_id:'wind_prior',stale:false},
    },
  },
};
const reconciled = runtime.reconcilePublicWithPrevious({source:{ok:false,error:'network_error'},weather:{},daylight:null},previous,NOW,'coarse_test');
assert.equal(reconciled.source.staleFallback,true);
assert.equal(reconciled.source.fallbackPacketReceiptId,'reality_packet_previous');
assert.equal(reconciled.weather.temperature_f.value,77);
assert.equal(reconciled.weather.temperature_f.stale,true);
assert.equal(reconciled.weather.temperature_f.freshness,'stale');
assert.equal(reconciled.weather.temperature_f.observed_at,'2026-08-13T10:00:00.000Z');
assert.equal(reconciled.weather.temperature_f.receipt_id,'temp_prior');
assert.equal(reconciled.daylight.value,'dark_before_sunrise');
assert.equal(reconciled.daylight.stale,true);
assert.equal(reconciled.weather.alert.unavailable,true);
assert.equal(reconciled.weather.alert.value,null);
assert.match(reconciled.weather.alert.error,/not_replayed/);

const noPrior = runtime.reconcilePublicWithPrevious({source:{ok:false,error:'timeout'},weather:{},daylight:null},null,NOW,'coarse_test');
assert.equal(noPrior.weather.temperature_f.unavailable,true);
assert.equal(noPrior.weather.temperature_f.value,null);
assert.equal(noPrior.daylight.unavailable,true);

const time = core.timeObservations({nowMs:NOW,timeZone:'America/Chicago'});
const phone = core.phoneObservations({battery_pct:61,charging:true,connectivity:'wifi'},{nowMs:NOW,observedAt:new Date(NOW).toISOString(),source:'phone_hands:test'});
const speech = runtime.speechSummary({time,daylight:reconciled.daylight,weather:reconciled.weather,phone});
assert.doesNotMatch(speech,/77 degrees Fahrenheit/);
assert.doesNotMatch(speech,/\brain\b/);
assert.match(speech,/last observation is stale/);
assert.match(speech,/61 percent battery/);

const compact = runtime.staleObservationFromCompact('weather.temperature_f',previous.projection.environment.temperature_f,{nowMs:NOW});
assert.equal(compact.stale,true);
assert.equal(compact.capability_state,'degraded');
assert.equal(compact.value,77);
console.log('Reality Membrane stale reconciliation and accessibility tests passed');
