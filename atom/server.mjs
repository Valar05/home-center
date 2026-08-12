import http from 'node:http';
import { readFile, mkdir, appendFile, writeFile } from 'node:fs/promises';
import { existsSync } from 'node:fs';
import { homedir } from 'node:os';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { randomUUID } from 'node:crypto';
import { spawn } from 'node:child_process';

const here=dirname(fileURLToPath(import.meta.url));
const stateDir=process.env.ATOM_STATE_DIR||join(homedir(),'.local','state','atom');
const port=Number(process.env.ATOM_PORT||8788);
const host=process.env.ATOM_HOST||'127.0.0.1';
const commandsFile=join(stateDir,'commands.jsonl');
const receiptsFile=join(stateDir,'receipts.jsonl');
const missionFile=join(stateDir,'missions.json');
const tabsFile=join(stateDir,'throne-tabs.json');
await mkdir(stateDir,{recursive:true});

async function lines(path){if(!existsSync(path))return[];return (await readFile(path,'utf8')).split('\n').filter(Boolean).map(x=>{try{return JSON.parse(x)}catch{return null}}).filter(Boolean)}
async function jsonFile(path,fallback){try{return JSON.parse(await readFile(path,'utf8'))}catch{return fallback}}
async function body(req,limit=128000){const chunks=[];let n=0;for await(const c of req){n+=c.length;if(n>limit)throw Object.assign(new Error('BODY_TOO_LARGE'),{status:413});chunks.push(c)}return chunks.length?JSON.parse(Buffer.concat(chunks).toString('utf8')):{}}
function send(res,status,value){const raw=Buffer.from(JSON.stringify(value));res.writeHead(status,{'content-type':'application/json; charset=utf-8','content-length':raw.length,'cache-control':'no-store'});res.end(raw)}
async function receipt(kind,summary,extra={}){const value={receiptId:randomUUID(),kind,summary,state:extra.state||'recorded',at:new Date().toISOString(),...extra};await appendFile(receiptsFile,JSON.stringify(value)+'\n');return value}
async function saveMission(command){const missions=await jsonFile(missionFile,[]);const mission={missionId:command.clientCommandId||randomUUID(),title:command.text.slice(0,96),summary:'Queued for Atom routing',state:'QUEUED',receiptState:'queued',createdAt:command.createdAt||new Date().toISOString()};missions.unshift(mission);await writeFile(missionFile,JSON.stringify(missions.slice(0,200),null,2));return mission}
async function diagnose(){const watchdog=join(homedir(),'bin','phone-hands-watchdog');if(!existsSync(watchdog))return receipt('diagnostic','Phone Hands watchdog is not installed.',{state:'blocked',blocker:'WATCHDOG_MISSING'});return await new Promise(resolve=>{const child=spawn(watchdog,['diagnose'],{env:process.env});let out='',err='';child.stdout.on('data',d=>out+=d);child.stderr.on('data',d=>err+=d);child.on('close',async code=>resolve(await receipt('diagnostic',(out||err||`watchdog exit ${code}`).trim().slice(-4000),{state:code===0?'complete':'degraded',exitCode:code}))})}

const staticRoot=join(here,'addons','chromium-throne');
const server=http.createServer(async(req,res)=>{try{const url=new URL(req.url,`http://${req.headers.host||host}`);if(req.method==='GET'&&(url.pathname==='/'||url.pathname==='/index.html')){const raw=await readFile(join(staticRoot,'index.html'));res.writeHead(200,{'content-type':'text/html; charset=utf-8'});return res.end(raw)}if(req.method==='GET'&&url.pathname==='/addon.mjs'){const raw=await readFile(join(staticRoot,'addon.mjs'));res.writeHead(200,{'content-type':'text/javascript; charset=utf-8'});return res.end(raw)}if(req.method==='GET'&&url.pathname==='/v1/atom/status'){const missions=await jsonFile(missionFile,[]);return send(res,200,{ok:true,state:'online',service:'Atom',offlinePrepared:true,terminalRequired:false,missions:missions.filter(x=>!['COMPLETE','CANCELLED'].includes(x.state)).slice(0,50)})}if(req.method==='POST'&&url.pathname==='/v1/atom/commands'){const input=await body(req);if(input.humanInitiated!==true||typeof input.text!=='string'||!input.text.trim())return send(res,400,{error:'INVALID_COMMAND'});const command={clientCommandId:input.clientCommandId||randomUUID(),text:input.text.trim(),createdAt:input.createdAt||new Date().toISOString(),source:input.source||'atom',humanInitiated:true,state:'QUEUED'};await appendFile(commandsFile,JSON.stringify(command)+'\n');const mission=await saveMission(command);const r=await receipt('command.accepted',`Atom accepted: ${command.text.slice(0,180)}`,{state:'queued',missionId:mission.missionId});return send(res,202,{ok:true,mission,receipt:r})}if(req.method==='GET'&&url.pathname==='/v1/atom/receipts'){const values=await lines(receiptsFile);return send(res,200,{receipts:values.reverse().slice(0,100)})}if(req.method==='POST'&&url.pathname==='/v1/atom/diagnose'){return send(res,200,await diagnose())}if(req.method==='GET'&&url.pathname==='/v1/atom/throne/tabs'){return send(res,200,{tabs:await jsonFile(tabsFile,[])})}return send(res,404,{error:'NOT_FOUND'})}catch(error){return send(res,error.status||500,{error:error.message})}});
server.listen(port,host,()=>console.log(JSON.stringify({ok:true,service:'Atom',url:`http://${host}:${port}`,stateDir,terminalRequired:false})));
