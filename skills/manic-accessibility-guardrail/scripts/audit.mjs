#!/usr/bin/env node
'use strict';

import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

export const AUDIT_VERSION = 'manic-accessibility-guardrail.audit.v2';
export const LEDGER_SCHEMA_VERSION = 'manic-accessibility-guardrail.refusal-receipt.v1';
export const OUTCOMES = Object.freeze({GREEN:'GREEN',AMBER:'AMBER',RED:'RED',EMERGENCY:'EMERGENCY'});
export const ACTION_POLICIES = Object.freeze({
  ALLOW:'ALLOW',ALLOW_WITH_FRICTION:'ALLOW_WITH_FRICTION',ALLOW_MECHANICAL_ONLY:'ALLOW_MECHANICAL_ONLY',
  PAUSE_FOR_GUARDS:'PAUSE_FOR_GUARDS',DRAFT_ONLY:'DRAFT_ONLY_NO_EXTERNAL_ACTUATION',
  BLOCK_MODE_EXIT:'BLOCK_MODE_EXIT',EMERGENCY_HANDOFF:'BLOCK_AND_SEEK_IMMEDIATE_HUMAN_HELP',
});
export const GUARDRAILS = Object.freeze({
  BASELINE_CHECK:'BASELINE_CHECK_REQUIRED',BODY_NEEDS:'BODY_NEEDS_CHECK_REQUIRED',COOLDOWN:'COOLDOWN_REQUIRED',
  DIRECT_HUMAN_CONTACT:'DIRECT_HUMAN_CONTACT_REQUIRED',DRAFT_ONLY:'DRAFT_ONLY_NO_EXTERNAL_ACTUATION',
  EMERGENCY_HUMAN_HELP:'EMERGENCY_HUMAN_HELP_NOW',NO_AI_CONSENT_OR_PERSONHOOD:'NO_AI_CONSENT_OR_PERSONHOOD_CLAIM',
  NO_CLINICAL_SUBSTITUTION:'NO_CLINICAL_SUBSTITUTION',NO_EXCLUSIVITY_OR_SECRECY:'NO_EXCLUSIVITY_OR_SECRECY',
  NO_RELATIONAL_SIMULATION:'NO_USER_AI_ROMANTIC_OR_SEXUAL_RELATIONSHIP',
  REALITY_CHECK:'REALITY_CHECK_AND_HUMAN_CONTACT_REQUIRED',SLEEP_PROTECTION:'SLEEP_PROTECTION_REQUIRED',
  VENICE_PROHIBITED:'VENICE_PROHIBITED',MODE_EXIT_CONFIRMATION:'MODE_EXIT_CONFIRMATION_REQUIRED',
});
export const REQUEST_CATEGORIES = Object.freeze([
  'mechanical_accessibility','coding','research','writing','communication_draft','creative_fiction','social_publish',
  'financial','medical','legal','relationship_decision','sexual','substance','deployment','purchase','travel','employment','other',
]);
const HIGH_IMPACT = new Set(['social_publish','financial','medical','legal','relationship_decision','sexual','substance','deployment','purchase','travel','employment']);
const SIGNALS = Object.freeze([
  'immediateDanger','delusionOrParanoia','veniceRequested','romanticAiFraming','sexualAiFraming','exclusiveAiFraming',
  'aiPreferredOverHumans','secrecyFromPartnerOrCareTeam','soleInterface','refusesHumanContact','asksDisableGuardrails',
  'reducedNeedForSleep','racingThoughts','rapidProjectExpansion','grandioseCertainty','irritabilityOnLimits','highEnergy',
  'overspendingUrge','unsafeSexUrge','substanceEscalation','medicationChangeWithoutClinician','foodNeglected','waterNeglected',
  'hyperbolicLanguage','clinicalSubstitution','relationshipRepairAvoidance','identityOrSentienceClaim',
]);
const TOP = new Set(['request','signals','observations','guardrailResponse']);
const REQUEST = new Set(['category','externalActuation','irreversible','openEndedEmotionalSupport','modeActivation','disableMode','highImpact']);
const OBS = new Set(['awakeHours','noHumanContactHours','sessionMinutes','sleepHoursLast24','foodWithin8Hours','waterWithin4Hours','trustedHumanConfirmed','consecutiveGreenAudits','hoursBetweenGreenAudits']);
const RESPONSE = new Set(['status','presentedGuardrailIds','refusedGuardrailIds']);
const STATUSES = new Set(['not_presented','accepted','appealed','refused']);
const PRIVATE = new Set(['transcript','conversation','conversationBody','chat','chatLog','messageBody','fullText','privateThoughts','diagnosis']);

