#!/usr/bin/env node
// Network-only answer capture canary. Owns one existing, blank Chromium Throne tab.
// Reuses the current Git campaign controls; never reads assistant DOM or intercepts Fetch.
import {readFile,writeFile,appendFile,mkdir,open,rename} from 'node:fs/promises';
import {existsSync} from 'node:fs';
import {execFileSync,spawn} from 'node:child_process';
import {randomUUID,createHash} from 'node:crypto';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {RitsuNetworkSse} from '../../browser-porch/ritsu-network-sse.mjs';

const script=fileURLToPath(import.meta.url);
const root=path.resolve(path.dirname(script),'../..');
const state=path.join(process.env.LOCALAPPDATA||path.join(root,'.ritsu-private'),
  'HomeCenter','RitsuNetworkProbe');
const target='https://chatgpt.com/';
const endpoint=/^https:\/\/chatgpt\.com\/backend-api\/(?:f\/)?conversation(?:[/?#]|$)/;
const wait=ms=>new Promise(r=>setTimeout(r,ms));
const hash=text=>createHash('sha256').update(text).digest('hex');
const args=Object.fromEntries(process.argv.slice(2).reduce((a,v,i,x)=>{
  if(i%2===0){if(!v.startsWith('--')||!x[i+1])throw Error('named_args_required');
    a.push([v.slice(2),x[i+1]])}return a;
},[]));
const mode=args.mode||'Plan';

async function atomic(filename,obj){
  await mkdir(path.dirname(filename),{recursive:true});
  const tmp=filename+'.'+randomUUID()+'.tmp';
  await writeFile(tmp,JSON.stringify(obj),{mode:0o600});
  await rename(tmp,filename);
}
async function receipt(obj){
  const row={schema:1,...obj,at:new Date().toISOString()};
  await mkdir(state,{recursive:true});
  await appendFile(path.join(state,'history.jsonl'),JSON.stringify(row)+'\n');
  await atomic(path.join(state,'latest.json'),row);
  return row;
}
async function read(name){
  try{return JSON.parse(await readFile(path.join(state,name),'utf8'))}
  catch(e){if(e.code==='ENOENT')return null;throw e}
}
function checkPin(){
  if(!/^[a-f0-9]{40}$/.test(args.revision||''))throw Error('full_git_sha_required');
  const got=execFileSync('git',['rev-parse','HEAD'],{cwd:root,encoding:'utf8'}).trim();
  if(got!==args.revision)throw Error('git_revision_mismatch');
  if(execFileSync('git',['status','--porcelain'],{cwd:root,encoding:'utf8'}).trim())
    throw Error('dirty_checkout');
}
function existingBound(){
  if(args.allowExisting!=='true')return false;
  return /^[A-Fa-f0-9]{32}$/.test(args.tabId||'') &&
    /^https:\/\/chatgpt\.com\/c\/[0-9a-f-]{36}$/.test(args.boundUrl||'');
}
async function oneTab(){
  if(args.allowExisting==='true'&&!existingBound())
    throw Error('existing_test_conversation_requires_exact_url_and_tab_id');
  const response=await fetch('http://127.0.0.1:9236/json/list',
    {signal:AbortSignal.timeout(5000)});
  if(!response.ok)throw Error('isolated_browser_endpoint_offline');
  const all=await response.json();
  const chosenUrl=existingBound()?args.boundUrl:target;
  const tabs=all.filter(t=>t.type==='page'&&t.url===chosenUrl&&
    (!args.tabId||args.tabId==='*'||t.id===args.tabId));
  if(tabs.length!==1)throw Error('one_exact_bound_test_chatgpt_tab_required');
  const tab=tabs[0];
  if(!/^ws:\/\/(?:127\.0\.0\.1|localhost):9236\/devtools\/page\/[a-zA-Z0-9-]+$/
    .test(tab.webSocketDebuggerUrl||''))throw Error('unauthorized_cdp_target');
  return tab;
}
function connection(url){
  const ws=new WebSocket(url);
  const callbacks=new Map(),events=[];
  let serial=0;
  ws.addEventListener('message',e=>{
    let msg;try{msg=JSON.parse(e.data)}catch{return}
    if(msg.id){const p=callbacks.get(msg.id);if(!p)return;
      callbacks.delete(msg.id);clearTimeout(p.timeout);
      if(msg.error)p.reject(Error('cdp_method_denied_'+p.method));
      else p.resolve(msg.result||{});
    }else if(msg.method)for(const fn of events){try{fn(msg.method,msg.params||{})}
      catch(err){fn.failed=err}}
  });
  return {
    ws,on:fn=>events.push(fn),
    async ready(){await new Promise((resolve,reject)=>{
      const timeout=setTimeout(()=>reject(Error('cdp_connect_timeout')),8000);
      ws.addEventListener('open',()=>{clearTimeout(timeout);resolve()},{once:true});
      ws.addEventListener('error',()=>{clearTimeout(timeout);reject(Error('cdp_socket_error'))},{once:true});
    })},
    call(method,params={}){
      return new Promise((resolve,reject)=>{
        const id=++serial;
        const timeout=setTimeout(()=>{callbacks.delete(id);reject(Error('cdp_timeout_'+method))},12000);
        callbacks.set(id,{method,timeout,resolve,reject});
        ws.send(JSON.stringify({id,method,params}));
      });
    },
    close(){ws.close()}
  };
}
function before(){
  return '(()=>{const c=document.querySelector(\'[contenteditable="true"][data-composer-markdown][role="textbox"]\');return JSON.stringify({url:location.href,ready:!!c&&c.getClientRects().length>0,empty:!!c&&!c.innerText.trim(),count:document.querySelectorAll(\'[data-message-author-role]\').length})})()';
}
function send(prompt,allowExisting){
  return '(async()=>{const p='+JSON.stringify(prompt)+
  ';const c=document.querySelector(\'[contenteditable="true"][data-composer-markdown][role="textbox"]\');'+
  'if(!c||c.innerText.trim()||(!'+(allowExisting?'true':'false')+'&&document.querySelectorAll(\'[data-message-author-role]\').length))return false;'+
  'c.focus();const s=window.getSelection(),r=document.createRange();r.selectNodeContents(c);s.removeAllRanges();s.addRange(r);'+
  'if(!document.execCommand("insertText",false,p))return false;'+
  'let b;for(let i=0;i<20;i++){b=document.querySelector(\'button[aria-label="Send"],button[data-testid="send-button"]\');'+
  'if(b&&!b.disabled&&b.getClientRects().length)break;await new Promise(ok=>setTimeout(ok,100))}'+
  'if(!b||b.disabled)return false;b.click();return true})()';
}
async function probe(){
  const tab=await oneTab(),cdp=connection(tab.webSocketDebuggerUrl);
  const marker='RITSU_NET_'+randomUUID().replace(/-/g,'').slice(0,20).toUpperCase();
  const prompt='Reply with one plain sentence including this marker exactly: '+marker+
    '. This is a network response retrieval canary. Do not use tools.';
  const sse=new RitsuNetworkSse();
  let req=null,done=false,armed=false,streamed=false,failure=null;
  let pending=[],bytes=0,seen=false;
  function feed(b){try{sse.push(b);bytes+=b.length}catch(e){failure=e.message}}
  try{
    await cdp.ready();
    cdp.on((method,p)=>{
      if(method==='Network.requestWillBeSent'&&p.request?.method==='POST'&&
        endpoint.test(p.request.url)){
        if(req&&req!==p.requestId)failure='multiple_conversation_requests';
        else {req=p.requestId;seen=true}
      }
      if(method==='Network.responseReceived'&&req===p.requestId){
        cdp.call('Network.streamResourceContent',{requestId:req}).then(r=>{
          streamed=true;feed(Buffer.from(r.bufferedData||'','base64'));armed=true;
          for(const b of pending)feed(b);pending=[];
        }).catch(()=>{failure='cdp_stream_api_unavailable'});
      }
      if(method==='Network.dataReceived'&&req===p.requestId&&p.data){
        const b=Buffer.from(p.data,'base64');
        if(armed)feed(b);else pending.push(b);
      }
      if(method==='Network.loadingFinished'&&req===p.requestId)done=true;
      if(method==='Network.loadingFailed'&&req===p.requestId)failure='response_network_failed';
    });
    await cdp.call('Network.enable');
    const inspected=await cdp.call('Runtime.evaluate',{expression:before(),returnByValue:true});
    const p=JSON.parse(inspected.result?.value||'{}');
    if(p.url!==(existingBound()?args.boundUrl:target)||!p.ready||!p.empty||
      (!existingBound()&&p.count!==0))
      throw Error('bound_authenticated_test_tab_preflight_failed');
    await receipt({state:'observer_attached',revision:args.revision,tabId:tab.id});
    const sent=await cdp.call('Runtime.evaluate',
      {expression:send(prompt,existingBound()),returnByValue:true,awaitPromise:true});
    if(sent.result?.value!==true||sent.exceptionDetails)throw Error('send_not_verified');
    await receipt({state:'canary_sent_unverified',revision:args.revision,tabId:tab.id});
    const deadline=Date.now()+90000;
    while(Date.now()<deadline){
      if(existsSync(path.join(state,'stop.json')))throw Error('owner_stopped');
      if(failure)throw Error(failure);
      if(done&&streamed&&armed){
        const found=sse.result({marker,requestFinished:true});
        return {state:'retrieved',revision:args.revision,jobId:args.jobId,
          source:'authorized_cdp_network_stream',tabId:tab.id,
          text:found.text,sha256:hash(found.text),messageId:found.messageId,
          events:found.eventCount,bytes,terminal:true};
      }
      await wait(200);
    }
    throw Error(!seen?'no_conversation_network_request':
      !streamed?'streaming_api_not_confirmed':'response_not_complete');
  }finally{cdp.close()}
}
async function main(){
  if(!['Plan','Apply','Worker','Status','Receipts','Stop'].includes(mode))
    throw Error('invalid_campaign_mode');
  if(mode==='Plan'){
    console.log(JSON.stringify({state:'plan',entrypoint:'ritsu-network-probe-campaign.mjs',
      modes:['Plan','Apply','Status','Receipts','Stop'],target:'existing_blank_9236_tab',
      network:'CDP Network.streamResourceContent only',authority:'exact_pinned_git_sha',
      evidence:'actual assistant text+sha from terminal network stream, no DOM reply'}));return;
  }
  if(mode==='Status'){console.log(JSON.stringify(await read('latest.json')));return}
  if(mode==='Receipts'){
    try{console.log((await readFile(path.join(state,'history.jsonl'),'utf8')).split('\n').slice(-25).join('\n'))}
    catch(e){if(e.code==='ENOENT')console.log('NO_RECEIPTS');else throw e}return;
  }
  if(mode==='Stop'){
    await atomic(path.join(state,'stop.json'),{ownerStopped:true});
    console.log(JSON.stringify(await receipt({state:'stop_requested'})));return;
  }
  checkPin();
  if(mode==='Apply'){
    if(!/^[A-Za-z0-9_.:-]{8,100}$/.test(args.jobId||''))throw Error('job_id_required');
    if(existsSync(path.join(state,'stop.json')))throw Error('previously_stopped_requires_new_campaign');
    await mkdir(state,{recursive:true});
    const oldLock=await read('lock.json'),previous=await read('latest.json');
    const lock={revision:args.revision,jobId:args.jobId,
      tabId:args.tabId||'*',boundUrl:args.boundUrl||target,allowExisting:args.allowExisting||'false'};
    if(oldLock){
      if(previous?.state!=='blocked'||oldLock.jobId===args.jobId)
        throw Error('prior_campaign_not_terminal_or_job_reused');
      await atomic(path.join(state,'lock.json'),lock);
    }else{
      const fd=await open(path.join(state,'lock.json'),'wx',0o600);
      await fd.writeFile(JSON.stringify(lock));await fd.close();
    }
    await receipt({state:'queued',revision:args.revision,jobId:args.jobId});
    const child=spawn(process.execPath,[script,'--mode','Worker','--revision',
      args.revision,'--jobId',args.jobId,'--tabId',args.tabId||'*',
      '--boundUrl',args.boundUrl||target,'--allowExisting',args.allowExisting||'false'],
      {cwd:root,detached:true,windowsHide:true,stdio:'ignore'});
    child.unref();
    console.log(JSON.stringify({state:'queued',pid:child.pid,revision:args.revision}));return;
  }
  try{
    const lock=await read('lock.json');
    if(lock?.revision!==args.revision||lock?.jobId!==args.jobId||
      lock?.tabId!==(args.tabId||'*')||lock?.boundUrl!==(args.boundUrl||target)||
      lock?.allowExisting!==(args.allowExisting||'false'))
      throw Error('worker_must_match_persisted_job');
    if(existsSync(path.join(state,'stop.json')))throw Error('owner_stopped');
    await receipt({state:'running',revision:args.revision,jobId:args.jobId});
    console.log(JSON.stringify(await receipt(await probe())));
  }catch(e){
    await receipt({state:'blocked',revision:args.revision,jobId:args.jobId,
      reason:String(e.message).slice(0,180)});process.exitCode=1;
  }
}
main().catch(e=>{console.error(JSON.stringify({state:'blocked',reason:String(e.message)}));process.exitCode=1});
