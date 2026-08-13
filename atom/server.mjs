import http from 'node:http';
import { readFile, mkdir, appendFile, writeFile } from 'node:fs/promises';
import { existsSync } from 'node:fs';
import { homedir } from 'node:os';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { randomUUID } from 'node:crypto';
import { spawn } from 'node:child_process';
import { createJudgmentJarReceiptService } from './judgment-jar-receipts.mjs';

const here=dirname(fileURLToPath(import.meta.url));
const repoRoot=dirname(here);
const judgmentJarConfigPath=process.env.HC_JUDGMENT_JARS_CONFIG||(existsSync(join(here,'config','judgment-jars.v1.json'))?join(here,'config','judgment-jars.v1.json'):join(repoRoot,'config','judgment-jars.v1.json'));
const stateDir=process.env.ATOM_STATE_DIR||join(homedir(),'.local','state','atom');
const port=Number(process.env.ATOM_PORT||8788);
const host=process.env.ATOM_HOST||'127.0.0.1';
const commandsFile=join(stateDir,'commands.jsonl');
const receiptsFile=join(stateDir,'receipts.jsonl');
const missionFile=join(stateDir,'missions.json');
const tabsFile=join(stateDir,'throne-tabs.json');
const vladContractPath=join(here,'vlad-operating-contract.json');
const judgmentJarCachePath=process.env.HC_JUDGMENT_JARS_CACHE||join(homedir(),'.local','state','home-center','vlad-swarm','judgment-jars.json');
await mkdir(stateDir,{recursive:true});