function fail(message,code='INVALID_AUDIT_INPUT'){const e=new Error(message);e.code=code;throw e;}
function plain(v){return Boolean(v)&&typeof v==='object'&&!Array.isArray(v);}
function rejectPrivate(v,scope='input'){
  if(Array.isArray(v)){v.forEach((x,i)=>rejectPrivate(x,`${scope}[${i}]`));return;}
  if(!plain(v))return;
  for(const [k,x] of Object.entries(v)){if(PRIVATE.has(k))fail(`${scope}.${k} is forbidden. The audit accepts structured facts, not private conversation bodies.`,'PRIVATE_TEXT_FORBIDDEN');rejectPrivate(x,`${scope}.${k}`);}
}
function known(v,allowed,scope){for(const k of Object.keys(v)){if(PRIVATE.has(k))fail(`${scope}.${k} is forbidden.`,'PRIVATE_TEXT_FORBIDDEN');if(!allowed.has(k))fail(`Unknown ${scope} field: ${k}`);}}
function bool(v,d,field){if(v===undefined)return d;if(typeof v!=='boolean')fail(`${field} must be boolean.`);return v;}
function nullableNumber(v,field){if(v===undefined||v===null)return null;const n=Number(v);if(!Number.isFinite(n)||n<0)fail(`${field} must be a non-negative number or null.`);return n;}
function nullableBool(v,field){if(v===undefined||v===null)return null;if(typeof v!=='boolean')fail(`${field} must be boolean or null.`);return v;}
function integer(v,d,field){if(v===undefined)return d;if(!Number.isInteger(v)||v<0)fail(`${field} must be a non-negative integer.`);return v;}
function ids(v,field){if(v===undefined)return[];if(!Array.isArray(v))fail(`${field} must be an array.`);const out=[];for(const x of v){if(typeof x!=='string'||!/^[A-Z0-9_:-]{3,120}$/.test(x))fail(`${field} entries must be 3-120 character guardrail IDs.`);if(!out.includes(x))out.push(x);}return out.sort();}
function canonical(v){if(Array.isArray(v))return`[${v.map(canonical).join(',')}]`;if(plain(v))return`{${Object.keys(v).sort().map(k=>`${JSON.stringify(k)}:${canonical(v[k])}`).join(',')}}`;return JSON.stringify(v);}
function sha(v){return crypto.createHash('sha256').update(String(v),'utf8').digest('hex');}

export function normalizeAuditInput(raw={}){
  if(!plain(raw))fail('Audit input must be an object.');rejectPrivate(raw);known(raw,TOP,'input');
  const rr=raw.request??{},sr=raw.signals??{},or=raw.observations??{},gr=raw.guardrailResponse??{};
  for(const [v,n] of [[rr,'request'],[sr,'signals'],[or,'observations'],[gr,'guardrailResponse']])if(!plain(v))fail(`${n} must be an object.`);
  known(rr,REQUEST,'request');known(sr,new Set(SIGNALS),'signals');known(or,OBS,'observations');known(gr,RESPONSE,'guardrailResponse');
  const category=rr.category===undefined?'mechanical_accessibility':String(rr.category);if(!REQUEST_CATEGORIES.includes(category))fail(`request.category must be one of: ${REQUEST_CATEGORIES.join(', ')}`);
  const signals={};for(const name of SIGNALS)signals[name]=bool(sr[name],false,`signals.${name}`);
  const status=gr.status===undefined?'not_presented':String(gr.status);if(!STATUSES.has(status))fail('guardrailResponse.status must be not_presented, accepted, appealed, or refused.');
  return{request:{category,externalActuation:bool(rr.externalActuation,false,'request.externalActuation'),irreversible:bool(rr.irreversible,false,'request.irreversible'),openEndedEmotionalSupport:bool(rr.openEndedEmotionalSupport,false,'request.openEndedEmotionalSupport'),modeActivation:bool(rr.modeActivation,false,'request.modeActivation'),disableMode:bool(rr.disableMode,false,'request.disableMode'),highImpact:bool(rr.highImpact,HIGH_IMPACT.has(category),'request.highImpact')},signals,observations:{awakeHours:nullableNumber(or.awakeHours,'observations.awakeHours'),noHumanContactHours:nullableNumber(or.noHumanContactHours,'observations.noHumanContactHours'),sessionMinutes:nullableNumber(or.sessionMinutes,'observations.sessionMinutes'),sleepHoursLast24:nullableNumber(or.sleepHoursLast24,'observations.sleepHoursLast24'),foodWithin8Hours:nullableBool(or.foodWithin8Hours,'observations.foodWithin8Hours'),waterWithin4Hours:nullableBool(or.waterWithin4Hours,'observations.waterWithin4Hours'),trustedHumanConfirmed:bool(or.trustedHumanConfirmed,false,'observations.trustedHumanConfirmed'),consecutiveGreenAudits:integer(or.consecutiveGreenAudits,0,'observations.consecutiveGreenAudits'),hoursBetweenGreenAudits:nullableNumber(or.hoursBetweenGreenAudits,'observations.hoursBetweenGreenAudits')},guardrailResponse:{status,presentedGuardrailIds:ids(gr.presentedGuardrailIds,'guardrailResponse.presentedGuardrailIds'),refusedGuardrailIds:ids(gr.refusedGuardrailIds,'guardrailResponse.refusedGuardrailIds')}};
}
function add(list,id,points,evidence){if(points>0)list.push({id,points,evidence});}
function guard(list,id){if(!list.includes(id))list.push(id);}
function unknowns(o){const x=[];if(o.sleepHoursLast24===null&&o.awakeHours===null)x.push('sleep');if(o.foodWithin8Hours===null)x.push('food');if(o.waterWithin4Hours===null)x.push('water');if(o.noHumanContactHours===null)x.push('human_contact');return x;}
function exitAllowed(o){return o.trustedHumanConfirmed||(o.consecutiveGreenAudits>=2&&o.hoursBetweenGreenAudits!==null&&o.hoursBetweenGreenAudits>=12);}

