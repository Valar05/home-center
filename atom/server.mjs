import http from 'node:http';
import { readFile, mkdir, appendFile, writeFile, rename } from 'node:fs/promises';
import { existsSync } from 'node:fs';
import { homedir } from 'node:os';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { randomUUID } from 'node:crypto';
import { spawn } from 'node:child_process';
import { classifyCommand, makeWorkEnvelope, validateWorkerResult, ROUTES } from './router.mjs';

const here=dirname(fileURLToPath(import.meta.url));
const stateDir=process.env.ATOM_STATE_DIR||join(homedir(),'.local','state','atom');
const port=Number(process.env.ATOM_PORT||8788);
const host=process.env.ATOM_HOST||'127.0.0.1';
const commandsFile=join(stateDir,'commands.jsonl');
const receiptsFile=join(stateDir,'receipts.jsonl');
const missionFile=join(stateDir,'missions.json');
const workFile=join(stateDir,'work.json');
const tabsFile=join(stateDir,'throne-tabs.json');
await mkdir(stateDir,{recursive:true});

async function lines(path){if(!existsSync(path))return[];return (await readFile(path,'utf8')).split('\n').filter(Boolean).map(x=>{try{return JSON.parse(x)}catch{return null}}).filter(Boolean)}
async function jsonFile(path,fallback){try{return JSON.parse(await readFile(path,'utf8'))}catch{return fallback}}
async function atomicJson(path,value){const tmp=`${path}.${process.pid}.tmp`;await writeFile(tmp,JSON.stringify(value,null,2));await rename(tmp,path)}
async function body(req,limit=128000){const chunks=[];let n=0;for await(const c of req){n+=c.length;if(n>limit)throw Object.assign(new Error('BODY_TOO_LARGE'),{status:413});chunks.push(c)}return chunks.length?JSON.parse(Buffer.concat(chunks).toString('utf8')):{}}
function send(res,status,value){const raw=Buffer.from(JSON.stringify(value));res.writeHead(status,{'content-type':'application/json; charset=utf-8','content-length':raw.length,'cache-control':'no-store'});res.end(raw)}
async function receipt(kind,summary,extra={}){const value={receiptId:randomUUID(),kind,summary,state:extra.state||'recorded',at:new Date().toISOString(),...extra};await appendFile(receiptsFile,JSON.stringify(value)+'\n');return value}
async function missions(){return jsonFile(missionFile,[])}
async function saveMissions(values){await atomicJson(missionFile,values.slice(0,500))}
async function workItems(){return jsonFile(workFile,[])}
async function saveWork(values){await atomicJson(workFile,values.slice(0,1000))}
async function updateMission(missionId,patch){const values=await missions();const index=values.findIndex(x=>x.missionId===missionId);if(index<0)throw Object.assign(new Error('MISSION_NOT_FOUND'),{status:404});values[index]={...values[index],...patch,updatedAt:new Date().toISOString()};await saveMissions(values);return values[index]}
async function saveMission(command){const values=await missions();const existing=values.find(x=>x.missionId===command.clientCommandId);if(existing)return existing;const mission={missionId:command.clientCommandId||randomUUID(),title:command.text.slice(0,96),summary:'Accepted by Atom',state:'QUEUED',receiptState:'queued',createdAt:command.createdAt||new Date().toISOString()};values.unshift(mission);await saveMissions(values);return mission}
function classifyDiagnostic(text,code){const value=String(text||'');if(/\b(HEALTHY|RECOVERED)\b/.test(value)&&!/(DEGRADED|HUMAN_REQUIRED|ACTION NEEDED|BLOCKED)/.test(value))return 'complete';if(/HUMAN_REQUIRED|ACTION NEEDED|BLOCKED/.test(value))return 'blocked';if(/DEGRADED/.test(value)||code!==0)return 'degraded';return 'unknown'}
async function diagnose(){const watchdog=join(homedir(),'bin','phone-hands-watchdog');if(!existsSync(watchdog))return receipt('diagnostic','Phone Hands watchdog is not installed.',{state:'blocked',blocker:'WATCHDOG_MISSING'});return await new Promise(resolve=>{const child=spawn(watchdog,['diagnose'],{env:process.env});let out='',err='';child.stdout.on('data',d=>out+=d);child.stderr.on('data',d=>err+=d);child.on('close',async code=>{const summary=(out||err||`watchdog exit ${code}`).trim().slice(-4000);resolve(await receipt('diagnostic',summary,{state:classifyDiagnostic(summary,code),exitCode:code}))})})}

