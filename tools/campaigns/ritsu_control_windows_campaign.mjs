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
const verb=process.argv[2]||'status';
function read(){try{return JSON.parse(fs.readFileSync(stateFile,'utf8'));}catch{return {stage:'not_started',revision:SHA};}}
function write(stage,other={}){const s={...read(),...other,stage,revision:SHA,updatedAt:new Date().toISOString()};fs.writeFileSync(stateFile+'.tmp',JSON.stringify(s,null,2));fs.renameSync(stateFile+'.tmp',stateFile);process.stdout.write(JSON.stringify(s)+'\n');}
function exec(command,args,opts={}) { const r=spawnSync(command,args,{cwd:REPO,encoding:'utf8',timeout:60000,maxBuffer:1500000,windowsHide:true,...opts});if(r.error||r.status!==0)throw Error(command+' '+args[0]+': '+String(r.error?.message||r.stderr||'exit '+r.status).slice(0,700));return String(r.stdout||'');}
function hash(buf){return createHash('sha256').update(buf).digest('hex');}
await fsp.mkdir(root,{recursive:true});
if(verb==='status'||verb==='receipts'){process.stdout.write(JSON.stringify(read(),null,2)+'\\n');if(verb==='receipts'&&fs.existsSync(log))process.stdout.write(fs.readFileSync(log,'utf8').slice(-6000));}
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
    // Read-only, connects to the existing signed-in browser. Does not send a prompt.
    write('doctor_running');
    const result=spawnSync('node',[target,'--doctor'],{cwd:worktree,encoding:'utf8',timeout:50000,maxBuffer:500000,windowsHide:true});
    const raw=(result.stdout||'').split(/\r?\n/).find(x=>x.startsWith('RITSU_BROWSER_RECEIPT='));
    if(result.status!==0||!raw)throw Error('doctor_failed: '+String(result.stderr||result.stdout||'no receipt').slice(0,600));
    const doctor=JSON.parse(raw.slice('RITSU_BROWSER_RECEIPT='.length));
    if(doctor.kind!=='doctor'||doctor.cdp!==true||!Array.isArray(doctor.surfaces)||
       !doctor.surfaces.some(x=>(x.promptId>0||x.editable>0)&&!x.challenge&&!x.login))
      throw Error('doctor_has_no_verified_signed_in_composer');
    write('doctor_verified',{doctor,doctorExit:result.status,phoneRoundTripVerified:false,agentComplete:false});
  }catch(e){write(stopped()?'stopped':'failed',{error:String(e.message||e).slice(0,1000),phoneRoundTripVerified:false,agentComplete:false});process.exitCode=1;}
}
else throw Error('unknown_verb');
