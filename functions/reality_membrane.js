const crypto = require('node:crypto');

const PRIVACY = Object.freeze({PUBLIC:'PUBLIC', DEVICE:'DEVICE', PERSONAL:'PERSONAL', SENSITIVE:'SENSITIVE'});
const CAPABILITY = Object.freeze({AVAILABLE:'available', UNAVAILABLE:'unavailable', DEGRADED:'degraded'});
const TIME_POLICIES = Object.freeze(['realtime','paused','compressed','explicitly_advanced','detached']);

function iso(ms = Date.now()) { return new Date(ms).toISOString(); }
function hashReceipt(value) { return `reality_${crypto.createHash('sha256').update(JSON.stringify(value)).digest('hex').slice(0,24)}`; }
function finite(value) { const n = Number(value); return Number.isFinite(n) ? n : null; }
function ageMs(observedAt, nowMs = Date.now()) { const t = Date.parse(observedAt || ''); return Number.isFinite(t) ? Math.max(0, nowMs - t) : null; }
function hasOwn(object, key) { return Object.prototype.hasOwnProperty.call(object || {}, key); }

function observation(input = {}, nowMs = Date.now()) {
  const observedAt = input.observed_at || iso(nowMs);
  const maxAgeMs = Number.isFinite(Number(input.max_age_ms)) ? Number(input.max_age_ms) : null;
  const age = ageMs(observedAt, nowMs);
  const stale = input.stale === true || (maxAgeMs !== null && age !== null && age > maxAgeMs);
  const valueSupplied = hasOwn(input, 'value') && input.value !== undefined;
  const unavailable = input.unavailable === true || input.capability_state === CAPABILITY.UNAVAILABLE || !valueSupplied;
  const capabilityState = unavailable ? CAPABILITY.UNAVAILABLE : (input.capability_state || CAPABILITY.AVAILABLE);
  const body = {
    observation_type: String(input.observation_type || 'unknown'),
    value: unavailable ? null : input.value,
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
    error: input.error ? String(input.error).slice(0,500) : '',
  };
  body.receipt_id = input.receipt_id || hashReceipt(body);
  return body;
}

function unavailableObservation(type, {source='unknown', privacy=PRIVACY.PUBLIC, locationScope=null, error='not_observed', nowMs=Date.now(), observedAt=null} = {}) {
  return observation({observation_type:type, unavailable:true, capability_state:CAPABILITY.UNAVAILABLE, source, privacy, location_scope:locationScope, error, observed_at:observedAt || iso(nowMs)}, nowMs);
}

function timeObservations({nowMs = Date.now(), timeZone = 'America/Chicago'} = {}) {
  const parts = new Intl.DateTimeFormat('en-US', {timeZone, weekday:'long', year:'numeric', month:'2-digit', day:'2-digit', hour:'2-digit', minute:'2-digit', second:'2-digit', hour12:false, timeZoneName:'short'}).formatToParts(new Date(nowMs));
  const map = Object.fromEntries(parts.filter((part)=>part.type !== 'literal').map((part)=>[part.type, part.value]));
  const local = `${map.year}-${map.month}-${map.day}T${map.hour}:${map.minute}:${map.second}`;
  const common = {observed_at:iso(nowMs), source:'home_center.runtime_clock', privacy:PRIVACY.PUBLIC, confidence:1};
  return {
    now: observation({...common, observation_type:'time.local', value:local}, nowMs),
    timezone: observation({...common, observation_type:'time.timezone', value:timeZone, source:'home_center.config'}, nowMs),
    date: observation({...common, observation_type:'time.date', value:`${map.year}-${map.month}-${map.day}`}, nowMs),
    weekday: observation({...common, observation_type:'time.weekday', value:map.weekday}, nowMs),
  };
}

