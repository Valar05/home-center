const crypto = require('node:crypto');

const PRIVACY = Object.freeze({PUBLIC:'PUBLIC', DEVICE:'DEVICE', PERSONAL:'PERSONAL', SENSITIVE:'SENSITIVE'});
const CAPABILITY = Object.freeze({AVAILABLE:'available', UNAVAILABLE:'unavailable', DEGRADED:'degraded'});

function iso(ms = Date.now()) { return new Date(ms).toISOString(); }
function hashReceipt(value) { return `reality_${crypto.createHash('sha256').update(JSON.stringify(value)).digest('hex').slice(0,24)}`; }
function finite(value) { const n = Number(value); return Number.isFinite(n) ? n : null; }
function ageMs(observedAt, nowMs = Date.now()) { const t = Date.parse(observedAt || ''); return Number.isFinite(t) ? Math.max(0, nowMs - t) : null; }

function observation(input = {}, nowMs = Date.now()) {
  const observedAt = input.observed_at || iso(nowMs);
  const maxAgeMs = Number.isFinite(Number(input.max_age_ms)) ? Number(input.max_age_ms) : null;
  const age = ageMs(observedAt, nowMs);
  const stale = input.stale === true || (maxAgeMs !== null && age !== null && age > maxAgeMs);
  const capabilityState = input.capability_state || CAPABILITY.AVAILABLE;
  const unavailable = capabilityState === CAPABILITY.UNAVAILABLE || input.unavailable === true;
  const error = input.error ? String(input.error).slice(0,500) : '';
  const body = {
    observation_type: String(input.observation_type || 'unknown'),
    value: unavailable ? null : (input.value === undefined ? null : input.value),
    units: input.units || null,
    observed_at: observedAt,
    source: String(input.source || 'unknown'),
    source_timestamp: input.source_timestamp || null,
    age_ms: age,
    freshness: stale ? 'stale' : 'fresh',
    confidence: input.confidence == null ? null : finite(input.confidence),
    location_scope: input.location_scope || null,
    privacy: input.privacy || PRIVACY.PUBLIC,
    capability_state: capabilityState,
    stale,
    unavailable,
    error,
  };
  body.receipt_id = input.receipt_id || hashReceipt(body);
  return body;
}

function timeObservations({nowMs = Date.now(), timeZone = 'America/Chicago'} = {}) {
  const d = new Date(nowMs);
  const parts = new Intl.DateTimeFormat('en-US', {timeZone, weekday:'long', year:'numeric', month:'2-digit', day:'2-digit', hour:'2-digit', minute:'2-digit', second:'2-digit', hour12:false, timeZoneName:'short'}).formatToParts(d);
  const map = Object.fromEntries(parts.filter(p=>p.type!=='literal').map(p=>[p.type,p.value]));
  const local = `${map.year}-${map.month}-${map.day}T${map.hour}:${map.minute}:${map.second}`;
  return {
    now: observation({observation_type:'time.local', value:local, units:null, observed_at:iso(nowMs), source:'home_center.runtime_clock', privacy:PRIVACY.PUBLIC, confidence:1}, nowMs),
    timezone: observation({observation_type:'time.timezone', value:timeZone, observed_at:iso(nowMs), source:'home_center.config', privacy:PRIVACY.PUBLIC, confidence:1}, nowMs),
    weekday: observation({observation_type:'time.weekday', value:map.weekday, observed_at:iso(nowMs), source:'home_center.runtime_clock', privacy:PRIVACY.PUBLIC, confidence:1}, nowMs),
  };
}

function daylightObservation({sunrise, sunset, nowMs = Date.now(), source='sun-provider', locationScope='coarse_locality'} = {}) {
  if (!sunrise || !sunset) return observation({observation_type:'environment.daylight', unavailable:true, capability_state:CAPABILITY.UNAVAILABLE, source, privacy:PRIVACY.PUBLIC, location_scope:locationScope, error:'sun_times_unavailable'}, nowMs);
  const now = nowMs; const rise = Date.parse(sunrise); const set = Date.parse(sunset);
  if (!Number.isFinite(rise) || !Number.isFinite(set)) return observation({observation_type:'environment.daylight', unavailable:true, capability_state:CAPABILITY.DEGRADED, source, privacy:PRIVACY.PUBLIC, location_scope:locationScope, error:'invalid_sun_times'}, nowMs);
  const value = now < rise ? 'dark_before_sunrise' : now >= set ? 'dark_after_sunset' : 'daylight';
  return observation({observation_type:'environment.daylight', value, observed_at:iso(nowMs), source, source_timestamp:iso(nowMs), privacy:PRIVACY.PUBLIC, location_scope:locationScope, confidence:1}, nowMs);
}

