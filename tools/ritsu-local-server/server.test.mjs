import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {createServer} from './server.mjs';
const sha=s=>createHash('sha256').update(s).digest('hex');
const token='a'.repeat(64);
const id='b7f2ddc2-629d-4a26-9d10-2d29ee381938';
test('one accepted turn streams partial and final to local SSE; replay and auth are safe',async()=>{
 const root=await fs.mkdtemp(path.join(os.tmpdir(),'ritsu-local-test-'));let calls=0;
 const runner=async(job,emit)=>{
   calls++;assert.equal(job.tabId,'main');assert.equal(job.turnId,id);
   await emit({version:1,text:'Beginning',sha256:sha('Beginning'),verified:false,complete:false});
   await emit({version:2,text:'Beginning and ending.',sha256:sha('Beginning and ending.'),
    verified:true,complete:true,source:'playwright-rendered-chatgpt-reply',
    url:'https://chatgpt.com/c/1234-abcd'});
 };
 const a=await createServer({root,host:'127.0.0.1',port:0,test:true,token,runner});
 const base='http://127.0.0.1:'+a.port;
 const headers={Authorization:'Bearer '+token};
 try{
  assert.equal((await fetch(base+'/v1/ritsu/status')).status,401);
  const status=await (await fetch(base+'/v1/ritsu/status',{headers})).json();
  assert.equal(status.transport,'tailscale-sse');assert.equal(status.cloudOps,0);
  const data=JSON.stringify({turnId:id,tabId:'main',text:'Hello Ritsu'});
  const first=await fetch(base+'/v1/ritsu/turn',{method:'POST',headers:{...headers,'Content-Type':'application/json'},body:data});
  assert.equal(first.status,202);
  const repeat=await fetch(base+'/v1/ritsu/turn',{method:'POST',headers:{...headers,'Content-Type':'application/json'},body:data});
  assert.equal(repeat.status,200);assert.equal((await repeat.json()).idempotent,true);
  const conflict=await fetch(base+'/v1/ritsu/turn',{method:'POST',headers:{...headers,'Content-Type':'application/json'},body:JSON.stringify({turnId:id,tabId:'main',text:'Different'})});
  assert.equal(conflict.status,409);
  for(let i=0;i<25&&a.seq()<3;i++)await new Promise(r=>setTimeout(r,20));
  assert.equal(a.seq(),3);assert.equal(calls,1);
  const conn=await fetch(base+'/v1/ritsu/events?after=0',{headers});
  assert.equal(conn.status,200);
  const reader=conn.body.getReader();const firstRead=await reader.read();
  const raw=Buffer.from(firstRead.value).toString();
  const events=raw.split('\n').filter(x=>x.startsWith('data: ')).map(x=>JSON.parse(x.slice(6)));
  assert.equal(events.length,3);assert.deepEqual(events.map(x=>x.type),['accepted','partial','complete']);
  assert.equal(events[2].text,'Beginning and ending.');assert.equal(events[2].verified,true);
  await reader.cancel();
 }finally{await a.close();await fs.rm(root,{recursive:true,force:true});}
});
