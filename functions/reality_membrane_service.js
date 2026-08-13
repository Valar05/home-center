'use strict';

const crypto = require('node:crypto');
const core = require('./reality_membrane');

const CONTRACT = 'home-center.reality.v1';
const RETENTION_MS = 72 * 60 * 60 * 1000;
const CALLABLE_OPERATIONS = Object.freeze([
  'reality.status',
  'reality.observe',
  'reality.history',
  'reality.sources',
  'reality.capabilities',
]);

function safeText(value, max = 1000) {
  const text = value == null ? '' : String(value).trim();
  return text.length > max ? text.slice(0, max) : text;
}

function safeObject(value) {
  return value && typeof value === 'object' && !Array.isArray(value) ? value : {};
}

function safeNumber(value, fallback = null) {
  const number = Number(value);
  return Number.isFinite(number) ? number : fallback;
}

function clamp(value, minimum, maximum, fallback) {
  const number = safeNumber(value, fallback);
  return Math.max(minimum, Math.min(maximum, number));
}

function sha(value) {
  return crypto.createHash('sha256').update(String(value || '')).digest('hex');
}

function ownerKey(user = {}) {
  const identity = safeText(user.email || user.uid || 'unknown', 320).toLowerCase();
  return `owner_${sha(identity).slice(0, 32)}`;
}

function ownerRoot(admin, user) {
  return admin.firestore().collection('realityOwners').doc(ownerKey(user));
}

function operationEntries() {
  return {
    'reality.status': {
      summary: 'Return bounded Reality Membrane operation/source state and the latest observation age without creating fiction.',
      write: false,
      requiredScopes: [],
      input: {},
    },
    'reality.observe': {
      summary: 'Return one compact provenance-bearing reality packet for Inner Fortress. Time is local; weather uses a caller-supplied coarse location; phone state uses bounded Phone Hands observation. Unknown stays unknown.',
      write: false,
      requiredScopes: [],
      input: {
        requestId: 'stable optional observation request id',
        timeZone: 'IANA timezone; default America/Chicago',
        location: 'optional {latitude, longitude, label}; coordinates are rounded to 0.1 degree and never returned',
        includeWeather: 'optional boolean default true',
        includePhone: 'optional boolean default true',
        phoneTimeoutMs: 'optional 1000-12000',
        scene: 'optional explicit Inner Fortress time bridge state',
      },
    },
    'reality.history': {
      summary: 'Return bounded transition/event history, not high-frequency telemetry.',
      write: false,
      requiredScopes: [],
      input: {sinceMs: 'optional epoch millis within retention', limit: 'optional 1-50'},
    },
    'reality.sources': {
      summary: 'List Reality Membrane source classes, privacy, cost, network dependence, and latest source state.',
      write: false,
      requiredScopes: [],
      input: {},
    },
    'reality.capabilities': {
      summary: 'Return target versus actually callable Reality Membrane operations and governing policy.',
      write: false,
      requiredScopes: [],
      input: {},
    },
  };
}

function coarseLocation(args = {}) {
  const location = safeObject(args.location);
  const latitude = safeNumber(location.latitude ?? args.latitude);
  const longitude = safeNumber(location.longitude ?? args.longitude);
  if (latitude === null || longitude === null || latitude < -90 || latitude > 90 || longitude < -180 || longitude > 180) {
    return {configured: false, scope: 'coarse_0.1_degree', label: '', error: 'coarse_location_required'};
  }
  const roundedLatitude = Math.round(latitude * 10) / 10;
  const roundedLongitude = Math.round(longitude * 10) / 10;
  return {
    configured: true,
    latitude: roundedLatitude,
    longitude: roundedLongitude,
    label: safeText(location.label || args.locationLabel || 'coarse_locality', 120),
    scope: 'coarse_0.1_degree',
  };
}

