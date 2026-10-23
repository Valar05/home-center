import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {createRelay} from './relay.mjs';
import {toThroneCommand} from './ritsu-turn-protocol.mjs';

async function post(url, value, headers={}) {
  return fetch(url, {method:'POST', headers:{'content-type':'application/json',...headers}, body:JSON.stringify(value)});
}

test('Ritsu chat turn has exact session, text, idempotency, origin and authenticated reply',async t=>{
  const extensionOrigin='chrome-extension://'+'m'.repeat(32);
  const throneCapability='r'.repeat(48);
  const events=[];
  const server=createRelay({port:0,extensionOrigin,throneCapability,eventSink:async e=>events.push(e)});
  await new Promise(resolve=>server.once('listening',resolve));
  t.after(()=>server.close());
  const base=`http://127.0.0.1:${server.address().port}/v1/throne`;
  const auth={authorization:`Bearer ${throneCapability}`};
  const extension={...auth,origin:extensionOrigin};
  const cmd=toThroneCommand({sessionId:'ritsu-session-001',turnId:'ritsu-turn-001',channel:'dialogue',prompt:'Say cobalt penguin.'});
  assert.equal((await post(base+'/command',cmd)).status,403);
  assert.equal((await post(base+'/command',cmd,auth)).status,202);
  assert.equal((await post(base+'/command',cmd,auth)).status,200);
  const collision=await post(base+'/command',{...cmd,turn:{...cmd.turn,prompt:'Different text'}},auth);
  assert.equal(collision.status,409);
  assert.equal((await collision.json()).error,'RITSU_TURN_ID_COLLISION');
  // A bearer is still required, and explicitly hostile/opaque origins
  // cannot masquerade as the installed Chrome extension.
  assert.equal((await fetch(base+'/command',{headers:{...auth,origin:'https://evil.example'}})).status,403);
  assert.equal((await fetch(base+'/command',{headers:{...auth,origin:'null'}})).status,403);
  assert.equal((await fetch(base+'/command',{headers:{origin:extensionOrigin}})).status,403);
  const lease=await fetch(base+'/command',{headers:auth});
  assert.equal(lease.status,200);
  const leased=(await lease.json()).command;
  assert.equal(leased.turn.prompt,'Say cobalt penguin.');
  assert.equal(leased.action,'chat.turn');
  assert.ok(leased.lease.expiresAtMs-leased.lease.leasedAtMs>=180000);
  const status=await fetch(base+'/status',{headers:auth});
  const statusJson=await status.json();
  assert.ok(!JSON.stringify(statusJson).includes('cobalt penguin'));
  const resultUrl=base+'/result?commandId='+encodeURIComponent(cmd.commandId);
  assert.equal((await fetch(resultUrl)).status,403);
  assert.equal((await (await fetch(resultUrl,{headers:auth})).json()).state,'leased');
  const answer={ok:true,accepted:true,sessionId:cmd.turn.sessionId,turnId:cmd.turn.turnId,channel:'dialogue',tabId:42,text:'Cobalt penguin.'};
  assert.equal((await post(base+'/complete',{commandId:cmd.commandId,ok:true,result:answer},{...auth,origin:'https://evil.example'})).status,403);
  assert.equal((await post(base+'/complete',{commandId:cmd.commandId,ok:true,result:answer},extension)).status,200);
  const final=await (await fetch(resultUrl,{headers:auth})).json();
  assert.equal(final.state,'completed');
  assert.deepEqual(final.result,answer);
  assert.equal(events.at(-1).type,'throne.command.completed');
  // Chrome MV3 may omit Origin for a privileged cross-origin GET/POST.
  // A correct local bearer remains enough when the header is absent,
  // never when the header explicitly declares a foreign Origin.
  assert.equal((await fetch(base+'/command',{headers:auth})).status,204);
  assert.equal((await post(base+'/complete',{commandId:'nonexistent-probe-01',ok:false,result:{}},auth)).status,404);
});