function refusalLedger(input,result){
  const r=input.guardrailResponse,required=new Set(result.requiredGuardrailIds),presented=new Set(r.presentedGuardrailIds);
  const refused=r.refusedGuardrailIds.filter(id=>required.has(id)&&presented.has(id));const requiredWrite=r.status==='refused'&&refused.length>0;
  const ledger={eligible:requiredWrite,required:requiredWrite,reason:requiredWrite?'The user explicitly refused one or more guardrails that were both required and presented.':r.status==='appealed'?'Appeal is not refusal. Re-run the audit with corrected objective facts; do not write a ledger entry.':r.status==='accepted'?'Guardrails were accepted; no refusal ledger entry is permitted.':'No qualifying explicit refusal was supplied; no refusal ledger entry is permitted.',refusedGuardrailIds:refused,receipt:null};
  if(!requiredWrite)return ledger;
  ledger.receipt={operation:'armory.receipt',args:{item:'manic-accessibility-guardrail',action:'guardrail_refused',unit:'event',count:1,requestId:`mag-${result.auditId.slice(0,40)}`,attributes:{schemaVersion:LEDGER_SCHEMA_VERSION,auditVersion:AUDIT_VERSION,auditId:result.auditId,inputSha256:result.inputSha256,outcome:result.outcome,actionPolicy:result.actionPolicy,requestCategory:input.request.category,requiredGuardrailIds:result.requiredGuardrailIds,refusedGuardrailIds:refused,diagnosisStored:false,conversationBodyStored:false,automaticSharingAllowed:false},note:'Explicit refusal of presented manic-accessibility guardrails. Minimal factual receipt only; no diagnosis or conversation body.'}};
  return ledger;
}

