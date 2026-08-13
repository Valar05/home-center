#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';

const root = path.resolve(path.dirname(new URL(import.meta.url).pathname), '..');
const corePath = path.join(root, 'functions', 'reality_membrane.js');
const runtimePath = path.join(root, 'functions', 'reality_membrane_runtime.js');
let core = fs.readFileSync(corePath, 'utf8');
let runtime = fs.readFileSync(runtimePath, 'utf8');

const weatherMakeOld = `  const make=(type,value,units)=>observation({observation_type:type,value,units,observed_at:observedAt,source,source_timestamp:meta.sourceTimestamp||null,max_age_ms:maxAgeMs,privacy:PRIVACY.PUBLIC,location_scope:loc,confidence:meta.confidence==null?0.9:meta.confidence},nowMs);\n`;
const weatherMakeNew = `  const make=(type,value,units)=>{const missing=value===undefined||value===null;return observation({observation_type:type,value:missing?undefined:value,units,observed_at:observedAt,source,source_timestamp:meta.sourceTimestamp||null,max_age_ms:maxAgeMs,privacy:PRIVACY.PUBLIC,location_scope:loc,confidence:missing?null:(meta.confidence==null?0.9:meta.confidence),capability_state:missing?CAPABILITY.UNAVAILABLE:CAPABILITY.AVAILABLE,unavailable:missing,error:missing?'not_observed':''},nowMs);};\n`;
if (core.includes(weatherMakeOld)) core = core.replace(weatherMakeOld, weatherMakeNew);
else if (!core.includes("error:missing?'not_observed':''")) throw new Error('weather unknown-semantics anchor not found');

const phoneMakeOld = `  const make=(type,value,units=null)=>observation({observation_type:type,value,units,observed_at:observedAt,source,max_age_ms:meta.maxAgeMs||120000,privacy:PRIVACY.DEVICE,confidence:1,capability_state:value===undefined?CAPABILITY.UNAVAILABLE:CAPABILITY.AVAILABLE,unavailable:value===undefined},nowMs);\n`;
const phoneMakeNew = `  const make=(type,value,units=null)=>{const missing=value===undefined||value===null;return observation({observation_type:type,value:missing?undefined:value,units,observed_at:observedAt,source,max_age_ms:meta.maxAgeMs||120000,privacy:PRIVACY.DEVICE,confidence:missing?null:1,capability_state:missing?CAPABILITY.UNAVAILABLE:CAPABILITY.AVAILABLE,unavailable:missing,error:missing?'not_observed':''},nowMs);};\n`;
if (core.includes(phoneMakeOld)) core = core.replace(phoneMakeOld, phoneMakeNew);
else if (!core.includes("confidence:missing?null:1")) throw new Error('phone unknown-semantics anchor not found');

const compactOld = `function compactObservation(obs){return obs&&safeForDefault(obs)?{value:obs.value,units:obs.units,observed_at:obs.observed_at,stale:obs.stale,source:obs.source,receipt_id:obs.receipt_id}:null;}\n`;
const compactNew = `function compactObservation(obs){return obs&&safeForDefault(obs)?{value:obs.value,units:obs.units,observed_at:obs.observed_at,source:obs.source,source_timestamp:obs.source_timestamp,age_ms:obs.age_ms,freshness:obs.freshness,confidence:obs.confidence,location_scope:obs.location_scope,privacy:obs.privacy,capability_state:obs.capability_state,receipt_id:obs.receipt_id,stale:obs.stale,unavailable:obs.unavailable,error:obs.error}:null;}\n`;
if (core.includes(compactOld)) core = core.replace(compactOld, compactNew);
else if (!core.includes('source_timestamp:obs.source_timestamp')) throw new Error('compact observation anchor not found');

const speechAnchor = `function speechSummary({time, daylight, weather, phone}) {\n`;
const speechClock = `function speechClock(value) {\n  const match = safeText(value,100).match(/T(\\d{2}):(\\d{2})/);\n  if (!match) return safeText(value,100);\n  const hour24 = Number(match[1]);\n  const hour12 = hour24 % 12 || 12;\n  return \\`${'${hour12}'}:${'${match[2]}'} ${'${hour24 >= 12 ? \'PM\' : \'AM\'}'}\\`;\n}\n\n`;
if (!runtime.includes('function speechClock(')) {
  if (!runtime.includes(speechAnchor)) throw new Error('speech clock anchor not found');
  runtime = runtime.replace(speechAnchor, speechClock + speechAnchor);
}

const localOld = `  if (local) {\n    const match = String(local).match(/T(\\d{2}):(\\d{2})/);\n    parts.push(match ? \\`${'${match[1]}'}:${'${match[2]}'}\\` : String(local));\n  }\n`;
const localNew = `  if (local) parts.push(speechClock(local));\n`;
if (runtime.includes(localOld)) runtime = runtime.replace(localOld, localNew);
else if (!runtime.includes('if (local) parts.push(speechClock(local));')) throw new Error('speech local-time anchor not found');

const routeOld = `  const route = phone && phone.audio_route && phone.audio_route.value;\n  if (route) parts.push(\\`${'${String(route).replace(/_/g,\' \')}'} audio\\`);\n  const connectivity = phone && phone.connectivity && phone.connectivity.value;\n  if (connectivity) parts.push(String(connectivity).replace(/_/g,' '));\n`;
const routeNew = `  const routeObservation = phone && phone.audio_route;\n  const route = routeObservation && routeObservation.stale !== true ? routeObservation.value : null;\n  if (route) parts.push(\\`${'${String(route).replace(/_/g,\' \')}'} audio\\`);\n  else if (routeObservation && routeObservation.unavailable) parts.push('audio route unavailable');\n  const connectivityObservation = phone && phone.connectivity;\n  const connectivity = connectivityObservation && connectivityObservation.stale !== true ? connectivityObservation.value : null;\n  if (connectivity) parts.push(String(connectivity).replace(/_/g,' '));\n  else if (connectivityObservation && connectivityObservation.unavailable) parts.push('connectivity unavailable');\n`;
if (runtime.includes(routeOld)) runtime = runtime.replace(routeOld, routeNew);
else if (!runtime.includes("parts.push('audio route unavailable')")) throw new Error('speech route/connectivity anchor not found');

const offlineOld = `offline:{local_time:true,phone_when_relay_available:true,last_weather_stale_reconciliation:'history_available_live_cache_pending'},`;
const offlineNew = `offline:{local_time:true,phone_when_relay_available:true,last_weather_stale_reconciliation:true,active_alert_replay:false},`;
if (runtime.includes(offlineOld)) runtime = runtime.replace(offlineOld, offlineNew);

fs.writeFileSync(corePath, core);
fs.writeFileSync(runtimePath, runtime);
console.log('Reality Membrane unknown semantics, compact provenance, and spoken-time patch applied');
