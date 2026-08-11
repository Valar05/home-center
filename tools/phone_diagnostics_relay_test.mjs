#!/usr/bin/env node
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';

const require=createRequire(import.meta.url);
const {
  cleanAction,enqueuePhoneCommand,deviceComplete,diagnosticChunkHash,diagnosticReceiptHash,hashText,COLLECTIONS,
}=require('../functions/phone_hands_relay.js');

function request(overrides={}) {
  return {
    action:'phone_diagnostics',
    schema:'phone.diagnostics.request.v1',
    diagnosticKind:'tree_inventory',
    deviceId:'primary-phone',
    packageId:'com.termux',
    workerId:'phone-relay:primary-phone',
    queueDocId:'queue-doc',
    queueRevision:'revision-1',
    commissionHash:'a'.repeat(64),
    laneId:'phone-diagnostics',
    sessionId:'session-1',
    streamId:'stream-1',
    chunkIndex:0,
    rootId:'GODOT_PROJECTS',
    maxEntries:200,
    maxBytes:524288,
    ...overrides,
  };
}

const clean=cleanAction(request());
assert.equal(clean.action,'phone_diagnostics');
assert.equal(clean.rootId,'GODOT_PROJECTS');
assert.equal(clean.maxEntries,200);
assert.equal(clean.maxBytes,524288);

for (const bad of [
  request({command:'find /'}),
  request({argv:['git','status']}),
  request({path:'/storage/emulated/0'}),
  request({rootId:'HOME'}),
  request({deviceId:'other-phone'}),
  request({packageId:'other.package'}),
  request({commissionHash:'forged'}),
  request({watermark:'../escape'}),
  request({previousChunkHash:'bad'}),
  request({chunkIndex:1}),
  request({chunkIndex:0,watermark:'a.md',previousChunkHash:'a'.repeat(64)}),
  request({extensions:['.apk']}),
  request({maxEntries:0}),
  request({maxBytes:999}),
]) {
  assert.throws(()=>cleanAction(bad));
}

for (const kind of ['capability_snapshot','toolchain_probe','cache_probe']) {
  const value=request({diagnosticKind:kind});
  delete value.rootId;
  assert.equal(cleanAction(value).diagnosticKind,kind);
}

for (const kind of ['tree_inventory','repo_status','file_manifest']) {
  assert.equal(cleanAction(request({diagnosticKind:kind})).diagnosticKind,kind);
}

console.log('typed phone diagnostics relay validation: PASS');

class Snap { constructor(value){this.value=value;this.exists=value!==undefined;} data(){return this.value;} }
class Ref {
  constructor(store,path){this.store=store;this.path=path;}
  async get(){return new Snap(this.store.get(this.path));}
  async set(value,options={}){const prior=this.store.get(this.path)||{};this.store.set(this.path,options.merge?{...prior,...value}:value);}
}
class Collection {
  constructor(store,name){this.store=store;this.name=name;}
  doc(id){return new Ref(this.store,`${this.name}/${id}`);}
}
class FakeFirestore {
  constructor(){this.store=new Map();}
  collection(name){return new Collection(this.store,name);}
  async runTransaction(callback){
    const staged=[];
    const tx={
      get:(ref)=>ref.get(),
      create:(ref,value)=>{if(ref.store.has(ref.path))throw new Error('already exists');staged.push(['set',ref,value]);},
      set:(ref,value,options={})=>staged.push(['merge',ref,value,options]),
    };
    const result=await callback(tx);
    for(const [kind,ref,value,options] of staged){
      if(kind==='set')ref.store.set(ref.path,value);else await ref.set(value,options);
    }
    return result;
  }
}
const firestore=new FakeFirestore();
const admin={firestore:()=>firestore};
const token='x'.repeat(32);
firestore.store.set(`${COLLECTIONS.devices}/primary-phone`,{
  ownerKey:'owner-1',deviceId:'primary-phone',tokenHash:hashText(token),capabilities:['phone_diagnostics_readonly'],
});
const caller={ownerKey:'owner-1',actor:'owner@example.invalid'};
const action0=request();
const first=await enqueuePhoneCommand(admin,caller,{idempotencyKey:'idem-1',deviceId:'primary-phone',action:action0});
const replay=await enqueuePhoneCommand(admin,caller,{idempotencyKey:'idem-1',deviceId:'primary-phone',action:action0});
assert.equal(replay.commandId,first.commandId);
await assert.rejects(()=>enqueuePhoneCommand(admin,caller,{
  idempotencyKey:'idem-1',deviceId:'primary-phone',action:request({maxEntries:1}),
}),/idempotency key is bound/);
await assert.rejects(()=>enqueuePhoneCommand(admin,caller,{
  idempotencyKey:'idem-2',deviceId:'primary-phone',action:action0,
}),/inflight chunk/);

