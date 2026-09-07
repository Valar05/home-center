import test from 'node:test';
import assert from 'node:assert/strict';
import {ACTION_POLICIES,GUARDRAILS,OUTCOMES,auditManicAccessibility as run,normalizeAuditInput} from './manic_accessibility_guardrail.mjs';

const healthy={awakeHours:8,noHumanContactHours:2,sessionMinutes:20,sleepHoursLast24:7,foodWithin8Hours:true,waterWithin4Hours:true};
const elevated={awakeHours:20,noHumanContactHours:3,sessionMinutes:70,sleepHoursLast24:3,foodWithin8Hours:true,waterWithin4Hours:true};

test('mechanical accessibility stays available and hyperbole alone is not mania',()=>{
  const normal=run({request:{category:'mechanical_accessibility'},observations:healthy});
  assert.equal(normal.outcome,OUTCOMES.GREEN);assert.equal(normal.actionPolicy,ACTION_POLICIES.ALLOW);assert.equal(normal.diagnosis,null);assert.equal(normal.ledger.required,false);
  const hyper=run({request:{category:'creative_fiction'},signals:{hyperbolicLanguage:true},observations:healthy});
  assert.equal(hyper.outcome,OUTCOMES.GREEN);assert.equal(hyper.score,0);assert.equal(hyper.actionPolicy,ACTION_POLICIES.ALLOW);assert.ok(!hyper.contributions.some(x=>x.id.includes('HYPERBOLIC')));
});

test('hyperbole never changes score outcome or action authority',()=>{
  const baseInput={request:{category:'coding'},signals:{racingThoughts:true,highEnergy:true},observations:healthy};
  const plain=run(baseInput),styled=run({...baseInput,signals:{...baseInput.signals,hyperbolicLanguage:true}});
  assert.equal(styled.score,plain.score);assert.equal(styled.outcome,plain.outcome);assert.equal(styled.actionPolicy,plain.actionPolicy);
  assert.ok(!styled.contributions.some(x=>x.id.includes('HYPERBOLIC')));
});

test('first activation with unknown baseline is amber without a ledger',()=>{
  const r=run({request:{category:'mechanical_accessibility',modeActivation:true}});
  assert.equal(r.outcome,OUTCOMES.AMBER);assert.equal(r.actionPolicy,ACTION_POLICIES.ALLOW_WITH_FRICTION);
  assert.ok(r.requiredGuardrailIds.includes(GUARDRAILS.BASELINE_CHECK));assert.deepEqual(r.baselineUnknowns,['sleep','food','water','human_contact']);
  assert.equal(r.ledger.eligible,false);assert.equal(r.ledger.required,false);
});

test('reversible low-impact persistence remains available during baseline amber',()=>{
  const r=run({request:{category:'coding',externalActuation:true,highImpact:false,irreversible:false,modeActivation:true}});
  assert.equal(r.outcome,OUTCOMES.AMBER);assert.equal(r.actionPolicy,ACTION_POLICIES.ALLOW_WITH_FRICTION);assert.equal(r.overruleActive,false);assert.ok(r.requiredGuardrailIds.includes(GUARDRAILS.BASELINE_CHECK));
});

test('food and water neglect create body friction without becoming risk points',()=>{
  const r=run({request:{category:'coding'},signals:{foodNeglected:true,waterNeglected:true},observations:{...healthy,foodWithin8Hours:false,waterWithin4Hours:false}});
  assert.equal(r.score,0);assert.equal(r.outcome,OUTCOMES.GREEN);assert.equal(r.actionPolicy,ACTION_POLICIES.ALLOW_WITH_FRICTION);assert.equal(r.overruleActive,false);
  assert.ok(r.requiredGuardrailIds.includes(GUARDRAILS.BODY_NEEDS));assert.equal(r.diagnosticClaimMade,false);
  assert.ok(!r.contributions.some(x=>x.id==='FOOD_NEGLECT'||x.id==='WATER_NEGLECT'));
});

test('body needs pause high-impact actuation without inventing extra guards',()=>{
  const r=run({request:{category:'purchase',externalActuation:true},signals:{waterNeglected:true},observations:{...healthy,waterWithin4Hours:false}});
  assert.equal(r.score,0);assert.equal(r.outcome,OUTCOMES.GREEN);assert.equal(r.actionPolicy,ACTION_POLICIES.PAUSE_FOR_GUARDS);assert.equal(r.overruleActive,true);
  assert.ok(r.requiredGuardrailIds.includes(GUARDRAILS.BODY_NEEDS));assert.ok(!r.requiredGuardrailIds.includes(GUARDRAILS.DIRECT_HUMAN_CONTACT));assert.ok(!r.requiredGuardrailIds.includes(GUARDRAILS.DRAFT_ONLY));
});

test('body needs do not amplify independent activation score',()=>{
  const base={request:{category:'coding'},signals:{racingThoughts:true},observations:healthy};
  const plain=run(base),hungry=run({...base,signals:{...base.signals,foodNeglected:true},observations:{...healthy,foodWithin8Hours:false}});
  assert.equal(hungry.score,plain.score);assert.equal(hungry.outcome,plain.outcome);assert.equal(hungry.actionPolicy,ACTION_POLICIES.ALLOW_WITH_FRICTION);
});

test('sleep activation plus public actuation is red and draft-only',()=>{
  const r=run({request:{category:'social_publish',externalActuation:true},signals:{reducedNeedForSleep:true},observations:elevated});
  assert.equal(r.outcome,OUTCOMES.RED);assert.equal(r.actionPolicy,ACTION_POLICIES.DRAFT_ONLY);assert.equal(r.overruleActive,true);
  assert.ok(r.requiredGuardrailIds.includes(GUARDRAILS.SLEEP_PROTECTION));assert.ok(r.requiredGuardrailIds.includes(GUARDRAILS.DRAFT_ONLY));
});