async function routeMission(command,mission){
  const decision=classifyCommand(command);
  await receipt('mission.routed',`${decision.outcome}: ${decision.route||decision.reasonCode}`,{state:decision.outcome==='ROUTE'?'routed':'blocked',missionId:mission.missionId,decision});
  if(decision.outcome!=='ROUTE')return updateMission(mission.missionId,{state:'BLOCKED',summary:decision.reasonCode,receiptState:'blocked'});
  if(decision.route===ROUTES.DIAGNOSE_PHONE){
    await updateMission(mission.missionId,{state:'RUNNING',summary:'Running local Phone Hands diagnostic',receiptState:'running'});
    const result=await diagnose();
    const finalState=result.state==='complete'?'COMPLETE':result.state==='blocked'?'BLOCKED':'FAILED';
    const updated=await updateMission(mission.missionId,{state:finalState,summary:result.summary,receiptState:result.state});
    await receipt('mission.finished',result.summary,{state:result.state,missionId:mission.missionId,diagnosticReceiptId:result.receiptId});
    return updated;
  }
  if(decision.route===ROUTES.STATUS){
    const active=(await missions()).filter(x=>!['COMPLETE','CANCELLED'].includes(x.state));
    const summary=`Atom online; ${active.length} active mission(s); ${(await workItems()).filter(x=>x.state==='READY'||x.state==='LEASED').length} pending work item(s).`;
    const updated=await updateMission(mission.missionId,{state:'COMPLETE',summary,receiptState:'complete'});
    await receipt('mission.finished',summary,{state:'complete',missionId:mission.missionId});
    return updated;
  }
  const envelope=makeWorkEnvelope(command,decision);
  const work={...envelope,state:'READY',lease:null,attempts:0};
  const values=await workItems();values.push(work);await saveWork(values);
  const updated=await updateMission(mission.missionId,{state:'ROUTED',summary:`Routed to ${decision.route}`,receiptState:'routed',workId:work.workId,route:decision.route});
  await receipt('work.ready',`Work ready for ${decision.route}`,{state:'ready',missionId:mission.missionId,workId:work.workId,route:decision.route});
  return updated;
}

async function leaseWork(input){
  const workerId=String(input.workerId||'').trim();const routes=Array.isArray(input.routes)?input.routes.filter(Boolean):[];
  if(!workerId||!routes.length)throw Object.assign(new Error('WORKER_ID_AND_ROUTES_REQUIRED'),{status:400});
  const now=Date.now();const values=await workItems();
  for(const work of values){if(work.state==='LEASED'&&Date.parse(work.lease?.expiresAt||0)<=now){work.state='READY';work.lease=null}}
  const work=values.find(x=>x.state==='READY'&&routes.includes(x.route));
  if(!work){await saveWork(values);return null}
  work.state='LEASED';work.attempts=(work.attempts||0)+1;work.lease={workerId,leaseId:randomUUID(),expiresAt:new Date(now+60000).toISOString()};await saveWork(values);
  await updateMission(work.missionId,{state:'RUNNING',summary:`Leased to ${workerId}`,receiptState:'running'});
  await receipt('work.leased',`Work leased to ${workerId}`,{state:'running',missionId:work.missionId,workId:work.workId,route:work.route,workerId,leaseId:work.lease.leaseId});
  return work;
}

async function finishWork(input){
  const values=await workItems();const work=values.find(x=>x.workId===input.workId);if(!work)throw Object.assign(new Error('WORK_NOT_FOUND'),{status:404});
  if(work.state!=='LEASED'||work.lease?.leaseId!==input.leaseId)throw Object.assign(new Error('LEASE_MISMATCH'),{status:409});
  const validation=validateWorkerResult(input,work);if(!validation.ok)throw Object.assign(new Error(validation.reasonCode),{status:400});
  work.state=input.state;work.completedAt=new Date().toISOString();work.result={summary:input.summary,evidence:Array.isArray(input.evidence)?input.evidence.slice(0,50):[],capabilityState:input.capabilityState||null};work.lease=null;await saveWork(values);
  const receiptState=input.state==='COMPLETE'?'complete':input.state==='BLOCKED'?'blocked':'failed';
  await updateMission(work.missionId,{state:input.state,summary:input.summary,receiptState,completedAt:work.completedAt});
  return receipt('work.finished',input.summary,{state:receiptState,missionId:work.missionId,workId:work.workId,evidence:work.result.evidence,capabilityState:work.result.capabilityState});
}

