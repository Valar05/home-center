#!/usr/bin/env node
import fs from 'node:fs';
import {createRequire} from 'node:module';

const require = createRequire(import.meta.url);
const contract = require('../functions/dungeon_run_contract');
const relayModule = require('../functions/phone_hands_relay');
const dungeonOperationModule = require('../functions/dungeon_run_operation');
const relay = fs.readFileSync('functions/phone_hands_relay.js', 'utf8');
const operation = fs.readFileSync('functions/dungeon_run_operation.js', 'utf8');
const mcp = fs.readFileSync('functions/home_center_mcp.js', 'utf8');
const phone = fs.readFileSync('tools/android_phone_home_center_relay.py', 'utf8');
const runner = fs.readFileSync('tools/mobile_coding_dungeon_v2.py', 'utf8');
const localAdapter = fs.readFileSync('tools/dungeon_local_adam.py', 'utf8');
const firestoreIndexes = JSON.parse(fs.readFileSync('firebase/firestore.indexes.json', 'utf8'));

for (const needle of [
  'cleanDungeonRun', 'cleanDungeonStatus', 'coding_dungeon_v2', 'requestHash',
  'priorityRank', 'leaseId', 'recoverStaleDungeonLeases', 'expireQueuedCommands',
  "orderBy('priorityRank','asc')", "orderBy('createdAtMs','asc')", "orderBy('commandId','asc')",
  'ADMISSION_EXPIRED', 'exact owner replay renewed expired admission', 'exact live admission lease',
]) if (!relay.includes(needle)) throw new Error(`typed relay boundary missing ${needle}`);

const queueIndex = firestoreIndexes.indexes.find((index) => index.collectionGroup === 'phoneHandsCommands');
const queueFields = (queueIndex?.fields || []).map((field) => field.fieldPath).join(',');
if (queueFields !== 'ownerKey,deviceId,status,priorityRank,createdAtMs,commandId') {
  throw new Error(`deterministic phone queue index is missing or misordered: ${queueFields}`);
}

for (const needle of [
  'dungeon_run', 'dungeon_status', 'dungeon_command_status', 'enqueuePhoneCommand',
  'callerFromHomeCenterUser', 'checkpoint-only', 'fortress_dungeon_v2',
  'compileDungeonWorkAction', 'executeDungeonWorkRequest', 'phone-local-fail-closed',
]) if (!operation.includes(needle)) throw new Error(`direct dungeon operation missing ${needle}`);

for (const needle of [
  "require('./dungeon_run_operation')", '...dungeonOperationEntries()',
  "operation === 'dungeon_run'", "operation === 'dungeon_status'",
  "operation === 'dungeon_command_status'", '2026-08-13.fortress-dungeon-v2',
  'DUNGEON_WORK_ROUTE', 'executeDungeonWorkRequest', 'defaultFortressWorkExecutor',
  'dungeonBudgetProfile', 'dungeonVerificationProfile',
]) if (!mcp.includes(needle)) throw new Error(`stable drive_operation ingress missing ${needle}`);
if (!operation.includes('fresh unique snapshot id for each poll')) {
  throw new Error('dungeon_status must advertise fresh immutable snapshot identity');
}

for (const needle of [
  'mobile_coding_dungeon_v2', 'DUNGEON_ACTIONS', 'coding_dungeon_v2',
  "if k in DUNGEON_ACTIONS:return dispatch(a)", "'leaseId':cmd.get('leaseId','')",
]) if (!phone.includes(needle)) throw new Error(`phone relay v2 integration missing ${needle}`);
if (phone.includes("p.get('manifest')") || phone.includes("dungeon_run requires manifest")) {
  throw new Error('legacy caller-selected manifest path remains reachable');
}
if (phone.indexOf("if k in DUNGEON_ACTIONS:return dispatch(a)") > phone.indexOf('gate=overlay_control_gate()')) {
  throw new Error('screenless dungeon ingress must bypass the overlay/Shizuku gate');
}