function weatherCodeLabel(value) {
  const code = Number(value);
  if (code === 0) return 'Clear';
  if ([1, 2].includes(code)) return 'Partly cloudy';
  if (code === 3) return 'Overcast';
  if ([45, 48].includes(code)) return 'Fog';
  if ([51, 53, 55, 56, 57].includes(code)) return 'Drizzle';
  if ([61, 63, 65, 66, 67].includes(code)) return 'Rain';
  if ([71, 73, 75, 77].includes(code)) return 'Snow';
  if ([80, 81, 82].includes(code)) return 'Rain showers';
  if ([85, 86].includes(code)) return 'Snow showers';
  if ([95, 96, 99].includes(code)) return 'Thunderstorm';
  return Number.isFinite(code) ? `Weather code ${code}` : '';
}

function precipitationKind(current = {}) {
  if (safeNumber(current.snowfall, 0) > 0) return 'snow';
  if (safeNumber(current.rain, 0) > 0) return 'rain';
  if (safeNumber(current.showers, 0) > 0) return 'showers';
  if (safeNumber(current.precipitation, 0) > 0) return 'mixed_precipitation';
  return 'none';
}

function nearestHourlyProbability(hourly = {}, currentEpochSeconds = 0) {
  const times = Array.isArray(hourly.time) ? hourly.time : [];
  const values = Array.isArray(hourly.precipitation_probability) ? hourly.precipitation_probability : [];
  if (!times.length || !values.length) return undefined;
  let bestIndex = -1;
  let bestDistance = Infinity;
  times.forEach((time, index) => {
    const numeric = Number(time);
    if (!Number.isFinite(numeric)) return;
    const distance = numeric >= currentEpochSeconds ? numeric - currentEpochSeconds : (currentEpochSeconds - numeric) + 3600;
    if (distance < bestDistance) {
      bestDistance = distance;
      bestIndex = index;
    }
  });
  return bestIndex >= 0 ? values[bestIndex] : undefined;
}

async function fetchJson(url, {fetchImpl = global.fetch, timeoutMs = 8000, headers = {}} = {}) {
  if (typeof fetchImpl !== 'function') throw new Error('fetch_unavailable');
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetchImpl(url, {headers, signal: controller.signal});
    const text = await response.text();
    let json = null;
    try {
      json = text ? JSON.parse(text) : {};
    } catch (_) {
      throw new Error(`provider_non_json_${response.status}`);
    }
    if (!response.ok) throw new Error(`provider_http_${response.status}:${safeText(json && (json.reason || json.detail || json.title), 180)}`);
    return json;
  } finally {
    clearTimeout(timer);
  }
}

function openMeteoUrl(location) {
  const params = new URLSearchParams({
    latitude: String(location.latitude),
    longitude: String(location.longitude),
    current: 'temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,rain,showers,snowfall,weather_code,wind_speed_10m,is_day',
    hourly: 'precipitation_probability',
    daily: 'sunrise,sunset',
    temperature_unit: 'fahrenheit',
    wind_speed_unit: 'mph',
    precipitation_unit: 'inch',
    timezone: 'auto',
    timeformat: 'unixtime',
    forecast_days: '1',
  });
  return `https://api.open-meteo.com/v1/forecast?${params.toString()}`;
}

function nwsAlertsUrl(location) {
  const params = new URLSearchParams({
    point: `${location.latitude},${location.longitude}`,
    status: 'actual',
    message_type: 'alert',
  });
  return `https://api.weather.gov/alerts/active?${params.toString()}`;
}

function parseAlerts(payload = {}) {
  const features = Array.isArray(payload.features) ? payload.features : [];
  return features.slice(0, 8).map((feature) => {
    const properties = safeObject(feature && feature.properties);
    return {
      id: safeText(feature && feature.id, 500),
      event: safeText(properties.event, 160),
      severity: safeText(properties.severity, 80),
      certainty: safeText(properties.certainty, 80),
      urgency: safeText(properties.urgency, 80),
      onset: safeText(properties.onset, 80),
      expires: safeText(properties.expires, 80),
      sender: safeText(properties.senderName, 200),
    };
  });
}

