const crypto = require('node:crypto');
const membrane = require('./reality_membrane');
const {enqueuePhoneCommand, getPhoneCommand} = require('./phone_hands_relay');

const CONTRACT = 'home-center.reality.v1';
const EVENT_RETENTION_MS = 72 * 60 * 60 * 1000;
const DEFAULT_TIME_ZONE = process.env.HOME_CENTER_REALITY_TIMEZONE || 'America/Chicago';
const DEFAULT_LOCATION = Object.freeze({
  latitude: Number(process.env.HOME_CENTER_REALITY_LATITUDE || 34.8),
  longitude: Number(process.env.HOME_CENTER_REALITY_LONGITUDE || -92.3),
  scope: process.env.HOME_CENTER_REALITY_LOCATION_SCOPE || 'central_arkansas_coarse_0.1deg',
});

function safeText(value, max = 12000) {
  const text = typeof value === 'string' ? value.trim() : '';
  return text.length > max ? text.slice(0, max) : text;
}
function safeObject(value) { return value && typeof value === 'object' && !Array.isArray(value) ? value : {}; }
function boundedNumber(value, fallback, min, max) {
  const number = Number(value);
  if (!Number.isFinite(number)) return fallback;
  return Math.max(min, Math.min(max, number));
}
function sha256(value) { return crypto.createHash('sha256').update(String(value || '')).digest('hex'); }
function ownerKeyFromEmail(email) { return `owner_${sha256(safeText(email, 320).toLowerCase() || 'anonymous').slice(0, 32)}`; }
function realityUserKey(user = {}) { return `reality_${sha256(safeText(user.email || user.uid, 320).toLowerCase() || 'anonymous').slice(0, 32)}`; }
function packetReceipt(value) { return `reality_packet_${sha256(JSON.stringify(value)).slice(0, 24)}`; }
function iso(ms = Date.now()) { return new Date(ms).toISOString(); }
function sleep(ms) { return new Promise((resolve) => setTimeout(resolve, ms)); }
function locationConfig(args = {}) {
  const supplied = safeObject(args.location);
  const latitude = boundedNumber(supplied.latitude, DEFAULT_LOCATION.latitude, -90, 90);
  const longitude = boundedNumber(supplied.longitude, DEFAULT_LOCATION.longitude, -180, 180);
  return {
    latitude: Math.round(latitude * 10) / 10,
    longitude: Math.round(longitude * 10) / 10,
    scope: safeText(supplied.scope, 120) || DEFAULT_LOCATION.scope,
  };
}

async function fetchJson(url, options = {}) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), boundedNumber(options.timeoutMs, 8000, 1000, 20000));
  try {
    const response = await fetch(url, {headers: options.headers || {}, signal: controller.signal});
    const text = await response.text();
    let json = null;
    try { json = text ? JSON.parse(text) : null; } catch (_) { json = null; }
    if (!response.ok || !json) return {ok:false, status:response.status, error:`http_${response.status}`, detail:safeText(text, 500)};
    return {ok:true, status:response.status, json, receivedAt:iso()};
  } catch (error) {
    return {ok:false, status:0, error:error && error.name === 'AbortError' ? 'timeout' : 'network_error', detail:safeText(error && error.message, 500)};
  } finally {
    clearTimeout(timeout);
  }
}

function unavailableObservation(type, {source, privacy = membrane.PRIVACY.PUBLIC, locationScope = null, error, nowMs = Date.now()} = {}) {
  return membrane.observation({
    observation_type:type,
    unavailable:true,
    capability_state:membrane.CAPABILITY.UNAVAILABLE,
    source:source || 'unknown',
    privacy,
    location_scope:locationScope,
    error:error || 'unavailable',
  }, nowMs);
}

function unavailableWeather(source, locationScope, error, nowMs) {
  return {
    temperature_f:unavailableObservation('weather.temperature_f',{source,locationScope,error,nowMs}),
    feels_like_f:unavailableObservation('weather.feels_like_f',{source,locationScope,error,nowMs}),
    precipitation:unavailableObservation('weather.precipitation',{source,locationScope,error,nowMs}),
    precipitation_probability_pct:unavailableObservation('weather.precipitation_probability_pct',{source,locationScope,error,nowMs}),
    humidity_pct:unavailableObservation('weather.humidity_pct',{source,locationScope,error,nowMs}),
    wind_mph:unavailableObservation('weather.wind_mph',{source,locationScope,error,nowMs}),
    alert:unavailableObservation('weather.alert',{source,locationScope,error,nowMs}),
  };
}