for (const needle of [
  'shell=False', 'codex-local-low-deterministic-v1', 'workspace-write',
  'ask-for-approval', 'checkpoint-only', 'prepare_worktree', 'launch_tmux',
  'QUARANTINED', 'phone-state://coding-dungeon-v2', 'TOKEN_DROUGHT_SCHEMA',
  'paid_inference_skipped', 'codex = None if drought["active"]', 'drought_sub',
]) if (!runner.includes(needle)) throw new Error(`phone-local coordinator missing ${needle}`);
for (const forbidden of ["shell=True", "subprocess.run(cmd", "get('manifest')", "get(\"manifest\")"] ) {
  if (runner.includes(forbidden)) throw new Error(`v2 coordinator contains forbidden execution surface: ${forbidden}`);
}
for (const needle of ['disabled_run_command', 'disabled_phone_intent', 'worker.run_command =', 'worker.phone_intent =']) {
  if (!localAdapter.includes(needle)) throw new Error(`local inference confinement missing ${needle}`);
}

const critical = contract.cleanDungeonRun({
  requestId:'critical-campaign-0001', campaignId:'fortress-online', workspaceId:'home-center',
  objective:'Repair one exact first-class execution aperture.', acceptance:['Typed ingress passes.'],
  lane:'critical', criticalReason:'The owner designated this as the recovery-critical lane.',
});
const standard = contract.cleanDungeonRun({
  requestId:'standard-campaign-0001', campaignId:'fortress-online', workspaceId:'home-center',
  objective:'Perform one ordinary bounded maintenance task.', acceptance:['Verification passes.'],
});
const status = contract.cleanDungeonStatus({requestId:'status-campaign-0001',jobId:'dng_0123456789abcdef01234567'});
const work = {
  taskId:'task-fortress-zero-token', ownerKey:'owner-test', projectId:'fortress-online',
  route:'fortress_dungeon_v2', requestText:'Continue the exact Fortress mission without paid inference.',
  requestHash:'a'.repeat(64), taskKind:'implement', stateHistory:[], subsystemRefs:[],
};
const workArgs = {
  requestId:'fortress-work-zero-token-0001', acceptance:['A verified isolated checkpoint exists.'],
  constraints:['Remote callers cannot clear local token drought.'], dungeonLane:'critical',
  dungeonCriticalReason:'Paid inference is exhausted and deterministic continuation is required.',
  dungeonBudgetProfile:'probe', dungeonVerificationProfile:'fast',
};
const compiledWork = dungeonOperationModule.compileDungeonWorkAction({caller:{ownerKey:'owner-test'},work,args:workArgs});
if (compiledWork.inferencePolicy !== 'codex-local-low-deterministic-v1' || compiledWork.publicationPolicy !== 'checkpoint-only') {
  throw new Error('work request did not preserve fixed inference/publication policy');
}
if ('tokenDrought' in compiledWork || 'paidInferenceAllowed' in compiledWork) {
  throw new Error('remote work request gained token-drought mutation authority');
}
await assertRejects(async()=>dungeonOperationModule.compileDungeonWorkAction({
  caller:{ownerKey:'owner-test'},work,args:{...workArgs,acceptance:undefined},
}),/acceptance/);
const queuedWork = await dungeonOperationModule.executeDungeonWorkRequest({
  admin:{}, caller:{ownerKey:'owner-test'}, work, args:workArgs, now:1700000000000,
  runOperation:async({args})=>({commandId:'phd_test',state:'queued',requestHash:contract.dungeonRequestHash(args),attached:false,result:null}),
});
if (queuedWork.state !== 'QUEUED' || queuedWork.result.commandId !== 'phd_test') throw new Error('work queue admission state is invalid');
const checkpointWork = await dungeonOperationModule.executeDungeonWorkRequest({
  admin:{}, caller:{ownerKey:'owner-test'}, work, args:workArgs, now:1700000000001,
  runOperation:async({args})=>({
    commandId:'phd_done',state:'completed',requestHash:contract.dungeonRequestHash(args),attached:true,
    result:{jobId:'dng_0123456789abcdef01234567',state:'SUCCEEDED',tmuxSession:'hc-dng-0123456789abcdef',statusRef:'phone-state://coding-dungeon-v2/jobs/dng_0123456789abcdef01234567'},
  }),
});
if (checkpointWork.state !== 'SUCCEEDED') throw new Error('verified checkpoint did not close the bounded work item');
if (!checkpointWork.result.capabilityMeaning.includes('does not mean pushed, merged, deployed')) throw new Error('checkpoint truth boundary was lost');

