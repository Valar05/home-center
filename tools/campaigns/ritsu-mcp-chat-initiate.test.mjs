import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtemp,readFile,rm} from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import {applyOne,makeMcpPrompt} from './ritsu-mcp-chat-initiate.mjs';

const tab={id:'existing-target-tab-01',type:'page',url:'https://chatgpt.com/',
  webSocketDebuggerUrl:'ws://127.0.0.1:9236/devtools/page/test'};
const prompt={turnId:'ritsu-mcp-real-canary-20261023-001',
  sessionId:'ritsu-control-real-session-20261023'};
const existing=()=>({json:async()=>[tab]});

test('one existing signed-in blank tab receives an MCP callback instruction, never assistant extraction',async t=>{
  const dir=await mkdtemp(path.join(os.tmpdir(),'ritsu-mcp-campaign-'));
  t.after(()=>rm(dir,{recursive:true,force:true}));
  let writes=0,sawInstruction=false;
  const evalImpl=async(_tab,_method,params)=>{
    if(writes++===0)return JSON.stringify({url:tab.url,ready:true,empty:true,
      userCount:0,assistantCount:0,loggedOut:false});
    assert.match(params.expression,/document\.execCommand/);
    assert.doesNotMatch(params.expression,/data-message-author-role="assistant"\]\s*.*innerText/);
    sawInstruction=params.expression.includes('ritsu.chat.publish');
    return JSON.stringify({ok:true,state:'user_message_observed'});
  };
  const r=await applyOne({...prompt,stateDirectory:dir,
    fetchImpl:async()=>existing(),evalImpl});
  assert.equal(r.observed,true);
  assert.equal(r.tabId,tab.id);
  assert.equal(r.returnAuthority,'Home Center MCP ritsu.chat.result, never Chrome DOM');
  assert.equal(sawInstruction,true);
  assert.equal(writes,2);
  const journal=JSON.parse(await readFile(path.join(dir,'mcp-canary-'+prompt.turnId+'.json'),'utf8'));
  assert.equal(journal.state,'user_prompt_observed');
  await assert.rejects(applyOne({...prompt,stateDirectory:dir,
    fetchImpl:async()=>existing(),
    evalImpl:async()=>JSON.stringify({url:tab.url,ready:true,empty:true,
      userCount:0,assistantCount:0,loggedOut:false})}),{code:'EEXIST'});
  assert.equal(writes,2); // No second irreversible evaluation.
});
test('uncertain dispatch is persisted and never blindly retried',async t=>{
  const dir=await mkdtemp(path.join(os.tmpdir(),'ritsu-mcp-uncertain-'));
  t.after(()=>rm(dir,{recursive:true,force:true}));
  let n=0;
  const evalImpl=async()=>{
    if(n++===0)return JSON.stringify({url:tab.url,ready:true,empty:true,
      userCount:0,assistantCount:0,loggedOut:false});
    throw Error('network dropped after click');
  };
  const r=await applyOne({...prompt,stateDirectory:dir,
    fetchImpl:async()=>existing(),evalImpl});
  assert.equal(r.observed,false);
  assert.equal(JSON.parse(await readFile(path.join(dir,'mcp-canary-'+prompt.turnId+'.json'),'utf8')).state,
    'dispatch_unknown');
  await assert.rejects(applyOne({...prompt,stateDirectory:dir,
    fetchImpl:async()=>existing(),
    evalImpl:async()=>JSON.stringify({url:tab.url,ready:true,empty:true,
      userCount:0,assistantCount:0,loggedOut:false})}),{code:'EEXIST'});
});
test('never opens another tab when existing browser ambiguous or signed out',async()=>{
  const dir=path.join(os.tmpdir(),'unused-ritsu-no-tabs');
  await assert.rejects(applyOne({...prompt,stateDirectory:dir,
    fetchImpl:async()=>({json:async()=>[tab,tab]})}),/exactly_one_existing/);
  await assert.rejects(applyOne({...prompt,stateDirectory:dir,
    fetchImpl:async()=>existing(),
    evalImpl:async()=>JSON.stringify({url:tab.url,ready:false,empty:true,
      userCount:0,assistantCount:0,loggedOut:true})}),/existing_authenticated/);
});
test('MCP prompt does not claim model identity or expose a pre-issued callback token',()=>{
  const s=makeMcpPrompt(prompt);
  assert.match(s,/ritsu.chat.prepare/);
  assert.match(s,/ritsu.chat.publish/);
  assert.match(s,/callbackKey/);
  assert.match(s,/If you cannot access/);
  assert.ok(!s.includes('Bearer '));
});
