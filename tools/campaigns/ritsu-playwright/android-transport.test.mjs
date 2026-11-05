import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtemp,rm} from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import {createRitsuPlaywrightTransport} from './android-transport.mjs';
import {createRitsuHomeCenterCoordinator} from '../../../browser-porch/ritsu-home-center-coordinator.mjs';
import {createRitsuAndroidGateway} from '../../../browser-porch/ritsu-android-gateway.mjs';
const tabId='A67990116B5D70AEB70B14563740A470',
  boundUrl='https://chatgpt.com/c/6adbd2f5-3cec-83e9-abce-8522a16b528b';
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
const token='T'.repeat(48);

test('Android gateway -> Home Center coordinator -> Playwright verified result -> phone feed',async t=>{
  const dir=await mkdtemp(path.join(os.tmpdir(),'ritsu-pw-gateway-'));
  t.after(()=>rm(dir,{recursive:true,force:true}));
  let sends=0;
  const transport=createRitsuPlaywrightTransport({directory:dir,tabId,boundUrl,
    reply:async ({prompt,marker})=>{
      assert.equal(prompt,'Please greet the phone.');
      assert.match(marker,/^RITSU_PHONE_PROOF_[A-F0-9]{20}$/);
      sends++;
      await sleep(30);
      return {text:'Hello from verified Playwright. 🦀',tabId};
    },
  });
  let snap=null;
  const coordinator=createRitsuHomeCenterCoordinator({
    namespace:'ritsu-test-namespace',controlSessionId:'ritsu-control-sess',
    dialogueSessionId:'ritsu-dialogue-sess',transport,
    store:{async load(){return snap},async save(_,x){snap=structuredClone(x)}},
  });
  const gate=createRitsuAndroidGateway({
    host:'127.0.0.1',port:0,clientBearer:token,
    allowLoopbackForTests:true,coordinator
  });
  const addr=await gate.start();t.after(()=>gate.close());
  const base='http://127.0.0.1:'+addr.port+'/v1/ritsu';
  const headers={authorization:'Bearer '+token,'content-type':'application/json'};
  const turnId='real-phone-turn-0001';
  const body=JSON.stringify({turnId,prompt:'Please greet the phone.',channel:'control'});
  const first=await fetch(base+'/turn',{method:'POST',headers,body});
  assert.equal(first.status,202);
  const ack=await first.json();
  assert.equal(ack.receipt.state,'queued');
  assert.equal(ack.receipt.result,null);
  assert.equal((await fetch(base+'/turn',{method:'POST',headers,body})).status,202);
  let result;
  for(let i=0;i<100;i++){
    result=await (await fetch(base+'/turn?turnId='+turnId,{headers})).json();
    if(result.receipt.state==='completed')break;
    await sleep(10);
  }
  assert.equal(result.receipt.state,'completed');
  assert.equal(result.receipt.result.text,'Hello from verified Playwright. 🦀');
  assert.equal(result.receipt.result.tabId,tabId);
  const feed=await (await fetch(base+'/feed?after=0',{headers})).json();
  assert.equal(feed.events.length,1);
  assert.equal(feed.events[0].text,'Hello from verified Playwright. 🦀');
  assert.equal(feed.events[0].channel,'control');
  assert.equal(sends,1);
});

test('duplicate turn does not dispatch twice; process restart becomes uncertain',async t=>{
  const dir=await mkdtemp(path.join(os.tmpdir(),'ritsu-pw-idempotence-'));
  t.after(()=>rm(dir,{recursive:true,force:true}));
  let calls=0;
  const transport=createRitsuPlaywrightTransport({directory:dir,tabId,boundUrl,
    reply:async()=>{calls++;throw Object.assign(new Error('browser_unknown'),{dispatched:true})}});
  const turn={version:'ritsu.chat.turn.v1',sessionId:'control-session-01',
    turnId:'turn-duplicate-001',channel:'control',prompt:'Hello'};
  const command={commandId:'ritsu.'+turn.turnId,action:'chat.turn',
    source:'home-center',turn};
  const a=await transport.submit(command);assert.equal(a.state,'queued');
  await transport.submit(command);
  for(let i=0;i<20;i++){const r=await transport.readResult(command.commandId);
    if(r?.state==='uncertain')break;await sleep(20)}
  assert.equal((await transport.readResult(command.commandId)).state,'uncertain');
  assert.equal(calls,1);
  await assert.rejects(transport.submit({...command,turn:{...turn,prompt:'changed'}}),/collision/);
});

test('bad caller, invalid chat URL and unauthorized channel are refused',async t=>{
  const dir=await mkdtemp(path.join(os.tmpdir(),'ritsu-pw-validation-'));
  t.after(()=>rm(dir,{recursive:true,force:true}));
  assert.throws(()=>createRitsuPlaywrightTransport({directory:dir,tabId:'wrong',boundUrl}),/authorized/);
  assert.throws(()=>createRitsuPlaywrightTransport({directory:dir,tabId,boundUrl:'https://example.com'}),/authorized/);
  const tr=createRitsuPlaywrightTransport({directory:dir,tabId,boundUrl,
    reply:async()=>{throw Error('must_not_call')}});
  await assert.rejects(tr.submit({commandId:'ritsu.turn-010',action:'exec',
    source:'phone',turn:{sessionId:'a'.repeat(8),turnId:'turn-010',channel:'control',prompt:'hello'}}),/invalid_home_center/);
});