async function lines(path){if(!existsSync(path))return[];return (await readFile(path,'utf8')).split('\n').filter(Boolean).map(x=>{try{return JSON.parse(x)}catch{return null}}).filter(Boolean)}
async function jsonFile(path,fallback){try{return JSON.parse(await readFile(path,'utf8'))}catch{return fallback}}
async function body(req,limit=128000){const chunks=[];let n=0;for await(const c of req){n+=c.length;if(n>limit)throw Object.assign(new Error('BODY_TOO_LARGE'),{status:413});chunks.push(c)}return chunks.length?JSON.parse(Buffer.concat(chunks).toString('utf8')):{}}
function send(res,status,value){const raw=Buffer.from(JSON.stringify(value));res.writeHead(status,{'content-type':'application/json; charset=utf-8','content-length':raw.length,'cache-control':'no-store'});res.end(raw)}
async function receipt(kind,summary,extra={}){const value={receiptId:randomUUID(),kind,summary,state:extra.state||'recorded',at:new Date().toISOString(),...extra};await appendFile(receiptsFile,JSON.stringify(value)+'\n');return value}
const jarReceiptService=await createJudgmentJarReceiptService({configPath:judgmentJarConfigPath,cachePath:judgmentJarCachePath,stateDir,emitReceipt:receipt});
async function saveMission(command){const missions=await jsonFile(missionFile,[]);const mission={missionId:command.clientCommandId||randomUUID(),title:command.text.slice(0,96),summary:'Queued for Atom routing',state:'QUEUED',receiptState:'queued',createdAt:command.createdAt||new Date().toISOString()};missions.unshift(mission);await writeFile(missionFile,JSON.stringify(missions.slice(0,200),null,2));return mission}
function classifyDiagnostic(text,code){const value=String(text||'');if(/\b(HEALTHY|RECOVERED)\b/.test(value)&&!/(DEGRADED|HUMAN_REQUIRED|ACTION NEEDED|BLOCKED)/.test(value))return 'complete';if(/HUMAN_REQUIRED|ACTION NEEDED|BLOCKED/.test(value))return 'blocked';if(/DEGRADED/.test(value)||code!==0)return 'degraded';return 'unknown'}
async function diagnose(){const watchdog=join(homedir(),'bin','phone-hands-watchdog');if(!existsSync(watchdog))return receipt('diagnostic','Phone Hands watchdog is not installed.',{state:'blocked',blocker:'WATCHDOG_MISSING'});return await new Promise(resolve=>{const child=spawn(watchdog,['diagnose'],{env:process.env});let out='',err='';child.stdout.on('data',d=>out+=d);child.stderr.on('data',d=>err+=d);child.on('close',async code=>{const summary=(out||err||`watchdog exit ${code}`).trim().slice(-4000);resolve(await receipt('diagnostic',summary,{state:classifyDiagnostic(summary,code),exitCode:code}))})})}
function normalizeJarKey(value){return String(value||'').trim().toLowerCase().replaceAll('judgement','judgment').replace(/[^a-z0-9]+/g,'-').replace(/^-+|-+$/g,'')}
async function judgmentJarRegistry(){const value=await jsonFile(judgmentJarCachePath,null);return value?.schema==='home-center.judgment-jars.registry.v2'?value:null}
function judgmentJarSummary(registry){
  if(!registry)return{loaded:false,complete:false,state:'blocked',cachePath:judgmentJarCachePath,error:'JUDGMENT_JAR_CACHE_UNAVAILABLE',jarCount:0,localJarCount:0,cabinetJarCount:0,unregisteredJarCount:0,activeJarIds:[]};
  const home=registry.homeCenter||{};
  const complete=registry.complete===true;
  const homeState=home.state||'unavailable';
  return{
    loaded:true,
    complete,
    state:complete?'synced':homeState==='stale'?'stale':'degraded',
    cachePath:judgmentJarCachePath,
    jarCount:Number(registry.jarCount||registry.jars?.length||0),
    localJarCount:Number(registry.localJarCount||0),
    cabinetJarCount:Number(registry.cabinetJarCount||0),
    unregisteredJarCount:Number(registry.unregisteredJarCount||0),
    activeJarIds:registry.activeJarIds||[],
    registryDigest:registry.registryDigest||'',
    sourceCommit:registry.sourceCommit||'unknown',
    repositorySourcePattern:registry.repositorySourcePattern||'',
    homeCenterState:homeState,
    homeCenterRegistryFileId:home.registryFileId||'',
    homeCenterRegistrySha256:home.registryTextSha256||'',
    homeCenterLastSuccessEpoch:Number(home.lastSuccessEpoch||0),
    homeCenterLastError:home.lastError||'',
    missingExecutableFunctions:home.missingExecutableFunctions||[],
  };
}
function publicJar(jar,includeBody=false){
  const keys=['id','order','title','status','scope','judgment','origin','sourceAuthority','sourceCompleteness','sourcePath','sourceSha256','sourceFileId','sourceType','sourceUrl','registrySection','governor','home','boundary','mixedVerdict','hardGates','forbiddenFlattening','compactLaw','runOrder','primaryVerdict','consultationRule','wound','lineage','capabilityState','aliases'];
  const value={};for(const key of keys){if(jar?.[key]!==undefined&&jar?.[key]!==null&&jar?.[key]!=='')value[key]=jar[key]}
  if(includeBody)value.body=jar?.body||'';
  return value;
}
function resolveJar(registry,key){const normalized=normalizeJarKey(key);const id=registry?.aliasIndex?.[normalized]||normalized;return (registry?.jars||[]).find(jar=>jar.id===id)||null}
function searchJars(registry,query){const normalized=normalizeJarKey(query);const tokens=normalized.split('-').filter(Boolean);return(registry?.jars||[]).map(jar=>{const haystack=normalizeJarKey([jar.id,jar.title,jar.scope,jar.judgment,jar.compactLaw,jar.hardGates,...(jar.aliases||[]),jar.body].join(' '));const score=normalized&&haystack.includes(normalized)?100+tokens.length:tokens.filter(token=>haystack.includes(token)).length;return{score,jar}}).filter(row=>row.score>0).sort((a,b)=>b.score-a.score||Number(a.jar.order||9999)-Number(b.jar.order||9999)||String(a.jar.id).localeCompare(String(b.jar.id))).map(row=>publicJar(row.jar))}
async function vladStatus(){const contract=await jsonFile(vladContractPath,null);if(!contract)return{loaded:false,state:'blocked',error:'VLAD_CONTRACT_MISSING',path:vladContractPath};const jars=await judgmentJarRegistry();return{loaded:true,state:'deterministic',identity:contract.identity,kind:contract.kind,wound:contract.wound,virtue:contract.virtue,role:contract.role,defaultMode:contract.defaultMode,ollamaDefault:contract.inferencePolicy?.ollamaDefault||'disabled',maxParallelWorkers:Number(contract.swarm?.maxParallelWorkers||0),operatorSurface:contract.swarm?.operatorSurface||'',codingOwner:contract.codingOwner||'Venice',finalRelease:contract.finalRelease||'Tetsuya',judgmentJars:judgmentJarSummary(jars),judgmentJarReceipts:await jarReceiptService.status()}}

