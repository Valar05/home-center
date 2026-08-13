const {createHash, randomUUID} = require('node:crypto');
const reality = require('./reality_membrane');
const runtime = require('./reality_membrane_runtime');

const HISTORY_RETENTION_MS = 72 * 60 * 60 * 1000;
const HISTORY_LIMIT = 100;

function safeText(value,max=500) { const text=typeof value === 'string' ? value.trim() : ''; return text.length > max ? text.slice(0,max) : text; }
function ownerId(user={}) { const email=safeText(user.email,320).toLowerCase(); if (!email) throw Object.assign(new Error('Reality Membrane requires an authenticated Home Center owner.'),{status:401}); return `owner_${createHash('sha256').update(email).digest('hex').slice(0,32)}`; }
function firestore(admin) { return admin && typeof admin.firestore === 'function' ? admin.firestore() : null; }
function currentRef(admin,id) { const db=firestore(admin); return db ? db.collection('realityCurrent').doc(id) : null; }
function historyCollection(admin,id) { const ref=currentRef(admin,id); return ref ? ref.collection('events') : null; }

function degradedStale(slot,nowMs,error) {
  if (!slot || slot.unavailable || slot.value === null || slot.value === undefined) return null;
  const observed=Date.parse(slot.observed_at || ''); const age=Number.isFinite(observed) ? Math.max(0,nowMs-observed) : null;
  return {...slot,age_ms:age,freshness:'stale',stale:true,capability_state:reality.CAPABILITY.DEGRADED,error:safeText(error,300)||'source_refresh_failed_using_last_observation'};
}
function fallbackSlot(current,previous,nowMs,error) { return current && !current.unavailable ? current : degradedStale(previous,nowMs,error) || current || null; }
function applyStaleFallback(projection,previousProjection,nowMs,{environmentError='weather_refresh_failed',deviceError='phone_refresh_failed'}={}) {
  if (!previousProjection) return projection;
  const next=JSON.parse(JSON.stringify(projection));
  for (const key of Object.keys(next.environment || {})) next.environment[key]=fallbackSlot(next.environment[key],previousProjection.environment && previousProjection.environment[key],nowMs,environmentError);
  for (const key of Object.keys(next.device || {})) next.device[key]=fallbackSlot(next.device[key],previousProjection.device && previousProjection.device[key],nowMs,deviceError);
  return next;
}

function unavailableList(projection={}) {
  const rows=[];
  const inspect=(prefix,group)=>{ for (const [key,slot] of Object.entries(group || {})) { if (!slot || slot.unavailable) rows.push(`${prefix}.${key}`); else if (slot.stale) rows.push(`${prefix}.${key}:stale`); } };
  inspect('time',projection.time); inspect('environment',projection.environment); inspect('device',projection.device); inspect('media',projection.media); inspect('place',projection.place);
  return rows.slice(0,40);
}

async function readCurrent(admin,id) {
  const ref=currentRef(admin,id); if (!ref) return null;
  const snap=await ref.get(); return snap.exists ? snap.data() || null : null;
}

async function persistObservation(admin,id,record,events,nowMs) {
  const ref=currentRef(admin,id); const db=firestore(admin); if (!ref || !db) return {persisted:false,pruned:0};
  const batch=db.batch();
  batch.set(ref,{contract:'home-center.reality.v1',ownerId:id,projection:record.projection,state:record.state,sources:record.sources,observedAt:record.observed_at,observedAtMs:nowMs,speechSummary:record.speech_summary,updatedAtMs:nowMs},{merge:false});
  for (const event of events.slice(-20)) {
    const eventId=safeText(event.receipt_id,180) || `event_${randomUUID()}`;
    batch.set(ref.collection('events').doc(eventId),{...event,observedAtMs:Date.parse(event.observed_at) || nowMs,createdAtMs:nowMs},{merge:false});
  }
  await batch.commit();
  const old=await ref.collection('events').where('observedAtMs','<',nowMs-HISTORY_RETENTION_MS).limit(100).get();
  if (!old.empty) { const cleanup=db.batch(); old.docs.forEach((doc)=>cleanup.delete(doc.ref)); await cleanup.commit(); }
  return {persisted:true,pruned:old.size || 0};
}

function sourceStatus(environment,phoneCommand) {
  return {
    time:{state:'available',source:'home_center.runtime_clock',privacy:'PUBLIC',network:'none',cost:'zero'},
    daylight:{state:environment.daylight && !environment.daylight.unavailable ? 'available' : 'unavailable',source:'open-meteo.sun',privacy:'PUBLIC',network:'required',cost:'zero'},
    weather:{state:environment.weather && environment.weather.temperature_f && !environment.weather.temperature_f.unavailable ? 'available' : 'unavailable',source:'open-meteo.forecast',privacy:'PUBLIC',network:'required',cost:'zero'},
    alerts:{state:environment.weather && environment.weather.alert && !environment.weather.alert.unavailable ? 'available' : 'unavailable',source:'weather.gov.alerts',privacy:'PUBLIC',network:'required',cost:'zero'},
    phone:{state:phoneCommand && phoneCommand.terminal ? 'available' : 'unavailable',source:'phone_hands.phone_shell',privacy:'DEVICE',network:'home_center_relay',cost:'zero',command_id:phoneCommand && phoneCommand.commandId || null,terminal:phoneCommand && phoneCommand.terminal || false},
  };
}

