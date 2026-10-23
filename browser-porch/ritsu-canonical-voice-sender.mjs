// Only the approved Windows Pocket TTS + 19643 phone relay.
import {spawn} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import path from 'node:path';

export function createCanonicalVoiceSender({relayRoot,spawnImpl=spawn}={}) {
  if(process.platform!=='win32' && spawnImpl===spawn)
    throw new Error('Windows_canonical_relay_only');
  if(!path.isAbsolute(relayRoot||''))
    throw new Error('approved_canonical_relay_root_required');
  const script=fileURLToPath(new URL('./ritsu-canonical-voice-send.ps1',import.meta.url));
  return ({text})=>new Promise((resolve,reject)=>{
    if(typeof text!=='string'||!text.trim()||text.length>600)
      return reject(new Error('invalid_voice_chunk'));
    const child=spawnImpl('powershell.exe',
      ['-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass',
        '-File',script],
      {env:{...process.env,HOME_CENTER_RITSU_CANONICAL_RELAY_ROOT:relayRoot},
        stdio:['pipe','pipe','pipe'],windowsHide:true});
    let stdout='',stderr='';
    const timeout=setTimeout(()=>child.kill(),60000);
    child.stdout?.on('data',part=>{
      stdout+=part.toString();if(stdout.length>5000)child.kill();
    });
    child.stderr?.on('data',part=>{
      stderr+=part.toString();if(stderr.length>5000)child.kill();
    });
    child.on('error',error=>{clearTimeout(timeout);reject(error);});
    child.on('close',code=>{
      clearTimeout(timeout);
      if(code!==0)return reject(new Error('canonical_relay_sender_failed'));
      try{
        const value=JSON.parse(stdout.trim());
        if(value.ok!==true||typeof value.relayId!=='string'||
            !/^[A-Za-z0-9_.:-]{8,100}$/.test(value.relayId))
          throw new Error('relay receipt invalid');
        resolve({ok:true,relayId:value.relayId});
      }catch{reject(new Error('canonical_relay_response_unverified'));}
    });
    child.stdin.end(JSON.stringify({text}));
  });
}