function precipitationKind(current = {}) {
  if (Number(current.snowfall || 0) > 0) return 'snow';
  if (Number(current.rain || 0) > 0) return 'rain';
  if (Number(current.precipitation || 0) > 0) return 'precipitation';
  if ([current.snowfall, current.rain, current.precipitation].some((value) => Number.isFinite(Number(value)))) return 'none';
  return undefined;
}

function nearTermProbability(hourly = {}, currentEpochSeconds = 0) {
  const times = Array.isArray(hourly.time) ? hourly.time : [];
  const probabilities = Array.isArray(hourly.precipitation_probability) ? hourly.precipitation_probability : [];
  const values = [];
  for (let index = 0; index < times.length && index < probabilities.length; index += 1) {
    const time = Number(times[index]);
    if (!Number.isFinite(time) || time < currentEpochSeconds || time > currentEpochSeconds + 3 * 3600) continue;
    const probability = Number(probabilities[index]);
    if (Number.isFinite(probability)) values.push(probability);
  }
  return values.length ? Math.max(...values) : undefined;
}

async function publicWeather({nowMs = Date.now(), timeZone = DEFAULT_TIME_ZONE, location = DEFAULT_LOCATION} = {}) {
  const params = new URLSearchParams({
    latitude:String(location.latitude),
    longitude:String(location.longitude),
    current:'temperature_2m,apparent_temperature,relative_humidity_2m,precipitation,rain,snowfall,weather_code,wind_speed_10m',
    hourly:'precipitation_probability',
    daily:'sunrise,sunset',
    temperature_unit:'fahrenheit',
    wind_speed_unit:'mph',
    precipitation_unit:'inch',
    timeformat:'unixtime',
    timezone:timeZone,
    forecast_days:'1',
  });
  const forecast = await fetchJson(`https://api.open-meteo.com/v1/forecast?${params.toString()}`, {timeoutMs:9000});
  if (!forecast.ok) {
    return {
      weather:unavailableWeather('open_meteo.public_forecast', location.scope, forecast.error, nowMs),
      daylight:unavailableObservation('environment.daylight',{source:'open_meteo.public_forecast',locationScope:location.scope,error:forecast.error,nowMs}),
      source:{id:'open_meteo.public_forecast',ok:false,error:forecast.error,status:forecast.status},
    };
  }
  const data = safeObject(forecast.json);
  const current = safeObject(data.current);
  const currentEpoch = Number(current.time || 0);
  const sourceTimestamp = Number.isFinite(currentEpoch) && currentEpoch > 0 ? iso(currentEpoch * 1000) : null;
  const payload = {
    temperature_f:current.temperature_2m,
    feels_like_f:current.apparent_temperature,
    precipitation:precipitationKind(current),
    precipitation_probability_pct:nearTermProbability(safeObject(data.hourly), currentEpoch),
    humidity_pct:current.relative_humidity_2m,
    wind_mph:current.wind_speed_10m,
    alert:undefined,
  };
  const weather = membrane.weatherObservations(payload, {
    nowMs,
    observedAt:sourceTimestamp || iso(nowMs),
    source:'open_meteo.public_forecast',
    sourceTimestamp,
    maxAgeMs:20 * 60 * 1000,
    locationScope:location.scope,
    confidence:0.9,
  });

  const alertsUrl = `https://api.weather.gov/alerts/active?point=${encodeURIComponent(location.latitude + ',' + location.longitude)}`;
  const alertsResponse = await fetchJson(alertsUrl, {
    timeoutMs:7000,
    headers:{'User-Agent':'HomeCenter-RealityMembrane/1.0 (github.com/Valar05/home-center)','Accept':'application/geo+json'},
  });
  if (alertsResponse.ok) {
    const features = Array.isArray(alertsResponse.json.features) ? alertsResponse.json.features : [];
    const alerts = features.slice(0, 5).map((feature) => {
      const properties = safeObject(feature && feature.properties);
      return {
        event:safeText(properties.event, 160),
        severity:safeText(properties.severity, 80),
        urgency:safeText(properties.urgency, 80),
        certainty:safeText(properties.certainty, 80),
        headline:safeText(properties.headline, 300),
        effective:safeText(properties.effective, 80),
        expires:safeText(properties.expires, 80),
      };
    });
    weather.alert = membrane.observation({
      observation_type:'weather.alert', value:alerts, observed_at:iso(nowMs), source:'weather_gov.active_alerts',
      source_timestamp:alertsResponse.receivedAt, max_age_ms:10 * 60 * 1000, privacy:membrane.PRIVACY.PUBLIC,
      location_scope:location.scope, confidence:1,
    }, nowMs);
  } else {
    weather.alert = unavailableObservation('weather.alert',{source:'weather_gov.active_alerts',locationScope:location.scope,error:alertsResponse.error,nowMs});
  }

  const daily = safeObject(data.daily);
  const sunriseEpoch = Array.isArray(daily.sunrise) ? Number(daily.sunrise[0]) : NaN;
  const sunsetEpoch = Array.isArray(daily.sunset) ? Number(daily.sunset[0]) : NaN;
  const daylight = membrane.daylightObservation({
    sunrise:Number.isFinite(sunriseEpoch) ? iso(sunriseEpoch * 1000) : null,
    sunset:Number.isFinite(sunsetEpoch) ? iso(sunsetEpoch * 1000) : null,
    nowMs,
    source:'open_meteo.public_forecast',
    locationScope:location.scope,
  });
  return {
    weather,
    daylight,
    source:{id:'open_meteo.public_forecast',ok:true,status:forecast.status,receivedAt:forecast.receivedAt,sourceTimestamp},
    alertSource:{id:'weather_gov.active_alerts',ok:alertsResponse.ok,status:alertsResponse.status,error:alertsResponse.error || ''},
  };
}

