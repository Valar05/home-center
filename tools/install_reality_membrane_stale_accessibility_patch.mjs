#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';

const root = path.resolve(path.dirname(new URL(import.meta.url).pathname), '..');
const target = path.join(root, 'functions', 'reality_membrane_runtime.js');
let source = fs.readFileSync(target, 'utf8');

const helperAnchor = `function observationUnavailableList(groups = {}) {\n`;
const helpers = `function staleObservationFromCompact(type, compact, {privacy = membrane.PRIVACY.PUBLIC, locationScope = DEFAULT_LOCATION.scope, error = 'source_unavailable_last_known', nowMs = Date.now()} = {}) {\n  const prior = compact && typeof compact === 'object' ? compact : null;\n  if (!prior || prior.value === null || prior.value === undefined || !prior.observed_at) {\n    return unavailableObservation(type,{source:prior && prior.source || 'last_known',privacy,locationScope,error,nowMs});\n  }\n  return membrane.observation({\n    observation_type:type, value:prior.value, units:prior.units || null, observed_at:prior.observed_at,\n    source:prior.source || 'last_known', source_timestamp:null, privacy, location_scope:locationScope,\n    confidence:null, stale:true, capability_state:membrane.CAPABILITY.DEGRADED,\n    receipt_id:prior.receipt_id || undefined, error,\n  }, nowMs);\n}\n\nfunction reconcilePublicWithPrevious(publicResult = {}, previousSnapshot = null, nowMs = Date.now(), locationScope = DEFAULT_LOCATION.scope) {\n  if (publicResult && publicResult.source && publicResult.source.ok === true) return publicResult;\n  const snapshot = previousSnapshot && typeof previousSnapshot === 'object' ? previousSnapshot : {};\n  const projection = snapshot.projection && typeof snapshot.projection === 'object' ? snapshot.projection : {};\n  const environment = projection.environment && typeof projection.environment === 'object' ? projection.environment : {};\n  const time = projection.time && typeof projection.time === 'object' ? projection.time : {};\n  const error = safeText(publicResult && publicResult.source && publicResult.source.error, 200) || 'network_source_unavailable';\n  const weather = {\n    temperature_f:staleObservationFromCompact('weather.temperature_f',environment.temperature_f,{locationScope,error,nowMs}),\n    feels_like_f:staleObservationFromCompact('weather.feels_like_f',environment.feels_like_f,{locationScope,error,nowMs}),\n    precipitation:staleObservationFromCompact('weather.precipitation',environment.precipitation,{locationScope,error,nowMs}),\n    precipitation_probability_pct:staleObservationFromCompact('weather.precipitation_probability_pct',environment.precipitation_probability_pct,{locationScope,error,nowMs}),\n    humidity_pct:staleObservationFromCompact('weather.humidity_pct',environment.humidity_pct,{locationScope,error,nowMs}),\n    wind_mph:staleObservationFromCompact('weather.wind_mph',environment.wind_mph,{locationScope,error,nowMs}),\n    alert:unavailableObservation('weather.alert',{source:'weather_gov.active_alerts',locationScope,error:'active_alerts_unavailable_not_replayed',nowMs}),\n  };\n  const daylight = staleObservationFromCompact('environment.daylight',time.daylight,{locationScope,error,nowMs});\n  return {\n    ...publicResult, weather, daylight,\n    source:{...(publicResult && publicResult.source || {}),ok:false,staleFallback:true,fallbackPacketReceiptId:safeText(snapshot.receiptId,200),error},\n  };\n}\n\nasync function latestRealitySnapshot(admin, user) {\n  const root = admin.firestore().collection('realityUsers').doc(realityUserKey(user));\n  const latest = await root.collection('state').doc('latest').get();\n  if (!latest.exists) return null;\n  const state = latest.data() || {};\n  if (!state.packetReceiptId) return null;\n  const snapshot = await root.collection('snapshots').doc(state.packetReceiptId).get();\n  return snapshot.exists ? snapshot.data() || null : null;\n}\n\n`;
if (!source.includes('function staleObservationFromCompact(')) {
  if (!source.includes(helperAnchor)) throw new Error('stale reconciliation helper anchor not found');
  source = source.replace(helperAnchor, helpers + helperAnchor);
}

const valueTextOld = `function valueText(observation, suffix = '') {\n  if (!observation || observation.unavailable || observation.value === null || observation.value === undefined) return '';\n`;
const valueTextNew = `function valueText(observation, suffix = '') {\n  if (!observation || observation.unavailable || observation.stale === true || observation.value === null || observation.value === undefined) return '';\n`;
if (source.includes(valueTextOld)) source = source.replace(valueTextOld, valueTextNew);

