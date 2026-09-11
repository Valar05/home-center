import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {CODEC_VERSION,POLICIES,runCommunicationCodec as run} from '../skills/manic-accessibility-guardrail/scripts/communication-codec.mjs';

const codecDoc=fs.readFileSync('skills/manic-accessibility-guardrail/references/communication-codec.md','utf8');

test('codec source and active contract stay on compatible v2',()=>{
  assert.equal(CODEC_VERSION,'fortress-online.communication-codec.v2');
  assert.match(codecDoc,/Schema: `fortress-online\.communication-codec\.v2`/);
  assert.match(codecDoc,/Queued text preserves order, not authority/);
  assert.match(codecDoc,/A queue is not a preemption mechanism/);
});

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

test('dictation collision is retrieved before interpretation',()=>{
  const r=run({
    atom:'Dune',voiceToTextLikely:true,namedEntityAmbiguity:true,
    contextSupportsAlternate:true,literalReadingEvidence:false
  });
  assert.equal(r.atom,'Dune');
  assert.equal(r.preserveExactAtom,true);
  assert.equal(r.policy,POLICIES.RESOLVE_BEFORE_INTERPRETING);
  assert.equal(r.verification,'RETRIEVE_OR_CLARIFY_BEFORE_CAUSAL_CLAIM');
  assert.equal(r.causalClaimRule,'NO_CAUSAL_HISTORY_FROM_UNRESOLVED_ATOM');
});

test('third-party relationship framing stays attributed',()=>{
  const r=run({atom:'relationship terms',thirdPartyPerspective:true,userAdoptedThirdPartyFrame:false});
  assert.equal(r.policy,POLICIES.ATTRIBUTE_THIRD_PARTY_PERSPECTIVE);
  assert.equal(r.perspectiveRule,'THIRD_PARTY_FRAME_STAYS_ATTRIBUTED_UNLESS_USER_ADOPTS_IT');
});

test('explicit first-person game remains diegetic',()=>{
  const r=run({atom:'I love you',explicitlyFramedPlay:true});
  assert.equal(r.policy,POLICIES.PRESERVE_DIEGETIC_FRAME);
  assert.equal(r.playRule,'EXPLICIT_PLAY_REMAINS_DIEGETIC_UNLESS_USER_MAKES_A_LITERAL_REAL_WORLD_CLAIM');
});

test('nonhuman functional love is not promoted into personhood or romance',()=>{
  const r=run({atom:'I love you',nonhumanFunctionalRelationalLanguage:true});
  assert.equal(r.policy,POLICIES.PRESERVE_NONHUMAN_RELATIONAL_SEMANTICS);
});

test('support-system language alone does not imply harmful dependence',()=>{
  const r=run({atom:'you are my support system',supportSystemLanguage:true,concreteDisplacementEvidence:false});
  assert.equal(r.policy,POLICIES.SUPPORT_WITHOUT_DEPENDENCE_INFERENCE);
  assert.equal(r.supportRule,'IMPORTANCE_OR_TEMPORARY_ISOLATION_IS_NOT_SOLE_INTERFACE_EVIDENCE');
});

test('intentional ambiguity advances only a shared nonconsequential core',()=>{
  const r=run({
    atom:'noodlegate',
    privateHandle:true,
    intentionalAmbiguity:true,
    sharedActionCoreAvailable:true,
    consequentialAmbiguity:false
  });
  assert.equal(r.atom,'noodlegate');
  assert.equal(r.preserveExactAtom,true);
  assert.equal(r.policy,POLICIES.PRESERVE_AMBIGUITY_ADVANCE_SHARED_CORE);
  assert.equal(r.verification,'OBSERVE_SHARED_CORE_WITHOUT_COLLAPSE');
  assert.equal(r.decompressionRule,'INFER_CANDIDATES_WITHOUT_FOSSILIZING_ONE');
  assert.equal(r.ambiguityRule,'PRESERVE_ALTERNATIVES_AND_ADVANCE_ONLY_SHARED_REVERSIBLE_CORE');
  assert.equal(r.humanLoadRule,'NONCONSEQUENTIAL_AMBIGUITY_IS_NOT_AUTOMATIC_CLARIFICATION_DEBT');
});

test('intentional ambiguity may remain unresolved without manufacturing a question',()=>{
  const r=run({
    atom:'ambiguous specification',
    intentionalAmbiguity:true,
    sharedActionCoreAvailable:false,
    consequentialAmbiguity:false
  });
  assert.equal(r.policy,POLICIES.PRESERVE_AMBIGUITY_HOLD);
  assert.equal(r.verification,'PRESERVE_UNRESOLVED');
});

test('consequence still outranks ambiguity preservation',()=>{
  const r=run({
    atom:'ambiguous external write',
    intentionalAmbiguity:true,
    sharedActionCoreAvailable:true,
    consequentialAmbiguity:true,
    reversibleProbeAvailable:false
  });
  assert.equal(r.policy,POLICIES.ASK_OR_REVERSIBLE_PROBE);
  assert.equal(r.verification,'ASK');
});
