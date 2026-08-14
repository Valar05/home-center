#!/usr/bin/env node
import fs from 'node:fs';
import {createRequire} from 'node:module';

const require = createRequire(import.meta.url);
const contract = require('../functions/dungeon_run_contract');
const relayModule = require('../functions/phone_hands_relay');
const relay = fs.readFileSync('functions/phone_hands_relay.js', 'utf8');
const operation = fs.readFileSync('functions/dungeon_run_operation.js', 'utf8');
const mcp = fs.readFileSync('functions/home_center_mcp.js', 'utf8');
const phone = fs.readFileSync('tools/android_phone_home_center_relay.py', 'utf8');
const runner = fs.readFileSync('tools/mobile_coding_dungeon_v2.py', 'utf8');

for (const needle of [
  'cleanDungeonRun', 'cleanDungeonStatus', 'coding_dungeon_v2', 'requestHash',
  'priorityRank', 'leaseId', 'recoverStaleDungeonLeases', 'exact live admission lease',
]) if (!relay.includes(needle)) throw new Error(`typed relay boundary missing ${needle}`);

for (const needle of [
  'dungeon_run', 'dungeon_status', 'dungeon_command_status', 'enqueuePhoneCommand',
  'callerFromHomeCenterUser', 'checkpoint-only',
]) if (!operation.includes(needle)) throw new Error(`direct dungeon operation missing ${needle}`);

for (const needle of [
  "require('./dungeon_run_operation')", '...dungeonOperationEntries()',
  "operation === 'dungeon_run'", "operation === 'dungeon_status'",
  "operation === 'dungeon_command_status'", '2026-08-13.fortress-dungeon-v2',
]) if (!mcp.includes(needle)) throw new Error(`stable drive_operation ingress missing ${needle}`);

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
  'QUARANTINED', 'phone-state://coding-dungeon-v2',
]) if (!runner.includes(needle)) throw new Error(`phone-local coordinator missing ${needle}`);
for (const forbidden of ["shell=True", "subprocess.run(cmd", "get('manifest')", "get(\"manifest\")"] ) {
  if (runner.includes(forbidden)) throw new Error(`v2 coordinator contains forbidden execution surface: ${forbidden}`);
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

class Snap { constructor(value){this.value=value;this.exists=value!==undefined;} data(){return this.value;} }
class Ref {
  constructor(store,path){this.store=store;this.path=path;}
  async get(){return new Snap(this.store.get(this.path));}
  async set(value,options={}){const prior=this.store.get(this.path)||{};this.store.set(this.path,options.merge?{...prior,...value}:value);}
}
class Collection { constructor(store,name){this.store=store;this.name=name;} doc(id){return new Ref(this.store,`${this.name}/${id}`);} }
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
firestore.store.set(commandPath,{...firestore.store.get(commandPath),status:'leased',leaseOwner:'device:primary-phone',leaseId:'lease-live'});
const submitReceipt={
  schema:'home-center.dungeon-submit-receipt.v2',requestId:critical.requestId,
  inputHash:contract.dungeonRequestHash(critical),jobId:'dng_0123456789abcdef01234567',
  tmuxSession:'hc-dng-0123456789abcdef',state:'ACCEPTED',attached:false,
};
await assertRejects(()=>relayModule.deviceComplete(admin,{
  deviceId:'primary-phone',deviceToken:token,commandId:admitted.commandId,leaseId:'lease-stale',status:'completed',result:submitReceipt,
}),/exact live admission lease/);
await relayModule.deviceComplete(admin,{
  deviceId:'primary-phone',deviceToken:token,commandId:admitted.commandId,leaseId:'lease-live',status:'completed',result:submitReceipt,
});

async function assertRejects(call, pattern){
  let error;
  try{await call();}catch(exc){error=exc;}
  if(!error||!pattern.test(String(error.message||error)))throw new Error(`expected rejection ${pattern}, received ${error}`);
}

console.log('Fortress typed dungeon ingress / critical lane / fixed decay contract: PASS');
