'use strict';
const test=require('node:test');
const assert=require('node:assert/strict');
const api=require('./ritsu_voice_api');

test('fixed Warm voice and fixed phone transport',()=>{
 const request=api.validateSpeak({requestId:'turn-000001',text:'Hello, darling.',voice:'warm-v1',delivery:'phone'});
 assert.equal(request.voice,'warm-v1');
 assert.equal(request.delivery,'phone');
 assert.equal(request.expectedChunks,null);
 assert.throws(()=>api.validateSpeak({requestId:'turn-000002',text:'hello',voice:'fixed:kokoro:af_heart'}),/Warm v1/);
 assert.throws(()=>api.validateSpeak({requestId:'turn-000003',text:'hello',delivery:'drive'}),/phone/);
 assert.throws(()=>api.validateSpeak({requestId:'turn-000004',text:'ok',action:'shell.exec'}),/Unexpected/);
});
test('fail closed on invalid payload',()=>{
 for(const a of [
  {requestId:'x',text:'hello'},
  {requestId:'turn-000005',text:''},
  {requestId:'turn-000006',text:'x'.repeat(5001)},
  {requestId:'turn-000007',text:'one\u0000two'},
  {requestId:'turn-000008',text:'ok',chunks:51}
 ])assert.throws(()=>api.validateSpeak(a));
});
test('advertise only the three narrow operations, never generic shell',()=>{
 const e=api.entryList();
 assert.deepEqual(Object.keys(e).sort(),['ritsu.voice.speak','ritsu.voice.status','ritsu.voice.worker.register']);
 assert.equal(JSON.stringify(e).includes('shell.exec'),false);
});
function fakeDb(){
 const rows=new Map();
 return {firestore(){return {
  collection(name){return {doc(key){const p=name+'/'+key;return {path:p,async get(){return {exists:rows.has(p),data(){return rows.get(p)}}}}}}},
  async runTransaction(fn){return fn({
   async get(ref){return {exists:rows.has(ref.path),data(){return rows.get(ref.path)}}},
   create(ref,value){if(rows.has(ref.path))throw Error('duplicate');rows.set(ref.path,value)},
   set(ref,value){rows.set(ref.path,value)},
   update(ref,patch){rows.set(ref.path,{...rows.get(ref.path),...patch})}
  });}
 }}};
}
test('retry with same id is idempotent and content cannot change',async()=>{
 const admin=fakeDb(),user={email:'owner@example.com'},args={requestId:'speech-0001',text:'Complete exact reply.'};
 const first=await api.runOperation({admin,user,operation:'ritsu.voice.speak',args});
 assert.equal(first.status,'queued');assert.equal(first.idempotent,false);
 const again=await api.runOperation({admin,user,operation:'ritsu.voice.speak',args});
 assert.equal(again.idempotent,true);
 await assert.rejects(api.runOperation({admin,user,operation:'ritsu.voice.speak',args:{...args,text:'New reply'}}),/Idempotency conflict/);
});
