// Ritsu Local Link. Direct Tailscale SSE, durable turns, no Home Center cloud.
import http from 'node:http';
import fs from 'node:fs/promises';
import {spawn,execFileSync} from 'node:child_process';
import {randomBytes,createHash,timingSafeEqual} from 'node:crypto';
import path from 'node:path';
import os from 'node:os';
import {fileURLToPath} from 'node:url';
const HOME=path.join(os.homedir(),'.ritsu-control','local-link');
const BRIDGE=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../campaigns/ritsu_control_playwright_bridge.mjs');
const hash=s=>createHash('sha256').update(s).digest('hex');
const turnPattern=/^[a-fA-F0-9-]{36}$/,tabPattern=/^[A-Za-z0-9_-]{4,80}$/;
function tailnet(ip){const p=String(ip).split('.');return p.length===4&&p.every(x=>/^[0-9]{1,3}$/.test(x)&&+x<=255)&&p[0]==='100'&&+p[1]>=64&&+p[1]<=127;}
export async function tokenAt(root=HOME){
  await fs.mkdir(root,{recursive:true,mode:0o700});
  const file=path.join(root,'device-token');
  try{const t=(await fs.readFile(file,'utf8')).trim();if(!/^[a-f0-9]{64}$/.test(t))throw Error('invalid_existing_token');return t;}
  catch(e){if(e.code!=='ENOENT')throw e;const t=randomBytes(32).toString('hex');await fs.writeFile(file,t+'\n',{flag:'wx',mode:0o600});return t;}
}
function tailIp(){const exe=process.platform==='win32'?'tailscale.exe':'tailscale';const out=execFileSync(exe,['ip','-4'],{encoding:'utf8',timeout:9000}).trim().split(/\s+/)[0];if(!tailnet(out))throw Error('tailscale_not_connected');return out;}
export async function createServer(opts={}){
  const root=opts.root||HOME,host=opts.host||tailIp();
  if(!tailnet(host)&&!(opts.test&&host==='127.0.0.1'))throw Error('tailnet_only');
  const token=opts.token||await tokenAt(root);await fs.mkdir(root,{recursive:true,mode:0o700});
  const filename=path.join(root,'events.jsonl'),listeners=new Set(),turns=new Map(),history=[];
  let seq=0,writer=Promise.resolve(),busy=false;const jobs=[];
  try{const raw=await fs.readFile(filename,'utf8');for(const line of raw.split('\n')){
    if(!line)continue;const e=JSON.parse(line);if(e.seq!==seq+1)throw Error('journal_sequence_invalid');
    seq=e.seq;history.push(e);if(e.turnId){const r=turns.get(e.turnId)||{tabId:e.tabId,hash:''};
    if(r.tabId!==e.tabId)throw Error('journal_collision');if(e.promptSha256)r.hash=e.promptSha256;r.state=e.type;turns.set(e.turnId,r);}
  }}catch(e){if(e.code!=='ENOENT')throw e;}
  if(history.length>10000)throw Error('journal_exceeds_limit');
  for(const row of turns.values())if(['accepted','partial'].includes(row.state))row.state='uncertain';
  async function append(e){
    const task=writer.then(async()=>{
      const row={seq:seq+1,...e};
      await fs.appendFile(filename,JSON.stringify(row)+'\n',{mode:0o600});
      seq=row.seq;history.push(row);
      if(e.turnId){
        const r=turns.get(e.turnId)||{tabId:e.tabId,hash:''};
        r.state=e.type;if(e.promptSha256)r.hash=e.promptSha256;
        turns.set(e.turnId,r);
      }
      const wire='id: '+row.seq+'\ndata: '+JSON.stringify(row)+'\n\n';
      for(const res of listeners)if(!res.destroyed)res.write(wire);
      return row;
    });
    writer=task.catch(()=>{});
    return task;
  }  async function defaultRunner(job,emit){
    const p=spawn(process.execPath,[BRIDGE,'--turn',job.turnId,'--tab',job.tabId,
      '--prompt-b64',Buffer.from(job.text).toString('base64')],{cwd:opts.cwd||path.dirname(BRIDGE),
      windowsHide:true,stdio:['ignore','pipe','pipe'],env:{...process.env,RITSU_LOCAL_STREAM:'1'}});
    let rest='',stderr='',writes=[],completed=false;
    p.stderr.on('data',b=>{stderr=(stderr+b.toString()).slice(-500);});
    p.stdout.on('data',b=>{rest+=b.toString();let n;while((n=rest.indexOf('\n'))>=0){
      const line=rest.slice(0,n).trim();rest=rest.slice(n+1);
      if(!line.startsWith('RITSU_STREAM_EVENT='))continue;
      try{const ev=JSON.parse(line.slice('RITSU_STREAM_EVENT='.length));
        if(ev.turnId!==job.turnId||ev.tabId!==job.tabId||ev.sha256!==hash(ev.text))continue;
        if(ev.complete)completed=true;
        writes.push(emit(ev));
      }catch{}
    }});
    const code=await new Promise((resolve,reject)=>{p.on('error',reject);p.on('close',resolve);});
    await Promise.all(writes);
    if(code!==0||!completed)throw Error('browser_uncertain_'+code+'_'+stderr);
  }
  async function pump(){if(busy)return;busy=true;try{while(jobs.length){
    const job=jobs.shift();let rev=0,complete=false;
    try{await (opts.runner||defaultRunner)(job,async ev=>{
      if(!Number.isInteger(ev.version)||ev.version<=rev||complete)return;
      if(typeof ev.text!=='string'||ev.text.length>5000||hash(ev.text)!==ev.sha256)return;
      if(ev.complete&&(!ev.verified||ev.source!=='playwright-rendered-chatgpt-reply'||
        !/^https:\/\/chatgpt\.com\/c\/[A-Za-z0-9-]+$/.test(ev.url||'')))
        throw Error('unverified_completion');
      rev=ev.version;
      await append({type:ev.complete?'complete':'partial',turnId:job.turnId,tabId:job.tabId,
        revision:rev,text:ev.text,sha256:hash(ev.text),verified:!!ev.complete,url:ev.complete?ev.url:undefined});
      if(ev.complete)complete=true;
    });
    if(!complete)throw Error('no_verified_final');
    }catch(e){await append({type:'uncertain',turnId:job.turnId,tabId:job.tabId,message:String(e.message||e).slice(0,110)});}
  }}finally{busy=false;}}
  const server=http.createServer(async(req,res)=>{
    const send=(status,obj)=>{if(res.headersSent)return res.end();res.writeHead(status,{'Content-Type':'application/json','Cache-Control':'no-store'});res.end(JSON.stringify(obj));};
    const auth=String(req.headers.authorization||'');
    const a=createHash('sha256').update(token).digest(),b=createHash('sha256').update(auth.startsWith('Bearer ')?auth.slice(7):'').digest();
    if(!auth.startsWith('Bearer ')||!timingSafeEqual(a,b))return send(401,{error:'not_paired'});
    try{const url=new URL(req.url,'http://localhost');
      if(req.method==='GET'&&url.pathname==='/v1/ritsu/status')return send(200,{ok:true,transport:'tailscale-sse',cloudOps:0,seq});
      if(req.method==='GET'&&url.pathname==='/v1/ritsu/events'){
        const after=Number(url.searchParams.get('after')||'0');
        if(!Number.isSafeInteger(after)||after<0||after>seq)return send(400,{error:'invalid_cursor'});
        if(history.length&&after<history[0].seq-1)return send(409,{error:'journal_gap'});
        res.writeHead(200,{'Content-Type':'text/event-stream','Cache-Control':'no-store','Connection':'keep-alive'});
        res.write(': linked\n\n');for(const e of history)if(e.seq>after)res.write('id: '+e.seq+'\ndata: '+JSON.stringify(e)+'\n\n');
        listeners.add(res);const heartbeat=setInterval(()=>{if(!res.destroyed)res.write(': alive\n\n');},15000);
        req.on('close',()=>{clearInterval(heartbeat);listeners.delete(res);});return;
      }
      if(req.method==='POST'&&url.pathname==='/v1/ritsu/turn'){
        let text='',size=0;for await(const part of req){size+=part.length;if(size>13000)return send(413,{error:'too_large'});text+=part.toString();}
        const turn=JSON.parse(text);
        if(!turnPattern.test(turn.turnId||'')||!tabPattern.test(turn.tabId||'')||
           typeof turn.text!=='string'||!turn.text.trim()||turn.text.length>5000)return send(400,{error:'invalid_turn'});
        const digest=hash(turn.text),prior=turns.get(turn.turnId);
        if(prior){if(prior.tabId!==turn.tabId||prior.hash!==digest)return send(409,{error:'collision'});
          return send(200,{accepted:true,idempotent:true,state:prior.state,turnId:turn.turnId});}
        await append({type:'accepted',turnId:turn.turnId,tabId:turn.tabId,promptSha256:digest});
        jobs.push(turn);void pump();return send(202,{accepted:true,idempotent:false,turnId:turn.turnId});
      }
      return send(404,{error:'route_not_found'});
    }catch(e){send(500,{error:String(e.message||e).slice(0,110)});}
  });
  await new Promise((ok,no)=>{server.once('error',no);server.listen(opts.port??19646,host,ok);});
  return {host,port:server.address().port,seq:()=>seq,close:()=>new Promise(done=>{for(const c of listeners)c.end();server.close(done);})};
}
if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url)){
  const root=process.env.RITSU_LOCAL_ROOT||HOME;
  if(process.argv[2]==='token'){console.log(await tokenAt(root));process.exit(0);}
  const s=await createServer({root});console.log('RITSU_LINK=http://'+s.host+':'+s.port);
  process.on('SIGINT',()=>s.close().then(()=>process.exit()));
}