function daylightObservation({sunrise, sunset, dawn=null, dusk=null, nowMs=Date.now(), source='sun-provider', sourceTimestamp=null, locationScope='coarse_locality'} = {}) {
  if (!sunrise || !sunset) return unavailableObservation('environment.daylight', {source, privacy:PRIVACY.PUBLIC, locationScope, error:'sun_times_unavailable', nowMs});
  const rise = Date.parse(sunrise); const set = Date.parse(sunset); const dawnMs = Date.parse(dawn || sunrise); const duskMs = Date.parse(dusk || sunset);
  if (![rise,set,dawnMs,duskMs].every(Number.isFinite)) return unavailableObservation('environment.daylight', {source, privacy:PRIVACY.PUBLIC, locationScope, error:'invalid_sun_times', nowMs});
  let value = 'daylight';
  if (nowMs < dawnMs) value = 'dark_before_dawn';
  else if (nowMs < rise) value = 'dawn';
  else if (nowMs >= duskMs) value = 'dark_after_dusk';
  else if (nowMs >= set) value = 'dusk';
  return observation({observation_type:'environment.daylight', value, observed_at:iso(nowMs), source, source_timestamp:sourceTimestamp, privacy:PRIVACY.PUBLIC, location_scope:locationScope, confidence:1}, nowMs);
}

function weatherObservations(payload = {}, meta = {}) {
  const nowMs = meta.nowMs || Date.now(); const source = meta.source || 'weather.provider'; const observedAt = meta.observedAt || iso(nowMs); const maxAgeMs = meta.maxAgeMs == null ? 20*60*1000 : meta.maxAgeMs; const loc = meta.locationScope || 'coarse_locality';
  const make = (type, value, units, available = value !== undefined && value !== null) => available
    ? observation({observation_type:type, value, units, observed_at:observedAt, source, source_timestamp:meta.sourceTimestamp || null, max_age_ms:maxAgeMs, privacy:PRIVACY.PUBLIC, location_scope:loc, confidence:meta.confidence == null ? 0.9 : meta.confidence, receipt_id:meta.receiptId || undefined}, nowMs)
    : unavailableObservation(type, {source, privacy:PRIVACY.PUBLIC, locationScope:loc, error:meta.error || 'not_observed', nowMs, observedAt});
  if (!payload || typeof payload !== 'object') return {status:unavailableObservation('weather.status', {source, privacy:PRIVACY.PUBLIC, locationScope:loc, error:meta.error || 'weather_unavailable', nowMs})};
  const numberValue = (key) => hasOwn(payload,key) && finite(payload[key]) !== null ? finite(payload[key]) : undefined;
  return {
    temperature_f: make('weather.temperature_f', numberValue('temperature_f'), 'F'),
    feels_like_f: make('weather.feels_like_f', numberValue('feels_like_f'), 'F'),
    precipitation: make('weather.precipitation', hasOwn(payload,'precipitation') ? payload.precipitation : undefined, null),
    precipitation_probability_pct: make('weather.precipitation_probability_pct', numberValue('precipitation_probability_pct'), '%'),
    humidity_pct: make('weather.humidity_pct', numberValue('humidity_pct'), '%'),
    wind_mph: make('weather.wind_mph', numberValue('wind_mph'), 'mph'),
    alert: make('weather.alert', hasOwn(payload,'alert') ? payload.alert : undefined, null),
  };
}

