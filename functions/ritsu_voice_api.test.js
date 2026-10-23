'use strict';
const test=require('node:test');
const assert=require('node:assert/strict');
const api=require('./ritsu_voice_api');

test('fixed Warm voice and fixed phone transport',()=>{
 const request=api.validateSpeak({requestId:'turn-000001',text:'Hello, darling.',voice:'warm-v1',delivery:'phone'});
 assert.equal(request.voice,'warm-v1');
 assert.equal(request.delivery,'phone');
 assert.equal(request.expectedChunks,null);
 assert.equal(request.profile,'normal');
 assert.equal(api.validateSpeak({requestId:'turn-profile-10',text:'hello',profile:'somber'}).profile,'somber');
 assert.throws(()=>api.validateSpeak({requestId:'turn-profile-11',text:'hello',profile:'unregistered'}),/Unsupported Ritsu profile/);
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
test('advertise fixed profile registry and three narrow ticket operations, never generic shell',()=>{
 const e=api.entryList();
 assert.deepEqual(Object.keys(e).sort(),['ritsu.voice.profiles','ritsu.voice.speak','ritsu.voice.status','ritsu.voice.worker.register']);
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

test('every registered voice receives the user-approved minus-one semitone pitch shift',()=>{
 const catalog=require('./ritsu_voice_profiles.json');
 assert.deepEqual(Object.keys(catalog.profiles).sort(),['amused','happy','normal','somber','upset','whisper']);
 for (const [name,profile] of Object.entries(catalog.profiles)) assert.equal(profile.pitchSemitones,-1,`${name} pitch must be -1 semitone`);
});
