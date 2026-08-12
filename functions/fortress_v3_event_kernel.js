'use strict';
const fs=require('node:fs');
const path=require('node:path');
const crypto=require('node:crypto');

const EVENT_VERSION=1;
function canonical(v){return JSON.stringify(v,Object.keys(v||{}).sort());}
function hash(v){return crypto.createHash('sha256').update(typeof v==='string'?v:JSON.stringify(v)).digest('hex');}
function ensureDir(file){fs.mkdirSync(path.dirname(path.resolve(file)),{recursive:true});}
function eventId(e){return `evt-${hash([e.type,e.campaignId||'',e.text||'',e.data||null,e.receipt||null,e.timestamp||''].map(x=>JSON.stringify(x)).join('\n')).slice(0,20)}`;}
function normalizeEvent(input={}){
  const e={version:EVENT_VERSION,type:String(input.type||'').trim(),campaignId:input.campaignId?String(input.campaignId).trim():null,text:input.text===undefined?null:String(input.text),data:input.data&&typeof input.data==='object'?input.data:null,receipt:input.receipt&&typeof input.receipt==='object'?input.receipt:null,timestamp:String(input.timestamp||new Date().toISOString()),source:String(input.source||'unknown')};
  if(!e.type) throw new Error('FORTRESS_V3_EVENT_TYPE_REQUIRED');
  e.id=input.id||eventId(e);
  return e;
}
function appendEvent(file,input){
  const e=normalizeEvent(input); ensureDir(file);
  const line=JSON.stringify(e)+'\n';
  if(fs.existsSync(file)){
    const text=fs.readFileSync(file,'utf8');
    if(text.split('\n').some(x=>x&&JSON.parse(x).id===e.id)) return {event:e,appended:false};
  }
  fs.appendFileSync(file,line,{encoding:'utf8',flag:'a'});
  return {event:e,appended:true};
}
function readEvents(file){if(!fs.existsSync(file))return[];return fs.readFileSync(file,'utf8').split('\n').filter(Boolean).map((line,i)=>{try{return normalizeEvent(JSON.parse(line));}catch(err){throw new Error(`FORTRESS_V3_EVENT_LOG_CORRUPT:${i+1}:${err.message}`);}});}
function blankState(){return{version:3,activeCampaignId:null,campaigns:{},global:{corrections:[],constraints:[],capabilities:{},failures:[],receipts:[]},unresolvedInputs:[],lastEventId:null};}
function campaign(state,id){if(!id)throw new Error('FORTRESS_V3_CAMPAIGN_REQUIRED');if(!state.campaigns[id])state.campaigns[id]={id,objective:'',owner:'Drew Clarke',status:'active',constraints:[],corrections:[],boundaries:[],receipts:[],facts:{},history:[]};return state.campaigns[id];}
function apply(state,input){const e=normalizeEvent(input);const s=structuredClone(state||blankState());s.lastEventId=e.id;
  switch(e.type){
    case 'user.input': s.unresolvedInputs.push({eventId:e.id,text:e.text,source:e.source,timestamp:e.timestamp,campaignHint:e.campaignId}); break;
    case 'campaign.activate': campaign(s,e.campaignId); s.activeCampaignId=e.campaignId; break;
    case 'campaign.define': {const c=campaign(s,e.campaignId);Object.assign(c,e.data||{});c.id=e.campaignId;break;}
    case 'campaign.constraint': {const c=campaign(s,e.campaignId);if(e.text&&!c.constraints.includes(e.text))c.constraints.push(e.text);break;}
    case 'campaign.correction': {const c=campaign(s,e.campaignId);if(e.text&&!c.corrections.includes(e.text))c.corrections.push(e.text);if(e.text&&!s.global.corrections.includes(e.text))s.global.corrections.push(e.text);break;}
    case 'campaign.boundary.set': {const c=campaign(s,e.campaignId);const b=e.data||{};if(!b.id)throw new Error('FORTRESS_V3_BOUNDARY_ID_REQUIRED');const i=c.boundaries.findIndex(x=>x.id===b.id);const next={id:b.id,description:b.description||'',requiresOperator:b.requiresOperator===true,satisfied:b.satisfied===true,handoff:b.handoff||null,evidence:Array.isArray(b.evidence)?b.evidence:[]};if(i>=0)c.boundaries[i]={...c.boundaries[i],...next};else c.boundaries.push(next);break;}
    case 'campaign.receipt': {const c=campaign(s,e.campaignId);if(!e.receipt)throw new Error('FORTRESS_V3_RECEIPT_REQUIRED');c.receipts.push(e.receipt);s.global.receipts.push({campaignId:e.campaignId,...e.receipt});if(e.receipt.ok===true&&e.receipt.boundaryId){const b=c.boundaries.find(x=>x.id===e.receipt.boundaryId);if(b){b.satisfied=true;b.evidence=[...(b.evidence||[]),e.receipt];}}break;}
    case 'failure.record': s.global.failures.push({campaignId:e.campaignId,text:e.text,data:e.data,timestamp:e.timestamp,eventId:e.id}); break;
    case 'capability.set': if(e.data?.id)s.global.capabilities[e.data.id]={...e.data,eventId:e.id}; else throw new Error('FORTRESS_V3_CAPABILITY_ID_REQUIRED'); break;
    case 'input.resolve': s.unresolvedInputs=s.unresolvedInputs.filter(x=>x.eventId!==e.data?.eventId); break;
    default: throw new Error(`FORTRESS_V3_UNKNOWN_EVENT:${e.type}`);
  }
  if(e.campaignId&&s.campaigns[e.campaignId])s.campaigns[e.campaignId].history.push(e.id);
  return s;
}
function reduce(events){return events.reduce((s,e)=>apply(s,e),blankState());}
function nextAction(state){const id=state.activeCampaignId;if(!id)return{type:'select_campaign',reason:'no_active_campaign'};const c=state.campaigns[id];const b=(c.boundaries||[]).find(x=>!x.satisfied);if(!b)return{type:'verify_completion',campaignId:id};if(b.requiresOperator){if(!b.handoff?.command)return{type:'repair_boundary',campaignId:id,boundaryId:b.id,reason:'missing_executable_handoff'};return{type:'operator_handoff',campaignId:id,boundaryId:b.id,handoff:b.handoff};}return{type:'execute',campaignId:id,boundaryId:b.id};}
function snapshotFromLog(file){const events=readEvents(file);return{events,state:reduce(events),next:nextAction(reduce(events))};}
module.exports={EVENT_VERSION,normalizeEvent,appendEvent,readEvents,blankState,apply,reduce,nextAction,snapshotFromLog};