function phoneObservations(payload = {}, meta = {}) {
  const nowMs = meta.nowMs || Date.now(); const observedAt = meta.observedAt || iso(nowMs); const source = meta.source || 'phone_hands';
  const make = (type, key, units=null, transform=(value)=>value) => {
    if (!hasOwn(payload,key) || payload[key] === undefined || payload[key] === null) return unavailableObservation(type, {source, privacy:PRIVACY.DEVICE, error:meta.error || 'not_observed', nowMs, observedAt});
    const transformed = transform(payload[key]);
    if (transformed === undefined || transformed === null || (typeof transformed === 'number' && !Number.isFinite(transformed))) return unavailableObservation(type, {source, privacy:PRIVACY.DEVICE, error:meta.error || 'invalid_observation', nowMs, observedAt});
    return observation({observation_type:type, value:transformed, units, observed_at:observedAt, source, source_timestamp:meta.sourceTimestamp || null, max_age_ms:meta.maxAgeMs || 120000, privacy:PRIVACY.DEVICE, confidence:meta.confidence == null ? 1 : meta.confidence, receipt_id:meta.receiptId || undefined}, nowMs);
  };
  return {
    battery_pct: make('phone.battery_pct','battery_pct','%',finite),
    charging: make('phone.charging','charging'),
    power_source: make('phone.power_source','power_source'),
    connectivity: make('phone.connectivity','connectivity'),
    audio_route: make('phone.audio_route','audio_route'),
    screen_state: make('phone.screen_state','screen_state'),
    thermal_state: make('phone.thermal_state','thermal_state'),
  };
}

function safeForDefault(obs) { return obs && (obs.privacy === PRIVACY.PUBLIC || obs.privacy === PRIVACY.DEVICE); }
function compactObservation(obs) {
  if (!obs || !safeForDefault(obs)) return null;
  return {
    value:obs.value, units:obs.units, observed_at:obs.observed_at, source_timestamp:obs.source_timestamp,
    age_ms:obs.age_ms, freshness:obs.freshness, confidence:obs.confidence, location_scope:obs.location_scope,
    privacy:obs.privacy, capability_state:obs.capability_state, receipt_id:obs.receipt_id,
    stale:obs.stale, unavailable:obs.unavailable, error:obs.error, source:obs.source,
  };
}
function compactGroup(group={}) { const out={}; for (const [key,value] of Object.entries(group || {})) { const compact=compactObservation(value); if (compact) out[key]=compact; } return out; }
function compactProjection({observedAt=null,time={},daylight=null,weather={},phone={},media={},place={},changes=[],unavailable=[]} = {}) {
  return {
    observed_at: observedAt || iso(),
    time:{now:compactObservation(time.now),timezone:compactObservation(time.timezone),date:compactObservation(time.date),weekday:compactObservation(time.weekday),daylight:compactObservation(daylight)},
    environment:{temperature_f:compactObservation(weather.temperature_f),feels_like_f:compactObservation(weather.feels_like_f),precipitation:compactObservation(weather.precipitation),precipitation_probability_pct:compactObservation(weather.precipitation_probability_pct),humidity_pct:compactObservation(weather.humidity_pct),wind_mph:compactObservation(weather.wind_mph),alert:compactObservation(weather.alert)},
    device:{battery_pct:compactObservation(phone.battery_pct),charging:compactObservation(phone.charging),power_source:compactObservation(phone.power_source),connectivity:compactObservation(phone.connectivity),audio_route:compactObservation(phone.audio_route),screen_state:compactObservation(phone.screen_state),thermal_state:compactObservation(phone.thermal_state)},
    media:compactGroup(media), place:compactGroup(place), changes_since_checkpoint:Array.isArray(changes)?changes.slice(-20):[], unavailable:Array.isArray(unavailable)?unavailable.slice(-20):[],
  };
}

function transitionEvents(previous={}, current={}, observedAt=iso()) {
  const out=[]; const emit=(type,from,to)=>out.push({event_type:type,from,to,observed_at:observedAt,receipt_id:hashReceipt({type,from,to,observedAt})});
  if (previous.precipitation !== current.precipitation && current.precipitation != null) emit(current.precipitation === 'rain' ? 'rain.started' : 'weather.changed', previous.precipitation, current.precipitation);
  if (previous.charging !== current.charging && current.charging != null) emit('phone.charging',previous.charging,current.charging);
  if (previous.battery_pct !== current.battery_pct && Number(current.battery_pct) <= 15 && Number(previous.battery_pct) > 15) emit('phone.low_battery',previous.battery_pct,current.battery_pct);
  if (previous.audio_route !== current.audio_route && current.audio_route != null) emit('audio.route_changed',previous.audio_route,current.audio_route);
  if (previous.connectivity !== current.connectivity && current.connectivity != null) emit(current.connectivity === 'offline' ? 'connectivity.offline' : 'connectivity.restored',previous.connectivity,current.connectivity);
  if (previous.daylight !== current.daylight && current.daylight === 'daylight') emit('sun.risen',previous.daylight,current.daylight);
  return out;
}

