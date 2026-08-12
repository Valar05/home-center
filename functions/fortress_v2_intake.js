'use strict';
const crypto=require('node:crypto');
const {readCampaign,persistCampaign,persistCorrection,persistLearnedRule}=require('./fortress_v2_ledger');
const {learnIncident}=require('./fortress_v2_learning');
function idFor(text){return crypto.createHash('sha256').update(text).digest('hex').slice(0,16);}
function classifyDelta(text=''){const s=String(text).trim();const correction=/fail|failed|wrong|didn.?t|don't|do not|no update|no learning|stop|lost|gloss|assum|retard|sucks/i.test(s);const campaign=/campaign|objective|current|immediate objective|route|boundary|requested|architecture|ledger|continue continue|vlad|computer hands|fortress bridge/i.test(s);return{correction,campaign};}
function ingestUserDelta(text,{source='chat',timestamp=new Date().toISOString()}={}){const raw=String(text||'').trim();if(!raw)throw new Error('FORTRESS_INTAKE_EMPTY');const c=readCampaign()||{id:'unassigned',constraints:[],corrections:[],receipts:[],boundaries:[]};const kind=classifyDelta(raw);c.intake=Array.isArray(c.intake)?c.intake:[];const id=`intake-${idFor(raw)}`;if(!c.intake.some(x=>x.id===id))c.intake.push({id,source,timestamp,text:raw,classification:kind});if(kind.correction){c.corrections=[...new Set([...(c.corrections||[]),raw])];persistCorrection(raw);const learned=learnIncident({correction:raw,source:'fortress-intake'});if(learned.incident.kind!=='unknown_failure')persistLearnedRule(learned);}persistCampaign(c);return{campaignId:c.id,intakeId:id,classification:kind,persisted:true,correctionCount:(c.corrections||[]).length};}
module.exports={classifyDelta,ingestUserDelta};
