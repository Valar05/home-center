import test from 'node:test';
import assert from 'node:assert/strict';
import {createRitsuAndroidGateway} from './ritsu-android-gateway.mjs';

function fakeCoordinator() {
  const turns=new Map();
  let posts=0;
  const feed=[];
  return {
    get posts(){return posts;},
    async submitUserTurn({turnId,channel,prompt}) {
      if(channel!=='control')throw new Error('phone_not_allowed_to_delegate');
      const old=turns.get(turnId);
      if(old) {
        if(old.turn.prompt!==prompt)throw new Error('turn_id_collision');
        return old;
      }
      posts++;
      const row={turn:{turnId,channel,prompt},state:'queued',result:null};
      turns.set(turnId,row);
      return row;
    },
    async readOneTurn(id) {
      const row=turns.get(id);
      if(!row)throw new Error('turn_not_found');
      return row;
    },
    async projectedFeed(){return feed;},
    complete(id,text) {
      const row=turns.get(id);
      row.state='completed';
      row.result={text,tabId:27};
      feed.push({type:'chat_result',channel:'control',turnId:id,
        text,sequence:feed.length+1});
    }
  };
}
const token='T'.repeat(48);
async function make() {
  const coordinator=fakeCoordinator();
  const gate=createRitsuAndroidGateway({
    host:'127.0.0.1',port:0,allowLoopbackForTests:true,
    clientBearer:token,coordinator
  });
  const {port}=await gate.start();
  return {gate,coordinator,base:'http://127.0.0.1:'+port+'/v1/ritsu'};
}
function headers(tokenValue=token) {
  return {'authorization':'Bearer '+tokenValue,
    'content-type':'application/json'};
}
async function post(base,turnId,prompt,extra={}) {
  return fetch(base+'/turn',{method:'POST',headers:headers(),
    body:JSON.stringify({turnId,prompt,...extra})});
}

test('gateway refuses public, LAN and generic wildcard binding',()=>{
  for(const host of ['0.0.0.0','192.168.1.5','8.8.8.8','100.63.0.5','100.128.0.1','example.com'])
    assert.throws(()=>createRitsuAndroidGateway({
      host,clientBearer:token,port:19646,coordinator:fakeCoordinator()
    }),/tailnet/);
  assert.throws(()=>createRitsuAndroidGateway({
    host:'127.0.0.1',clientBearer:token,coordinator:fakeCoordinator()
  }),/tailnet/);
  assert.throws(()=>createRitsuAndroidGateway({
    host:'100.84.15.2',clientBearer:'short',coordinator:fakeCoordinator()
  }),/capability/);
  assert.doesNotThrow(()=>createRitsuAndroidGateway({
    host:'100.64.0.1',clientBearer:token,coordinator:fakeCoordinator()
  }));
  assert.doesNotThrow(()=>createRitsuAndroidGateway({
    host:'100.127.255.254',clientBearer:token,coordinator:fakeCoordinator()
  }));
});

test('unpaired phone never sees prompt, feed or accepted submit',async t=>{
  const {gate,base}=await make();t.after(()=>gate.close());
  assert.equal((await fetch(base+'/health')).status,401);
  assert.equal((await fetch(base+'/feed',{headers:headers('wrong')})).status,401);
  assert.equal((await fetch(base+'/turn?turnId=turn-secret-001',{headers:headers('wrong')})).status,401);
  assert.equal((await fetch(base+'/turn',{method:'POST',headers:headers('wrong'),
    body:JSON.stringify({turnId:'turn-secret-001',prompt:'Do not forward'})})).status,401);
});

test('owner main-thread message is durable, idempotent and completed only after verified result',async t=>{
  const {gate,base,coordinator}=await make();t.after(()=>gate.close());
  const id='phone-turn-abc-001';
  let result=await post(base,id,'Hello Ritsu.');
  assert.equal(result.status,202);
  let body=await result.json();
  assert.equal(body.boundary,'home_center_only_not_browser_delivery');
  assert.equal(body.receipt.state,'queued');
  assert.equal(body.receipt.result,null);
  assert.equal(coordinator.posts,1);
  result=await post(base,id,'Hello Ritsu.');
  assert.equal(result.status,202);
  assert.equal(coordinator.posts,1);
  assert.equal((await post(base,id,'Mutated!')).status,409);
  assert.equal((await post(base,'phone-worker-001','Do an unapproved worker job',{channel:'worker'})).status,400);
  const queued=await (await fetch(base+'/turn?turnId='+id,{headers:headers()})).json();
  assert.equal(queued.receipt.state,'queued');
  assert.equal(queued.receipt.result,null);
  coordinator.complete(id,'Verified CONTROL reply from Chromium Throne.');
  const finished=await (await fetch(base+'/turn?turnId='+id,{headers:headers()})).json();
  assert.equal(finished.receipt.state,'completed');
  assert.equal(finished.receipt.result.text,'Verified CONTROL reply from Chromium Throne.');
  const feed=await (await fetch(base+'/feed?after=0',{headers:headers()})).json();
  assert.equal(feed.events.length,1);
  assert.equal(feed.events[0].channel,'control');
  assert.equal(feed.nextCursor,1);
  const empty=await (await fetch(base+'/feed?after=1',{headers:headers()})).json();
  assert.deepEqual(empty.events,[]);
});

test('malformed requests do not reach Home Center coordinator',async t=>{
  const {gate,base,coordinator}=await make();t.after(()=>gate.close());
  assert.equal((await post(base,'bad','Hi')).status,400);
  assert.equal((await post(base,'long-test-0001','z'.repeat(5001))).status,400);
  assert.equal((await post(base,'control-allow-001','Hello',{channel:'dialogue'})).status,400);
  assert.equal((await fetch(base+'/feed?after=-3',{headers:headers()})).status,400);
  assert.equal((await fetch(base+'/turn?turnId=no',{headers:headers()})).status,400);
  assert.equal((await fetch(base+'/not-supported',{headers:headers()})).status,404);
  assert.equal(coordinator.posts,0);
});