function timeBridge({realNow, sceneTime=null, lastSceneCheckpoint=null, policy='detached', worldRate=1} = {}) {
  if (!TIME_POLICIES.includes(policy)) throw new Error(`Unsupported Inner Fortress time policy: ${policy}`);
  const realMs = Date.parse(realNow || ''); const sceneMs = Date.parse(sceneTime || ''); const checkpointMs = Date.parse(lastSceneCheckpoint || '');
  const elapsedRealMs = Number.isFinite(realMs) && Number.isFinite(checkpointMs) ? Math.max(0,realMs-checkpointMs) : null;
  let elapsedWorldMs = null;
  if (policy === 'realtime') elapsedWorldMs = elapsedRealMs;
  else if (policy === 'paused') elapsedWorldMs = 0;
  else if (policy === 'compressed' && elapsedRealMs !== null) elapsedWorldMs = Math.round(elapsedRealMs * Math.max(0,Number(worldRate) || 1));
  else if (policy === 'explicitly_advanced' && Number.isFinite(sceneMs) && Number.isFinite(checkpointMs)) elapsedWorldMs = Math.max(0,sceneMs-checkpointMs);
  return {REAL_NOW:realNow || null,SCENE_TIME:sceneTime || null,LAST_SCENE_CHECKPOINT:lastSceneCheckpoint || null,ELAPSED_REAL_TIME_MS:elapsedRealMs,ELAPSED_WORLD_TIME_MS:elapsedWorldMs,POLICY:policy,WORLD_RATE:policy === 'compressed' ? Math.max(0,Number(worldRate) || 1) : null};
}

function speechSummary(projection = {}) {
  const parts=['Reality:']; const value=(slot)=>slot && !slot.unavailable && !slot.stale ? slot.value : null;
  const time=value(projection.time && projection.time.now); if (time) parts.push(String(time).replace('T',' ')+'.');
  const daylight=value(projection.time && projection.time.daylight); if (daylight) parts.push(String(daylight).replaceAll('_',' ')+'.');
  const temp=value(projection.environment && projection.environment.temperature_f); if (temp !== null) parts.push(`${Math.round(Number(temp))} degrees.`);
  const precipitation=value(projection.environment && projection.environment.precipitation); if (precipitation && precipitation !== 'none') parts.push(`${precipitation}.`);
  const battery=value(projection.device && projection.device.battery_pct); const charging=value(projection.device && projection.device.charging);
  if (battery !== null) parts.push(`Phone ${charging ? 'charging at' : 'at'} ${Math.round(Number(battery))} percent.`);
  const route=value(projection.device && projection.device.audio_route); if (route) parts.push(`${String(route).replaceAll('_',' ')} connected.`);
  const connectivity=value(projection.device && projection.device.connectivity); if (connectivity) parts.push(`${connectivity}.`);
  return parts.join(' ').replace(/\s+/g,' ').trim();
}

function realityCapabilities() {
  return {contract:'home-center.reality.v1',operations:['reality.status','reality.observe','reality.history','reality.sources','reality.capabilities'],optional:['reality.subscribe','reality.events'],privacy:Object.values(PRIVACY),timePolicies:[...TIME_POLICIES],cost_policy:'zero-dollar-default',unknown_policy:'unknown-remains-unknown',fiction_policy:'observations_only_no_narrative_generation'};
}

module.exports={PRIVACY,CAPABILITY,TIME_POLICIES,observation,unavailableObservation,timeObservations,daylightObservation,weatherObservations,phoneObservations,compactObservation,compactProjection,transitionEvents,timeBridge,speechSummary,realityCapabilities};