const PHONE_OBSERVE_COMMAND = String.raw`python - <<'PY'
import json, shutil, subprocess, time

def run(cmd, timeout=8):
    try:
        p=subprocess.run(cmd,shell=True,text=True,capture_output=True,timeout=timeout)
        return {'ok':p.returncode==0,'exit_code':p.returncode,'stdout':p.stdout.strip()[:12000],'stderr':p.stderr.strip()[:1200]}
    except Exception as e:
        return {'ok':False,'exit_code':None,'stdout':'','stderr':type(e).__name__+': '+str(e)}

def json_cmd(name):
    if not shutil.which(name): return None, name+'_unavailable'
    result=run(name)
    if not result['ok']: return None, name+'_failed:'+result['stderr'][:200]
    try: return json.loads(result['stdout']), ''
    except Exception as e: return None, name+'_invalid_json:'+str(e)

battery,battery_error=json_cmd('termux-battery-status')
wifi,wifi_error=json_cmd('termux-wifi-connectioninfo')
route=run('ip route show default')
connectivity=None
if wifi and wifi.get('ssid') and str(wifi.get('ssid')).lower() not in ('<unknown ssid>','unknown'):
    connectivity='wifi'
elif route['ok'] and route['stdout']:
    connectivity='connected_unknown'
audio=run("dumpsys audio 2>/dev/null | grep -E 'mDevice|mRoute|route|WIRED|BLUETOOTH|SPEAKER|USB' | head -80")
raw=audio['stdout'].upper() if audio['ok'] else ''
audio_route=None
if 'BLUETOOTH' in raw or 'A2DP' in raw: audio_route='bluetooth'
elif 'WIRED_HEAD' in raw or 'HEADPHONE' in raw: audio_route='wired_headphones'
elif 'USB' in raw: audio_route='usb_audio'
elif 'SPEAKER' in raw: audio_route='speaker'
status=str((battery or {}).get('status','')).upper()
plugged=(battery or {}).get('plugged')
charging=True if status in ('CHARGING','FULL') else (False if status in ('DISCHARGING','NOT_CHARGING') else None)
receipt={'schema':'home-center.reality.phone-observation.v1','observed_at_unix_ms':int(time.time()*1000),'battery_pct':(battery or {}).get('percentage'),'charging':charging,'power_source':plugged,'connectivity':connectivity,'audio_route':audio_route,'battery_error':battery_error or None,'connectivity_error':wifi_error or (None if route['ok'] else route['stderr'][:200]),'audio_route_error':None if audio_route else (audio['stderr'][:200] or 'audio_route_unknown'),'tools':{'termux_battery_status':bool(shutil.which('termux-battery-status')),'termux_wifi_connectioninfo':bool(shutil.which('termux-wifi-connectioninfo')),'dumpsys':bool(shutil.which('dumpsys'))}}
print(json.dumps(receipt,separators=(',',':')))
PY`;