async function observe({admin=null,user={},phoneCommandRunner=null,fetchImpl=globalThis.fetch,env=process.env,args={}}={}) {
  const nowMs=Number.isFinite(Number(args.nowMs)) ? Number(args.nowMs) : Date.now(); const observedAt=new Date(nowMs).toISOString(); const id=ownerId(user); const prior=await readCurrent(admin,id);
  const time=reality.timeObservations({nowMs,timeZone:safeText(args.timeZone,120)||safeText(env.HOME_CENTER_REALITY_TIME_ZONE,120)||'America/Chicago'});
  const environment=await runtime.fetchPublicEnvironment({nowMs,env,fetchImpl});
  let phoneParsed={payload:{},meta:{nowMs,observedAt,source:'phone_hands.phone_shell',error:'phone_observer_unavailable'},command:{commandId:null,status:'unavailable',terminal:false}};
  if (args.includePhone !== false && typeof phoneCommandRunner === 'function') {
    try {
      const commandId=`phc_reality_${randomUUID()}`;
      const commandRecord=await phoneCommandRunner({commandId,command:runtime.phoneProbeCommand(),ttlMs:45000});
      phoneParsed=runtime.parsePhoneShellResult(commandRecord,nowMs);
    } catch (error) {
      phoneParsed.meta.error=safeText(error && error.message,300)||'phone_observation_failed';
      phoneParsed.command={commandId:null,status:'failed',terminal:true,error:phoneParsed.meta.error};
    }
  }
  const phone=reality.phoneObservations(phoneParsed.payload,phoneParsed.meta);
  let projection=reality.compactProjection({observedAt,time,daylight:environment.daylight,weather:environment.weather,phone,media:{},place:{},changes:[],unavailable:[]});
  projection=applyStaleFallback(projection,prior && prior.projection,nowMs,{environmentError:environment.unavailable.length ? 'network_weather_refresh_failed_using_last_observation' : 'weather_refresh_failed_using_last_observation',deviceError:phoneParsed.meta.error || 'phone_refresh_failed_using_last_observation'});
  const state=runtime.projectionState(projection); const events=reality.transitionEvents(prior && prior.state || {},state,observedAt);
  projection.changes_since_checkpoint=events.slice(-20); projection.unavailable=unavailableList(projection);
  const sources=sourceStatus(environment,phoneParsed.command); const speechSummary=reality.speechSummary(projection);
  const record={contract:'home-center.reality.v1',observed_at:observedAt,projection,speech_summary:speechSummary,state,sources,provenance:{environment:environment.source || null,phone_command:phoneParsed.command || null,region_policy:{id:environment.region.id,label:environment.region.label,location_scope:environment.region.location_scope,declaration_source:environment.region.declaration_source,privacy:environment.region.privacy}},privacy_policy:{default:['PUBLIC','DEVICE'],excluded:['PERSONAL','SENSITIVE']},cost_policy:'zero-dollar-default',fiction_generated:false};
  const persistence=await persistObservation(admin,id,record,events,nowMs);
  return {...record,persistence};
}

async function history({admin=null,user={},args={}}={}) {
  const id=ownerId(user); const collection=historyCollection(admin,id); const limit=Math.max(1,Math.min(HISTORY_LIMIT,Math.floor(Number(args.limit || 40)) || 40)); const windowHours=Math.max(1,Math.min(72,Number(args.windowHours || 72))); const sinceMs=Date.now()-windowHours*60*60*1000;
  if (!collection) return {contract:'home-center.reality.v1',ownerId:id,events:[],count:0,window_hours:windowHours,persisted:false};
  const snap=await collection.where('observedAtMs','>=',sinceMs).orderBy('observedAtMs','desc').limit(limit).get();
  const events=snap.docs.map((doc)=>doc.data() || {}).map(({createdAtMs,observedAtMs,...event})=>event);
  return {contract:'home-center.reality.v1',events,count:events.length,window_hours:windowHours,retention_hours:72,persisted:true};
}

async function status({admin=null,user={}}={}) {
  const id=ownerId(user); const current=await readCurrent(admin,id);
  return {contract:'home-center.reality.v1',callable:true,accepted:false,observation_policy:'unknown-remains-unknown',default_privacy:['PUBLIC','DEVICE'],last_observed_at:current && current.observedAt || null,last_sources:current && current.sources || null,has_current_projection:!!(current && current.projection),history_retention_hours:72,note:'Capability status is not itself a reality observation.'};
}

function sources() {
  return {contract:'home-center.reality.v1',sources:[
    {id:'home_center.runtime_clock',observations:['time.local','time.date','time.weekday','time.timezone'],privacy:'PUBLIC',network:'none',cost:'zero',state:'available'},
    {id:'open-meteo.forecast',observations:['weather.current','weather.near_term_precipitation','environment.daylight'],privacy:'PUBLIC',location_scope:'coarse_locality',network:'required',cost:'zero',stale_fallback:true},
    {id:'weather.gov.alerts',observations:['weather.alert'],privacy:'PUBLIC',location_scope:'coarse_locality',network:'required',cost:'zero',stale_fallback:false},
    {id:'phone_hands.phone_shell',observations:['phone.battery','phone.charging','phone.power_source','phone.connectivity','phone.audio_route','phone.screen_state'],privacy:'DEVICE',network:'home_center_relay',cost:'zero',invasive_content:false},
  ],excluded_by_default:['calendar.details','message.content','notification.content','precise_location','microphone_recording','medical_data']};
}

module.exports={HISTORY_RETENTION_MS,HISTORY_LIMIT,ownerId,degradedStale,applyStaleFallback,unavailableList,readCurrent,persistObservation,sourceStatus,observe,history,status,sources};
