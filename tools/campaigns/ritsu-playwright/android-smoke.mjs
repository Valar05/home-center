#!/usr/bin/env node
// Bounded Home Center Ritsu Control HTTP -> REAL Playwright -> HTTP test.
// Uses loopback and randomly generated private bearer. Does NOT touch the
// active phone gateway, phone pairing, audio sender, or Android APK.
import {randomBytes,randomUUID,createHash} from 'node:crypto';
import {open,mkdir,writeFile,rename} from 'node:fs/promises';
import {execFileSync} from 'node:child_process';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {createRitsuPlaywrightTransport} from './android-transport.mjs';
import {createFileCoordinatorStore} from '../../../browser-porch/ritsu-coordinator-file-store.mjs';
import {createRitsuHomeCenterCoordinator} from '../../../browser-porch/ritsu-home-center-coordinator.mjs';
import {createRitsuAndroidGateway} from '../../../browser-porch/ritsu-android-gateway.mjs';

const args=Object.fromEntries(process.argv.slice(2).reduce((out,x,i,a)=>{
  if(i%2===0){if(!x.startsWith('--')||!a[i+1])throw Error('named_pair_required');out.push([x.slice(2),a[i+1]])}
  return out
},[]));
const repo=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../../..');
const local=process.env.LOCALAPPDATA||path.join(repo,'.private');
const base=path.join(local,'HomeCenter','RitsuPlaywrightAndroidSmoke');
const name='ritsu-android-test-'+randomUUID().replaceAll('-','').slice(0,16);
const folder=path.join(base,name);
const sha=text=>createHash('sha256').update(text,'utf8').digest('hex');
let gate;
async function atomic(file,data){
  const p=file+'.'+randomUUID()+'.tmp';await writeFile(p,JSON.stringify(data));
  await rename(p,file);
}
async function main(){
  const pin=execFileSync('git',['rev-parse','HEAD'],{cwd:repo,encoding:'utf8'}).trim();
  if(!/^[a-f0-9]{40}$/.test(args.revision)||pin!==args.revision||
    execFileSync('git',['status','--porcelain'],{cwd:repo,encoding:'utf8'}).trim())
    throw Error('pinned_clean_revision_required');
  if(!/^[A-Fa-f0-9]{32}$/.test(args.tabId||'')||
    !/^https:\/\/chatgpt\.com\/c\/[a-f0-9-]{36}$/.test(args.boundUrl||''))
    throw Error('explicit_single_chat_binding_required');
  await mkdir(folder,{recursive:true,mode:0o700});
  const clientBearer=randomBytes(32).toString('base64url');
  const transport=createRitsuPlaywrightTransport({
    directory:path.join(folder,'transport'),tabId:args.tabId,boundUrl:args.boundUrl
  });
  const coordinator=createRitsuHomeCenterCoordinator({
    namespace:'android-smoke-'+randomUUID().replaceAll('-','').slice(0,16),
    controlSessionId:'android-control-smoke-01',
    dialogueSessionId:'android-dialogue-smoke-01',
    transport,store:createFileCoordinatorStore({directory:path.join(folder,'coordinator')})
  });
  gate=createRitsuAndroidGateway({host:'127.0.0.1',port:0,
    clientBearer,coordinator,allowLoopbackForTests:true});
  const address=await gate.start();
  const url='http://127.0.0.1:'+address.port+'/v1/ritsu';
  const headers={authorization:'Bearer '+clientBearer,'content-type':'application/json'};
  const turnId='phone-smoke-'+randomUUID().replaceAll('-','').slice(0,16);
  const prompt='Write exactly one sentence explaining that this reply traveled through Ritsu Control, Home Center, and Playwright. Include a crab emoji.';
  const post=await fetch(url+'/turn',{method:'POST',headers,
    body:JSON.stringify({turnId,channel:'control',prompt})});
  if(post.status!==202)throw Error('phone_http_submit_not_accepted');
  const ack=await post.json();
  if(ack.receipt?.state!=='queued')throw Error('phone_submit_ack_unexpected');
  const deadline=Date.now()+110000;let last=null;
  while(Date.now()<deadline){
    await new Promise(r=>setTimeout(r,850));
    const r=await fetch(url+'/turn?turnId='+turnId,{headers});
    if(!r.ok)throw Error('phone_http_read_failed');
    last=(await r.json()).receipt;
    if(last?.state==='completed')break;
    if(['failed','unknown'].includes(last?.state))break;
  }
  if(last?.state!=='completed')throw Error('phone_visible_reply_not_completed_'+(last?.state||'timeout'));
  const reply=last?.result?.text;
  if(typeof reply!=='string'||!reply.trim())throw Error('gateway_completed_without_text');
  const feed=await (await fetch(url+'/feed?after=0',{headers})).json();
  if(!Array.isArray(feed.events)||feed.events.length!==1||
     feed.events[0].text!==reply)throw Error('android_feed_text_not_exact');
  const state={schema:1,state:'verified_phone_contract_not_physical_phone',
    jobId:name,revision:pin,conversationUrl:args.boundUrl,tabId:args.tabId,
    transport:'RitsuControl_HTTP__HomeCenter__Playwright__HTTP',
    text:reply,sha256:sha(reply),events:feed.events.length,at:new Date().toISOString()};
  await atomic(path.join(folder,'receipt.json'),state);
  await atomic(path.join(base,'latest.json'),state);
  process.stdout.write(JSON.stringify({state:state.state,receipt:path.join(folder,'receipt.json'),
    sha256:state.sha256,bytes:Buffer.byteLength(reply,'utf8'),events:state.events})+'\n');
}
main().catch(async e=>{
  await mkdir(base,{recursive:true}).catch(()=>{});
  await atomic(path.join(base,'latest.json'),{state:'blocked',jobId:name,
    reason:String(e.message).slice(0,140),at:new Date().toISOString()}).catch(()=>{});
  process.stderr.write(JSON.stringify({state:'blocked',reason:String(e.message).slice(0,140)})+'\n');
  process.exitCode=1;
}).finally(async()=>{if(gate)await gate.close().catch(()=>{})});