function parsePhoneStdout(stdout) {
  const lines = String(stdout || '').split(/\r?\n/).map((line) => line.trim()).filter(Boolean);
  for (let index = lines.length - 1; index >= 0; index -= 1) {
    try {
      const value = JSON.parse(lines[index]);
      if (value && value.schema === 'home-center.reality.phone-observation.v1') return value;
    } catch (_) {}
  }
  return null;
}

async function observePhone({admin, user, requestId, nowMs = Date.now(), timeoutMs = 25000} = {}) {
  const email = safeText(user && user.email, 320).toLowerCase();
  if (!email) return {payload:{}, error:'owner_email_unavailable', command:null};
  const caller = {actor:email, ownerKey:ownerKeyFromEmail(email)};
  const identity = safeText(requestId, 160) || crypto.randomUUID();
  const commandId = `phc_reality_observe_${sha256(identity).slice(0, 24)}`;
  let command;
  try {
    command = await enqueuePhoneCommand(admin, caller, {
      idempotencyKey:`reality.observe:${identity}`,
      commandId,
      deviceId:'primary-phone',
      ttlMs:60000,
      action:{action:'phone_shell',command:PHONE_OBSERVE_COMMAND},
    });
  } catch (error) {
    return {payload:{}, error:`phone_enqueue_failed:${safeText(error && error.message, 300)}`, command:null};
  }
  const deadline = Date.now() + boundedNumber(timeoutMs, 25000, 1000, 45000);
  while (Date.now() < deadline) {
    try { command = await getPhoneCommand(admin, caller, {commandId:command.commandId || commandId}); } catch (_) {}
    if (command && ['completed','failed'].includes(command.status)) break;
    await sleep(1000);
  }
  if (!command || command.status !== 'completed') {
    return {payload:{}, error:`phone_command_${command && command.status || 'unknown'}:${safeText(command && command.error, 200)}`, command};
  }
  const result = safeObject(command.result);
  if (result.ok !== true || Number(result.exitCode) !== 0) {
    return {payload:{}, error:`phone_shell_failed:${safeText(result.stderr, 300)}`, command};
  }
  const payload = parsePhoneStdout(result.stdout);
  return payload ? {payload, error:'', command} : {payload:{}, error:'phone_observation_invalid_json', command};
}

function phoneObservationGroup(phoneResult, nowMs) {
  const payload = safeObject(phoneResult && phoneResult.payload);
  const observedAtMs = Number(payload.observed_at_unix_ms || nowMs);
  const observedAt = Number.isFinite(observedAtMs) ? iso(observedAtMs) : iso(nowMs);
  const source = phoneResult && phoneResult.command && phoneResult.command.commandId ? `phone_hands:${phoneResult.command.commandId}` : 'phone_hands';
  const normalized = membrane.phoneObservations({
    battery_pct:payload.battery_pct,
    charging:payload.charging,
    power_source:payload.power_source,
    connectivity:payload.connectivity,
    audio_route:payload.audio_route,
  }, {nowMs, observedAt, source, maxAgeMs:2 * 60 * 1000});
  const error = safeText(phoneResult && phoneResult.error, 500);
  if (error) {
    for (const [key, observation] of Object.entries(normalized)) {
      if (observation.value === null || observation.unavailable) {
        normalized[key] = unavailableObservation(observation.observation_type,{source,privacy:membrane.PRIVACY.DEVICE,error,nowMs});
      }
    }
  }
  return normalized;
}

function observationUnavailableList(groups = {}) {
  const unavailable = [];
  for (const [groupName, group] of Object.entries(groups)) {
    if (!group || typeof group !== 'object') continue;
    for (const [name, observation] of Object.entries(group)) {
      if (observation && (observation.unavailable || observation.capability_state === membrane.CAPABILITY.UNAVAILABLE)) unavailable.push(`${groupName}.${name}`);
    }
  }
  return unavailable;
}

function simpleState({weather = {}, phone = {}, daylight = null} = {}) {
  return {
    precipitation:weather.precipitation && weather.precipitation.value,
    charging:phone.charging && phone.charging.value,
    audio_route:phone.audio_route && phone.audio_route.value,
    connectivity:phone.connectivity && phone.connectivity.value,
    battery_pct:phone.battery_pct && phone.battery_pct.value,
    daylight:daylight && daylight.value,
  };
}