const daylightOld = `  if (daylight && daylight.value) {\n`;
const daylightNew = `  if (daylight && daylight.value && daylight.stale !== true) {\n`;
if (source.includes(daylightOld)) source = source.replace(daylightOld, daylightNew);

const precipitationOld = `  const precipitation = weather && weather.precipitation && weather.precipitation.value;\n  if (precipitation && precipitation !== 'none') parts.push(String(precipitation));\n`;
const precipitationNew = `  const precipitationObservation = weather && weather.precipitation;\n  const precipitation = precipitationObservation && precipitationObservation.stale !== true ? precipitationObservation.value : null;\n  if (precipitation && precipitation !== 'none') parts.push(String(precipitation));\n  if (weather && Object.values(weather).some((observation) => observation && observation.stale === true)) parts.push('weather source unavailable; last observation is stale');\n`;
if (source.includes(precipitationOld)) source = source.replace(precipitationOld, precipitationNew);

const snapshotOld = `  batch.set(root.collection('snapshots').doc(packet.receipt_id),{\n    receiptId:packet.receipt_id, observedAtMs:nowMs, observedAt:packet.observed_at,\n    projection:packet.projection, unavailable:packet.unavailable, sourceReceipts:packet.source_receipts,\n  },{merge:false});\n`;
const snapshotNew = `  batch.set(root.collection('snapshots').doc(packet.receipt_id),{\n    receiptId:packet.receipt_id, observedAtMs:nowMs, observedAt:packet.observed_at,\n    projection:packet.projection, unavailable:packet.unavailable, sourceReceipts:packet.source_receipts,\n    speechSummary:packet.speech_summary, timeBridge:packet.time_bridge, privacyPolicy:packet.privacy_policy,\n    costPolicy:packet.cost_policy, fictionGenerated:packet.fiction_generated, packetByteCount:Buffer.byteLength(JSON.stringify(packet),'utf8'),\n  },{merge:false});\n`;
if (!source.includes('speechSummary:packet.speech_summary')) {
  if (!source.includes(snapshotOld)) throw new Error('snapshot persistence anchor not found');
  source = source.replace(snapshotOld, snapshotNew);
}

const observeOld = `  const time = include.has('time') ? membrane.timeObservations({nowMs,timeZone}) : {};\n  const weatherPromise = include.has('weather') || include.has('daylight') ? publicWeather({nowMs,timeZone,location}) : Promise.resolve({weather:{},daylight:null,source:null});\n`;
const observeNew = `  const time = include.has('time') ? membrane.timeObservations({nowMs,timeZone}) : {};\n  const previousSnapshotPromise = latestRealitySnapshot(admin,user).catch(() => null);\n  const weatherPromise = include.has('weather') || include.has('daylight') ? publicWeather({nowMs,timeZone,location}) : Promise.resolve({weather:{},daylight:null,source:null});\n`;
if (source.includes(observeOld)) source = source.replace(observeOld, observeNew);

const awaitOld = `  const [publicResult, phoneResult] = await Promise.all([weatherPromise, phonePromise]);\n  const weather = include.has('weather') ? publicResult.weather : {};\n  const daylight = include.has('daylight') ? publicResult.daylight : null;\n`;
const awaitNew = `  const [publicResultRaw, phoneResult, previousSnapshot] = await Promise.all([weatherPromise, phonePromise, previousSnapshotPromise]);\n  const publicResult = reconcilePublicWithPrevious(publicResultRaw,previousSnapshot,nowMs,location.scope);\n  const weather = include.has('weather') ? publicResult.weather : {};\n  const daylight = include.has('daylight') ? publicResult.daylight : null;\n`;
if (!source.includes('publicResultRaw, phoneResult, previousSnapshot')) {
  if (!source.includes(awaitOld)) throw new Error('observe reconciliation anchor not found');
  source = source.replace(awaitOld, awaitNew);
}

const exportOld = `  nearTermProbability,\n  parsePhoneStdout,\n`;
const exportNew = `  nearTermProbability,\n  staleObservationFromCompact,\n  reconcilePublicWithPrevious,\n  parsePhoneStdout,\n`;
if (source.includes(exportOld)) source = source.replace(exportOld, exportNew);

fs.writeFileSync(target, source);
console.log('Reality Membrane stale reconciliation and durable accessibility snapshot patch applied');