const staticRoot=join(here,'addons','chromium-throne');
const server=http.createServer(async(req,res)=>{try{const url=new URL(req.url,`http://${req.headers.host||host}`);
  if(req.method==='GET'&&(url.pathname==='/'||url.pathname==='/index.html')){const raw=await readFile(join(staticRoot,'index.html'));res.writeHead(200,{'content-type':'text/html; charset=utf-8'});return res.end(raw)}
  if(req.method==='GET'&&url.pathname==='/addon.mjs'){const raw=await readFile(join(staticRoot,'addon.mjs'));res.writeHead(200,{'content-type':'text/javascript; charset=utf-8'});return res.end(raw)}
  if(req.method==='GET'&&url.pathname==='/manifest.webmanifest'){const raw=await readFile(join(staticRoot,'manifest.webmanifest'));res.writeHead(200,{'content-type':'application/manifest+json'});return res.end(raw)}
  if(req.method==='GET'&&url.pathname==='/sw.js'){const raw=await readFile(join(staticRoot,'sw.js'));res.writeHead(200,{'content-type':'text/javascript; charset=utf-8','service-worker-allowed':'/'});return res.end(raw)}
  if(req.method==='GET'&&url.pathname==='/v1/atom/status'){const values=await missions();const works=await workItems();return send(res,200,{ok:true,state:'online',service:'Atom',offlinePrepared:true,terminalRequired:false,missions:values.filter(x=>!['COMPLETE','CANCELLED'].includes(x.state)).slice(0,50),work:{ready:works.filter(x=>x.state==='READY').length,leased:works.filter(x=>x.state==='LEASED').length}})}
  if(req.method==='POST'&&url.pathname==='/v1/atom/commands'){const input=await body(req);if(input.humanInitiated!==true||typeof input.text!=='string'||!input.text.trim())return send(res,400,{error:'INVALID_COMMAND'});const command={clientCommandId:input.clientCommandId||randomUUID(),text:input.text.trim(),createdAt:input.createdAt||new Date().toISOString(),source:input.source||'atom',humanInitiated:true,state:'QUEUED'};const prior=(await missions()).find(x=>x.missionId===command.clientCommandId);if(prior)return send(res,200,{ok:true,idempotentReplay:true,mission:prior});await appendFile(commandsFile,JSON.stringify(command)+'\n');const mission=await saveMission(command);const accepted=await receipt('command.accepted',`Atom accepted: ${command.text.slice(0,180)}`,{state:'queued',missionId:mission.missionId});const routed=await routeMission(command,mission);return send(res,202,{ok:true,mission:routed,receipt:accepted})}
  if(req.method==='GET'&&url.pathname==='/v1/atom/receipts'){const values=await lines(receiptsFile);return send(res,200,{receipts:values.reverse().slice(0,100)})}
  if(req.method==='POST'&&url.pathname==='/v1/atom/diagnose'){return send(res,200,await diagnose())}
  if(req.method==='GET'&&url.pathname==='/v1/atom/throne/tabs'){return send(res,200,{tabs:await jsonFile(tabsFile,[])})}
  if(req.method==='POST'&&url.pathname==='/v1/atom/workers/lease'){const leased=await leaseWork(await body(req));return leased?send(res,200,{work:leased}):send(res,204,{})}
  if(req.method==='POST'&&url.pathname==='/v1/atom/workers/finish'){return send(res,200,{receipt:await finishWork(await body(req))})}
  return send(res,404,{error:'NOT_FOUND'})
}catch(error){return send(res,error.status||500,{error:error.message})}});
server.listen(port,host,()=>console.log(JSON.stringify({ok:true,service:'Atom',url:`http://${host}:${port}`,stateDir,terminalRequired:false,missionRouter:true})));