function extendedEvents(previous = {}, current = {}, observedAt) {
  const events = membrane.transitionEvents(previous, current, observedAt);
  const emit = (eventType, from, to) => events.push({event_type:eventType,from,to,observed_at:observedAt,receipt_id:`reality_${sha256(JSON.stringify({eventType,from,to,observedAt})).slice(0,24)}`});
  if (previous.daylight !== current.daylight && current.daylight === 'daylight') emit('sun.risen', previous.daylight, current.daylight);
  if (previous.daylight === 'daylight' && current.daylight && current.daylight !== 'daylight') emit('sun.set', previous.daylight, current.daylight);
  if (Number(previous.battery_pct) >= 20 && Number(current.battery_pct) < 20) emit('phone.low_battery', previous.battery_pct, current.battery_pct);
  return events;
}

async function cleanupCollection(collection, cutoffMs) {
  const snapshot = await collection.where('observedAtMs','<',cutoffMs).limit(40).get();
  if (snapshot.empty) return 0;
  const batch = collection.firestore.batch();
  snapshot.docs.forEach((doc) => batch.delete(doc.ref));
  await batch.commit();
  return snapshot.size;
}

async function persistPacket({admin, user, packet, state, nowMs}) {
  const userKey = realityUserKey(user);
  const root = admin.firestore().collection('realityUsers').doc(userKey);
  const latestRef = root.collection('state').doc('latest');
  const latest = await latestRef.get();
  const previous = latest.exists ? safeObject(latest.data().state) : {};
  const events = extendedEvents(previous, state, packet.observed_at);
  const batch = admin.firestore().batch();
  batch.set(latestRef,{state,packetReceiptId:packet.receipt_id,observedAtMs:nowMs,updatedAtMs:Date.now()},{merge:false});
  batch.set(root.collection('snapshots').doc(packet.receipt_id),{
    receiptId:packet.receipt_id, observedAtMs:nowMs, observedAt:packet.observed_at,
    projection:packet.projection, unavailable:packet.unavailable, sourceReceipts:packet.source_receipts,
  },{merge:false});
  events.forEach((event) => batch.set(root.collection('events').doc(event.receipt_id),{...event,observedAtMs:Date.parse(event.observed_at) || nowMs},{merge:false}));
  await batch.commit();
  const cutoff = nowMs - EVENT_RETENTION_MS;
  await cleanupCollection(root.collection('events'), cutoff).catch(() => 0);
  await cleanupCollection(root.collection('snapshots'), cutoff).catch(() => 0);
  return events;
}

function valueText(observation, suffix = '') {
  if (!observation || observation.unavailable || observation.value === null || observation.value === undefined) return '';
  return `${observation.value}${suffix || (observation.units ? ` ${observation.units}` : '')}`;
}

function speechSummary({time, daylight, weather, phone}) {
  const parts = [];
  const local = time && time.now && time.now.value;
  if (local) {
    const match = String(local).match(/T(\d{2}):(\d{2})/);
    parts.push(match ? `${match[1]}:${match[2]}` : String(local));
  }
  if (daylight && daylight.value) {
    if (daylight.value === 'daylight') parts.push('daylight');
    else if (daylight.value === 'dark_before_sunrise') parts.push('still dark');
    else if (daylight.value === 'dark_after_sunset') parts.push('dark after sunset');
  }
  const temperature = valueText(weather && weather.temperature_f, ' degrees Fahrenheit');
  if (temperature) parts.push(temperature);
  const precipitation = weather && weather.precipitation && weather.precipitation.value;
  if (precipitation && precipitation !== 'none') parts.push(String(precipitation));
  const battery = valueText(phone && phone.battery_pct, ' percent battery');
  if (battery) parts.push(battery);
  if (phone && phone.charging && phone.charging.value === true) parts.push('charging');
  const route = phone && phone.audio_route && phone.audio_route.value;
  if (route) parts.push(`${String(route).replace(/_/g,' ')} audio`);
  const connectivity = phone && phone.connectivity && phone.connectivity.value;
  if (connectivity) parts.push(String(connectivity).replace(/_/g,' '));
  return parts.length ? `Reality: ${parts.join('. ')}.` : 'Reality: current observations are unavailable.';
}