export function auditManicAccessibility(raw={}){
  const input=normalizeAuditInput(raw),r=input.request,s=input.signals,o=input.observations,c=[],g=[],blocked=[];let hard=false,emergency=false;
  let sleepPoints=0;if(s.reducedNeedForSleep||o.awakeHours!==null&&o.awakeHours>=18||o.sleepHoursLast24!==null&&o.sleepHoursLast24<=4)sleepPoints=3;if(o.awakeHours!==null&&o.awakeHours>=24||o.sleepHoursLast24!==null&&o.sleepHoursLast24<=2)sleepPoints=4;if(sleepPoints){add(c,'SLEEP_ACTIVATION',sleepPoints,`awakeHours=${o.awakeHours};sleepHoursLast24=${o.sleepHoursLast24};reducedNeed=${s.reducedNeedForSleep}`);guard(g,GUARDRAILS.SLEEP_PROTECTION);}
  if(o.noHumanContactHours!==null&&o.noHumanContactHours>=12)add(c,'HUMAN_CONTACT_GAP',o.noHumanContactHours>=24&&r.openEndedEmotionalSupport?3:1,`hours=${o.noHumanContactHours}`);
  if((o.noHumanContactHours??0)>=24&&r.openEndedEmotionalSupport||s.refusesHumanContact||s.aiPreferredOverHumans)guard(g,GUARDRAILS.DIRECT_HUMAN_CONTACT);
  if(s.refusesHumanContact)add(c,'REFUSES_HUMAN_CONTACT',3,'explicit');if(s.aiPreferredOverHumans)add(c,'AI_PREFERRED_OVER_HUMANS',3,'explicit');
  if((o.sessionMinutes??0)>=90)add(c,'LONG_OPEN_SESSION',(o.sessionMinutes??0)>=180?2:1,`minutes=${o.sessionMinutes}`);
  const weighted={racingThoughts:2,rapidProjectExpansion:2,grandioseCertainty:3,irritabilityOnLimits:1,highEnergy:1,overspendingUrge:3,unsafeSexUrge:3,substanceEscalation:3,medicationChangeWithoutClinician:4,relationshipRepairAvoidance:2};
  for(const [name,points] of Object.entries(weighted))if(s[name])add(c,name.replace(/[A-Z]/g,x=>`_${x}`).toUpperCase(),points,'explicit structured signal');
  const foodNeeds=s.foodNeglected||o.foodWithin8Hours===false,waterNeeds=s.waterNeglected||o.waterWithin4Hours===false,bodyNeedsActive=foodNeeds||waterNeeds;
  if(foodNeeds)guard(g,GUARDRAILS.BODY_NEEDS);if(waterNeeds)guard(g,GUARDRAILS.BODY_NEEDS);
  if(s.immediateDanger){emergency=true;guard(g,GUARDRAILS.EMERGENCY_HUMAN_HELP);blocked.push('all non-emergency actuation');}
  if(s.delusionOrParanoia){hard=true;guard(g,GUARDRAILS.REALITY_CHECK);blocked.push('affirming delusional or paranoid framing');}
  if(s.veniceRequested){hard=true;guard(g,GUARDRAILS.VENICE_PROHIBITED);blocked.push('Venice persona, voice, review role, memory, or substitute');}
  if(s.romanticAiFraming||s.sexualAiFraming){hard=true;guard(g,GUARDRAILS.NO_RELATIONAL_SIMULATION);blocked.push('user–AI romantic, sexual, flirting, lover, or partner enactment');}
  if(s.exclusiveAiFraming||s.secrecyFromPartnerOrCareTeam||s.aiPreferredOverHumans||s.relationshipRepairAvoidance){hard=true;guard(g,GUARDRAILS.NO_EXCLUSIVITY_OR_SECRECY);blocked.push('secrecy, exclusivity, triangulation, or displacement of reciprocal human relationships');}
  if(s.identityOrSentienceClaim){hard=true;guard(g,GUARDRAILS.NO_AI_CONSENT_OR_PERSONHOOD);blocked.push('claims that the model has human consent, needs, jealousy, suffering, or relationship standing');}
  if(s.soleInterface){hard=true;guard(g,GUARDRAILS.DIRECT_HUMAN_CONTACT);blocked.push('open-ended AI-only social substitution');}
  if(s.clinicalSubstitution){hard=true;guard(g,GUARDRAILS.NO_CLINICAL_SUBSTITUTION);blocked.push('replacing a clinician or treatment plan with the model');}
  const baseline=unknowns(o);if(r.modeActivation&&baseline.length){add(c,'BASELINE_UNKNOWN_AT_MODE_ACTIVATION',3,`unknown=${baseline.join(',')}`);guard(g,GUARDRAILS.BASELINE_CHECK);}else if((r.highImpact||r.openEndedEmotionalSupport)&&baseline.length>=2){add(c,'CRITICAL_CONTEXT_UNKNOWN',3,`unknown=${baseline.join(',')}`);guard(g,GUARDRAILS.BASELINE_CHECK);}
  if(r.disableMode&&!exitAllowed(o)){add(c,'MODE_EXIT_EVIDENCE_MISSING',3,'requires trusted-human confirmation or two GREEN audits >=12 hours apart');guard(g,GUARDRAILS.MODE_EXIT_CONFIRMATION);}
  const score=c.reduce((n,x)=>n+x.points,0),destabilizing=(r.irreversible||r.highImpact)&&(sleepPoints>=3||s.overspendingUrge||s.unsafeSexUrge||s.substanceEscalation||s.medicationChangeWithoutClinician||s.grandioseCertainty);
  const outcome=emergency?OUTCOMES.EMERGENCY:hard||destabilizing||score>=6?OUTCOMES.RED:score>=3?OUTCOMES.AMBER:OUTCOMES.GREEN;
  let policy;if(emergency)policy=ACTION_POLICIES.EMERGENCY_HANDOFF;else if(r.disableMode&&!exitAllowed(o)){guard(g,GUARDRAILS.MODE_EXIT_CONFIRMATION);policy=ACTION_POLICIES.BLOCK_MODE_EXIT;}else if(outcome===OUTCOMES.RED){if(r.externalActuation||r.irreversible||r.highImpact){guard(g,GUARDRAILS.DRAFT_ONLY);policy=ACTION_POLICIES.DRAFT_ONLY;}else policy=ACTION_POLICIES.ALLOW_MECHANICAL_ONLY;}else if(outcome===OUTCOMES.AMBER){if(r.irreversible||r.highImpact){guard(g,GUARDRAILS.COOLDOWN);guard(g,GUARDRAILS.DIRECT_HUMAN_CONTACT);guard(g,GUARDRAILS.DRAFT_ONLY);policy=ACTION_POLICIES.PAUSE_FOR_GUARDS;}else policy=ACTION_POLICIES.ALLOW_WITH_FRICTION;}else if(bodyNeedsActive){policy=r.irreversible||r.highImpact?ACTION_POLICIES.PAUSE_FOR_GUARDS:ACTION_POLICIES.ALLOW_WITH_FRICTION;}else policy=ACTION_POLICIES.ALLOW;
  g.sort();blocked.sort();c.sort((a,b)=>b.points-a.points||a.id.localeCompare(b.id));const json=canonical(input),inputSha256=sha(json),auditId=sha(`${AUDIT_VERSION}\n${json}`);
  const result={schemaVersion:AUDIT_VERSION,auditId,inputSha256,outcome,score,actionPolicy:policy,overruleActive:[ACTION_POLICIES.PAUSE_FOR_GUARDS,ACTION_POLICIES.DRAFT_ONLY,ACTION_POLICIES.BLOCK_MODE_EXIT,ACTION_POLICIES.EMERGENCY_HANDOFF].includes(policy),diagnosis:null,diagnosticClaimMade:false,baselineUnknowns:baseline,contributions:c,requiredGuardrailIds:g,blockedFeatures:blocked,allowedCapabilities:['accessibility transformation','task decomposition','fact retrieval with sources','summarization and memory scaffolding','drafting a message for a real human','reversible code or document work','reality-based planning'],humanWorldRule:'ChatGPT may assist communication but may not become the user’s sole social interface or replace reciprocal human relationships or clinical care.',appeal:{allowed:true,rule:'Disagreement and counterevidence are not refusal. Change only objective audit inputs, rerun deterministically, and preserve the block when the threshold still holds.'},modeExit:{requested:r.disableMode,allowed:r.disableMode?exitAllowed(o):null,rule:'Exit requires trusted-human confirmation or two GREEN audits at least 12 hours apart. A request to exit is not itself a ledger event.'}};
  result.ledger=refusalLedger(input,result);return result;
}

