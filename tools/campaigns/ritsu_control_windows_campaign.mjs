// Pinned, resumable Ritsu Control Windows campaign. Run only on authorized windows-hands-01.
// command: node ritsu_control_windows_campaign.mjs run|status|resume|stop|receipts
import fs from 'node:fs';
import fsp from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import {spawn,spawnSync} from 'node:child_process';
import {createHash} from 'node:crypto';
const SHA='a6c42b235232ad8969e358f3e793c7885f686e3e';
const REPO=path.join(os.homedir(),'workspace','home-center');
const root=path.join(process.env.LOCALAPPDATA||path.join(os.homedir(),'AppData','Local'),'RitsuControlBridge');
const stateFile=path.join(root,'campaign-state.json');
const log=path.join(root,'campaign.log');
const target=path.join(root,'ritsu_control_playwright_bridge.mjs');
const worktree=path.join(root,'checkout-'+SHA.slice(0,12));
const chromeRoot=path.join(os.homedir(),'AppData','Local','HomeCenter','ChromiumThrone');
const launchCmd=path.join(chromeRoot,'launch-chromium-throne.cmd');
const existingProfile=path.join(chromeRoot,'profile');
const cdp='http://127.0.0.1:9236';
const pause=ms=>new Promise(resolve=>setTimeout(resolve,ms));
async function chromeAlive(){
  try{
    const res=await fetch(cdp+'/json/version',{signal:AbortSignal.timeout(1800)});
    if(!res.ok)return false;
    const v=await res.json();
    return /chrome|chromium/i.test(String(v.Browser||''));
  }catch{return false;}
}
function managedChromePids(){
  const ps="$ErrorActionPreference='Stop';Get-CimInstance Win32_Process -Filter \"name='chrome.exe'\" | Where-Object { $_.CommandLine -like '*HomeCenter*ChromiumThrone*profile*' } | ForEach-Object { $_.ProcessId }";
  const r=spawnSync('powershell.exe',['-NoProfile','-NonInteractive','-Command',ps],{encoding:'utf8',timeout:15000,windowsHide:true});
  if(r.error||r.status!==0)throw Error('managed_browser_process_inspection_failed');
  return String(r.stdout||'').trim().split(/\s+/).filter(x=>/^\d+$/.test(x)).map(Number);
}
async function ensureManagedBrowser(){
  if(await chromeAlive())return {port:9236,started:false};
  if(!fs.existsSync(launchCmd)||!fs.existsSync(existingProfile))
    throw Error('approved_existing_chromium_throne_profile_or_launcher_missing');
  const original=fs.readFileSync(launchCmd,'utf8');
  if(!original.includes('--remote-debugging-address=127.0.0.1') ||
     !original.includes('--user-data-dir=') ||
     !original.includes('chrome-for-testing') ||
     !original.includes('ChromiumThrone') ||
     !(original.includes('--remote-debugging-port=9234')||
       original.includes('--remote-debugging-port=9236')))
    throw Error('managed_throne_launcher_unrecognized');
  const backup=launchCmd+'.before-ritsu-playwright-port.bak';
  if(!fs.existsSync(backup))fs.copyFileSync(launchCmd,backup,fs.constants.COPYFILE_EXCL);
  const patched=original.replace('--remote-debugging-port=9234','--remote-debugging-port=9236');
  if(patched!==original){fs.writeFileSync(launchCmd+'.new',patched);fs.renameSync(launchCmd+'.new',launchCmd);}
  if(!fs.readFileSync(launchCmd,'utf8').includes('--remote-debugging-port=9236'))
    throw Error('managed_throne_debugging_port_not_persisted');
  write('browser_launch_preflight',{managedProfile:existingProfile,cdpPort:9236,launcherBackup:backup});
  const pids=managedChromePids();
  if(pids.length){
    // Fail closed if an existing session is using the profile without CDP.
    // Never destroy a live Chrome window or corrupt a profile to enable debugging.
    throw Error('managed_profile_in_use_without_cdp_restart_requires_reconciliation');
  }
  const child=spawn('cmd.exe',['/d','/c',launchCmd],{detached:true,windowsHide:true,stdio:'ignore',cwd:chromeRoot});
  child.unref();
  const deadline=Date.now()+25000;
  while(Date.now()<deadline){
    if(await chromeAlive())return {port:9236,started:true};
    await pause(800);
  }
  throw Error('managed_throne_browser_did_not_expose_cdp');
}
const verb=process.argv[2]||'status';
function read(){try{return JSON.parse(fs.readFileSync(stateFile,'utf8'));}catch{return {stage:'not_started',revision:SHA};}}
function write(stage,other={}){const s={...read(),...other,stage,revision:SHA,updatedAt:new Date().toISOString()};fs.writeFileSync(stateFile+'.tmp',JSON.stringify(s,null,2));fs.renameSync(stateFile+'.tmp',stateFile);process.stdout.write(JSON.stringify(s)+'\n');}
function exec(command,args,opts={}) { const r=spawnSync(command,args,{cwd:REPO,encoding:'utf8',timeout:60000,maxBuffer:1500000,windowsHide:true,...opts});if(r.error||r.status!==0)throw Error(command+' '+args[0]+': '+String(r.error?.message||r.stderr||'exit '+r.status).slice(0,700));return String(r.stdout||'');}
function hash(buf){return createHash('sha256').update(buf).digest('hex');}
await fsp.mkdir(root,{recursive:true});
if(verb==='status'||verb==='receipts'){process.stdout.write(JSON.stringify(read(),null,2)+'\n');if(verb==='receipts'&&fs.existsSync(log))process.stdout.write(fs.readFileSync(log,'utf8').slice(-6000));}
else if(verb==='stop'){fs.writeFileSync(path.join(root,'STOP'),'1');const s=read();if(s.pid&&s.pid!==process.pid){spawnSync('taskkill',['/PID',String(s.pid),'/T','/F'],{windowsHide:true,timeout:10000});}write('stopped',{stopRequested:true});}
else if(verb==='run'||verb==='resume'){
  const s=read();if(s.pid){try{process.kill(s.pid,0);throw Error('campaign_worker_already_running_pid_'+s.pid)}catch(e){if(e.message.startsWith('campaign_worker'))throw e;}}
  fs.rmSync(path.join(root,'STOP'),{force:true});
  const out=fs.openSync(log,'a'); const child=spawn(process.execPath,[process.argv[1],'__worker'],{detached:true,windowsHide:true,stdio:['ignore',out,out],cwd:REPO});child.unref();fs.closeSync(out);write('launched',{pid:child.pid,stopRequested:false});
}
else if(verb==='__worker'){
  const stopped=()=>fs.existsSync(path.join(root,'STOP'));
  try {
    if(!fs.existsSync(path.join(REPO,'.git')))throw Error('approved_repo_missing');
    if(stopped())throw Error('owner_stop');
    write('fetching');
    exec('git',['-C',REPO,'fetch','--no-tags','origin',SHA],{env:{...process.env,GIT_LFS_SKIP_SMUDGE:'1'}});
    const got=exec('git',['-C',REPO,'rev-parse','FETCH_HEAD']).trim();
    if(got!==SHA)throw Error('fetched_sha_mismatch');
    if(stopped())throw Error('owner_stop');
    write('isolated_checkout');
    if(!fs.existsSync(worktree))exec('git',['-C',REPO,'worktree','add','--detach',worktree,SHA],{env:{...process.env,GIT_LFS_SKIP_SMUDGE:'1'}});
    const check=exec('git',['-C',worktree,'rev-parse','HEAD']).trim();
    if(check!==SHA)throw Error('worktree_sha_mismatch');
    const dirty=exec('git',['-C',worktree,'status','--porcelain']).trim();
    if(dirty)throw Error('isolated_checkout_dirty');
    if(stopped())throw Error('owner_stop');
    const source=path.join(worktree,'tools','campaigns','ritsu_control_playwright_bridge.mjs');
    const bytes=fs.readFileSync(source);
    exec('node',['--check',source],{cwd:worktree});
    const checksum=hash(bytes);
    const backup=target+'.before-'+SHA.slice(0,12)+'.bak';
    if(fs.existsSync(target)&&hash(fs.readFileSync(target))!==checksum&&!fs.existsSync(backup))fs.copyFileSync(target,backup,fs.constants.COPYFILE_EXCL);
    if(!fs.existsSync(target)||hash(fs.readFileSync(target))!==checksum){
      fs.writeFileSync(target+'.tmp',bytes);fs.renameSync(target+'.tmp',target);
    }
    if(hash(fs.readFileSync(target))!==checksum)throw Error('staged_hash_mismatch');
    write('staged',{deployedPath:target,sourceSha256:checksum,backupPath:fs.existsSync(backup)?backup:null});
    if(stopped())throw Error('owner_stop');
    write('browser_recovery');
    const managed=await ensureManagedBrowser();
    write('browser_connected',{browser:managed});
    if(stopped())throw Error('owner_stop');
    // Read-only doctor; first require the existing authenticated managed profile.
    write('doctor_running');
    const result=spawnSync('node',[target,'--doctor'],{cwd:worktree,encoding:'utf8',timeout:50000,maxBuffer:500000,windowsHide:true});
    const raw=(result.stdout||'').split(/\r?\n/).find(x=>x.startsWith('RITSU_BROWSER_RECEIPT='));
    if(result.status!==0||!raw)throw Error('doctor_failed: '+String(result.stderr||result.stdout||'no receipt').slice(0,600));
    const doctor=JSON.parse(raw.slice('RITSU_BROWSER_RECEIPT='.length));
    if(stopped())throw Error('owner_stop');
    if(doctor.kind!=='doctor'||doctor.cdp!==true||!Array.isArray(doctor.surfaces)||
       !doctor.surfaces.some(x=>(x.promptId>0||x.editable>0)&&!x.challenge&&!x.login))
      throw Error('doctor_has_no_verified_signed_in_composer');
    const nodeTests=spawnSync('node',['--test','tools/ritsu-agent-loop/contract.test.mjs','tools/ritsu-agent-loop/journal.test.mjs'],
        {cwd:worktree,encoding:'utf8',timeout:60000,maxBuffer:500000,windowsHide:true});
    if(nodeTests.status!==0)throw Error('agent_contract_tests_failed: '+String(nodeTests.stderr||nodeTests.stdout).slice(-400));
    write('doctor_verified',{doctor,doctorExit:result.status,nodeContractTests:true,phoneRoundTripVerified:false,agentComplete:false});
  }catch(e){write(stopped()?'stopped':'failed',{error:String(e.message||e).slice(0,1000),phoneRoundTripVerified:false,agentComplete:false});process.exitCode=1;}
}
else throw Error('unknown_verb');
