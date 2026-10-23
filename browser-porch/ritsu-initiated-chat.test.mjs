import test from 'node:test';
import assert from 'node:assert/strict';
import {createInitiatedChat} from './ritsu-initiated-chat.mjs';

function turn(id='chat-test-turn-001',channel='control') {
  return {turnId:id,channel,sessionId:'home-center-main-session'};
}
function verified(id='chat-test-turn-001',text='A real ChatGPT response.') {
  const expected=turn(id);
  return {turn:expected,state:'completed',result:{
    turnId:id,channel:expected.channel,sessionId:expected.sessionId,
    tabId:42,text
  }};
}

test('initiates ONCE and returns actual Chrome result with matching Home Center identity',async()=>{
  let submitCount=0,reads=0;
  const coordinator={
    async submitUserTurn(payload) {
      submitCount++;
      assert.deepEqual(payload,{turnId:'chat-test-turn-001',
        channel:'control',prompt:'What is your result?'});
      return {turn:{...turn(),prompt:payload.prompt},state:'queued'};
    },
    async readOneTurn(id) {
      reads++;
      assert.equal(id,'chat-test-turn-001');
      return reads<3?{turn:turn(),state:'leased'}:verified();
    }
  };
  let clock=0;
  const bridge=createInitiatedChat({
    coordinator,
    now:()=>clock,pause:async(ms)=>{clock+=ms;}
  });
  const result=await bridge.initiateAndRetrieve({
    turnId:'chat-test-turn-001',prompt:'What is your result?',
    timeoutMs:10000,pollMs:1000
  });
  assert.equal(result.state,'retrieved');
  assert.equal(result.verified,true);
  assert.equal(result.text,'A real ChatGPT response.');
  assert.equal(result.sessionId,'home-center-main-session');
  assert.equal(result.tabId,42);
  assert.equal(result.pollCount,3);
  assert.equal(submitCount,1);
});

test('queued or leased cannot be reported as retrieved, and expiry never resubmits',async()=>{
  let clock=0, posts=0, reads=0;
  const bridge=createInitiatedChat({
    coordinator:{
      async submitUserTurn({turnId,prompt,channel}){
        posts++;
        return {turn:{...turn(turnId,channel),prompt},state:'queued'};
      },
      async readOneTurn(){reads++;return {turn:turn(),state:'leased'};}
    },
    now:()=>clock,pause:async(ms)=>{clock+=ms;}
  });
  const r=await bridge.initiateAndRetrieve({
    turnId:'chat-test-turn-001',prompt:'Hello',
    timeoutMs:2000,pollMs:1000
  });
  assert.equal(r.state,'pending');
  assert.equal(r.text,null);
  assert.equal(r.verified,false);
  assert.equal(posts,1);
  assert.ok(reads>=2);
});

test('read-only resume fetches completion after uncertain network outcome',async()=>{
  let submits=0;
  const bridge=createInitiatedChat({coordinator:{
    async submitUserTurn(){submits++;throw Error('must_not_repost');},
    async readOneTurn(){return verified();}
  }});
  const result=await bridge.retrieve({turnId:'chat-test-turn-001'});
  assert.equal(result.state,'retrieved');
  assert.equal(submits,0);
});

test('identity mismatch, failed and unknown outcomes cannot return text',async()=>{
  const bridge=createInitiatedChat({coordinator:{
    async submitUserTurn(){throw Error('not-called');},
    async readOneTurn(){return {...verified(),result:{...verified().result,sessionId:'some_other_session'}};}
  }});
  await assert.rejects(bridge.retrieve({turnId:'chat-test-turn-001'}),
    /completed_reply_lacks_chatgpt_identity/);
  for(const state of ['failed','unknown']){
    const x=createInitiatedChat({coordinator:{
      async submitUserTurn(){throw Error('not-called');},
      async readOneTurn(){return {turn:turn(),state,result:{text:'fake'}};}
    }});
    const r=await x.retrieve({turnId:'chat-test-turn-001'});
    assert.equal(r.verified,false);
    assert.equal(r.text,null);
  }
});

test('reject invalid IDs and disconnected coordinator',async()=>{
  assert.throws(()=>createInitiatedChat({}),/authoritative/);
  const b=createInitiatedChat({coordinator:{
    async submitUserTurn(){throw Error('unreachable');},
    async readOneTurn(){throw Error('unreachable');}
  }});
  await assert.rejects(b.initiateAndRetrieve({
    turnId:'abc',prompt:'Test'
  }),/valid_single_chat_turn_required/);
  await assert.rejects(b.retrieve({turnId:'abc'}),/stable_turn_id_required/);
});
