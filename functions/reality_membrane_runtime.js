const {createHash} = require('node:crypto');
const reality = require('./reality_membrane');

const DEFAULT_REGION = Object.freeze({
  id:'central_arkansas',
  latitude:34.85,
  longitude:-92.30,
  locationScope:'coarse_locality',
  label:'Central Arkansas',
  declarationSource:'owner_declared_coarse_region',
});

function safeText(value, max=500) { const text=typeof value === 'string' ? value.trim() : ''; return text.length > max ? text.slice(0,max) : text; }
function finite(value) { const number=Number(value); return Number.isFinite(number) ? number : null; }
function sourceReceipt(prefix, value) { return `${prefix}_${createHash('sha256').update(JSON.stringify(value)).digest('hex').slice(0,24)}`; }
function regionConfig(env=process.env) {
  const latitude=finite(env.HOME_CENTER_REALITY_COARSE_LATITUDE); const longitude=finite(env.HOME_CENTER_REALITY_COARSE_LONGITUDE);
  return {
    ...DEFAULT_REGION,
    latitude:latitude === null ? DEFAULT_REGION.latitude : latitude,
    longitude:longitude === null ? DEFAULT_REGION.longitude : longitude,
    label:safeText(env.HOME_CENTER_REALITY_COARSE_LABEL,120) || DEFAULT_REGION.label,
    id:safeText(env.HOME_CENTER_REALITY_COARSE_ID,80) || DEFAULT_REGION.id,
    configuredBy:latitude === null || longitude === null ? 'bounded_owner_default' : 'runtime_environment',
  };
}

function weatherCodeKind(code) {
  const n=Number(code);
  if ([95,96,99].includes(n)) return 'thunderstorm';
  if ([71,73,75,77,85,86].includes(n)) return 'snow';
  if ([51,53,55,56,57,61,63,65,66,67,80,81,82].includes(n)) return 'rain';
  if ([45,48].includes(n)) return 'fog';
  return 'none';
}

function nearestHourlyProbability(hourly={}, nowMs=Date.now()) {
  const times=Array.isArray(hourly.time) ? hourly.time : []; const probabilities=Array.isArray(hourly.precipitation_probability) ? hourly.precipitation_probability : [];
  let best=null;
  for (let index=0; index<Math.min(times.length,probabilities.length); index+=1) {
    const at=Date.parse(times[index]); const probability=finite(probabilities[index]);
    if (!Number.isFinite(at) || probability === null || at < nowMs-60*60*1000 || at > nowMs+3*60*60*1000) continue;
    if (!best || Math.abs(at-nowMs) < Math.abs(best.at-nowMs)) best={at,probability};
  }
  return best ? best.probability : undefined;
}

function parseOpenMeteo(payload={}, {nowMs=Date.now(), region=DEFAULT_REGION}={}) {
  const current=payload && typeof payload.current === 'object' ? payload.current : {};
  const daily=payload && typeof payload.daily === 'object' ? payload.daily : {};
  const observedAt=safeText(current.time,80) || new Date(nowMs).toISOString();
  const code=finite(current.weather_code);
  const precipitationAmount=finite(current.precipitation);
  const rainAmount=finite(current.rain);
  const kind=rainAmount !== null && rainAmount > 0 ? 'rain' : precipitationAmount !== null && precipitationAmount > 0 ? weatherCodeKind(code) === 'none' ? 'precipitation' : weatherCodeKind(code) : weatherCodeKind(code);
  const payloadForMembrane={
    temperature_f:finite(current.temperature_2m),
    feels_like_f:finite(current.apparent_temperature),
    precipitation:kind,
    precipitation_probability_pct:nearestHourlyProbability(payload.hourly || {},nowMs),
    humidity_pct:finite(current.relative_humidity_2m),
    wind_mph:finite(current.wind_speed_10m),
  };
  const receiptId=sourceReceipt('weather_open_meteo',{observedAt,payload:payloadForMembrane,region:region.id});
  const weather=reality.weatherObservations(payloadForMembrane,{nowMs,observedAt,sourceTimestamp:observedAt,source:'open-meteo.forecast',locationScope:region.locationScope,confidence:0.9,receiptId});
  const sunrise=Array.isArray(daily.sunrise) ? daily.sunrise[0] : null; const sunset=Array.isArray(daily.sunset) ? daily.sunset[0] : null;
  const daylight=reality.daylightObservation({sunrise,sunset,nowMs,source:'open-meteo.sun',sourceTimestamp:safeText(payload.generationtime_ms ? observedAt : '',80) || observedAt,locationScope:region.locationScope});
  return {weather,daylight,source:{id:'open-meteo.forecast',receipt_id:receiptId,observed_at:observedAt,location_scope:region.locationScope,cost:'zero',network:'required'}};
}