async function fetchWeatherBundle(location, {fetchImpl = global.fetch, nowMs = Date.now()} = {}) {
  if (!location.configured) return {ok: false, error: location.error, location};
  const weather = await fetchJson(openMeteoUrl(location), {fetchImpl, timeoutMs: 8000});
  const current = safeObject(weather.current);
  const currentEpochSeconds = safeNumber(current.time, Math.floor(nowMs / 1000));
  let alerts = null;
  let alertError = '';
  try {
    const alertPayload = await fetchJson(nwsAlertsUrl(location), {
      fetchImpl,
      timeoutMs: 6000,
      headers: {
        Accept: 'application/geo+json',
        'User-Agent': 'HomeCenter-RealityMembrane/1.0 (dclarke1005@gmail.com)',
      },
    });
    alerts = parseAlerts(alertPayload);
  } catch (error) {
    alertError = safeText(error.message || error, 300);
  }
  const daily = safeObject(weather.daily);
  const sunriseSeconds = Array.isArray(daily.sunrise) ? safeNumber(daily.sunrise[0]) : null;
  const sunsetSeconds = Array.isArray(daily.sunset) ? safeNumber(daily.sunset[0]) : null;
  const payload = {
    condition: weatherCodeLabel(current.weather_code),
    weather_code: current.weather_code,
    temperature_f: current.temperature_2m,
    feels_like_f: current.apparent_temperature,
    precipitation: precipitationKind(current),
    precipitation_inches: current.precipitation,
    precipitation_probability_pct: nearestHourlyProbability(safeObject(weather.hourly), currentEpochSeconds),
    humidity_pct: current.relative_humidity_2m,
    wind_mph: current.wind_speed_10m,
    severe_alerts: alerts,
  };
  const receiptSeed = {
    provider: 'open-meteo',
    sourceTimestamp: currentEpochSeconds,
    locationScope: location.scope,
    locationLabel: location.label,
    payload,
  };
  return {
    ok: true,
    payload,
    observedAtMs: currentEpochSeconds * 1000,
    sourceTimestampMs: currentEpochSeconds * 1000,
    sunriseMs: sunriseSeconds === null ? null : sunriseSeconds * 1000,
    sunsetMs: sunsetSeconds === null ? null : sunsetSeconds * 1000,
    timeZone: safeText(weather.timezone, 120),
    location,
    alertError,
    receiptId: core.hashReceipt(receiptSeed),
    attribution: ['Open-Meteo forecast API (CC BY 4.0)', 'National Weather Service alerts (US Government open data)'],
  };
}

function boolText(value) {
  return String(value || '').toLowerCase() === 'true';
}

function normalizePhoneReceipt(command = {}, nowMs = Date.now()) {
  const result = safeObject(command.result);
  if (command.status !== 'completed' || result.ok === false) {
    return {ok: false, error: safeText(command.error || result.stderr || 'phone_observe_failed', 500), commandId: safeText(command.commandId, 180)};
  }
  const battery = safeObject(result.battery);
  const status = safeNumber(battery.status);
  const powered = ['AC powered', 'USB powered', 'Wireless powered'].some((key) => boolText(battery[key]));
  let powerSource = '';
  if (boolText(battery['Wireless powered'])) powerSource = 'wireless';
  else if (boolText(battery['AC powered'])) powerSource = 'ac';
  else if (boolText(battery['USB powered'])) powerSource = 'usb';
  else if (powered) powerSource = 'external';
  else if (status !== null) powerSource = 'battery';
  const observedAtMs = safeNumber(result.timestamp, nowMs / 1000) * 1000;
  return {
    ok: true,
    commandId: safeText(command.commandId, 180),
    observedAtMs,
    payload: {
      battery_pct: safeNumber(battery.level),
      charging: status === null ? undefined : ([2, 5].includes(status) || powered),
      power_source: powerSource || undefined,
      connectivity: safeText(result.connectivity, 80) || 'home_center_relay_online',
      audio_route: safeText(result.audio_route, 80) || undefined,
      screen_state: safeText(result.screen_state, 80) || undefined,
      thermal_state: safeText(result.thermal_state, 80) || undefined,
    },
  };
}

function unwrapCommandCenter(value) {
  if (value && value.result && value.operation && value.toolName) return value.result;
  return value;
}

