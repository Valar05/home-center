import assert from 'node:assert/strict';
import {mkdtemp,rm} from 'node:fs/promises';
import os from 'node:os';import path from 'node:path';
import {createServer} from './server.mjs';
const root=await mkdtemp(path.join(os.tmpdir(),'ritsu-stop-test-'));
const token='a'.repeat(64);
let release;
let stopCalls=0;
const waiting=new Promise(ok=>{release=ok;});
const s=await createServer({test:true,host:'127.0.0.1',port:0,root,token,
 runner:async(job,emit)=>{
   const text='partial answer arrived early';
   await emit({turnId:job.turnId,tabId:job.tabId,version:1,text,
     sha256:await sha(text),complete:false,verified:false});
   await waiting;
   const value='late completion must be suppressed';
   await emit({turnId:job.turnId,tabId:job.tabId,version:2,text:value,
     sha256:await sha(value),complete:true,verified:true,
     source:'playwright-rendered-chatgpt-reply',url:'https://chatgpt.com/c/test-conversation'});
 },stopRunner:async()=>{stopCalls++;return {verified:true}}});
const base='http://127.0.0.1:'+s.port;
function sha(s){return import('node:crypto').then(c=>c.createHash('sha256').update(s).digest('hex'));}
const headers={Authorization:'Bearer '+token,'Content-Type':'application/json'};
async function post(url,value){const r=await fetch(base+url,{method:'POST',headers,body:JSON.stringify(value)});return [r.status,await r.json()];}
const turnId='11111111-1111-4111-8111-111111111111',tabId='main_tab';
try{
 const initial=await post('/v1/ritsu/turn',{turnId,tabId,text:'Hello'});assert.equal(initial[0],202);
 await new Promise(r=>setTimeout(r,100));
 const stopped=await post('/v1/ritsu/turn/stop',{turnId,tabId});assert.equal(stopped[0],200);assert.equal(stopped[1].stopped,true);
 const repeated=await post('/v1/ritsu/turn/stop',{turnId,tabId});assert.equal(repeated[0],200);assert.equal(repeated[1].idempotent,true);
 assert.equal(stopCalls,1);release();await new Promise(r=>setTimeout(r,120));
 const q=await fetch(base+'/v1/ritsu/events?after=0',{headers:{Authorization:'Bearer '+token},signal:AbortSignal.timeout(1000)});
 const reader=q.body.getReader();let events='';const decoder=new TextDecoder();
 for(let tries=0;tries<8&&!events.includes('\"type\":\"stopped\"');tries++){
   const chunk=await reader.read();if(chunk.done)break;events+=decoder.decode(chunk.value);
 }
 assert.match(events,/"type":"partial"/);assert.match(events,/"type":"stopped"/);
 assert.doesNotMatch(events,/"type":"complete"/);reader.cancel();
 console.log('RITSU_STOP_TEST=PASS_REMOTE_ACK_IDEMPOTENT_NO_LATE_COMPLETE');
} finally{release();await s.close();await rm(root,{recursive:true,force:true});}