function severityRank(value) { return {Extreme:4,Severe:3,Moderate:2,Minor:1,Unknown:0}[safeText(value,40)] ?? 0; }
function parseNwsAlerts(payload={}) {
  const features=Array.isArray(payload.features) ? payload.features : [];
  const alerts=features.map((feature)=>feature && feature.properties || {}).filter(Boolean).map((properties)=>({event:safeText(properties.event,120),severity:safeText(properties.severity,40)||'Unknown',urgency:safeText(properties.urgency,40)||'Unknown',headline:safeText(properties.headline,240),sent:safeText(properties.sent,80),expires:safeText(properties.expires,80)}));
  alerts.sort((a,b)=>severityRank(b.severity)-severityRank(a.severity));
  return alerts.length ? {active:true,count:alerts.length,highest_severity:alerts[0].severity,events:alerts.slice(0,3)} : {active:false,count:0,highest_severity:'none',events:[]};
}

async function fetchJson(url,{fetchImpl=globalThis.fetch,timeoutMs=8000,headers={}}={}) {
  if (typeof fetchImpl !== 'function') throw new Error('fetch_unavailable');
  const controller=new AbortController(); const timer=setTimeout(()=>controller.abort(),timeoutMs);
  try {
    const response=await fetchImpl(url,{headers,signal:controller.signal});
    const text=await response.text();
    if (!response.ok) throw new Error(`http_${response.status}:${text.slice(0,160)}`);
    return JSON.parse(text);
  } finally { clearTimeout(timer); }
}

function openMeteoUrl(region) {
  const params=new URLSearchParams({latitude:String(region.latitude),longitude:String(region.longitude),current:'temperature_2m,apparent_temperature,precipitation,rain,relative_humidity_2m,wind_speed_10m,weather_code',hourly:'precipitation_probability',daily:'sunrise,sunset',temperature_unit:'fahrenheit',wind_speed_unit:'mph',precipitation_unit:'inch',timezone:'UTC',forecast_days:'1'});
  return `https://api.open-meteo.com/v1/forecast?${params}`;
}
function nwsAlertsUrl(region) { return `https://api.weather.gov/alerts/active?point=${encodeURIComponent(region.latitude)},${encodeURIComponent(region.longitude)}`; }

async function fetchPublicEnvironment({nowMs=Date.now(),env=process.env,fetchImpl=globalThis.fetch}={}) {
  const region=regionConfig(env); const unavailable=[]; let parsed;
  try { parsed=parseOpenMeteo(await fetchJson(openMeteoUrl(region),{fetchImpl}),{nowMs,region}); }
  catch (error) {
    const detail=safeText(error && error.message,200) || 'weather_refresh_failed';
    const weather=reality.weatherObservations({}, {nowMs,source:'open-meteo.forecast',locationScope:region.locationScope,error:detail});
    parsed={weather,daylight:reality.unavailableObservation('environment.daylight',{source:'open-meteo.sun',privacy:reality.PRIVACY.PUBLIC,locationScope:region.locationScope,error:detail,nowMs}),source:{id:'open-meteo.forecast',state:'unavailable',error:detail,cost:'zero',network:'required',location_scope:region.locationScope}};
    unavailable.push('weather','daylight');
  }
  try {
    const alerts=parseNwsAlerts(await fetchJson(nwsAlertsUrl(region),{fetchImpl,headers:{'User-Agent':'Home Center Reality Membrane (owner-operated; dclarke1005@gmail.com)','Accept':'application/geo+json'}}));
    parsed.weather.alert=reality.observation({observation_type:'weather.alert',value:alerts,observed_at:new Date(nowMs).toISOString(),source:'weather.gov.alerts',source_timestamp:new Date(nowMs).toISOString(),privacy:reality.PRIVACY.PUBLIC,location_scope:region.locationScope,confidence:1,receipt_id:sourceReceipt('weather_nws_alerts',alerts),max_age_ms:10*60*1000},nowMs);
  } catch (error) {
    parsed.weather.alert=reality.unavailableObservation('weather.alert',{source:'weather.gov.alerts',privacy:reality.PRIVACY.PUBLIC,locationScope:region.locationScope,error:safeText(error && error.message,200)||'alerts_unavailable',nowMs});
    unavailable.push('weather.alert');
  }
  return {...parsed,region:{id:region.id,label:region.label,location_scope:region.locationScope,declaration_source:region.declarationSource,configured_by:region.configuredBy,privacy:'PERSONAL'},unavailable:[...new Set(unavailable)]};
}

