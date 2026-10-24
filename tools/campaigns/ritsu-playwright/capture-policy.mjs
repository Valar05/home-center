import {createHash} from 'node:crypto';

const CHAT_PREFIX='https://chatgpt.com/c/';
const ID=/^[A-Za-z0-9_.:-]{8,120}$/;
const TAB=/^[A-Fa-f0-9]{32}$/;
const SHA=/^[a-f0-9]{40}$/;
const MAX_TEXT=64000;

export function validateConfig({revision,jobId,tabId,boundUrl}){
  if(!SHA.test(revision||''))throw Error('pinned_commit_required');
  if(!ID.test(jobId||''))throw Error('unique_job_id_required');
  if(!TAB.test(tabId||''))throw Error('exact_existing_chrome_target_id_required');
  let url;try{url=new URL(boundUrl)}catch{throw Error('bound_conversation_url_required')}
  if(!url.href.startsWith(CHAT_PREFIX)||url.hostname!=='chatgpt.com'||
    !/^\/c\/[A-Za-z0-9-]{36}$/.test(url.pathname)||url.search||url.hash)
    throw Error('single_bound_chatgpt_conversation_required');
  return {revision,jobId,tabId,boundUrl:url.href};
}

export function canaryPrompt(marker){
  if(!/^RITSU_PW_[A-F0-9]{20}$/.test(marker||''))
    throw Error('random_canary_required');
  return 'Reply with one plain sentence including this marker exactly: '+marker+
    '. This is a Playwright response retrieval canary. Do not use tools.';
}

export function evidence({marker,text,baseline,assistantCount,stableSamples,stopVisible,
                          promptObserved,conversationUrl,boundUrl,jobId,tabId,revision}){
  const checks={revision,jobId,tabId,boundUrl};
  validateConfig(checks);
  if(conversationUrl!==boundUrl)throw Error('conversation_changed');
  if(!promptObserved)throw Error('prompt_not_observed');
  if(!Number.isInteger(baseline)||assistantCount!==baseline+1)
    throw Error('assistant_count_changed_unexpectedly');
  if(stopVisible)throw Error('generation_still_running');
  if(stableSamples<3)throw Error('reply_not_settled');
  if(typeof text!=='string'||!text.trim()||text.length>MAX_TEXT)
    throw Error('invalid_response_length');
  if(!text.includes(marker))throw Error('no_matching_canary_in_assistant_text');
  return Object.freeze({
    schema:1,state:'retrieved',source:'playwright_existing_bound_tab_dom',
    revision,jobId,tabId,boundUrl,baseline,assistantCount,
    text,sha256:createHash('sha256').update(text,'utf8').digest('hex'),
    exactCanaryMatched:true,stableSamples,generationStopped:true
  });
}

export function publicDiagnostic(e){
  return {kind:'playwright_canary',reason:String(e?.message||e).slice(0,160)};
}
