'use strict';

const crypto = require('node:crypto');

const PRIVACY = Object.freeze({
  PUBLIC: 'PUBLIC',
  DEVICE: 'DEVICE',
  PERSONAL: 'PERSONAL',
  SENSITIVE: 'SENSITIVE',
});
const CAPABILITY = Object.freeze({
  AVAILABLE: 'available',
  UNAVAILABLE: 'unavailable',
  DEGRADED: 'degraded',
});
const TIME_POLICIES = Object.freeze([
  'realtime',
  'paused',
  'compressed',
  'explicitly_advanced',
  'detached',
]);

function iso(ms = Date.now()) {
  return new Date(ms).toISOString();
}

function canonicalJson(value) {
  if (value === null || typeof value === 'boolean' || typeof value === 'string') return JSON.stringify(value);
  if (typeof value === 'number' && Number.isFinite(value)) return JSON.stringify(value);
  if (Array.isArray(value)) return `[${value.map(canonicalJson).join(',')}]`;
  if (value && typeof value === 'object') {
    return `{${Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${canonicalJson(value[key])}`).join(',')}}`;
  }
  return JSON.stringify(null);
}

function hashReceipt(value) {
  const digest = crypto.createHash('sha256').update(canonicalJson(value)).digest('hex');
  return `reality_${digest.slice(0, 24)}`;
}

function finite(value) {
  const number = Number(value);
  return Number.isFinite(number) ? number : undefined;
}

function timestamp(value, fallbackMs = null) {
  if (Number.isFinite(Number(value))) return iso(Number(value));
  if (typeof value === 'string' && Number.isFinite(Date.parse(value))) return new Date(value).toISOString();
  return fallbackMs === null ? null : iso(fallbackMs);
}

function ageMs(observedAt, nowMs = Date.now()) {
  const parsed = Date.parse(observedAt || '');
  return Number.isFinite(parsed) ? Math.max(0, nowMs - parsed) : null;
}

function observation(input = {}, nowMs = Date.now()) {
  const observedAt = timestamp(input.observed_at, nowMs);
  const sourceTimestamp = timestamp(input.source_timestamp);
  const maxAgeMs = finite(input.max_age_ms);
  const age = ageMs(observedAt, nowMs);
  const stale = input.stale === true || (maxAgeMs !== undefined && age !== null && age > maxAgeMs);
  const capabilityState = input.capability_state || CAPABILITY.AVAILABLE;
  const hasValue = Object.prototype.hasOwnProperty.call(input, 'value') && input.value !== undefined;
  const unavailable = input.unavailable === true || capabilityState === CAPABILITY.UNAVAILABLE || !hasValue;
  const body = {
    observation_type: String(input.observation_type || 'unknown'),
    value: unavailable ? null : input.value,
    units: input.units || null,
    observed_at: observedAt,
    source: String(input.source || 'unknown'),
    source_timestamp: sourceTimestamp,
    age_ms: age,
    max_age_ms: maxAgeMs === undefined ? null : maxAgeMs,
    freshness: stale ? 'stale' : 'fresh',
    confidence: input.confidence === undefined ? null : (finite(input.confidence) ?? null),
    location_scope: input.location_scope || null,
    privacy: input.privacy || PRIVACY.PUBLIC,
    capability_state: capabilityState,
    stale,
    unavailable,
    error: input.error ? String(input.error).slice(0, 500) : '',
  };
  body.receipt_id = input.receipt_id || hashReceipt(body);
  return body;
}

function unavailableObservation({type, source, privacy = PRIVACY.PUBLIC, locationScope = null, error = 'not_observed'} = {}, nowMs = Date.now()) {
  return observation({
    observation_type: type,
    source,
    privacy,
    location_scope: locationScope,
    capability_state: CAPABILITY.UNAVAILABLE,
    unavailable: true,
    error,
  }, nowMs);
}

function staleObservation(existing, error, nowMs = Date.now()) {
  if (!existing || typeof existing !== 'object') return null;
  return observation({
    ...existing,
    value: existing.value,
    stale: true,
    unavailable: existing.unavailable === true,
    capability_state: existing.capability_state === CAPABILITY.UNAVAILABLE ? CAPABILITY.UNAVAILABLE : CAPABILITY.DEGRADED,
    error: error || existing.error || 'refresh_failed',
    receipt_id: existing.receipt_id,
  }, nowMs);
}

function localClockParts(nowMs, timeZone) {
  const formatter = new Intl.DateTimeFormat('en-US', {
    timeZone,
    weekday: 'long',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hourCycle: 'h23',
  });
  const map = Object.fromEntries(formatter.formatToParts(new Date(nowMs))
    .filter((part) => part.type !== 'literal')
    .map((part) => [part.type, part.value]));
  const year = Number(map.year);
  const month = Number(map.month);
  const day = Number(map.day);
  const hour = Number(map.hour);
  const minute = Number(map.minute);
  const second = Number(map.second);
  const localAsUtc = Date.UTC(year, month - 1, day, hour, minute, second);
  const roundedNow = Math.floor(nowMs / 1000) * 1000;
  const offsetMinutes = Math.round((localAsUtc - roundedNow) / 60000);
  const sign = offsetMinutes >= 0 ? '+' : '-';
  const absolute = Math.abs(offsetMinutes);
  const offset = `${sign}${String(Math.floor(absolute / 60)).padStart(2, '0')}:${String(absolute % 60).padStart(2, '0')}`;
  const localIso = `${map.year}-${map.month}-${map.day}T${map.hour}:${map.minute}:${map.second}${offset}`;
  return {map, localIso, offsetMinutes};
}

function timeObservations({nowMs = Date.now(), timeZone = 'America/Chicago'} = {}) {
  let parts;
  try {
    parts = localClockParts(nowMs, timeZone);
  } catch (error) {
    return {
      now: unavailableObservation({type: 'time.local', source: 'home_center.runtime_clock', error: `timezone_error:${error.message}`}, nowMs),
      timezone: observation({observation_type: 'time.timezone', value: timeZone, source: 'home_center.config', privacy: PRIVACY.PUBLIC, confidence: 1}, nowMs),
      date: unavailableObservation({type: 'time.date', source: 'home_center.runtime_clock', error: 'timezone_error'}, nowMs),
      weekday: unavailableObservation({type: 'time.weekday', source: 'home_center.runtime_clock', error: 'timezone_error'}, nowMs),
    };
  }
  const common = {observed_at: iso(nowMs), privacy: PRIVACY.PUBLIC, confidence: 1};
  return {
    now: observation({observation_type: 'time.local', value: parts.localIso, units: 'iso8601', source: 'home_center.runtime_clock', ...common}, nowMs),
    timezone: observation({observation_type: 'time.timezone', value: timeZone, source: 'home_center.config', ...common}, nowMs),
    date: observation({observation_type: 'time.date', value: `${parts.map.year}-${parts.map.month}-${parts.map.day}`, units: 'date', source: 'home_center.runtime_clock', ...common}, nowMs),
    weekday: observation({observation_type: 'time.weekday', value: parts.map.weekday, source: 'home_center.runtime_clock', ...common}, nowMs),
  };
}

function daylightObservation({sunrise, sunset, nowMs = Date.now(), source = 'sun-provider', locationScope = 'coarse_locality', receiptId = ''} = {}) {
  const rise = Number.isFinite(Number(sunrise)) ? Number(sunrise) : Date.parse(sunrise || '');
  const set = Number.isFinite(Number(sunset)) ? Number(sunset) : Date.parse(sunset || '');
  if (!Number.isFinite(rise) || !Number.isFinite(set)) {
    return unavailableObservation({type: 'environment.daylight', source, privacy: PRIVACY.PUBLIC, locationScope, error: 'sun_times_unavailable'}, nowMs);
  }
  const value = nowMs < rise ? 'dark_before_sunrise' : nowMs >= set ? 'dark_after_sunset' : 'daylight';
  return observation({
    observation_type: 'environment.daylight',
    value,
    observed_at: iso(nowMs),
    source,
    source_timestamp: iso(nowMs),
    privacy: PRIVACY.PUBLIC,
    location_scope: locationScope,
    confidence: 1,
    receipt_id: receiptId || undefined,
  }, nowMs);
}

function weatherObservations(payload = {}, meta = {}) {
  const nowMs = meta.nowMs || Date.now();
  const source = meta.source || 'weather.provider';
  const observedAt = timestamp(meta.observedAt, nowMs);
  const maxAgeMs = meta.maxAgeMs == null ? 20 * 60 * 1000 : Number(meta.maxAgeMs);
  const locationScope = meta.locationScope || 'coarse_locality';
  const receiptId = meta.receiptId || '';
  const common = {
    observed_at: observedAt,
    source,
    source_timestamp: meta.sourceTimestamp || observedAt,
    max_age_ms: maxAgeMs,
    privacy: PRIVACY.PUBLIC,
    location_scope: locationScope,
    confidence: meta.confidence == null ? 0.9 : meta.confidence,
    receipt_id: receiptId || undefined,
  };
  const numeric = (type, raw, units) => {
    const value = finite(raw);
    return value === undefined
      ? unavailableObservation({type, source, privacy: PRIVACY.PUBLIC, locationScope, error: 'field_unavailable'}, nowMs)
      : observation({observation_type: type, value, units, ...common}, nowMs);
  };
  const text = (type, raw) => typeof raw === 'string' && raw.trim()
    ? observation({observation_type: type, value: raw.trim(), ...common}, nowMs)
    : unavailableObservation({type, source, privacy: PRIVACY.PUBLIC, locationScope, error: 'field_unavailable'}, nowMs);
  return {
    condition: text('weather.condition', payload.condition),
    weather_code: numeric('weather.weather_code', payload.weather_code, 'wmo_code'),
    temperature_f: numeric('weather.temperature_f', payload.temperature_f, 'F'),
    feels_like_f: numeric('weather.feels_like_f', payload.feels_like_f, 'F'),
    precipitation: text('weather.precipitation', payload.precipitation),
    precipitation_inches: numeric('weather.precipitation_inches', payload.precipitation_inches, 'in'),
    precipitation_probability_pct: numeric('weather.precipitation_probability_pct', payload.precipitation_probability_pct, '%'),
    humidity_pct: numeric('weather.humidity_pct', payload.humidity_pct, '%'),
    wind_mph: numeric('weather.wind_mph', payload.wind_mph, 'mph'),
    severe_alerts: Array.isArray(payload.severe_alerts)
      ? observation({observation_type: 'weather.severe_alerts', value: payload.severe_alerts.slice(0, 8), units: 'alerts', ...common, source: meta.alertSource || source}, nowMs)
      : unavailableObservation({type: 'weather.severe_alerts', source: meta.alertSource || source, privacy: PRIVACY.PUBLIC, locationScope, error: meta.alertError || 'alerts_unavailable'}, nowMs),
  };
}

function phoneObservations(payload = {}, meta = {}) {
  const nowMs = meta.nowMs || Date.now();
  const observedAt = timestamp(meta.observedAt, nowMs);
  const source = meta.source || 'phone_hands';
  const receiptId = meta.receiptId || '';
  const common = {
    observed_at: observedAt,
    source,
    source_timestamp: meta.sourceTimestamp || observedAt,
    max_age_ms: meta.maxAgeMs || 2 * 60 * 1000,
    privacy: PRIVACY.DEVICE,
    confidence: meta.confidence == null ? 1 : meta.confidence,
    receipt_id: receiptId || undefined,
  };
  const numeric = (type, raw, units) => {
    const value = finite(raw);
    return value === undefined
      ? unavailableObservation({type, source, privacy: PRIVACY.DEVICE, error: 'field_unavailable'}, nowMs)
      : observation({observation_type: type, value, units, ...common}, nowMs);
  };
  const bool = (type, raw) => typeof raw === 'boolean'
    ? observation({observation_type: type, value: raw, ...common}, nowMs)
    : unavailableObservation({type, source, privacy: PRIVACY.DEVICE, error: 'field_unavailable'}, nowMs);
  const text = (type, raw) => typeof raw === 'string' && raw.trim()
    ? observation({observation_type: type, value: raw.trim(), ...common}, nowMs)
    : unavailableObservation({type, source, privacy: PRIVACY.DEVICE, error: 'field_unavailable'}, nowMs);
  return {
    battery_pct: numeric('phone.battery_pct', payload.battery_pct, '%'),
    charging: bool('phone.charging', payload.charging),
    power_source: text('phone.power_source', payload.power_source),
    connectivity: text('phone.connectivity', payload.connectivity),
    audio_route: text('phone.audio_route', payload.audio_route),
    screen_state: text('phone.screen_state', payload.screen_state),
    thermal_state: text('phone.thermal_state', payload.thermal_state),
  };
}

function safeForDefault(value) {
  return value && (value.privacy === PRIVACY.PUBLIC || value.privacy === PRIVACY.DEVICE);
}

function compactObservation(value) {
  if (!value || !safeForDefault(value)) return null;
  return {
    value: value.value,
    units: value.units,
    observed_at: value.observed_at,
    source: value.source,
    source_timestamp: value.source_timestamp,
    age_ms: value.age_ms,
    freshness: value.freshness,
    stale: value.stale,
    confidence: value.confidence,
    location_scope: value.location_scope,
    privacy: value.privacy,
    capability_state: value.capability_state,
    unavailable: value.unavailable,
    error: value.error,
    receipt_id: value.receipt_id,
  };
}

function compactGroup(group = {}) {
  const out = {};
  for (const [key, value] of Object.entries(group || {})) {
    const compact = compactObservation(value);
    if (compact) out[key] = compact;
  }
  return out;
}

function compactProjection({nowMs = Date.now(), time = {}, daylight = null, weather = {}, phone = {}, media = {}, place = {}, changes = [], unavailable = [], timeBridge: bridge = null} = {}) {
  const projection = {
    observed_at: iso(nowMs),
    time: {
      now: compactObservation(time.now),
      timezone: compactObservation(time.timezone),
      date: compactObservation(time.date),
      weekday: compactObservation(time.weekday),
      daylight: compactObservation(daylight),
    },
    environment: compactGroup(weather),
    device: compactGroup(phone),
    media: compactGroup(media),
    place: compactGroup(place),
    changes_since_checkpoint: Array.isArray(changes) ? changes.slice(-20) : [],
    unavailable: Array.isArray(unavailable) ? unavailable.slice(-40) : [],
  };
  if (bridge) projection.time_bridge = bridge;
  return projection;
}

function eventRecord(type, from, to, observedAt, sourceReceipts = []) {
  const body = {
    event_type: type,
    from,
    to,
    observed_at: observedAt,
    privacy: PRIVACY.DEVICE,
    source_receipts: sourceReceipts.filter(Boolean).slice(0, 8),
  };
  return {...body, receipt_id: hashReceipt(body)};
}

function transitionEvents(previous = {}, current = {}, observedAt = iso(), sourceReceipts = []) {
  const out = [];
  const changed = (key) => previous[key] !== current[key] && current[key] !== undefined && current[key] !== null;
  if (changed('precipitation')) out.push(eventRecord(current.precipitation === 'rain' ? 'rain.started' : 'weather.changed', previous.precipitation, current.precipitation, observedAt, sourceReceipts));
  if (changed('daylight') && current.daylight === 'daylight') out.push(eventRecord('sun.risen', previous.daylight, current.daylight, observedAt, sourceReceipts));
  if (changed('charging')) out.push(eventRecord(current.charging ? 'phone.charging' : 'phone.not_charging', previous.charging, current.charging, observedAt, sourceReceipts));
  if (changed('audio_route')) out.push(eventRecord('audio.route_changed', previous.audio_route, current.audio_route, observedAt, sourceReceipts));
  if (changed('connectivity')) out.push(eventRecord(current.connectivity === 'offline' ? 'connectivity.offline' : 'connectivity.restored', previous.connectivity, current.connectivity, observedAt, sourceReceipts));
  const previousBattery = finite(previous.battery_pct);
  const currentBattery = finite(current.battery_pct);
  if (currentBattery !== undefined && currentBattery <= 20 && (previousBattery === undefined || previousBattery > 20)) {
    out.push(eventRecord('phone.low_battery', previousBattery ?? null, currentBattery, observedAt, sourceReceipts));
  }
  return out;
}

function timeBridge({realNow = Date.now(), sceneTime = null, lastSceneCheckpoint = null, policy = 'detached', compressionRatio = 1} = {}) {
  const selectedPolicy = TIME_POLICIES.includes(policy) ? policy : 'detached';
  const realNowMs = Number.isFinite(Number(realNow)) ? Number(realNow) : Date.parse(realNow || '');
  const checkpoint = lastSceneCheckpoint && typeof lastSceneCheckpoint === 'object' ? lastSceneCheckpoint : {};
  const checkpointRealMs = Number.isFinite(Number(checkpoint.real_time)) ? Number(checkpoint.real_time) : Date.parse(checkpoint.real_time || '');
  const checkpointSceneMs = Number.isFinite(Number(checkpoint.scene_time)) ? Number(checkpoint.scene_time) : Date.parse(checkpoint.scene_time || '');
  const sceneMs = Number.isFinite(Number(sceneTime)) ? Number(sceneTime) : Date.parse(sceneTime || '');
  const elapsedReal = Number.isFinite(realNowMs) && Number.isFinite(checkpointRealMs) ? Math.max(0, realNowMs - checkpointRealMs) : null;
  let elapsedWorld = null;
  if (selectedPolicy === 'realtime') elapsedWorld = elapsedReal;
  else if (selectedPolicy === 'paused') elapsedWorld = 0;
  else if (selectedPolicy === 'compressed' && elapsedReal !== null) elapsedWorld = elapsedReal * Math.max(0, Number(compressionRatio) || 1);
  else if (selectedPolicy === 'explicitly_advanced' && Number.isFinite(sceneMs) && Number.isFinite(checkpointSceneMs)) elapsedWorld = sceneMs - checkpointSceneMs;
  return {
    REAL_NOW: Number.isFinite(realNowMs) ? iso(realNowMs) : null,
    SCENE_TIME: Number.isFinite(sceneMs) ? iso(sceneMs) : null,
    LAST_SCENE_CHECKPOINT: Number.isFinite(checkpointRealMs) || Number.isFinite(checkpointSceneMs) ? {
      real_time: Number.isFinite(checkpointRealMs) ? iso(checkpointRealMs) : null,
      scene_time: Number.isFinite(checkpointSceneMs) ? iso(checkpointSceneMs) : null,
    } : null,
    ELAPSED_REAL_TIME_MS: elapsedReal,
    ELAPSED_WORLD_TIME_MS: elapsedWorld,
    policy: selectedPolicy,
    compression_ratio: selectedPolicy === 'compressed' ? Math.max(0, Number(compressionRatio) || 1) : null,
  };
}

function clockSpeech(value) {
  const match = String(value || '').match(/T(\d{2}):(\d{2})/);
  if (!match) return '';
  let hour = Number(match[1]);
  const minute = match[2];
  const suffix = hour >= 12 ? 'PM' : 'AM';
  hour %= 12;
  if (hour === 0) hour = 12;
  return `${hour}:${minute} ${suffix}`;
}

function accessibilitySummary(projection = {}) {
  const pieces = [];
  const now = projection.time && projection.time.now;
  if (now && !now.unavailable) pieces.push(clockSpeech(now.value) || String(now.value));
  const daylight = projection.time && projection.time.daylight;
  if (daylight && !daylight.unavailable) {
    const labels = {dark_before_sunrise: 'Still dark', dark_after_sunset: 'Dark outside', daylight: 'Daylight'};
    pieces.push(labels[daylight.value] || String(daylight.value));
  }
  const environment = projection.environment || {};
  if (environment.temperature_f && !environment.temperature_f.unavailable) pieces.push(`${Math.round(environment.temperature_f.value)} degrees`);
  if (environment.condition && !environment.condition.unavailable) pieces.push(String(environment.condition.value));
  const device = projection.device || {};
  if (device.battery_pct && !device.battery_pct.unavailable) {
    const charging = device.charging && !device.charging.unavailable && device.charging.value === true;
    pieces.push(`Phone ${charging ? 'charging at' : 'at'} ${Math.round(device.battery_pct.value)} percent`);
  }
  if (device.audio_route && !device.audio_route.unavailable) pieces.push(`${device.audio_route.value} audio`);
  if (device.connectivity && !device.connectivity.unavailable) pieces.push(`${device.connectivity.value} connectivity`);
  return `Reality: ${pieces.length ? pieces.join('. ') : 'No fresh observations available'}.`;
}

function realityCapabilities({callableOperations = []} = {}) {
  const targetOperations = ['reality.status', 'reality.observe', 'reality.history', 'reality.sources', 'reality.capabilities'];
  return {
    contract: 'home-center.reality.v1',
    target_operations: targetOperations,
    callable_operations: callableOperations.filter((operation) => targetOperations.includes(operation)),
    optional_operations: ['reality.subscribe', 'reality.events'],
    privacy: Object.values(PRIVACY),
    cost_policy: 'zero-dollar-default',
    unknown_policy: 'unknown-remains-unknown',
    layer_policy: ['real_observation', 'derived_interpretation', 'fictional_transformation', 'inner_fortress_canon'],
    time_policies: [...TIME_POLICIES],
  };
}

module.exports = {
  PRIVACY,
  CAPABILITY,
  TIME_POLICIES,
  iso,
  canonicalJson,
  hashReceipt,
  finite,
  observation,
  unavailableObservation,
  staleObservation,
  timeObservations,
  daylightObservation,
  weatherObservations,
  phoneObservations,
  compactProjection,
  compactObservation,
  transitionEvents,
  timeBridge,
  accessibilitySummary,
  realityCapabilities,
};