const PHONE_PROBE_PYTHON = String.raw`import json, shutil, subprocess

def read(path):
    try:
        with open(path, encoding='utf-8') as handle: return handle.read().strip()
    except Exception: return None

def run(command, timeout=3):
    try:
        return subprocess.run(command, capture_output=True, text=True, timeout=timeout, check=False).stdout.strip()
    except Exception: return ''

battery_raw=read('/sys/class/power_supply/battery/capacity')
try: battery=int(battery_raw) if battery_raw is not None else None
except Exception: battery=None
status=(read('/sys/class/power_supply/battery/status') or '').lower()
charging=status in ('charging','full') if status else None
power_source=None
for name,label in [('wireless','wireless'),('usb','usb'),('ac','ac')]:
    if read('/sys/class/power_supply/%s/online' % name) == '1': power_source=label; break

connectivity=None
if shutil.which('termux-wifi-connectioninfo'):
    raw=run(['termux-wifi-connectioninfo'])
    try:
        wifi=json.loads(raw or '{}')
        state=str(wifi.get('supplicant_state') or '').upper()
        if state in ('COMPLETED','ASSOCIATED'): connectivity='wifi'
    except Exception: pass
if connectivity is None:
    network_type=run(['getprop','gsm.network.type']) if shutil.which('getprop') else ''
    if network_type and network_type.lower() not in ('unknown','none'): connectivity='cellular'
if connectivity is None:
    route=run(['sh','-c','ip route 2>/dev/null | head -1'])
    connectivity='connected' if route else 'offline'

audio_route=None
h2w=read('/sys/class/switch/h2w/state')
if h2w and h2w != '0': audio_route='wired_headphones'
try:
    cards=read('/proc/asound/cards') or ''
    if audio_route is None and 'USB' in cards.upper(): audio_route='usb_audio'
except Exception: pass
if audio_route is None and shutil.which('rish'):
    audio=run(['rish','-c','dumpsys audio'],4).lower()
    if 'bluetooth_a2dp' in audio and ('active' in audio or 'selected' in audio): audio_route='bluetooth'
    elif 'wired_head' in audio and ('active' in audio or 'selected' in audio): audio_route='wired_headphones'
    elif 'usb' in audio and ('active' in audio or 'selected' in audio): audio_route='usb_audio'
    elif 'speaker' in audio and ('active' in audio or 'selected' in audio): audio_route='speaker'

screen_state=None
if shutil.which('rish'):
    power=run(['rish','-c','dumpsys power'],3)
    if 'Display Power: state=ON' in power or 'mWakefulness=Awake' in power: screen_state='on'
    elif 'Display Power: state=OFF' in power or 'mWakefulness=Asleep' in power: screen_state='off'

print(json.dumps({'battery_pct':battery,'charging':charging,'power_source':power_source,'connectivity':connectivity,'audio_route':audio_route,'screen_state':screen_state}, separators=(',',':')))`;

function phoneProbeCommand() { return `python -c "import base64;exec(base64.b64decode('${Buffer.from(PHONE_PROBE_PYTHON,'utf8').toString('base64')}'))"`; }
function parsePhoneShellResult(commandRecord={}, nowMs=Date.now()) {
  const commandId=safeText(commandRecord.commandId,180); const terminal=commandRecord.status === 'completed' || commandRecord.status === 'failed'; const shell=commandRecord.result && typeof commandRecord.result === 'object' ? commandRecord.result : {};
  if (!terminal || shell.ok !== true || Number(shell.exitCode) !== 0) return {payload:{},meta:{nowMs,observedAt:new Date(nowMs).toISOString(),source:'phone_hands.phone_shell',receiptId:commandId ? `phone_hands:${commandId}` : undefined,error:safeText(commandRecord.error || shell.stderr || 'phone_observation_unavailable',300)},command:{commandId,status:commandRecord.status || 'unknown',terminal,success:false,exitCode:Number.isFinite(Number(shell.exitCode)) ? Number(shell.exitCode) : null}};
  let payload={};
  try { payload=JSON.parse(safeText(shell.stdout,10000)); } catch (error) { return {payload:{},meta:{nowMs,observedAt:new Date(commandRecord.completedAtMs || nowMs).toISOString(),source:'phone_hands.phone_shell',receiptId:`phone_hands:${commandId}`,error:'phone_observation_invalid_json'},command:{commandId,status:commandRecord.status,terminal:true,success:false,exitCode:Number(shell.exitCode)}}; }
  return {payload,meta:{nowMs,observedAt:new Date(commandRecord.completedAtMs || nowMs).toISOString(),source:'phone_hands.phone_shell',sourceTimestamp:new Date(commandRecord.completedAtMs || nowMs).toISOString(),receiptId:`phone_hands:${commandId}`,confidence:1},command:{commandId,status:commandRecord.status,terminal:true,success:true,exitCode:Number(shell.exitCode)}};
}

function projectionState(projection={}) {
  const value=(slot)=>slot && !slot.unavailable ? slot.value : null;
  return {precipitation:value(projection.environment && projection.environment.precipitation),charging:value(projection.device && projection.device.charging),battery_pct:value(projection.device && projection.device.battery_pct),audio_route:value(projection.device && projection.device.audio_route),connectivity:value(projection.device && projection.device.connectivity),daylight:value(projection.time && projection.time.daylight)};
}

module.exports={DEFAULT_REGION,regionConfig,weatherCodeKind,nearestHourlyProbability,parseOpenMeteo,parseNwsAlerts,fetchJson,openMeteoUrl,nwsAlertsUrl,fetchPublicEnvironment,phoneProbeCommand,parsePhoneShellResult,projectionState,sourceReceipt};