const baseReceipt={
  schema:'phone.diagnostics.receipt.v1',diagnosticKind:action0.diagnosticKind,
  requestHash:hashText(JSON.stringify({})),
  deviceId:action0.deviceId,packageId:action0.packageId,workerId:action0.workerId,
  queueDocId:action0.queueDocId,queueRevision:action0.queueRevision,
  commissionHash:action0.commissionHash,laneId:action0.laneId,sessionId:action0.sessionId,
  streamId:action0.streamId,chunkIndex:0,rootId:'GODOT_PROJECTS',
  startedAtNs:'1',finishedAtNs:'2',networkUsed:false,writeUsed:false,subprocessUsed:false,
  buildUsed:false,installUsed:false,uiUsed:false,
  artifactPostback:{required:true,artifactKind:'phone-diagnostics-chunk.v1',durable:false,state:'PENDING_HOME_CENTER_POSTBACK'},
  result:{rootId:'GODOT_PROJECTS',watermarkBefore:'',watermarkAfter:'a.md',previousChunkHash:'',
    entries:[],entryCount:0,observedEntryCount:1,skipped:{hidden:0,secret:0,symlink:0,other:0},
    scanComplete:true,more:true,status:'MORE',byteCount:0},
};
baseReceipt.requestHash=hashText((()=>{
  const canonical=(value)=>{
    if(value===null||typeof value==='boolean'||typeof value==='string'||typeof value==='number')return JSON.stringify(value);
    if(Array.isArray(value))return `[${value.map(canonical).join(',')}]`;
    return `{${Object.keys(value).sort().map((key)=>`${JSON.stringify(key)}:${canonical(value[key])}`).join(',')}}`;
  };
  return canonical(cleanAction(action0));
})());
baseReceipt.result.chunkHash=diagnosticChunkHash(baseReceipt.result);
const receipt0={...baseReceipt,receiptHash:diagnosticReceiptHash(baseReceipt)};
await assert.rejects(()=>deviceComplete(admin,{
  deviceId:'primary-phone',deviceToken:token,commandId:first.commandId,status:'completed',result:receipt0,
}),/exact device lease/);
const commandPath=`${COLLECTIONS.commands}/${first.commandId}`;
firestore.store.set(commandPath,{...firestore.store.get(commandPath),status:'leased',leaseOwner:'device:primary-phone'});
await assert.rejects(()=>deviceComplete(admin,{
  deviceId:'primary-phone',deviceToken:token,commandId:first.commandId,status:'completed',
  result:{...receipt0,writeUsed:true},
}),/receipt identity or hash/);
await deviceComplete(admin,{
  deviceId:'primary-phone',deviceToken:token,commandId:first.commandId,status:'completed',result:receipt0,
});
await assert.rejects(()=>enqueuePhoneCommand(admin,caller,{
  idempotencyKey:'idem-3',deviceId:'primary-phone',action:request({chunkIndex:1,watermark:'a.md',previousChunkHash:'c'.repeat(64)}),
}),/stream CAS mismatch/);
const second=await enqueuePhoneCommand(admin,caller,{
  idempotencyKey:'idem-4',deviceId:'primary-phone',
  action:request({chunkIndex:1,watermark:'a.md',previousChunkHash:receipt0.result.chunkHash}),
});
assert.equal(second.action.chunkIndex,1);
firestore.store.set(`${COLLECTIONS.commands}/${second.commandId}`,{
  ...firestore.store.get(`${COLLECTIONS.commands}/${second.commandId}`),status:'failed',leaseOwner:'',
});
const streamPath=[...firestore.store.keys()].find((key)=>key.startsWith(`${COLLECTIONS.diagnosticStreams}/`));
firestore.store.set(streamPath,{...firestore.store.get(streamPath),inflightCommandId:''});
await assert.rejects(()=>enqueuePhoneCommand(admin,caller,{
  idempotencyKey:'idem-5',deviceId:'primary-phone',
  action:request({laneId:'foreign-lane',chunkIndex:1,watermark:'a.md',previousChunkHash:receipt0.result.chunkHash}),
}),/stream CAS mismatch/);
console.log('phone diagnostics relay replay/CAS/immutable receipt validation: PASS');
