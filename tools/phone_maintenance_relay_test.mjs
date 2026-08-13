#!/usr/bin/env node
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';

const require=createRequire(import.meta.url);
const {
  cleanAction,enqueuePhoneCommand,devicePull,deviceComplete,maintenanceReceiptHash,hashText,COLLECTIONS,rejectNativeMaintenanceFromCommandCenter,
}=require('../functions/phone_hands_relay.js');
const phoneSurface=require('../functions/phone_operation_surface.js');

function canonical(value){
  if(value===null||typeof value==='boolean'||typeof value==='string'||typeof value==='number')return JSON.stringify(value);
  if(Array.isArray(value))return `[${value.map(canonical).join(',')}]`;
  return `{${Object.keys(value).sort().map((key)=>`${JSON.stringify(key)}:${canonical(value[key])}`).join(',')}}`;
}
function action(overrides={}){
  return {
    action:'anvil_shell_build_install',schema:'phone.maintenance.anvil-shell.v1',
    operation:'anvil_shell.build_install.v1',automaticReplay:false,
    deviceId:'primary-phone',packageId:'com.continuecontinue.anvilshell',
    workerId:'phone-relay:primary-phone',queueDocId:'queue-anvil-1',
    queueRevision:'revision-1',commissionHash:'a'.repeat(64),
    laneId:'PHONE_MAINTENANCE',sessionId:'session-1',approvalId:'approval-1',
    leaseId:'lease-1',sourceRepository:'Valar05/continue-continue',
    sourceHead:'7e0e949ba3e3aefa8df608226086b6273cfb16ca',
    sourceSubdir:'edge/android-shell',expectedVersionName:'0.1.0-checkpoint',
    timeoutSeconds:1800,networkPolicy:'bootstrap-and-build',
    rollbackPolicy:'retain_previous_apk_if_present',...overrides,
  };
}

assert.deepEqual(Object.keys(phoneSurface.operationEntries()).sort(),[
  'phone.devices','phone.diagnostics.enqueue','phone.maintenance.enqueue','phone.operation.get',
]);
const clean=cleanAction(action());
assert.equal(clean.operation,'anvil_shell.build_install.v1');
assert.equal(clean.automaticReplay,false);
for(const bad of [
  action({command:'gradle assemble'}),action({argv:['sh','-c','id']}),
  action({url:'https://example.invalid/source'}),action({sourceRepository:'other/repo'}),
  action({sourceSubdir:'../escape'}),action({deviceId:'other-phone'}),
  action({laneId:'PHONE_INTERACTION'}),action({automaticReplay:true}),
  action({sourceHead:'main'}),action({commissionHash:'bad'}),
  action({networkPolicy:'offline'}),action({timeoutSeconds:3601}),
]) assert.throws(()=>cleanAction(bad));
assert.throws(
  ()=>rejectNativeMaintenanceFromCommandCenter({action:action()}),
  (error)=>error&&error.status===410&&error.code==='capability_retired.command_center_phone_maintenance',
);
assert.doesNotThrow(()=>rejectNativeMaintenanceFromCommandCenter({action:{action:'phone_diagnostics'}}));

