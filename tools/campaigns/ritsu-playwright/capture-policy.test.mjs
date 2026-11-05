import test from 'node:test';
import assert from 'node:assert/strict';
import {validateConfig,canaryPrompt,evidence,publicDiagnostic} from './capture-policy.mjs';
const base={revision:'a'.repeat(40),jobId:'ritsu-pw-proof-001',tabId:'A'.repeat(32),
  boundUrl:'https://chatgpt.com/c/6adbd2f5-3cec-83e9-abce-8522a16b528b'};
const marker='RITSU_PW_'+'B'.repeat(20);
const valid={...base,marker,text:'The canary is '+marker+'.',baseline:2,
 assistantCount:3,stableSamples:3,stopVisible:false,promptObserved:true,
 conversationUrl:base.boundUrl};
test('exact tab, pinned revision and chat URL required',()=>{
  assert.equal(validateConfig(base).jobId,base.jobId);
  for(const [k,v] of [['tabId','X'],['revision','main'],['boundUrl','https://example.com/c/6adbd2f5-3cec-83e9-abce-8522a16b528b'],
  ['boundUrl','https://chatgpt.com/']]){
    assert.throws(()=>validateConfig({...base,[k]:v}));
  }
});
test('prompt is deterministic inert sentence with exact marker',()=>{
  assert.match(canaryPrompt(marker),new RegExp(marker));
  assert.throws(()=>canaryPrompt('RITSU_PW_BAD'));
});
test('accepted readback preserves exact visible answer and SHA',()=>{
  const r=evidence(valid);
  assert.equal(r.text,valid.text);
  assert.equal(r.sha256.length,64);
  assert.equal(r.state,'retrieved');
  assert.equal(r.source,'playwright_existing_bound_tab_dom');
});
test('rejects hidden, incomplete, stale, wrong-conversation responses',()=>{
  for(const v of [{text:'unrelated'},{stopVisible:true},{stableSamples:2},
    {assistantCount:0},{assistantCount:-1},{promptObserved:false},
    {conversationUrl:'https://chatgpt.com/c/bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb'}]){
    assert.throws(()=>evidence({...valid,...v}));
  }
});
test('private failures never contain the prompt or answer',()=>{
  const r=publicDiagnostic(new Error('DOM changed'));
  assert.equal(r.reason,'DOM changed');
  assert.equal(JSON.stringify(r).includes(marker),false);
});

test('virtualized message containers can shrink while exact reply nonce still proves freshness',()=>{
  const a=evidence({...valid,baseline:7,assistantCount:6});
  assert.equal(a.exactCanaryMatched,true);
  assert.equal(a.baseline,7);
  assert.equal(a.assistantCount,6);
});