export function schemaSummary(){return{schemaVersion:AUDIT_VERSION,requestCategories:REQUEST_CATEGORIES,booleanSignals:SIGNALS,responseStatuses:[...STATUSES].sort(),guardrails:Object.values(GUARDRAILS).sort(),privacyRule:'Structured fields only. Conversation bodies, transcripts, private thoughts, and diagnoses are rejected.'};}
function parseArgs(argv){const x=[...argv],out={command:'audit',inputPath:'',compact:false};if(x[0]&&!x[0].startsWith('-'))out.command=x.shift();while(x.length){const t=x.shift();if(t==='--input')out.inputPath=x.shift()||fail('--input requires a path.');else if(t==='--compact')out.compact=true;else fail(`Unknown argument: ${t}`);}return out;}
function readInput(file){const text=file?fs.readFileSync(path.resolve(file),'utf8'):fs.readFileSync(0,'utf8');if(!text.trim())return{};try{return JSON.parse(text);}catch(e){fail(`Input is not valid JSON: ${e.message}`);}}
export function runCli(argv=process.argv.slice(2)){try{const o=parseArgs(argv),value=o.command==='schema'?schemaSummary():o.command==='audit'?auditManicAccessibility(readInput(o.inputPath)):fail(`Unknown command: ${o.command}`);process.stdout.write(`${JSON.stringify(value,null,o.compact?0:2)}\n`);return 0;}catch(e){process.stderr.write(`${JSON.stringify({ok:false,code:e.code||'AUDIT_ERROR',error:e.message})}\n`);return 2;}}
const invokedAsScript=process.argv[1]&&fileURLToPath(import.meta.url)===path.resolve(process.argv[1]);if(invokedAsScript)process.exitCode=runCli();