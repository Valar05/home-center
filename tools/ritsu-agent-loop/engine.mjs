import {parseAgentAction,executionDecision,receiptForAgent} from './contract.mjs';

const iso=()=>new Date().toISOString();
/**
 * Exact agent protocol: SCRIPT -> validate/execute -> receipt back to agent ->
 * next SCRIPT ... until the agent explicitly emits COMPLETE.
 *
 * A failed script is returned to the agent, never equated to DONE. Input and
 * requested assets are durable pauses; no image/file fetching is spontaneous.
 * The caller supplies real Home Center transport and isolated executor. This
 * module deliberately does not hallucinate a working ChatGPT connection.
 */
export async function runSlice({
  context,agent,executor,policy,journal,limit=24,signal,
}) {
  if(!context||!agent||typeof agent.next!=='function'||
     !executor||typeof executor.runValidated!=='function'||
     !journal||typeof journal.append!=='function'||
     typeof journal.checkpoint!=='function')
    throw Error('script_campaign_dependencies_missing');
  if(!Number.isInteger(limit)||limit<1||limit>500)
    throw Error('invalid_slice_limit');
  const receipts=journal.receipts||new Map();
  let previous=journal.pendingReceipt||null;
  let sequence=0;
  for(;sequence<limit;sequence++){
    if(signal?.aborted){
      await journal.checkpoint({phase:'stopped',reason:'owner_stop',at:iso()});
      return {phase:'stopped',reason:'owner_stop',sequence};
    }
    const raw=await agent.next({context,previousReceipt:previous,
      sequence,historySize:receipts.size});
    const action=parseAgentAction(raw,context);
    await journal.append({event:'agent_action',kind:action.kind,
      actionId:action.scriptId||null,tabId:action.tabId,
      machineId:action.machineId,at:iso()});
    if(action.kind==='complete'){
      await journal.checkpoint({phase:'completed',at:iso(),
        finalText:action.finalText,by:'agent_explicit_complete'});
      return {phase:'completed',finalText:action.finalText,sequence:sequence+1};
    }
    if(action.kind==='need_input'){
      await journal.checkpoint({phase:'needs_owner_input',at:iso(),
        question:action.question,key:action.key,options:action.options});
      return {phase:'needs_owner_input',question:action.question,
        key:action.key,options:action.options};
    }
    if(action.kind==='request_asset'){
      await journal.checkpoint({phase:'asset_requested',at:iso(),
        assetType:action.assetType,query:action.query,
        requestedByUser:true});
      return {phase:'asset_requested',assetType:action.assetType,query:action.query};
    }
    const decision=executionDecision(action,policy);
    if(!decision.execute){
      await journal.checkpoint({phase:'approval_required',at:iso(),
        machineId:action.machineId,scriptId:action.scriptId,
        sha256:action.sha256,reason:decision.reason});
      return {phase:'approval_required',reason:decision.reason,
        scriptId:action.scriptId};
    }
    // Crash-safe idempotence: the executor may only execute each scriptId
    // after the journal durably owns the intent. Replayed receipts return to
    // the agent without invoking a command for a second time.
    let receipt=receipts.get(action.scriptId);
    if(receipt && receipt.sha256!==action.sha256)
      throw Error('script_id_conflicts_with_prior_hash');
    if(!receipt){
      await journal.append({event:'script_commissioned',at:iso(),
        scriptId:action.scriptId,sha256:action.sha256,
        language:action.language,mode:action.mode});
      let outcome;
      try{outcome=await executor.runValidated(action,{signal});}
      catch(error){outcome={status:'failed',
        output:'Executor failed: '+String(error?.message||'unknown').slice(0,300),
        verified:false};}
      receipt=receiptForAgent(action,outcome);
      await journal.append({event:'script_receipt',at:iso(),
        scriptId:action.scriptId,receipt});
      receipts.set(action.scriptId,receipt);
    }else {
      await journal.append({event:'script_replayed',at:iso(),
        scriptId:action.scriptId});
    }
    previous=receipt;
    await journal.checkpoint({phase:'continue_required',at:iso(),
      lastScriptId:action.scriptId,lastStatus:receipt.status,
      lastReceipt:receipt});
  }
  await journal.checkpoint({phase:'continue_required',at:iso(),
    reason:'bounded_worker_slice',scriptSteps:sequence});
  return {phase:'continue_required',reason:'bounded_worker_slice',
    steps:sequence};
}