async function observePhone({callCommandCenter, requestId, timeoutMs = 8000, now = () => Date.now(), sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms))} = {}) {
  if (typeof callCommandCenter !== 'function') return {ok: false, error: 'phone_hands_bridge_unavailable'};
  const stable = safeText(requestId, 140) || `observe-${now()}`;
  const commandId = `reality_${sha(stable).slice(0, 28)}`;
  const enqueue = unwrapCommandCenter(await callCommandCenter('phone_hands.enqueue', {
    idempotencyKey: `reality-observe:${stable}`,
    commandId,
    deviceId: 'primary-phone',
    ttlMs: Math.max(30000, timeoutMs + 10000),
    action: {action: 'observe', ui: false, screen: false},
  }));
  const acceptedId = safeText(enqueue && enqueue.commandId, 180) || commandId;
  const deadline = now() + timeoutMs;
  let command = enqueue;
  while (now() < deadline) {
    command = unwrapCommandCenter(await callCommandCenter('phone_hands.get', {commandId: acceptedId}));
    if (command && ['completed', 'failed'].includes(command.status)) return normalizePhoneReceipt(command, now());
    await sleep(400);
  }
  return {ok: false, error: 'phone_observe_timeout', commandId: acceptedId};
}

function staleGroup(group, error, nowMs) {
  const out = {};
  for (const [key, value] of Object.entries(safeObject(group))) {
    const stale = core.staleObservation(value, error, nowMs);
    if (stale) out[key] = stale;
  }
  return out;
}

function groupValues(group = {}) {
  const out = {};
  for (const [key, value] of Object.entries(group || {})) {
    if (value && value.unavailable !== true) out[key] = value.value;
  }
  return out;
}

function collectUnavailable(groups = {}) {
  const out = [];
  for (const group of Object.values(groups)) {
    for (const value of Object.values(safeObject(group))) {
      if (value && value.unavailable === true) out.push(value.observation_type);
    }
  }
  return Array.from(new Set(out)).slice(0, 40);
}

async function readLatest(admin, user) {
  if (!admin || typeof admin.firestore !== 'function') return null;
  const snapshot = await ownerRoot(admin, user).collection('state').doc('latest').get();
  return snapshot.exists ? snapshot.data() : null;
}

async function persistObservation(admin, user, packet) {
  if (!admin || typeof admin.firestore !== 'function') return;
  const root = ownerRoot(admin, user);
  await root.collection('state').doc('latest').set({
    contract: CONTRACT,
    observedAtMs: Date.parse(packet.observed_at),
    observed_at: packet.observed_at,
    observations: packet.observations,
    projection: packet.projection,
    summary: packet.summary,
    source_states: packet.source_states,
    updatedAtMs: Date.now(),
  }, {merge: false});
  for (const event of packet.events.slice(0, 20)) {
    await root.collection('events').doc(event.receipt_id).set({...event, observedAtMs: Date.parse(event.observed_at)}, {merge: true});
  }
}

function sourceCatalog(latest = null) {
  const states = safeObject(latest && latest.source_states);
  return [
    {id: 'home_center.runtime_clock', privacy: 'PUBLIC', network: 'none', cost: 'zero', reliability: 'high', state: states.time || 'available'},
    {id: 'open-meteo.forecast', privacy: 'PUBLIC', network: 'required', cost: 'zero_only', reliability: 'medium_high', state: states.weather || 'location_required', attribution: 'CC BY 4.0'},
    {id: 'weather.gov.alerts', privacy: 'PUBLIC', network: 'required', cost: 'zero', reliability: 'high_when_available', state: states.alerts || 'location_required'},
    {id: 'command_center.phone_hands', privacy: 'DEVICE', network: 'home_center_relay', cost: 'zero', reliability: 'high', state: states.phone || 'not_observed'},
    {id: 'firestore.reality_events', privacy: 'DEVICE', network: 'home_center', cost: 'existing_infrastructure', reliability: 'high', state: 'available'},
  ];
}