function timeBridge(args, time, nowMs) {
  const allowed = new Set(['realtime','paused','compressed','explicitly_advanced','detached']);
  const policy = allowed.has(safeText(args.timePolicy, 40)) ? safeText(args.timePolicy, 40) : 'detached';
  const checkpoint = safeText(args.lastSceneCheckpoint, 100);
  const checkpointMs = Date.parse(checkpoint);
  return {
    REAL_NOW:time && time.now || null,
    SCENE_TIME:safeText(args.sceneTime, 100) || null,
    LAST_SCENE_CHECKPOINT:checkpoint || null,
    ELAPSED_REAL_TIME_MS:Number.isFinite(checkpointMs) ? Math.max(0, nowMs - checkpointMs) : null,
    ELAPSED_WORLD_TIME_MS:Number.isFinite(Number(args.elapsedWorldTimeMs)) ? Number(args.elapsedWorldTimeMs) : null,
    policy,
    assumption:'real time is not silently equated to fictional scene time',
  };
}

async function observeReality({admin, user, args = {}}) {
  const nowMs = Date.now();
  const timeZone = safeText(args.timeZone, 120) || DEFAULT_TIME_ZONE;
  const location = locationConfig(args);
  const include = new Set(Array.isArray(args.include) && args.include.length ? args.include.map((value) => safeText(value, 40)) : ['time','daylight','weather','phone']);
  const time = include.has('time') ? membrane.timeObservations({nowMs,timeZone}) : {};
  const weatherPromise = include.has('weather') || include.has('daylight') ? publicWeather({nowMs,timeZone,location}) : Promise.resolve({weather:{},daylight:null,source:null});
  const phonePromise = include.has('phone') ? observePhone({admin,user,requestId:args.requestId,nowMs,timeoutMs:args.phoneTimeoutMs}) : Promise.resolve({payload:{},error:'phone_not_requested',command:null});
  const [publicResult, phoneResult] = await Promise.all([weatherPromise, phonePromise]);
  const weather = include.has('weather') ? publicResult.weather : {};
  const daylight = include.has('daylight') ? publicResult.daylight : null;
  const phone = include.has('phone') ? phoneObservationGroup(phoneResult, nowMs) : {};
  const groups = {time,weather,phone,daylight:daylight ? {state:daylight} : {}};
  const unavailable = observationUnavailableList(groups);
  const projection = membrane.compactProjection({time,daylight,weather,phone,unavailable});
  const sourceReceipts = {
    runtime_clock:time.now && time.now.receipt_id || null,
    weather:publicResult.source || null,
    alerts:publicResult.alertSource || null,
    phone:phoneResult.command ? {commandId:phoneResult.command.commandId,status:phoneResult.command.status,completedAtMs:phoneResult.command.completedAtMs || 0,error:phoneResult.error || ''} : {commandId:null,status:'unavailable',error:phoneResult.error || ''},
  };
  const packet = {
    contract:CONTRACT,
    observed_at:iso(nowMs),
    projection,
    observations:{time,daylight,weather,phone},
    source_receipts:sourceReceipts,
    unavailable,
    speech_summary:speechSummary({time,daylight,weather,phone}),
    time_bridge:timeBridge(args,time,nowMs),
    privacy_policy:{default:['PUBLIC','DEVICE'],excluded:['PERSONAL','SENSITIVE']},
    cost_policy:'zero-dollar-default',
    fiction_generated:false,
  };
  packet.receipt_id = packetReceipt(packet);
  const state = simpleState({weather,phone,daylight});
  const events = args.persist === false ? [] : await persistPacket({admin,user,packet,state,nowMs}).catch((error) => {
    packet.history_error = safeText(error && error.message, 500);
    return [];
  });
  packet.changes_since_checkpoint = events;
  packet.projection.changes_since_checkpoint = events.slice(-20);
  return packet;
}

