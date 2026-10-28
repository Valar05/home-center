import test from 'node:test';
import assert from 'node:assert/strict';
import {spawn} from 'node:child_process';
import {mkdtemp,rm} from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {createRelay} from './relay.mjs';

const entry=fileURLToPath(new URL('./ritsu-home-center-cli.mjs',import.meta.url));
function invoke(request,env) {
  return new Promise((resolve,reject)=>{
    const child=spawn(process.execPath,[entry],{env:{...process.env,...env},
      stdio:['pipe','pipe','pipe']});
    let stdout='',stderr='';
    child.stdout.on('data',b=>stdout+=b);
    child.stderr.on('data',b=>stderr+=b);
    child.on('error',reject);
    child.on('close',code=>{
      let body;try{body=JSON.parse(code===0?stdout:stderr);}
      catch{return reject(new Error('unparseable_cli_response:'+stderr.slice(0,300)));}
      resolve({code,body});
    });
    child.stdin.end(JSON.stringify(request));
  });
}

test('trusted local Home Center executable survives process restart and stages real relay receipts',async t=>{
  const capability='x'.repeat(48);
  const origin='chrome-extension://'+'p'.repeat(32);
  const server=createRelay({port:0,extensionOrigin:origin,throneCapability:capability,
    eventSink:async()=>{}});
  await new Promise(resolve=>server.once('listening',resolve));
  t.after(()=>server.close());
  const dir=await mkdtemp(path.join(os.tmpdir(),'ritsu-hc-cli-'));
  t.after(()=>rm(dir,{recursive:true,force:true}));
  const base='http://127.0.0.1:'+server.address().port+'/v1/throne';
  const env={
    HOME_CENTER_RITSU_STATE_DIR:dir,
    HOME_CENTER_RITSU_NAMESPACE:'ritsu-cli-campaign-01',
    HOME_CENTER_RITSU_CONTROL_SESSION:'ritsu-cli-control-01',
    HOME_CENTER_RITSU_DIALOGUE_SESSION:'ritsu-cli-dialogue-01',
    HOME_CENTER_CHROMIUM_THRONE_CAPABILITY:capability,
    HOME_CENTER_RITSU_RELAY_URL:base,
  };
  const turn={operation:'submit',turnId:'ritsu-cli-turn-001',
    channel:'dialogue',prompt:'Ask the real desktop relay to send exactly once.'};
  const first=await invoke(turn,env);
  assert.equal(first.code,0);
  assert.equal(first.body.result.state,'queued');
  const duplicate=await invoke(turn,env);
  assert.equal(duplicate.code,0);
  assert.equal(duplicate.body.result.commandId,first.body.result.commandId);
  assert.equal((await invoke({...turn,prompt:'mutated prompt'},env)).code,1);

  const auth={authorization:'Bearer '+capability,origin};
  const leaseResp=await fetch(base+'/command',{headers:auth});
  assert.equal(leaseResp.status,200);
  const lease=(await leaseResp.json()).command;
  assert.equal(lease.action,'chat.turn');
  assert.equal(lease.turn.sessionId,'ritsu-cli-dialogue-01');
  assert.equal((await fetch(base+'/command',{headers:auth})).status,204);

  const mockReply={
    ok:true,accepted:false,sessionId:lease.turn.sessionId,
    turnId:lease.turn.turnId,channel:'dialogue',tabId:73,
    text:'Controlled extension-simulated answer, not live ChatGPT proof.',
  };
  const completed=await fetch(base+'/complete',{
    method:'POST',headers:{...auth,'content-type':'application/json'},
    body:JSON.stringify({commandId:lease.commandId,ok:true,result:mockReply}),
  });
  assert.equal(completed.status,200);
  const poll=await invoke({operation:'poll',turnId:turn.turnId},env);
  assert.equal(poll.code,0);
  assert.equal(poll.body.result.state,'completed');
  assert.equal(poll.body.result.result.text,mockReply.text);
  // Because only the main CONTROL thread can publish, the end-user merged
  // feed still hides secondary material even after a relay receipt.
  assert.deepEqual((await invoke({operation:'feed'},env)).body.result,[]);

  const main=await invoke({operation:'submit',turnId:'ritsu-cli-main-001',
    channel:'control',prompt:'Review the dialogue candidate.'},env);
  assert.equal(main.code,0);
  const mainLease=(await (await fetch(base+'/command',{headers:auth})).json()).command;
  assert.equal(mainLease.turn.channel,'control');
  const mainCompletion=await fetch(base+'/complete',{
    method:'POST',headers:{...auth,'content-type':'application/json'},
    body:JSON.stringify({commandId:mainLease.commandId,ok:true,result:{
      ok:true,accepted:false,sessionId:mainLease.turn.sessionId,
      turnId:mainLease.turn.turnId,channel:'control',tabId:75,
      text:'Main control result receipt.'}}),
  });
  assert.equal(mainCompletion.status,200);
  await invoke({operation:'poll',turnId:'ritsu-cli-main-001'},env);
  const publication=await invoke({operation:'publish',controlTurnId:'ritsu-cli-main-001',
    turnIds:[turn.turnId]},env);
  assert.equal(publication.code,0);
  const finalFeed=(await invoke({operation:'feed'},env)).body.result;
  assert.equal(finalFeed.length,2);
  assert.equal(finalFeed[1].text,mockReply.text);
  assert.equal(finalFeed[1].publishedByTurnId,'ritsu-cli-main-001');
});