test('Ritsu turn validation blocks bad user IDs and unbounded text before browser',async t=>{
  const server=createRelay({port:0,extensionOrigin:'chrome-extension://'+'j'.repeat(32),throneCapability:'t'.repeat(48),eventSink:async()=>{}});
  await new Promise(resolve=>server.once('listening',resolve));
  t.after(()=>server.close());
  const base=`http://127.0.0.1:${server.address().port}/v1/throne/command`;
  const auth={authorization:'Bearer '+'t'.repeat(48)};
  const cmd=toThroneCommand({sessionId:'session-ritsu-2',turnId:'turn-ritsu-2',channel:'control',prompt:'Status?'});
  assert.equal((await post(base,{...cmd,commandId:'mismatched-command'},auth)).status,400);
  assert.equal((await post(base,{...cmd,turn:{...cmd.turn,prompt:'z'.repeat(5001)}},auth)).status,400);
});

test('Chromium Throne route does one bounded turn rather than automatic swarm continuation',()=>{
  const source=fs.readFileSync(new URL('./extension/service-worker.js',import.meta.url),'utf8');
  const at=source.indexOf('async function executeOneRitsuTurn(');
  const end=source.indexOf('async function runStoredSwarm(',at);
  assert.ok(at>0 && end>at);
  const one=source.slice(at,end);
  assert.match(one,/func: submitChatGptPrompt/);
  assert.match(one,/waitForCompletedAssistant/);
  assert.doesNotMatch(one,/runStoredSwarm\(/);
  assert.doesNotMatch(one,/planVeniceContinuation|BOOT_ENVELOPE/);
  assert.match(one,/ritsu_session_tab_missing_no_auto_rotation/);
  assert.match(one,/ritsu_session_unbound_explicit_existing_tab_required/);
  assert.doesNotMatch(one,/tab = await createWorkerTab\(\)/);
  assert.match(source,/case 'ritsu\.chat\.bind'/);
  assert.match(source,/case 'ritsu\.chat\.sessions'/);
  assert.match(source,/async function bindRitsuChatSession/);
  assert.match(source,/ritsu_tab_owned_by_another_session/);
  assert.match(source,/ritsu_binding_requires_empty_authenticated_chatgpt_tab/);
  assert.match(one,/ritsuChatReceipts/);
  const composerCheck=one.indexOf('await requireRitsuPromptComposer(tab.id)');
  const unknownReceipt=one.indexOf("receipts[turnKey] = {state: 'unknown'");
  const chatSend=one.indexOf('func: submitChatGptPrompt');
  assert.ok(composerCheck>0 && unknownReceipt>composerCheck && chatSend>unknownReceipt,
    'signed-out ChatGPT must be rejected before the at-most-once send receipt');
  assert.match(source,/function probeRitsuPromptComposer\(\)/);
  assert.match(source,/ritsu_chatgpt_login_required/);
  assert.match(source,/data-composer-markdown/);
  assert.match(source,/document\.execCommand\('insertText'/);
  assert.match(source,/userMessageObserved: true/);
  assert.match(source,/Submit click not verified by ChatGPT user-message DOM/);
  assert.doesNotMatch(source,/composer\.textContent = prompt/);
  assert.doesNotMatch(source,/new KeyboardEvent\('keydown'.*'Enter'/);
  assert.match(source,/ChatGPT send button not enabled; no dispatch/);
});

test('Ritsu browser tab binding stays explicit and visible to owner',()=>{
  const markup=fs.readFileSync(new URL('./extension/sidepanel.html',import.meta.url),'utf8');
  const panel=fs.readFileSync(new URL('./extension/throne-panel.mjs',import.meta.url),'utf8');
  for (const element of ['ritsuSession','ritsuChannel','ritsuTab','ritsuBind','ritsuFindTabs','ritsuBindingStatus'])
    assert.match(markup,new RegExp('id="'+element+'"'));
  assert.match(panel,/chrome\.tabs\.query\(\{url:'https:\/\/chatgpt\.com\/\*'\}\)/);
  assert.match(panel,/type:'ritsu\.chat\.bind'/);
  assert.match(panel,/type:'ritsu\.chat\.sessions'/);
  assert.doesNotMatch(panel,/chrome\.tabs\.create/);
});