async function runObserve({admin, user, args = {}, callCommandCenter, fetchImpl = global.fetch, now = () => Date.now(), sleep} = {}) {
  const nowMs = now();
  const timeZone = safeText(args.timeZone || 'America/Chicago', 120);
  const location = coarseLocation(args);
  const previous = await readLatest(admin, user);
  const previousObservations = safeObject(previous && previous.observations);
  const time = core.timeObservations({nowMs, timeZone});
  let weather = {};
  let daylight = null;
  let weatherResult = null;
  const sourceStates = {time: 'available', weather: 'not_requested', alerts: 'not_requested', phone: 'not_requested'};

  if (args.includeWeather !== false) {
    try {
      weatherResult = await fetchWeatherBundle(location, {fetchImpl, nowMs});
      if (!weatherResult.ok) throw new Error(weatherResult.error || 'weather_unavailable');
      weather = core.weatherObservations(weatherResult.payload, {
        nowMs,
        observedAt: weatherResult.observedAtMs,
        sourceTimestamp: weatherResult.sourceTimestampMs,
        source: 'open-meteo.forecast',
        alertSource: 'weather.gov.alerts',
        alertError: weatherResult.alertError,
        locationScope: location.scope,
        receiptId: weatherResult.receiptId,
      });
      daylight = core.daylightObservation({
        sunrise: weatherResult.sunriseMs,
        sunset: weatherResult.sunsetMs,
        nowMs,
        source: 'open-meteo.forecast',
        locationScope: location.scope,
        receiptId: weatherResult.receiptId,
      });
      sourceStates.weather = 'fresh';
      sourceStates.alerts = weatherResult.alertError ? 'degraded' : 'fresh';
    } catch (error) {
      weather = staleGroup(previousObservations.weather, `weather_refresh_failed:${safeText(error.message || error, 180)}`, nowMs);
      daylight = core.staleObservation(previousObservations.daylight, `daylight_refresh_failed:${safeText(error.message || error, 180)}`, nowMs);
      if (!Object.keys(weather).length) weather = core.weatherObservations({}, {nowMs, source: 'open-meteo.forecast', locationScope: location.scope, alertError: safeText(error.message || error, 180)});
      if (!daylight) daylight = core.daylightObservation({nowMs, source: 'open-meteo.forecast', locationScope: location.scope});
      sourceStates.weather = location.configured ? 'unavailable' : 'location_required';
      sourceStates.alerts = sourceStates.weather;
    }
  }

  let phone = {};
  let phoneResult = null;
  if (args.includePhone !== false) {
    try {
      phoneResult = await observePhone({
        callCommandCenter,
        requestId: safeText(args.requestId, 140) || `reality-${nowMs}`,
        timeoutMs: clamp(args.phoneTimeoutMs, 1000, 12000, 8000),
        now,
        sleep,
      });
      if (!phoneResult.ok) throw new Error(phoneResult.error || 'phone_unavailable');
      phone = core.phoneObservations(phoneResult.payload, {
        nowMs,
        observedAt: phoneResult.observedAtMs,
        source: 'command_center.phone_hands',
        receiptId: phoneResult.commandId,
      });
      sourceStates.phone = 'fresh';
    } catch (error) {
      phone = staleGroup(previousObservations.phone, `phone_refresh_failed:${safeText(error.message || error, 180)}`, nowMs);
      if (!Object.keys(phone).length) phone = core.phoneObservations({}, {nowMs, source: 'command_center.phone_hands'});
      sourceStates.phone = 'unavailable';
    }
  }

  const currentValues = {
    ...groupValues(weather),
    ...groupValues(phone),
    daylight: daylight && daylight.unavailable !== true ? daylight.value : undefined,
  };
  const previousValues = safeObject(previous && previous.transition_values);
  const sourceReceipts = [
    weatherResult && weatherResult.receiptId,
    phoneResult && phoneResult.commandId,
  ].filter(Boolean);
  const events = core.transitionEvents(previousValues, currentValues, core.iso(nowMs), sourceReceipts);
  const bridge = safeObject(args.scene);
  const projection = core.compactProjection({
    nowMs,
    time,
    daylight,
    weather,
    phone,
    changes: events,
    unavailable: collectUnavailable({time, weather, phone, daylight: {daylight}}),
    timeBridge: Object.keys(bridge).length ? core.timeBridge({realNow: nowMs, ...bridge}) : null,
  });
  const packet = {
    contract: CONTRACT,
    layer: 'real_observation',
    observed_at: core.iso(nowMs),
    observations: {time, daylight, weather, phone},
    projection,
    summary: core.accessibilitySummary(projection),
    events,
    source_states: sourceStates,
    sources: sourceCatalog({source_states: sourceStates}),
    transition_values: currentValues,
    cost_policy: 'zero-dollar-default',
    paid_service_activated: false,
    fiction_generated: false,
    location: {scope: location.scope, label: location.label || null, configured: location.configured},
  };
  await persistObservation(admin, user, packet);
  return packet;
}

