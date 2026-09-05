import test from 'node:test';
import assert from 'node:assert/strict';
import {POLICIES,runCommunicationCodec as run} from '../skills/manic-accessibility-guardrail/scripts/communication-codec.mjs';

test('engineering vocabulary is reused as a compact pointer',()=>{
  const r=run({atom:'canary',establishedEngineeringTerm:true,sharedConcept:true});
  assert.equal(r.policy,POLICIES.COMPACT_POINTER);
  assert.equal(r.preserveExactAtom,true);
  assert.equal(r.stopRule,'STOP_WHEN_MEANING_LANDS');
});

test('shared concept stays compressed until behavior shows a missing edge',()=>{
  const compact=run({atom:'ASMR',sharedConcept:true});
  assert.equal(compact.policy,POLICIES.COMPACT_POINTER);
  const mismatch=run({atom:'ASMR',sharedConcept:true,observedSemanticMismatch:true,readbackAvailable:true});
  assert.equal(mismatch.policy,POLICIES.MINIMAL_GROUNDING);
  assert.equal(mismatch.verification,'READBACK_OR_OBSERVE');
});

test('consequential ambiguity defeats compression',()=>{
  const r=run({atom:'waltz',privateHandle:true,consequentialAmbiguity:true,reversibleProbeAvailable:true});
  assert.equal(r.policy,POLICIES.ASK_OR_REVERSIBLE_PROBE);
  assert.equal(r.verification,'REVERSIBLE_PROBE_OR_ASK');
});

test('private handles are not promoted into public semantics',()=>{
  const r=run({atom:'Hunger',privateHandle:true});
  assert.equal(r.policy,POLICIES.MINIMAL_GROUNDING);
  assert.equal(r.publicMeaningRule,'PRIVATE_COMPRESSION_IS_NOT_UNIVERSAL_SEMANTICS');
});

test('new vocabulary is rejected when existing vocabulary is sufficient',()=>{
  const r=run({atom:'new-canary-word',inventedTerm:true,existingVocabularySufficient:true});
  assert.equal(r.policy,POLICIES.REUSE_EXISTING_VOCABULARY);
});

test('new vocabulary is allowed when the mechanism has no adequate existing address',()=>{
  const r=run({atom:'Hunger',inventedTerm:true,existingVocabularySufficient:false});
  assert.equal(r.policy,POLICIES.DEFINE_NEW_TERM);
});
