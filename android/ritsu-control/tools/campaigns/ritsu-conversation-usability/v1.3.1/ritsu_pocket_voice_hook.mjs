// Windows-only optional Ritsu Pocket bridge. No new voice server or receiver.
// Exact installed sender SHA is authoritative. Unknown binaries are never used.
import {promises as fs} from 'node:fs';
import {createHash} from 'node:crypto';
import {spawn} from 'node:child_process';
import path from 'node:path';
import os from 'node:os';
const root=path.join(os.homedir(),'.ritsu-control','local-link');
const sender=path.join(os.homedir(),'workspace','ritsu-faster-qwen3-tts','ritsu_say.py');
const python=path.join(os.homedir(),'workspace','ritsu-faster-qwen3-tts','.venv','Scripts','python.exe');
const digest='3dda464df8d5e24d29db471df7c7b8d70d28741c98866996a980afe5443c6ad8';
const prefs=path.join(root,'ritsu-voice-preferences-v1.json');
const claims=path.join(root,'voice-claims-v1');
export async function voiceSet(tabId,enabled){
  if(!/^[A-Za-z0-9_-]{4,80}$/.test(tabId)||typeof enabled!=='boolean')throw Error('voice_preference_invalid');
  let value={};try{value=JSON.parse(await fs.readFile(prefs,'utf8'));}
  catch(e){if(e.code!=='ENOENT')throw e;}
  value[tabId]=enabled;const tmp=prefs+'.'+process.pid+'.new';
  await fs.writeFile(tmp,JSON.stringify(value),{mode:0o600});await fs.rename(tmp,prefs);
  return {verified:true,tabId,enabled};
}
export async function voiceAllowed(tabId){
  try{const value=JSON.parse(await fs.readFile(prefs,'utf8'));return value[tabId]===true;}
  catch(e){if(e.code==='ENOENT')return false;throw e;}
}
export async function voiceDeliver(tabId,turnId,text){
  if(!await voiceAllowed(tabId))return {voice:'OFF'};
  if(!/^[A-Za-z0-9_.:-]{8,100}$/.test(turnId))throw Error('voice_id_invalid');
  // A complete browser reply is not necessarily a semantically authored 450-char
  // unit. Do not regex-split, truncate, or silently omit any text.
  if(typeof text!=='string'||!text.trim()||text.length>450)
    return {voice:'EXACT_SPAN_UNSPEAKABLE',textCharacters:text?.length||0};
  const source=await fs.readFile(sender);
  if(createHash('sha256').update(source).digest('hex')!==digest)
    return {voice:'BLOCKED_SENDER_HASH_CHANGED'};
  await fs.access(python);
  await fs.mkdir(claims,{recursive:true,mode:0o700});
  const claim=path.join(claims,turnId+'.json');
  // Crash between process launch and ACK is ambiguous. Claim first, never replay.
  try{await fs.writeFile(claim,JSON.stringify({turnId,tabId,state:'CLAIMED',at:new Date().toISOString()}),{flag:'wx',mode:0o600});}
  catch(e){if(e.code==='EEXIST')return {voice:'ALREADY_CLAIMED_NO_RESUBMIT'};throw e;}
  const privateText=path.join(claims,turnId+'.text');
  await fs.writeFile(privateText,text,{flag:'wx',mode:0o600});
  const child=spawn(python,[sender,'--text-file',privateText,'--profile','normal','--turn-id',turnId],
    {windowsHide:true,stdio:['ignore','ignore','ignore']});
  return await new Promise(resolve=>{
    const timer=setTimeout(()=>{child.kill();resolve({voice:'TIMEOUT_NO_REPLAY'});},360000);
    child.once('error',()=>{clearTimeout(timer);resolve({voice:'SPAWN_FAILED_NO_REPLAY'});});
    child.once('close',code=>{clearTimeout(timer);fs.unlink(privateText).catch(()=>{});
      resolve({voice:code===0?'ENQUEUED_NOT_HEARD':'FAILED_NO_REPLAY',exitCode:code});});
  });
}