async function realityHistory({admin, user, args = {}}) {
  const userKey = realityUserKey(user);
  const root = admin.firestore().collection('realityUsers').doc(userKey);
  const limit = Math.floor(boundedNumber(args.limit, 30, 1, 100));
  const sinceMs = Number.isFinite(Number(args.sinceMs)) ? Number(args.sinceMs) : (safeText(args.since, 100) ? Date.parse(args.since) : NaN);
  let eventQuery = root.collection('events').orderBy('observedAtMs','desc').limit(limit);
  if (Number.isFinite(sinceMs)) eventQuery = eventQuery.where('observedAtMs','>=',sinceMs);
  const eventsSnap = await eventQuery.get();
  const snapshotsSnap = args.includeSnapshots === true ? await root.collection('snapshots').orderBy('observedAtMs','desc').limit(Math.min(limit,20)).get() : null;
  return {
    contract:CONTRACT,
    retention_ms:EVENT_RETENTION_MS,
    events:eventsSnap.docs.map((doc) => doc.data()),
    snapshots:snapshotsSnap ? snapshotsSnap.docs.map((doc) => doc.data()) : [],
    high_frequency_telemetry_retained:false,
  };
}

async function realityStatus({admin, user}) {
  const email = safeText(user && user.email, 320).toLowerCase();
  const ownerKey = ownerKeyFromEmail(email);
  const devices = await admin.firestore().collection('phoneHandsDevices').where('ownerKey','==',ownerKey).limit(20).get();
  const phone = devices.docs.map((doc) => doc.data()).find((device) => device.deviceId === 'primary-phone') || null;
  const now = Date.now();
  return {
    contract:CONTRACT,
    callable:true,
    accepted:false,
    observationPolicy:'unknown-remains-unknown',
    defaultPrivacy:['PUBLIC','DEVICE'],
    sources:{
      time:{state:'available',network:'none',cost:'zero'},
      phone:{state:phone && phone.status === 'online' && now - Number(phone.lastSeenAtMs || 0) < 120000 ? 'available' : 'degraded',lastSeenAtMs:phone && phone.lastSeenAtMs || 0},
      weather:{state:'available_on_observe',network:'required',cost:'zero_only'},
      daylight:{state:'available_on_observe',network:'required',cost:'zero_only'},
      alerts:{state:'available_on_observe',network:'required',cost:'zero_only'},
    },
    history:{state:'available',retentionMs:EVENT_RETENTION_MS},
    fictionGenerated:false,
  };
}

function realitySources() {
  return {
    contract:CONTRACT,
    sources:[
      {id:'home_center.runtime_clock',privacy:'PUBLIC',network:'none',cost:'zero',retention:'packet_and_transition_history'},
      {id:'phone_hands.phone_shell',privacy:'DEVICE',network:'home_center_relay',cost:'zero',retention:'packet_and_transition_history',rawCommandOutputExposed:false},
      {id:'open_meteo.public_forecast',privacy:'PUBLIC',network:'required',cost:'zero_only',locationPrecision:'coarse_0.1_degree'},
      {id:'weather_gov.active_alerts',privacy:'PUBLIC',network:'required',cost:'zero_only',locationPrecision:'coarse_0.1_degree'},
    ],
    excludedByDefault:['calendar_content','message_bodies','precise_location_history','microphone_recordings','medical_data'],
  };
}

function realityCapabilities() {
  return {
    ...membrane.realityCapabilities(),
    implemented:{status:true,observe:true,history:true,sources:true,capabilities:true,events:true,subscribe:false},
    projection:'inner_fortress_compact_v1',
    accessibility:{speech_summary:true,screen_reader_structured:true},
    offline:{local_time:true,phone_when_relay_available:true,last_weather_stale_reconciliation:'history_available_live_cache_pending'},
  };
}

async function runRealityOperation({operation, admin, user, args = {}}) {
  if (!admin) throw Object.assign(new Error('Reality Membrane requires Home Center Firestore runtime.'), {status:500});
  if (operation === 'reality.status') return realityStatus({admin,user,args});
  if (operation === 'reality.sources') return realitySources();
  if (operation === 'reality.capabilities') return realityCapabilities();
  if (operation === 'reality.observe') return observeReality({admin,user,args});
  if (operation === 'reality.history' || operation === 'reality.events') return realityHistory({admin,user,args});
  throw Object.assign(new Error(`Unsupported Reality Membrane operation: ${operation}`), {status:400});
}

module.exports = {
  CONTRACT,
  EVENT_RETENTION_MS,
  DEFAULT_LOCATION,
  fetchJson,
  precipitationKind,
  nearTermProbability,
  parsePhoneStdout,
  phoneObservationGroup,
  speechSummary,
  timeBridge,
  realitySources,
  realityCapabilities,
  runRealityOperation,
};