class Snap{constructor(value){this.value=value;this.exists=value!==undefined;}data(){return this.value;}}
class Ref{
  constructor(store,path){this.store=store;this.path=path;}
  async get(){return new Snap(this.store.get(this.path));}
  async set(value,options={}){const prior=this.store.get(this.path)||{};this.store.set(this.path,options.merge?{...prior,...value}:value);}
}
class Query{
  constructor(store,name,filters=[]){this.store=store;this.name=name;this.filters=filters;}
  where(key,_op,value){return new Query(this.store,this.name,[...this.filters,[key,value]]);}
  limit(){return this;}
  async get(){
    const docs=[];
    for(const [path,value] of this.store){
      if(!path.startsWith(this.name+'/'))continue;
      if(this.filters.every(([key,expected])=>value[key]===expected))docs.push({data:()=>value});
    }
    return {docs};
  }
}
class Collection extends Query{
  constructor(store,name){super(store,name);}
  doc(id){return new Ref(this.store,`${this.name}/${id}`);}
}
class FakeFirestore{
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
const token='x'.repeat(48);
firestore.store.set(`${COLLECTIONS.devices}/primary-phone`,{
  ownerKey:'owner-1',deviceId:'primary-phone',tokenHash:hashText(token),
  capabilities:['phone_diagnostics_readonly','phone_maintenance_anvil_shell'],
});
const caller={ownerKey:'owner-1',actor:'owner@example.invalid'};
const request=action();
const queued=await enqueuePhoneCommand(admin,caller,{idempotencyKey:'anvil-idem-1',deviceId:'primary-phone',action:request});
assert.equal(queued.replayPolicy,'NEVER_AUTOMATIC');
const replay=await enqueuePhoneCommand(admin,caller,{idempotencyKey:'anvil-idem-1',deviceId:'primary-phone',action:request});
assert.equal(replay.commandId,queued.commandId);
await assert.rejects(()=>enqueuePhoneCommand(admin,caller,{idempotencyKey:'anvil-idem-1',deviceId:'primary-phone',action:action({sessionId:'different'})}),/bound to a different request/);
const pulled=await devicePull(admin,{deviceId:'primary-phone',deviceToken:token,leaseMs:1000});
assert.equal(pulled.command.action.operation,'anvil_shell.build_install.v1');
const leased=firestore.store.get(`${COLLECTIONS.commands}/${queued.commandId}`);
assert.ok(leased.leaseExpiresAtMs-Date.now()>1700*1000);

const base={
  schema:'phone.maintenance.anvil-shell.receipt.v1',operation:request.operation,
  requestHash:hashText(canonical(cleanAction(request))),deviceId:request.deviceId,
  packageId:request.packageId,workerId:request.workerId,queueDocId:request.queueDocId,
  queueRevision:request.queueRevision,commissionHash:request.commissionHash,laneId:request.laneId,
  sessionId:request.sessionId,approvalId:request.approvalId,leaseId:request.leaseId,
  sourceRepository:request.sourceRepository,sourceHead:request.sourceHead,
  sourceSubdir:request.sourceSubdir,expectedVersionName:request.expectedVersionName,
  automaticReplay:false,networkUsed:true,writeUsed:true,subprocessUsed:true,buildUsed:true,
  installUsed:true,uiUsed:false,testsPassed:true,buildExit:0,installExit:0,
  readbackVerified:true,apkSha256:'b'.repeat(64),apkBytes:1234,signerSha256:'c'.repeat(64),
  installedApkSha256:'b'.repeat(64),installedPackageId:request.packageId,
  installedVersionName:request.expectedVersionName,installedVersionCode:'1',
  installStrategy:'pm',installedPaths:['/data/app/example/base.apk'],
  toolchain:{git:'git 2',java:'17',gradle:'8.13',apksigner:'0.9'},
  rollback:{policy:request.rollbackPolicy,previousPackageObserved:false,retained:false,previousApkSha256:''},
  startedAtNs:'1',finishedAtNs:'2',status:'INSTALLED_READBACK_VERIFIED',
};
const receipt={...base,receiptHash:maintenanceReceiptHash(base)};
await assert.rejects(()=>deviceComplete(admin,{deviceId:'primary-phone',deviceToken:token,commandId:queued.commandId,status:'completed',result:{...receipt,readbackVerified:false}}),/receipt identity/);
await deviceComplete(admin,{deviceId:'primary-phone',deviceToken:token,commandId:queued.commandId,status:'completed',result:receipt});
assert.equal(firestore.store.get(`${COLLECTIONS.commands}/${queued.commandId}`).status,'completed');
console.log('native phone maintenance allowlist, lease, replay, and terminal receipt validation: PASS');
