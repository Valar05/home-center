'use strict';

const crypto = require('node:crypto');
function text(v) { return typeof v === 'string' ? v.trim() : ''; }
function stableId(parts) { return crypto.createHash('sha256').update(parts.join('\n')).digest('hex').slice(0, 16); }

const CLASSIFIERS = [
  { kind: 'retrieval_failure', test: (x) => /assum|didn.?t look|context|lookup|retrieve|look things up/i.test(x) },
  { kind: 'premature_stop', test: (x) => /stop early|quit|documented failure|gave up|came early|one poke|forbid.*stop/i.test(x) },
  { kind: 'handoff_fanout', test: (x) => /multiple scripts|multiple commands|more than one (?:script|command|handoff)|one (?:script|command|handoff) at a time|wait for (?:the )?(?:receipt|output)|consume (?:the )?(?:receipt|output) before|stacked scripts|downstream command/i.test(x) },
  { kind: 'boundary_substitution', test: (x) => /wrong tool|substitut|different lane|adjacent tool|not the lane/i.test(x) },
  { kind: 'correction_regression', test: (x) => /again|regression|forgot|lost context|reintroduced|borked/i.test(x) },
  { kind: 'capability_laundering', test: (x) => /claimed|said.*done|not actually|stub|zero faith|not live|not there/i.test(x) },
  { kind: 'transport_failure', test: (x) => /quot|parser|shell|powershell|syntax|escaped|encoded command|lfs|smudge/i.test(x) },
];
const DEFAULT_RECIPES = Object.freeze({
  retrieval_failure: {rule:'material uncertainty creates a required lookup before execution', regression:'mission with unresolved required lookup must choose retrieve', autoAction:'add_required_lookup_heuristic'},
  premature_stop: {rule:'unfinished work cannot stop without a genuine external boundary requiring operator input', regression:'non-boundary stop reason must choose continue', autoAction:'add_stop_reason_regression'},
  handoff_fanout: {rule:'at a genuine operator-input boundary emit exactly one executable handoff and consume its receipt before another', regression:'operator boundary may expose at most one executable handoff and no downstream executable handoff before receipt consumption', autoAction:'set_single_handoff_gate'},
  boundary_substitution: {rule:'boundary-changing implementation remains proposed until approved', regression:'unapproved lane/tool change must continue original mission', autoAction:'add_boundary_regression'},
  correction_regression: {rule:'new corrections must preserve every earlier non-conflicting lock', regression:'dropping an earlier correction must fail cumulative diff', autoAction:'add_constraint_regression'},
  capability_laundering: {rule:'never advance capability state without state-specific external evidence', regression:'implementation evidence alone cannot prove delivery', autoAction:'add_evidence_regression'},
  transport_failure: {rule:'after a transport failure, switch to a safer deterministic transport and retain the failed form as a regression', regression:'known-fragile transport must be rejected or transformed before dispatch', autoAction:'add_transport_guard'},
  unknown_failure: {rule:'unclassified failures become explicit candidate incidents rather than disappearing', regression:'unknown incident remains pending classification and cannot auto-promote policy', autoAction:'queue_for_classification'},
});
function classifyIncident(input={}) { const corpus=[input.failure,input.correction,input.stderr,input.observation,input.context].map(text).filter(Boolean).join('\n'); const found=CLASSIFIERS.find(c=>c.test(corpus)); return found?found.kind:'unknown_failure'; }
function learnIncident(input={}) { const kind=classifyIncident(input); const recipe=DEFAULT_RECIPES[kind]; const summary=text(input.failure||input.correction||input.observation||input.stderr)||'unspecified incident'; const incidentId=`learned-${kind}-${stableId([kind,summary])}`; return {incident:{id:incidentId,kind,summary,source:text(input.source)||'runtime',observedAt:text(input.observedAt)||new Date().toISOString(),evidence:input.evidence||null},candidateRule:{id:`rule-${stableId([kind,recipe.rule])}`,kind,rule:recipe.rule,status:kind==='unknown_failure'?'needs_classification':'candidate',provenanceIncidentId:incidentId},candidateRegression:{id:`regression-${stableId([kind,recipe.regression,summary])}`,kind,assertion:recipe.regression,fixture:input.fixture||null,provenanceIncidentId:incidentId},autoAction:recipe.autoAction,promotion:{mayMutateV1:false,mayAutoPromote:kind!=='unknown_failure',required:['candidate regression encoded','full V2 suite green','no earlier lock regressed']}}; }
function proposeLearningBatch(incidents=[]) { const learned=incidents.map(learnIncident); const dedup=new Map(); for(const item of learned) dedup.set(item.candidateRegression.id,item); return {learned:[...dedup.values()],candidateCount:dedup.size,autoPromote:true,isolation:'fortress-online-v2'}; }
function promoteLearningBatch(batch={}, validation={}) { const learned=Array.isArray(batch.learned)?batch.learned:[]; const fullSuiteGreen=validation.fullSuiteGreen===true; const noRegression=validation.noEarlierLockRegressed===true; const encoded=new Set(validation.encodedRegressionIds||[]); const promoted=[]; const held=[]; for(const item of learned){ const reasons=[]; if(item.incident.kind==='unknown_failure') reasons.push('needs_classification'); if(!encoded.has(item.candidateRegression.id)) reasons.push('regression_not_encoded'); if(!fullSuiteGreen) reasons.push('full_suite_not_green'); if(!noRegression) reasons.push('earlier_lock_regressed'); if(reasons.length) held.push({item,reasons}); else promoted.push({...item,candidateRule:{...item.candidateRule,status:'active_v2'}}); } return {promoted,held,mayMutateV1:false,isolation:'fortress-online-v2',ok:held.length===0}; }
function learningCycle(incidents=[], validation={}) { const batch=proposeLearningBatch(incidents); const promotion=promoteLearningBatch(batch,validation); return {batch,promotion,activeRules:promotion.promoted.map(x=>x.candidateRule),next:promotion.held.length?'encode_or_classify_held_regressions':'observe_next_incident'}; }
module.exports={CLASSIFIERS,DEFAULT_RECIPES,classifyIncident,learnIncident,proposeLearningBatch,promoteLearningBatch,learningCycle};