const staticRoot=join(here,'addons','chromium-throne');
const server=http.createServer(async(req,res)=>{try{const url=new URL(req.url,`http://${req.headers.host||host}`);if(req.method==='GET'&&(url.pathname==='/'||url.pathname==='/index.html')){const raw=await readFile(join(staticRoot,'index.html'));res.writeHead(200,{'content-type':'text/html; charset=utf-8'});return res.end(raw)}if(req.method==='GET'&&url.pathname==='/addon.mjs'){const raw=await readFile(join(staticRoot,'addon.mjs'));res.writeHead(200,{'content-type':'text/javascript; charset=utf-8'});return res.end(raw)}if(req.method==='GET'&&url.pathname==='/manifest.webmanifest'){const raw=await readFile(join(staticRoot,'manifest.webmanifest'));res.writeHead(200,{'content-type':'application/manifest+json'});return res.end(raw)}if(req.method==='GET'&&url.pathname==='/sw.js'){const raw=await readFile(join(staticRoot,'sw.js'));res.writeHead(200,{'content-type':'text/javascript; charset=utf-8','service-worker-allowed':'/'});return res.end(raw)}if(req.method==='GET'&&url.pathname==='/v1/atom/status'){const missions=await jsonFile(missionFile,[]);return send(res,200,{ok:true,state:'online',service:'Atom',offlinePrepared:true,terminalRequired:false,vlad:await vladStatus(),missions:missions.filter(x=>!['COMPLETE','CANCELLED'].includes(x.state)).slice(0,50)})}if(req.method==='GET'&&url.pathname==='/v1/atom/vlad'){return send(res,200,{ok:true,vlad:await vladStatus(),contract:await jsonFile(vladContractPath,null)})}if(req.method==='GET'&&url.pathname==='/v1/atom/vlad/jars'){const registry=await judgmentJarRegistry();if(!registry)return send(res,503,{ok:false,error:'JUDGMENT_JAR_CACHE_UNAVAILABLE',cachePath:judgmentJarCachePath});const id=url.searchParams.get('id');if(id){const jar=resolveJar(registry,id);if(!jar)return send(res,404,{ok:false,error:'JUDGMENT_JAR_NOT_FOUND',id});const packet={ok:true,registry:judgmentJarSummary(registry),jar:publicJar(jar,true)};const usage=await jarReceiptService.recordContextAccess(registry,jar,'atom.vlad.jars.get',id,JSON.stringify(packet));return send(res,200,{...packet,usage})}const query=url.searchParams.get('q');if(query)return send(res,200,{ok:true,registry:judgmentJarSummary(registry),query,matches:searchJars(registry,query)});return send(res,200,{ok:true,registry:judgmentJarSummary(registry),jars:(registry.jars||[]).map(jar=>publicJar(jar))})}if(req.method==='GET'&&url.pathname==='/v1/atom/vlad/jars/receipts/status'){return send(res,200,{ok:true,usage:await jarReceiptService.status()})}if(req.method==='POST'&&url.pathname==='/v1/atom/vlad/jars/receipts'){const result=await jarReceiptService.record(await body(req));return send(res,result.status,result)}if(req.method==='POST'&&url.pathname==='/v1/atom/commands'){const input=await body(req);if(input.humanInitiated!==true||typeof input.text!=='string'||!input.text.trim())return send(res,400,{error:'INVALID_COMMAND'});const command={clientCommandId:input.clientCommandId||randomUUID(),text:input.text.trim(),createdAt:input.createdAt||new Date().toISOString(),source:input.source||'atom',humanInitiated:true,state:'QUEUED',orchestrator:'Vlad',mode:'deterministic'};await appendFile(commandsFile,JSON.stringify(command)+'\n');const mission=await saveMission(command);const r=await receipt('command.accepted',`Atom/Vlad accepted: ${command.text.slice(0,180)}`,{state:'queued',missionId:mission.missionId,orchestrator:'Vlad',mode:'deterministic'});return send(res,202,{ok:true,mission,receipt:r,vlad:await vladStatus()})}if(req.method==='GET'&&url.pathname==='/v1/atom/receipts'){const values=await lines(receiptsFile);return send(res,200,{receipts:values.reverse().slice(0,100)})}if(req.method==='POST'&&url.pathname==='/v1/atom/diagnose'){return send(res,200,await diagnose())}if(req.method==='GET'&&url.pathname==='/v1/atom/throne/tabs'){return send(res,200,{tabs:await jsonFile(tabsFile,[])})}return send(res,404,{error:'NOT_FOUND'})}catch(error){return send(res,error.status||500,{error:error.message})}});
server.listen(port,host,()=>console.log(JSON.stringify({ok:true,service:'Atom',url:`http://${host}:${port}`,stateDir,terminalRequired:false,vladContract:vladContractPath,judgmentJarCache:judgmentJarCachePath,judgmentJarConfig:judgmentJarConfigPath})));