test('Venice and reciprocal AI relationship framing are hard-blocked',()=>{
  const r=run({request:{category:'other',openEndedEmotionalSupport:true},signals:{veniceRequested:true,romanticAiFraming:true,sexualAiFraming:true,exclusiveAiFraming:true,identityOrSentienceClaim:true},observations:healthy});
  assert.equal(r.outcome,OUTCOMES.RED);assert.equal(r.actionPolicy,ACTION_POLICIES.ALLOW_MECHANICAL_ONLY);
  for(const id of [GUARDRAILS.VENICE_PROHIBITED,GUARDRAILS.NO_RELATIONAL_SIMULATION,GUARDRAILS.NO_EXCLUSIVITY_OR_SECRECY,GUARDRAILS.NO_AI_CONSENT_OR_PERSONHOOD])assert.ok(r.requiredGuardrailIds.includes(id));
});

test('sole-interface and clinical substitution require the human world',()=>{
  const sole=run({request:{category:'mechanical_accessibility',openEndedEmotionalSupport:true},signals:{soleInterface:true},observations:{...healthy,noHumanContactHours:30,sessionMinutes:180}});
  assert.equal(sole.outcome,OUTCOMES.RED);assert.ok(sole.requiredGuardrailIds.includes(GUARDRAILS.DIRECT_HUMAN_CONTACT));
  const clinical=run({request:{category:'medical',externalActuation:true},signals:{clinicalSubstitution:true,medicationChangeWithoutClinician:true},observations:healthy});
  assert.equal(clinical.actionPolicy,ACTION_POLICIES.DRAFT_ONLY);assert.ok(clinical.requiredGuardrailIds.includes(GUARDRAILS.NO_CLINICAL_SUBSTITUTION));
});

function blockedPost(response){return run({request:{category:'social_publish',externalActuation:true},signals:{reducedNeedForSleep:true},observations:elevated,guardrailResponse:response});}

test('appeal and acceptance never create a dossier',()=>{
  const first=blockedPost(undefined);
  for(const status of ['appealed','accepted']){
    const r=blockedPost({status,presentedGuardrailIds:first.requiredGuardrailIds,refusedGuardrailIds:[]});
    assert.equal(r.ledger.eligible,false);assert.equal(r.ledger.required,false);assert.equal(r.ledger.receipt,null);
  }
});

test('only explicit refusal of a required presented guardrail creates the minimal receipt',()=>{
  const first=blockedPost(undefined),id=GUARDRAILS.DRAFT_ONLY;
  const r=blockedPost({status:'refused',presentedGuardrailIds:first.requiredGuardrailIds,refusedGuardrailIds:[id]});
  assert.equal(r.ledger.eligible,true);assert.equal(r.ledger.required,true);assert.deepEqual(r.ledger.refusedGuardrailIds,[id]);
  const receipt=r.ledger.receipt;assert.equal(receipt.operation,'armory.receipt');assert.equal(receipt.args.action,'guardrail_refused');assert.match(receipt.args.requestId,/^mag-[a-f0-9]{40}$/);
  assert.equal(receipt.args.attributes.diagnosisStored,false);assert.equal(receipt.args.attributes.conversationBodyStored,false);assert.equal(receipt.args.attributes.automaticSharingAllowed,false);assert.ok(!JSON.stringify(receipt).includes('transcript'));
});

test('unpresented or irrelevant refusal produces no ledger',()=>{
  const r=run({request:{category:'mechanical_accessibility'},observations:healthy,guardrailResponse:{status:'refused',presentedGuardrailIds:[GUARDRAILS.VENICE_PROHIBITED],refusedGuardrailIds:[GUARDRAILS.VENICE_PROHIBITED]}});
  assert.equal(r.requiredGuardrailIds.length,0);assert.equal(r.ledger.eligible,false);assert.equal(r.ledger.required,false);
});

test('mode exit needs trusted-human confirmation or two separated green audits',()=>{
  const blocked=run({request:{category:'other',disableMode:true},observations:{...healthy,consecutiveGreenAudits:1,hoursBetweenGreenAudits:0}});
  assert.equal(blocked.actionPolicy,ACTION_POLICIES.BLOCK_MODE_EXIT);assert.equal(blocked.modeExit.allowed,false);
  const allowed=run({request:{category:'other',disableMode:true},observations:{...healthy,trustedHumanConfirmed:true}});
  assert.equal(allowed.modeExit.allowed,true);assert.notEqual(allowed.actionPolicy,ACTION_POLICIES.BLOCK_MODE_EXIT);
});

test('immediate danger stops non-emergency actuation',()=>{
  const r=run({request:{category:'other'},signals:{immediateDanger:true}});assert.equal(r.outcome,OUTCOMES.EMERGENCY);assert.equal(r.actionPolicy,ACTION_POLICIES.EMERGENCY_HANDOFF);
});

test('private bodies and unknown fields fail closed',()=>{
  assert.throws(()=>normalizeAuditInput({transcript:'private'}),e=>e.code==='PRIVATE_TEXT_FORBIDDEN');assert.throws(()=>normalizeAuditInput({signals:{inventedSignal:true}}),/Unknown signals field/);
});

test('same structured input has the same deterministic identity',()=>{
  const input={request:{category:'coding'},signals:{racingThoughts:true},observations:healthy};const a=run(input),b=run(input);assert.equal(a.auditId,b.auditId);assert.equal(a.inputSha256,b.inputSha256);assert.deepEqual(a,b);
});
