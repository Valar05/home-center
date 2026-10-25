import {createHash} from 'node:crypto';

export const SCRIPT_PROTOCOL='ritsu.script-loop.v1';
export const MACHINES=Object.freeze({
  'termux-android':Object.freeze({label:'Android · Termux',platform:'android',shell:'bash'}),
  'windows-cauldron':Object.freeze({label:'Windows · THECAULDRON',platform:'win32',shell:'powershell'}),
  'windows-generic':Object.freeze({label:'Other Windows machine',platform:'win32',shell:'powershell'}),
  'home-center-cloud':Object.freeze({label:'Home Center cloud',platform:'cloud',shell:'none'}),
  'local-sandbox':Object.freeze({label:'Local test sandbox',platform:'test',shell:'node'}),
});
export const sha256=x=>createHash('sha256').update(x,'utf8').digest('hex');
const ID=/^[A-Za-z0-9_.:-]{8,100}$/;
const tabs=/^[A-Za-z0-9_-]{4,80}$/;
const digest=/^[a-f0-9]{64}$/;
const allowedKinds=new Set(['run_script','complete','need_input','request_asset']);
const allowedLanguage=new Set(['bash','node','powershell']);
const allowedAssets=new Set(['image','file']);
const str=(x,max)=>typeof x==='string'&&x.length<=max?x:null;

export function parseAgentAction(raw,ctx) {
  if(!raw||typeof raw!=='object'||Array.isArray(raw))throw Error('invalid_action');
  const {protocol,kind,campaignId,turnId,tabId,machineId}=raw;
  if(protocol!==SCRIPT_PROTOCOL||!allowedKinds.has(kind)||!ID.test(campaignId||'')||
     !ID.test(turnId||'')||!tabs.test(tabId||'')||!Object.hasOwn(MACHINES,machineId))
    throw Error('invalid_envelope');
  if(ctx && (campaignId!==ctx.campaignId || tabId!==ctx.tabId ||
              machineId!==ctx.machineId))
    throw Error('campaign_machine_or_tab_mismatch');
  const base={protocol,kind,campaignId,turnId,tabId,machineId};
  if(kind==='complete') {
    // Only an explicit, nonempty COMPLETE from the agent terminates a campaign.
    const finalText=str(raw.finalText,10000);
    if(!finalText||!finalText.trim()||raw.script||raw.asset)throw Error('invalid_completion');
    return {...base,finalText};
  }
  if(kind==='need_input') {
    const question=str(raw.question,1000),key=str(raw.key,60);
    if(!question?.trim()||!key||!/^[A-Za-z0-9_-]+$/.test(key))
      throw Error('invalid_input_request');
    const options=raw.options;
    if(!Array.isArray(options)||options.length<2||options.length>20||
       options.some(x=>typeof x!=='string'||x.length>100||!x.trim())||
       new Set(options).size!==options.length)
      throw Error('invalid_input_options');
    return {...base,question,key,options:[...options]};
  }
  if(kind==='request_asset') {
    if(!allowedAssets.has(raw.assetType)||!raw.requestedByUser)
      throw Error('asset_must_be_explicitly_requested');
    const query=str(raw.query,1000);
    if(!query?.trim())throw Error('invalid_asset_query');
    return {...base,assetType:raw.assetType,query,requestedByUser:true};
  }
  if(!ID.test(raw.scriptId||'')||!allowedLanguage.has(raw.language)||
     !str(raw.script,32768)?.trim()||!digest.test(raw.sha256||'')||
     sha256(raw.script)!==raw.sha256)
    throw Error('invalid_script_or_hash');
  if(raw.mode!=='inspect'&&raw.mode!=='workspace-write')
    throw Error('invalid_script_mode');
  if(!str(raw.relativeCwd,240)||raw.relativeCwd.startsWith('/')||
     raw.relativeCwd.split(/[\\/]+/).some(x=>x==='..'||x==='')||
     /^[A-Za-z]:/.test(raw.relativeCwd))
    throw Error('unsafe_relative_directory');
  const timeoutSeconds=Number(raw.timeoutSeconds||45);
  if(!Number.isInteger(timeoutSeconds)||timeoutSeconds<1||timeoutSeconds>300)
    throw Error('script_timeout_not_allowed');
  return {...base,scriptId:raw.scriptId,language:raw.language,
    script:raw.script,sha256:raw.sha256,mode:raw.mode,
    relativeCwd:raw.relativeCwd,timeoutSeconds};
}

export function executionDecision(action,policy) {
  if(action.kind!=='run_script')return {execute:false,reason:'not_a_script'};
  if(!policy||policy.machineId!==action.machineId||
     policy.tabId!==action.tabId||policy.ownerApproved!==true)
    return {execute:false,reason:'owner_machine_binding_required'};
  if(action.language!==policy.language)
    return {execute:false,reason:'wrong_machine_interpreter'};
  if(action.mode==='workspace-write'&&!policy.allowWorkspaceWrites)
    return {execute:false,reason:'workspace_write_not_approved'};
  // Syntax checking is necessary but not an OS sandbox. The actual executor
  // must run under an owner-approved filesystem/identity boundary, never a
  // privileged default account. Block escalation rather than "linting" it.
  if(policy.executionIsolationVerified!==true)
    return {execute:false,reason:'executor_isolation_not_verified'};
  return {execute:true,reason:'owner_approved_bound_machine'};
}

export function receiptForAgent(action,outcome) {
  if(action.kind!=='run_script')throw Error('script_required');
  if(!outcome||typeof outcome!=='object')throw Error('receipt_required');
  return Object.freeze({protocol:SCRIPT_PROTOCOL,kind:'script_receipt',
    campaignId:action.campaignId,tabId:action.tabId,machineId:action.machineId,
    scriptId:action.scriptId,sha256:action.sha256,
    status:String(outcome.status||'unknown'),
    exitCode:Number.isInteger(outcome.exitCode)?outcome.exitCode:null,
    output:String(outcome.output||'').slice(-16000),
    outputTruncated:Boolean(outcome.outputTruncated),
    verified:Boolean(outcome.verified),
    timestamp:new Date().toISOString()});
}