function weatherObservations(payload = {}, meta = {}) {
  const nowMs = meta.nowMs || Date.now(); const source = meta.source || 'weather.provider'; const observedAt = meta.observedAt || iso(nowMs); const maxAgeMs = meta.maxAgeMs == null ? 20*60*1000 : meta.maxAgeMs;
  const loc = meta.locationScope || 'coarse_locality';
  const make=(type,value,units)=>observation({observation_type:type,value,units,observed_at:observedAt,source,source_timestamp:meta.sourceTimestamp||null,max_age_ms:maxAgeMs,privacy:PRIVACY.PUBLIC,location_scope:loc,confidence:meta.confidence==null?0.9:meta.confidence},nowMs);
  if (!payload || typeof payload !== 'object') return {status:observation({observation_type:'weather.status',unavailable:true,capability_state:CAPABILITY.UNAVAILABLE,source,privacy:PRIVACY.PUBLIC,location_scope:loc,error:'weather_unavailable'},nowMs)};
  return {
    temperature_f: make('weather.temperature_f', finite(payload.temperature_f), 'F'),
    feels_like_f: make('weather.feels_like_f', finite(payload.feels_like_f), 'F'),
    precipitation: make('weather.precipitation', payload.precipitation ?? null, null),
    precipitation_probability_pct: make('weather.precipitation_probability_pct', finite(payload.precipitation_probability_pct), '%'),
    humidity_pct: make('weather.humidity_pct', finite(payload.humidity_pct), '%'),
    wind_mph: make('weather.wind_mph', finite(payload.wind_mph), 'mph'),
    alert: make('weather.alert', payload.alert ?? null, null),
  };
}

function phoneObservations(payload = {}, meta = {}) {
  const nowMs = meta.nowMs || Date.now(); const observedAt = meta.observedAt || iso(nowMs); const source = meta.source || 'phone_hands';
  const make=(type,value,units=null)=>observation({observation_type:type,value,units,observed_at:observedAt,source,max_age_ms:meta.maxAgeMs||120000,privacy:PRIVACY.DEVICE,confidence:1,capability_state:value === undefined ? CAPABILITY.UNAVAILABLE : CAPABILITY.AVAILABLE,unavailable:value === undefined},nowMs);
  return {
    battery_pct: make('phone.battery_pct', finite(payload.battery_pct), '%'),
    charging: make('phone.charging', payload.charging),
    power_source: make('phone.power_source', payload.power_source),
    connectivity: make('phone.connectivity', payload.connectivity),
    audio_route: make('phone.audio_route', payload.audio_route),
    screen_state: make('phone.screen_state', payload.screen_state),
    thermal_state: make('phone.thermal_state', payload.thermal_state),
  };
}

function safeForDefault(obs) { return obs && (obs.privacy === PRIVACY.PUBLIC || obs.privacy === PRIVACY.DEVICE); }
function compactProjection({time={}, daylight=null, weather={}, phone={}, media={}, place={}, changes=[], unavailable=[]} = {}) {
  const pick = (o) => o && safeForDefault(o) ? {value:o.value, units:o.units, observed_at:o.observed_at, stale:o.stale, source:o.source, receipt_id:o.receipt_id} : null;
  return {
    observed_at: iso(),
    time: {now:pick(time.now), timezone:pick(time.timezone), weekday:pick(time.weekday), daylight:pick(daylight)},
    environment: {temperature_f:pick(weather.temperature_f), feels_like_f:pick(weather.feels_like_f), precipitation:pick(weather.precipitation), precipitation_probability_pct:pick(weather.precipitation_probability_pct), humidity_pct:pick(weather.humidity_pct), wind_mph:pick(weather.wind_mph), alert:pick(weather.alert)},
    device: {battery_pct:pick(phone.battery_pct), charging:pick(phone.charging), power_source:pick(phone.power_source), connectivity:pick(phone.connectivity), audio_route:pick(phone.audio_route), screen_state:pick(phone.screen_state), thermal_state:pick(phone.thermal_state)},
    media, place, changes_since_checkpoint:Array.isArray(changes)?changes.slice(-20):[], unavailable:Array.isArray(unavailable)?unavailable.slice(-20):[],
  };
}

function transitionEvents(previous = {}, current = {}, observedAt = iso()) {
  const out=[]; const emit=(type,from,to)=>out.push({event_type:type,from,to,observed_at:observedAt,receipt_id:hashReceipt({type,from,to,observedAt})});
  if (previous.precipitation !== current.precipitation && current.precipitation != null) emit(current.precipitation === 'rain' ? 'rain.started' : 'weather.changed', previous.precipitation, current.precipitation);
  if (previous.charging !== current.charging && current.charging != null) emit('phone.charging', previous.charging, current.charging);
  if (previous.audio_route !== current.audio_route && current.audio_route != null) emit('audio.route_changed', previous.audio_route, current.audio_route);
  if (previous.connectivity !== current.connectivity && current.connectivity != null) emit(current.connectivity === 'offline' ? 'connectivity.offline' : 'connectivity.restored', previous.connectivity, current.connectivity);
  return out;
}

function realityCapabilities() {
  return {contract:'home-center.reality.v1', operations:['reality.status','reality.observe','reality.history','reality.sources','reality.capabilities'], optional:['reality.subscribe','reality.events'], privacy:[...Object.values(PRIVACY)], cost_policy:'zero-dollar-default', unknown_policy:'unknown-remains-unknown'};
}

module.exports={PRIVACY,CAPABILITY,observation,timeObservations,daylightObservation,weatherObservations,phoneObservations,compactProjection,transitionEvents,realityCapabilities};