test('two simultaneous host CLI processes cannot overwrite each other\'s turn journal',async t=>{
  const capability='y'.repeat(48);
  const origin='chrome-extension://'+'p'.repeat(32);
  const server=createRelay({port:0,extensionOrigin:origin,throneCapability:capability,
    eventSink:async()=>{}});
  await new Promise(resolve=>server.once('listening',resolve));
  t.after(()=>server.close());
  const dir=await mkdtemp(path.join(os.tmpdir(),'ritsu-hc-concurrent-'));
  t.after(()=>rm(dir,{recursive:true,force:true}));
  const base='http://127.0.0.1:'+server.address().port+'/v1/throne';
  const env={
    HOME_CENTER_RITSU_STATE_DIR:dir,
    HOME_CENTER_RITSU_NAMESPACE:'ritsu-cli-concurrent-01',
    HOME_CENTER_RITSU_CONTROL_SESSION:'ritsu-concurrent-main-01',
    HOME_CENTER_RITSU_DIALOGUE_SESSION:'ritsu-concurrent-talk-01',
    HOME_CENTER_CHROMIUM_THRONE_CAPABILITY:capability,
    HOME_CENTER_RITSU_RELAY_URL:base,
  };
  const requests=[
    {operation:'submit',turnId:'ritsu-concurrent-a1',channel:'dialogue',prompt:'First.'},
    {operation:'submit',turnId:'ritsu-concurrent-b2',channel:'control',prompt:'Second.'},
  ];
  const results=await Promise.all(requests.map(request=>invoke(request,env)));
  assert.deepEqual(results.map(r=>r.code),[0,0]);
  const snapshot=(await invoke({operation:'state'},env)).body.result;
  assert.equal(snapshot.turns.length,2);
  assert.deepEqual(snapshot.turns.map(row=>row.turn.turnId).sort(),
    ['ritsu-concurrent-a1','ritsu-concurrent-b2']);
  const auth={authorization:'Bearer '+capability,origin};
  const one=(await (await fetch(base+'/command',{headers:auth})).json()).command;
  const two=(await (await fetch(base+'/command',{headers:auth})).json()).command;
  assert.deepEqual([one.turn.turnId,two.turn.turnId].sort(),
    ['ritsu-concurrent-a1','ritsu-concurrent-b2']);
});