const now = Date.now();
const chosen = relayModule.selectQueuedCommand([
  {commandId:'ordinary', action:standard, createdAtMs:now-1000, expiresAtMs:now+10000},
  {commandId:'critical', action:critical, createdAtMs:now, expiresAtMs:now+10000},
  {commandId:'status', action:status, createdAtMs:now+1000, expiresAtMs:now+10000},
], now);
if (chosen.commandId !== 'status') throw new Error('status/critical deterministic queue ordering failed');
const criticalChosen = relayModule.selectQueuedCommand([
  {commandId:'ordinary', action:standard, createdAtMs:now-1000, expiresAtMs:now+10000},
  {commandId:'critical', action:critical, createdAtMs:now, expiresAtMs:now+10000},
], now);
if (criticalChosen.commandId !== 'critical') throw new Error('critical lane did not outrank ordinary work');

class Snap {
  constructor(value, ref=null){this.value=value;this.exists=value!==undefined;this.ref=ref;}
  data(){return this.value;}
}
class Ref {
  constructor(store,path){this.store=store;this.path=path;}
  async get(){return new Snap(this.store.get(this.path),this);}
  async set(value,options={}){const prior=this.store.get(this.path)||{};this.store.set(this.path,options.merge?{...prior,...value}:value);}
}
class Query {
  constructor(store,name,filters=[],orders=[],cap=Infinity){
    this.store=store;this.name=name;this.filters=filters;this.orders=orders;this.cap=cap;
  }
  where(field,op,value){
    if(op!=='==')throw new Error(`fake query supports equality only, received ${op}`);
    return new Query(this.store,this.name,[...this.filters,[field,value]],this.orders,this.cap);
  }
  orderBy(field,direction='asc'){
    return new Query(this.store,this.name,this.filters,[...this.orders,[field,direction]],this.cap);
  }
  limit(cap){return new Query(this.store,this.name,this.filters,this.orders,cap);}
  async get(){
    const prefix=`${this.name}/`;
    const rows=[...this.store.entries()].filter(([path,value])=>
      path.startsWith(prefix)&&this.filters.every(([field,expected])=>value?.[field]===expected));
    rows.sort((left,right)=>{
      for(const [field,direction] of this.orders){
        const a=left[1]?.[field];const b=right[1]?.[field];
        const compared=typeof a==='number'&&typeof b==='number'?a-b:String(a??'').localeCompare(String(b??''));
        if(compared)return direction==='desc'?-compared:compared;
      }
      return left[0].localeCompare(right[0]);
    });
    return {docs:rows.slice(0,this.cap).map(([path,value])=>new Snap(value,new Ref(this.store,path)))};
  }
}
class Collection {
  constructor(store,name){this.store=store;this.name=name;}
  doc(id){return new Ref(this.store,`${this.name}/${id}`);}
  where(field,op,value){return new Query(this.store,this.name).where(field,op,value);}
}
class FakeFirestore {
  constructor(){this.store=new Map();}
  collection(name){return new Collection(this.store,name);}
  async runTransaction(callback){
    const staged=[];
    const transaction={
      get:(ref)=>ref.get(),
      create:(ref,value)=>{if(ref.store.has(ref.path))throw new Error('already exists');staged.push(['create',ref,value,{}]);},
      set:(ref,value,options={})=>staged.push(['set',ref,value,options]),
    };
    const result=await callback(transaction);
    for(const [,ref,value,options] of staged) await ref.set(value,options);
    return result;
  }
}
const firestore=new FakeFirestore();
const admin={firestore:()=>firestore};
const caller={ownerKey:'owner-test',actor:'owner@example.invalid'};
const token='x'.repeat(40);
firestore.store.set(`${relayModule.COLLECTIONS.devices}/primary-phone`,{
  deviceId:'primary-phone',ownerKey:caller.ownerKey,tokenHash:relayModule.hashText(token),capabilities:['coding_dungeon_v2'],
});
const admitted=await relayModule.enqueuePhoneCommand(admin,caller,{
  idempotencyKey:critical.requestId,deviceId:'primary-phone',action:critical,
});
const attached=await relayModule.enqueuePhoneCommand(admin,caller,{
  idempotencyKey:critical.requestId,deviceId:'primary-phone',action:critical,
});
if(admitted.commandId!==attached.commandId||attached.attached!==true)throw new Error('exact replay did not attach');
await assertRejects(()=>relayModule.enqueuePhoneCommand(admin,caller,{
  idempotencyKey:critical.requestId,deviceId:'primary-phone',action:{...critical,objective:'Different exact intent that must conflict.'},
}),/different exact intent/);
const commandPath=`${relayModule.COLLECTIONS.commands}/${admitted.commandId}`;
const ordinaryAdmitted=await relayModule.enqueuePhoneCommand(admin,caller,{
  idempotencyKey:standard.requestId,deviceId:'primary-phone',action:standard,
});
const ordinaryPath=`${relayModule.COLLECTIONS.commands}/${ordinaryAdmitted.commandId}`;
firestore.store.set(ordinaryPath,{...firestore.store.get(ordinaryPath),createdAtMs:admitted.createdAtMs-10000});
const pulled=await relayModule.devicePull(admin,{deviceId:'primary-phone',deviceToken:token,leaseMs:30000});
if(pulled.command?.commandId!==admitted.commandId)throw new Error('indexed device pull did not honor critical priority over older ordinary work');
const liveLease=pulled.command.leaseId;
const submitReceipt={
  schema:'home-center.dungeon-submit-receipt.v2',requestId:critical.requestId,
  inputHash:contract.dungeonRequestHash(critical),jobId:'dng_0123456789abcdef01234567',
  tmuxSession:'hc-dng-0123456789abcdef',state:'ACCEPTED',attached:false,
};
await assertRejects(()=>relayModule.deviceComplete(admin,{
  deviceId:'primary-phone',deviceToken:token,commandId:admitted.commandId,leaseId:'lease-stale',status:'completed',result:submitReceipt,
}),/exact live admission lease/);
await relayModule.deviceComplete(admin,{
  deviceId:'primary-phone',deviceToken:token,commandId:admitted.commandId,leaseId:liveLease,status:'completed',result:submitReceipt,
});
firestore.store.set(ordinaryPath,{
  ...firestore.store.get(ordinaryPath),status:'queued',expiresAtMs:Date.now()-1,
});
const expiredPull=await relayModule.devicePull(admin,{deviceId:'primary-phone',deviceToken:token,leaseMs:30000});
if(expiredPull.command!==null||firestore.store.get(ordinaryPath)?.failureCode!=='ADMISSION_EXPIRED') {
  throw new Error('expired queued admission was not closed explicitly');
}
const renewed=await relayModule.enqueuePhoneCommand(admin,caller,{
  idempotencyKey:standard.requestId,deviceId:'primary-phone',action:standard,
});
if(renewed.commandId!==ordinaryAdmitted.commandId||renewed.status!=='queued'||renewed.attached!==true||
   renewed.lastRecoveryReason!=='exact owner replay renewed expired admission') {
  throw new Error('exact expired admission replay did not renew the same command identity');
}

async function assertRejects(call, pattern){
  let error;
  try{await call();}catch(exc){error=exc;}
  if(!error||!pattern.test(String(error.message||error)))throw new Error(`expected rejection ${pattern}, received ${error}`);
}

console.log('Fortress typed dungeon ingress / critical lane / fixed decay contract: PASS');
