'use strict';
const test=require('node:test');
const assert=require('node:assert/strict');
const {entryList,runOperation}=require('./ritsu_chat_callback_api');

function fakeAdmin() {
  const docs=new Map();
  const ref=id=>({id,async get(){
    const row=docs.get(id);return {exists:!!row,data:()=>structuredClone(row)};
  }});
  return {firestore:()=>({
    collection:name=>({
      doc:id=>ref(name+'/'+id)
    }),
    runTransaction:async work=>{
      const pending=[];
      const tx={
        get:r=>r.get(),
        create:(r,v)=>{if(docs.has(r.id))throw Error('duplicate_firestore_create');
          pending.push(()=>docs.set(r.id,structuredClone(v)));},
        update:(r,v)=>pending.push(()=>docs.set(r.id,{...docs.get(r.id),...structuredClone(v)}))
      };
      const out=await work(tx);pending.forEach(f=>f());return out;
    }
  })};
}
const user={email:'owner@example.test'};
const other={email:'other@example.test'};
const sessionId='ritsu-control-session-20261023';
const requestId='ritsu-real-turn-20261023';
const call=(admin,u,operation,args)=>runOperation({admin,user:u,operation,args});
test('MCP registry exposes target-publish and origin-retrieve but no DOM/screen action',()=>{
  assert.deepEqual(Object.keys(entryList()).sort(),
    ['ritsu.chat.prepare','ritsu.chat.publish','ritsu.chat.result']);
  const source=require('node:fs').readFileSync(__filename.replace(/\.test\.js$/,'.js'),'utf8');
  for (const forbidden of ['document.querySelector(', 'chrome.scripting', 'page.screenshot(', 'puppeteer.launch('])
    assert.equal(source.includes(forbidden),false,'MCP backend must not read browser DOM: '+forbidden);
});
test('one named ChatGPT worker publishes exact response and initiator retrieves via MCP',async()=>{
  const admin=fakeAdmin();
  const prepared=await call(admin,user,'ritsu.chat.prepare',{
    requestId,sessionId,channel:'control'
  });
  assert.equal(prepared.state,'prepared');
  assert.equal(prepared.callbackOperation,'ritsu.chat.publish');
  assert.ok(prepared.callbackKey.length>=30);
  const before=await call(admin,user,'ritsu.chat.result',{turnId:requestId});
  assert.equal(before.state,'prepared');
  assert.equal(before.text,null);
  const answer='I am reporting from the initiated ChatGPT conversation.';
  const args={requestId,sessionId,channel:'control',
    callbackKey:prepared.callbackKey,text:answer};
  const published=await call(admin,user,'ritsu.chat.publish',args);
  assert.equal(published.accepted,true);
  assert.equal(published.provenance,'responding_mcp_tool_call');
  const result=await call(admin,user,'ritsu.chat.result',{turnId:requestId});
  assert.equal(result.text,answer);
  assert.equal(result.source,'responding_chat_mcp_tool_call');
  assert.equal(result.nativeApiProvenance,false);
  assert.equal(result.channel,'control');
  assert.equal(result.sessionId,sessionId);
  const again=await call(admin,user,'ritsu.chat.publish',args);
  assert.equal(again.idempotent,true);
  await assert.rejects(call(admin,user,'ritsu.chat.publish',{
    ...args,text:'A forged replacement'}),
    /already_published_immutable/);
});
test('MCP callback is owner-scoped and requires exact scoped key and session',async()=>{
  const admin=fakeAdmin();
  const prepared=await call(admin,user,'ritsu.chat.prepare',{
    requestId,sessionId,channel:'control'});
  assert.equal((await call(admin,user,'ritsu.chat.prepare',{
    requestId,sessionId,channel:'control'})).callbackKey,null);
  await assert.rejects(call(admin,other,'ritsu.chat.result',{turnId:requestId}),
    /not_prepared/);
  await assert.rejects(call(admin,other,'ritsu.chat.publish',{
    requestId,sessionId,channel:'control',
    callbackKey:prepared.callbackKey,text:'Incorrect owner'}),
    /not_prepared/);
  await assert.rejects(call(admin,user,'ritsu.chat.publish',{
    requestId,sessionId:'different-session',channel:'control',
    callbackKey:prepared.callbackKey,text:'Incorrect session'}),
    /identity_mismatch/);
  await assert.rejects(call(admin,user,'ritsu.chat.publish',{
    requestId,sessionId,channel:'control',
    callbackKey:'A'.repeat(43),text:'Incorrect key'}),
    /identity_mismatch/);
  const saved=await call(admin,user,'ritsu.chat.result',{turnId:requestId});
  assert.equal(saved.text,null);
});
test('callbacks reject malformed and oversized text or ids',async()=>{
  const admin=fakeAdmin();
  await assert.rejects(call(admin,user,'ritsu.chat.prepare',{
    requestId:'x',sessionId,channel:'control'}),
    /turn_id_invalid/);
  const t=await call(admin,user,'ritsu.chat.prepare',{
    requestId,sessionId,channel:'control'});
  await assert.rejects(call(admin,user,'ritsu.chat.publish',{
    requestId,sessionId,channel:'control',
    callbackKey:t.callbackKey,text:'Y'.repeat(5001)}),
    /bounded_answer_text_required/);
  const after=await call(admin,user,'ritsu.chat.result',{turnId:requestId});
  assert.equal(after.state,'prepared');
});
