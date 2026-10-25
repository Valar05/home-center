import test from 'node:test';
import assert from 'node:assert/strict';
import {parseAgentAction,sha256,executionDecision,SCRIPT_PROTOCOL,
        receiptForAgent} from './contract.mjs';
import {runSlice} from './engine.mjs';

const context={campaignId:'campaign-test-00001',
  tabId:'main',machineId:'termux-android'};
const script=(id,body='console.log("ok")')=>({
  protocol:SCRIPT_PROTOCOL,kind:'run_script',...context,
  turnId:'turn-test-0001',scriptId:id,language:'node',script:body,
  sha256:sha256(body),relativeCwd:'.',mode:'inspect',timeoutSeconds:10
});
// Strict relative work directories allow '.' meaning workspace root.
function action(id,body='console.log("ok")'){
  return {...script(id,body),relativeCwd:'workspace'};
}
const complete={protocol:SCRIPT_PROTOCOL,kind:'complete',...context,
  turnId:'turn-test-0001',finalText:'Agent finished after verified steps.'};
const policy={...context,ownerApproved:true,language:'node',
  allowWorkspaceWrites:false,executionIsolationVerified:true};
function log(){
 const entries=[],checkpoints=[];
 return {entries,checkpoints,receipts:new Map(),
   async append(x){entries.push(x)},
   async checkpoint(x){checkpoints.push(x)}};
}
test('agent auto continues scripts and only explicit COMPLETE ends campaign',async()=>{
 let calls=0,outputs=[];
 const actions=[action('script-0000001'),action('script-0000002'),complete];
 const state=log();
 const agent={async next({previousReceipt}){
   if(previousReceipt)outputs.push(previousReceipt);
   return actions.shift();
 }};
 const executor={async runValidated(a){calls++;return {
   status:'succeeded',exitCode:0,output:'RESULT='+a.scriptId,verified:true
 }}};
 const result=await runSlice({context,policy,agent,executor,journal:state,limit:10});
 assert.equal(result.phase,'completed');
 assert.equal(result.finalText,complete.finalText);
 assert.equal(calls,2);
 assert.equal(outputs.length,2);
 assert.equal(outputs[0].scriptId,'script-0000001');
 assert.equal(outputs[1].scriptId,'script-0000002');
 assert.equal(state.checkpoints.at(-1).phase,'completed');
});
test('failed execution is returned to agent, not treated as done',async()=>{
 const actions=[action('script-0000003'),action('script-0000004'),complete];
 let failedReceipt=false;
 const result=await runSlice({context,policy,
   agent:{async next({previousReceipt}){
     if(previousReceipt?.status==='failed')failedReceipt=true;
     return actions.shift();
   }},
   executor:{async runValidated(a){
      if(a.scriptId==='script-0000003')throw Error('synthetic_engine_failure');
      return {status:'succeeded',exitCode:0,output:'repaired',verified:true};
   }},
   journal:log()});
 assert.equal(result.phase,'completed');
 assert.equal(failedReceipt,true);
});
test('bounded checkpoint is CONTINUE_REQUIRED, never COMPLETED',async()=>{
 let i=0;
 const journal=log();
 const result=await runSlice({context,policy,journal,limit:2,
   agent:{async next(){return action('script-'+String(++i).padStart(7,'0'))}},
   executor:{async runValidated(){return {status:'succeeded',verified:true}}}});
 assert.equal(result.phase,'continue_required');
 assert.equal(journal.checkpoints.at(-1).phase,'continue_required');
});
test('same script ID with same hash only executes once',async()=>{
 const actions=[action('script-0000005'),action('script-0000005'),complete];
 let count=0;
 const j=log();
 const done=await runSlice({context,policy,journal:j,
  agent:{async next(){return actions.shift()}},
  executor:{async runValidated(){count++;return {status:'succeeded',verified:true}}}});
 assert.equal(done.phase,'completed');
 assert.equal(count,1);
 assert(j.entries.some(e=>e.event==='script_replayed'));
});
test('file/image requires explicit user request and never autoloads',async()=>{
 const asset={...context,protocol:SCRIPT_PROTOCOL,turnId:'turn-test-0001',
   kind:'request_asset',assetType:'image',requestedByUser:true,query:'screenshot'};
 assert.throws(()=>parseAgentAction({...asset,requestedByUser:false},context),
   /asset_must_be_explicitly_requested/);
 let executed=false;
 const res=await runSlice({context,policy,journal:log(),
  agent:{async next(){return asset}},
  executor:{async runValidated(){executed=true}}});
 assert.equal(res.phase,'asset_requested');
 assert.equal(executed,false);
});
test('machine target, script hash, unsafe cwd and write gates',()=>{
 assert.throws(()=>parseAgentAction({...action('script-0000006'),machineId:'windows-cauldron'},context),
   /mismatch/);
 assert.throws(()=>parseAgentAction({...action('script-0000006'),sha256:'0'.repeat(64)},context),
   /invalid_script_or_hash/);
 assert.throws(()=>parseAgentAction({...action('script-0000006'),relativeCwd:'../outside'},context),
   /unsafe_relative_directory/);
 const x=parseAgentAction({...action('script-0000006'),mode:'workspace-write'},context);
 assert.equal(executionDecision(x,policy).execute,false);
 assert.equal(executionDecision(parseAgentAction(action('script-0000006'),context),
  {...policy,executionIsolationVerified:false}).execute,false);
});
test('owner input has predefined dropdown options; cannot end implicitly',async()=>{
 const ask={...context,protocol:SCRIPT_PROTOCOL,turnId:'turn-test-0001',
    kind:'need_input',question:'Which machine?',key:'machine',
    options:['Phone Termux','THECAULDRON Windows','Home Center cloud']};
 const res=await runSlice({context,policy,journal:log(),
    agent:{async next(){return ask}},executor:{async runValidated(){throw Error('never')}}});
 assert.equal(res.phase,'needs_owner_input');
 assert.deepEqual(res.options,ask.options);
 assert.throws(()=>parseAgentAction({...ask,options:[]},context),/input_options/);
 assert.throws(()=>parseAgentAction({...complete,finalText:''},context),/invalid_completion/);
});
