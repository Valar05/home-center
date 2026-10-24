'use strict';
const test=require('node:test');
const assert=require('node:assert/strict');
const {createHash}=require('node:crypto');
const {runRitsuCloudPairMcp:run}=require('./ritsu_cloud_pairing_mcp');
const id='Ritsu_Owner_Pair_ABC123456789';
const code='037592',email='owner@example.invalid',uid='firebase-owner';
const hash=createHash('sha256').update(code).digest('hex');
function fixture(state='pending',expiresAtMs=Date.now()+600000){
 const docs=new Map([['termuxPairingRequests/'+id,{clientKind:'ritsu-control-android',status:state,
     codeHash:hash,requestedGroups:['drive','docs','github'],expiresAtMs}]]);
 function ref(k){return {k}}
 const db={collection(name){return {doc(key){return ref(name+'/'+key)}}},
 async runTransaction(fn){
  const writes=[];
  const tx={
    async get(r){return {exists:docs.has(r.k),data:()=>docs.get(r.k)}},
    update(r,x){writes.push(()=>docs.set(r.k,{...docs.get(r.k),...x}))},
    create(r,x){if(docs.has(r.k))throw Error('duplicate');writes.push(()=>docs.set(r.k,x))}
  };
  const out=await fn(tx);for(const w of writes)w();return out;
 }};
 const admin={firestore:()=>db,auth:()=>({getUserByEmail:async e=>({uid,email:e,disabled:false})})};
 return {docs,admin};
}
const actor={email};
const args={pairingId:id,code,approved:true,requestId:'owner-pair-audit-20261023-001'};
test('valid owner+exact code approve then app claim readback',async()=>{
 const f=fixture();
 const r=await run({admin:f.admin,user:actor,operation:'ritsu.cloud.pair.approve',args});
 assert.equal(r.state,'approved');assert.equal(r.devicePaired,false);
 assert.equal(f.docs.get('termuxPairingRequests/'+id).uid,uid);
 assert.equal(f.docs.get('termuxPairingRequests/'+id).approvalSource,'home_center_mcp_oauth_owner');
 const repeated=await run({admin:f.admin,user:actor,operation:'ritsu.cloud.pair.approve',args});
 assert.equal(repeated.idempotent,true);
 f.docs.get('termuxPairingRequests/'+id).status='claimed';
 const st=await run({admin:f.admin,user:actor,operation:'ritsu.cloud.pair.status',args:{pairingId:id}});
 assert.deepEqual([st.state,st.devicePaired],['claimed',true]);
});
test('wrong code, missing approval and expired challenge cannot approve',async()=>{
 for(const [field,value,expected] of [['code','037593','ritsu_pairing_code_rejected'],['approved',false,'explicit_pairing_approval_required']]){
  const f=fixture();
  await assert.rejects(run({admin:f.admin,user:actor,operation:'ritsu.cloud.pair.approve',args:{...args,[field]:value}}),
    err=>err.code===expected);
  assert.equal(f.docs.get('termuxPairingRequests/'+id).status,'pending');
 }
 const f=fixture('pending',Date.now()-1);
 await assert.rejects(run({admin:f.admin,user:actor,operation:'ritsu.cloud.pair.approve',args}),/expired_or_used/);
});
test('wrong Ritsu client or extra scopes blocked',async()=>{
 const f=fixture();f.docs.get('termuxPairingRequests/'+id).clientKind='codex-termux';
 await assert.rejects(run({admin:f.admin,user:actor,operation:'ritsu.cloud.pair.approve',args}),/not_ritsu_control/);
 const f2=fixture();f2.docs.get('termuxPairingRequests/'+id).requestedGroups.push('admin');
 await assert.rejects(run({admin:f2.admin,user:actor,operation:'ritsu.cloud.pair.approve',args}),/scope_rejected/);
});
test('Firebase owner mapping required',async()=>{
 const f=fixture();f.admin.auth=()=>({getUserByEmail:async()=>{const e=Error('absent');e.code='auth/user-not-found';throw e}});
 await assert.rejects(run({admin:f.admin,user:actor,operation:'ritsu.cloud.pair.approve',args}),/not_registered/);
});
test('cannot read another owners claimed pairing or reuse audit id for another challenge',async()=>{
 const f=fixture('claimed');f.docs.get('termuxPairingRequests/'+id).uid='other';
 await assert.rejects(run({admin:f.admin,user:actor,operation:'ritsu.cloud.pair.status',args:{pairingId:id}}),/other_owner/);
 const f2=fixture();f2.docs.set('ritsuCloudOAuthPairAudit/'+args.requestId,{uid:'other',pairingId:id,state:'approved'});
 await assert.rejects(run({admin:f2.admin,user:actor,operation:'ritsu.cloud.pair.approve',args}),/audit_request_id_conflict/);
});