async function runHistory({admin, user, args = {}, now = () => Date.now()} = {}) {
  const nowMs = now();
  const sinceMs = Math.max(nowMs - RETENTION_MS, safeNumber(args.sinceMs, nowMs - RETENTION_MS));
  const limit = Math.floor(clamp(args.limit, 1, 50, 20));
  if (!admin || typeof admin.firestore !== 'function') {
    return {contract: CONTRACT, events: [], retention_ms: RETENTION_MS, unavailable: true, error: 'history_store_unavailable'};
  }
  const snapshot = await ownerRoot(admin, user).collection('events')
    .where('observedAtMs', '>=', sinceMs)
    .orderBy('observedAtMs', 'desc')
    .limit(limit)
    .get();
  return {
    contract: CONTRACT,
    since_ms: sinceMs,
    retention_ms: RETENTION_MS,
    event_count: snapshot.docs.length,
    events: snapshot.docs.map((doc) => doc.data()).filter((event) => event && event.observedAtMs >= nowMs - RETENTION_MS),
    telemetry_policy: 'transition_events_only',
  };
}

async function runStatus({admin, user, now = () => Date.now()} = {}) {
  const latest = await readLatest(admin, user);
  const observedAtMs = safeNumber(latest && latest.observedAtMs);
  const age = observedAtMs === null ? null : Math.max(0, now() - observedAtMs);
  return {
    contract: CONTRACT,
    callable_operations: [...CALLABLE_OPERATIONS],
    accepted: false,
    latest_observed_at: latest && latest.observed_at || null,
    latest_age_ms: age,
    latest_stale: age === null ? null : age > 20 * 60 * 1000,
    source_states: latest && latest.source_states || {time: 'available', weather: 'not_observed', alerts: 'not_observed', phone: 'not_observed'},
    observation_policy: 'unknown-remains-unknown',
    default_privacy: ['PUBLIC', 'DEVICE'],
    fiction_generated: false,
  };
}

async function runOperation({operation, admin, user, args = {}, callCommandCenter, fetchImpl = global.fetch, now = () => Date.now(), sleep} = {}) {
  if (!CALLABLE_OPERATIONS.includes(operation)) throw Object.assign(new Error(`Unsupported Reality Membrane operation: ${operation}`), {status: 400});
  if (operation === 'reality.capabilities') return core.realityCapabilities({callableOperations: CALLABLE_OPERATIONS});
  if (operation === 'reality.status') return runStatus({admin, user, now});
  if (operation === 'reality.sources') {
    const latest = await readLatest(admin, user);
    return {contract: CONTRACT, sources: sourceCatalog(latest), coordinates_returned: false, paid_service_activated: false};
  }
  if (operation === 'reality.history') return runHistory({admin, user, args, now});
  if (operation === 'reality.observe') return runObserve({admin, user, args, callCommandCenter, fetchImpl, now, sleep});
  throw Object.assign(new Error('Unsupported Reality Membrane operation.'), {status: 400});
}

module.exports = {
  CONTRACT,
  RETENTION_MS,
  CALLABLE_OPERATIONS,
  operationEntries,
  coarseLocation,
  weatherCodeLabel,
  precipitationKind,
  nearestHourlyProbability,
  openMeteoUrl,
  nwsAlertsUrl,
  parseAlerts,
  fetchWeatherBundle,
  normalizePhoneReceipt,
  observePhone,
  sourceCatalog,
  runObserve,
  runHistory,
  runStatus,
  runOperation,
};
