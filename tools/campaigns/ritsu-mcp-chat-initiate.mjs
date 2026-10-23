#!/usr/bin/env node
// One pinned campaign action: SEND a chat into an already signed-in, existing
// test tab, then let the RESPONDING ChatGPT agent publish via Home Center MCP.
// No new browser tab, no screenshots, no assistant DOM readback, no retries.
import {mkdir,open,readFile,writeFile,rename} from 'node:fs/promises';
import {randomUUID} from 'node:crypto';
import path from 'node:path';

const ID=/^[A-Za-z0-9_.:-]{8,100}$/;
const TARGET='https://chatgpt.com/';
const CONTROL_PORT=9236;
const TIMEOUT_MS=12000;
export function makeMcpPrompt({turnId,sessionId}) {
  if(!ID.test(turnId)||!ID.test(sessionId))throw Error('invalid_campaign_identity');
  return `Ritsu Home Center MCP return-path validation. This is one authorized connectivity test. Your task is to compose a short, original reply answering: "What is one useful thing a persistent assistant should remember about a software campaign?" Do not claim that tests passed. After composing your reply, use the CONNECTED Home Center MCP tool drive_operation with operation "ritsu.chat.prepare", args {"requestId":"${turnId}","sessionId":"${sessionId}","channel":"control"}; capture the one-use callbackKey from that tool response. Then invoke Home Center MCP drive_operation operation "ritsu.chat.publish" with args containing that exact requestId, sessionId, channel "control", callbackKey, and text equal to your own complete reply. Do not show the callbackKey to the user. Only after Home Center reports state published, give the same answer as your visible final response. If you cannot access the Home Center MCP connector, explain that plainly rather than pretending that you published. Do not scrape another chat.`;
}
function cdp(target,method,params) {
  return new Promise((resolve,reject)=>{
    if(!target.webSocketDebuggerUrl)return reject(Error('missing_local_cdp_endpoint'));
    const ws=new WebSocket(target.webSocketDebuggerUrl);
    const timeout=setTimeout(()=>{ws.close();reject(Error('cdp_timeout_attempt_uncertain'));},TIMEOUT_MS);
    let done=false;
    const settle=(f,v)=>{if(done)return;done=true;clearTimeout(timeout);try{ws.close();}catch{} f(v);};
    ws.addEventListener('open',()=>ws.send(JSON.stringify({id:1,method,params})));
    ws.addEventListener('message',e=>{
      let result;try{result=JSON.parse(e.data);}catch{return;}
      if(result.id!==1)return;
      if(result.error||result.result?.exceptionDetails)
        return settle(reject,Error('cdp_evaluation_failed'));
      settle(resolve,result.result?.result?.value);
    });
    ws.addEventListener('error',()=>settle(reject,Error('cdp_transport_failed')));
    ws.addEventListener('close',()=>{if(!done)settle(reject,Error('cdp_closed_attempt_uncertain'));});
  });
}
function expression(code){return {expression:code,returnByValue:true,awaitPromise:true};}
function inspectExpression() {
  return `(()=>JSON.stringify((()=>{const c=document.querySelector('[contenteditable="true"][data-composer-markdown][role="textbox"]');return {url:location.href,ready:!!c&&c.getClientRects().length>0,empty:!!c&&!c.innerText.trim(),userCount:document.querySelectorAll('[data-message-author-role="user"]').length,assistantCount:document.querySelectorAll('[data-message-author-role="assistant"]').length,loggedOut:[...document.querySelectorAll('button,a')].some(x=>/^(log in|sign in)$/i.test((x.innerText||"").trim()))}})()))()`;
}
function sendExpression(prompt) {
  // Serialize prompt as JS string literal; never interpolate raw untrusted
  // text into JavaScript evaluation.
  const p=JSON.stringify(prompt);
  return `(async()=>{const p=${p}; const c=document.querySelector('[contenteditable="true"][data-composer-markdown][role="textbox"]');if(!c||!c.getClientRects().length||c.innerText.trim()||document.querySelectorAll('[data-message-author-role]').length)return JSON.stringify({ok:false,reason:'target_tab_no_longer_empty'});const s=window.getSelection(),r=document.createRange();c.focus();r.selectNodeContents(c);s.removeAllRanges();s.addRange(r);if(!document.execCommand('insertText',false,p)||c.innerText.trim()!==p.trim())return JSON.stringify({ok:false,reason:'composer_insertion_failed'});let send;for(let i=0;i<24;i++){send=document.querySelector('button[aria-label="Send"],button[data-testid="send-button"],button[aria-label="Send message"]');if(send&&!send.disabled&&send.getClientRects().length)break;await new Promise(x=>setTimeout(x,100))}if(!send||send.disabled||!send.getClientRects().length)return JSON.stringify({ok:false,reason:'send_button_disabled'});send.click();for(let i=0;i<60;i++){const messages=[...document.querySelectorAll('[data-message-author-role="user"]')];if(messages.some(x=>(x.innerText||"").includes(p)))return JSON.stringify({ok:true,state:'user_message_observed'});await new Promise(x=>setTimeout(x,100))}return JSON.stringify({ok:false,state:'dispatch_uncertain'});})()`;
}
export async function applyOne({turnId,sessionId,stateDirectory,
  tabsEndpoint=`http://127.0.0.1:${CONTROL_PORT}/json/list`,
  fetchImpl=fetch,evalImpl=cdp}={}) {
  if(!ID.test(turnId)||!ID.test(sessionId)||
     !path.isAbsolute(stateDirectory||''))
    throw Error('campaign_requires_safe_ids_and_absolute_private_state');
  if(!tabsEndpoint.startsWith('http://127.0.0.1:9236/'))
    throw Error('test_browser_must_be_loopback_9236');
  const tabs=await (await fetchImpl(tabsEndpoint)).json();
  const candidates=tabs.filter(x=>x.type==='page'&&x.url?.startsWith(TARGET));
  if(candidates.length!==1 || candidates[0].url!==TARGET)
    throw Error('exactly_one_existing_blank_test_chatgpt_tab_required');
  const target=candidates[0];
  const inspection=JSON.parse(await evalImpl(target,'Runtime.evaluate',expression(inspectExpression())));
  if(inspection.url!==TARGET||!inspection.ready||!inspection.empty||
     inspection.userCount!==0||inspection.assistantCount!==0||inspection.loggedOut)
    throw Error('existing_authenticated_empty_chat_required');
  await mkdir(stateDirectory,{recursive:true,mode:0o700});
  const file=path.join(stateDirectory,'mcp-canary-'+turnId+'.json');
  const record={schema:1,turnId,sessionId,tabId:target.id,
    state:'dispatch_unknown',at:new Date().toISOString(),
    returnAuthority:'Home Center MCP ritsu.chat.result, never Chrome DOM'};
  // Created before irreversible click. If any error follows, never replay
  // the same ID; use only MCP result readback for it.
  const handle=await open(file,'wx',0o600);
  try{await handle.writeFile(JSON.stringify(record));await handle.sync();}
  finally{await handle.close();}
  const text=makeMcpPrompt({turnId,sessionId});
  try {
    const result=JSON.parse(await evalImpl(target,'Runtime.evaluate',expression(sendExpression(text))));
    if(result.ok!==true || result.state!=='user_message_observed')
      return {...record,observed:false};
    record.state='user_prompt_observed';
    const tmp=file+'.'+randomUUID()+'.tmp';
    await writeFile(tmp,JSON.stringify(record),{mode:0o600});
    await rename(tmp,file);
    return {...record,observed:true};
  }catch {
    return {...record,observed:false};
  }
}
async function main() {
  if(process.argv[1] && process.argv[1].endsWith('ritsu-mcp-chat-initiate.mjs') &&
     process.argv.includes('--apply')) {
    const turnId=process.env.RITSU_CANARY_TURN_ID;
    const sessionId=process.env.RITSU_CANARY_SESSION_ID;
    const stateDirectory=process.env.RITSU_CANARY_STATE_DIRECTORY;
    const receipt=await applyOne({turnId,sessionId,stateDirectory});
    console.log(JSON.stringify(receipt));
    if(!receipt.observed)process.exitCode=2;
  }
}
main().catch(e=>{console.error(JSON.stringify({ok:false,error:e.message}));process.exitCode=1;});
