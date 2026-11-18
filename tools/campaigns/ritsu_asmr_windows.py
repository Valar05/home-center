#!/usr/bin/env python3
"""Offline Pocket Ritsu ASMR renderer. Never sends audio to phone relay."""
import argparse, datetime, hashlib, io, json, os, re, subprocess, sys, time, urllib.request, wave
from pathlib import Path
ROOT=Path(os.environ.get('LOCALAPPDATA',str(Path.home())))/'RitsuASMR'
RUNS=ROOT/'runs'
PROFILE='whisper'
VOICE_SHA='B99EB2E16612E8B8C3E3A96F74BD631676CC79071779537FD94C564DB5796BE5'
BASE='http://127.0.0.1:10205'
SAMPLE='The room is quiet now. The last little sound of the day has settled into the carpet.\n\n[Pause:1500]\n\nThere. You can hear the soft rustling of paper, and the distant rain at the window.'
def sha(b):return hashlib.sha256(b).hexdigest()
DREW_STATE_SHA='12F022B4CD21E116640393132BF1F4268E0F6B5F787FB76969E4ACA44FC5BC10'
DREW_CONFIG_SHA='D04489AB5EA5822660E82FE5D5F2207C47C5958BCA8CBB4C8E215BA3DB2ED944'
DREW_ROOT=ROOT.parent/'DrewVoice'/'factory-v1'/'F2D451E6BF4FE2CDD6F8B2AFBE0D7B32E04E323463228FEAC1D187A27D08BD79'
V2_SHA='0141A450D8A370495D84755B4E620A718CB955F1139643F62F7C5CD147515FF7'
V2_PATH=ROOT.parent/'RitsuWhisperV2'/'factory-v1'/'65E99200D19FD2F021F972CD3EAFF3D33F440D8BD78131E243876AA8CE673FA7'/'ritsu-whisper-v2.safetensors'
CLEAN_PAIR=ROOT.parent/'ASMRDeepCleanPair'/'factory-v1'
CLEAN_DREW_SHA='DA4D803B4F1FF35CEE909D533B978969B78AEC51178EC88C82D8883383293268'
CLEAN_DREW_CONFIG='396F91083E773062C7BA27C044FB57362D35AA01070E4DBA12699C0ADB965233'
CLEAN_RITSU_SHA='F6A787F1D58D11694676A2A4D44A89840F77B0D56A0585A5FB4DAC52F0C1FE97'
CLEAN_DREW_ROOT=CLEAN_PAIR/'drew-whisper-clean-v2'
CLEAN_RITSU_PATH=CLEAN_PAIR/'ritsu-whisper-clean-v3'/'voice.safetensors'
DREW_MODEL=None
DREW_STATE=None
def select_voice(ep):
 global PROFILE,VOICE_SHA,DREW_ROOT,DREW_STATE_SHA,DREW_CONFIG_SHA,V2_PATH,V2_SHA
 if ep.startswith('DREW_CLEAN_DARK_VELVET_'):
  PROFILE='dark-velvet';VOICE_SHA=DREW_STATE_SHA=CLEAN_DREW_SHA;DREW_ROOT=CLEAN_DREW_ROOT;DREW_CONFIG_SHA=CLEAN_DREW_CONFIG
 elif ep.startswith('RITSU_WHISPER_V3_'):
  PROFILE='whisper-v3';VOICE_SHA=V2_SHA=CLEAN_RITSU_SHA;V2_PATH=CLEAN_RITSU_PATH
 elif ep.startswith('DREW_DARK_VELVET_'):
  PROFILE='dark-velvet';VOICE_SHA=DREW_STATE_SHA
 elif ep.startswith('RITSU_WHISPER_V2_'):
  PROFILE='whisper-v2';VOICE_SHA=V2_SHA
def drew_voice_path():
 return DREW_ROOT/('voice.safetensors' if DREW_STATE_SHA==CLEAN_DREW_SHA else 'drew-whisper.safetensors')
def drew_check():
 for name,h in [(drew_voice_path().name,DREW_STATE_SHA),('profiles.json',DREW_CONFIG_SHA)]:
  if sha((DREW_ROOT/name).read_bytes()).upper()!=h:raise RuntimeError('Drew voice/preset identity mismatch')
 return {'engine':'pocket-tts','model':'offline_conditioning_verified','sampleRate':24000}
def v2_check():
 if sha(V2_PATH.read_bytes()).upper()!=V2_SHA:raise RuntimeError('Whisper V2 candidate state mismatch')
 return {'engine':'pocket-tts','model':'offline_conditioning_verified','sampleRate':24000}
def drew_synth(text):
 global DREW_MODEL,DREW_STATE
 import numpy as np
 if DREW_MODEL is None:
  if PROFILE in ('whisper-v2','whisper-v3'):v2_check()
  else:drew_check()
  os.environ['HF_HUB_OFFLINE']='1';os.environ['TRANSFORMERS_OFFLINE']='1'
  from pocket_tts import TTSModel
  DREW_MODEL=TTSModel.load_model(language='english')
  DREW_STATE=DREW_MODEL.get_state_for_audio_prompt(str(V2_PATH if PROFILE in ('whisper-v2','whisper-v3') else drew_voice_path()))
 if int(DREW_MODEL.config.mimi.sample_rate)!=24000:raise RuntimeError('Drew sample rate mismatch')
 signal=DREW_MODEL.generate_audio(model_state=DREW_STATE,text_to_generate=text)
 pcm=np.asarray(signal.detach().cpu().float().numpy(),dtype=np.float32).reshape(-1)
 if not len(pcm) or not np.isfinite(pcm).all() or np.max(np.abs(pcm))>=2:raise RuntimeError('Drew audio invalid')
 b=io.BytesIO()
 with wave.open(b,'wb') as w:
  w.setnchannels(1);w.setsampwidth(2);w.setframerate(24000)
  w.writeframes(np.rint(np.clip(pcm,-1,1-1/32768)*32768).astype('<i2').tobytes())
 return b.getvalue()
def drew_mix(folder):
 import shutil
 drew_check()
 cfg=json.loads((DREW_ROOT/'profiles.json').read_text(encoding='utf-8'))
 if cfg['voiceStateSha256']!=DREW_STATE_SHA:raise RuntimeError('Preset voice mismatch')
 exe=shutil.which('ffmpeg')
 if not exe:raise RuntimeError('FFmpeg missing')
 src=folder/'mix.partial.wav';dst=folder/'mix.processed.partial.wav'
 p=subprocess.run([exe,'-hide_banner','-nostdin','-v','error','-y','-i',str(src),'-af',cfg['profiles']['dark-velvet']['filter'],'-ac','1','-ar','24000','-c:a','pcm_s16le',str(dst)],capture_output=True,text=True,timeout=600)
 if p.returncode:raise RuntimeError('Dark Velvet DSP failed: '+p.stderr[-220:])
 with wave.open(str(dst),'rb') as w:
  if (w.getnchannels(),w.getsampwidth(),w.getframerate())!=(1,2,24000) or not w.getnframes():raise RuntimeError('DSP output invalid')
 return dst
def atomic(p,v):
 p.parent.mkdir(parents=True,exist_ok=True);t=p.with_suffix(p.suffix+'.tmp')
 with t.open('w',encoding='utf-8') as f:
  json.dump(v,f,indent=2);f.flush();os.fsync(f.fileno())
 os.replace(t,p)
def state(folder,**kw):
 try:old=json.loads((folder/'status.json').read_text(encoding='utf-8'))
 except (ValueError,OSError):old={}
 old.update(kw);old['updatedUtc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
 atomic(folder/'status.json',old);return old
def folder_for(ep):
 if not re.fullmatch(r'[A-Za-z0-9_-]{1,64}',ep):raise ValueError('Unsafe episode ID')
 return RUNS/ep
def parse(text):
 segments=[]
 for para in re.split(r'\n\s*\n',text.replace('\r\n','\n').strip()):
  para=para.strip()
  if not para:continue
  m=re.fullmatch(r'\[(?:Pause|Long gentle pause|Final long gentle silence)(?::(\d{1,5}))?\]',para,re.I)
  if m:
   ms=int(m.group(1)) if m.group(1) else (4000 if ('long' in para.lower() or 'final' in para.lower()) else 1200)
   if ms>30000:raise ValueError('Pause too long')
   segments.append(('pause',ms));continue
  if para.startswith('[') and para.endswith(']'):raise ValueError('Unknown direction: '+para[:65])
  if len(para)>450:raise ValueError('Passage over 450 characters; author coherent shorter passages')
  segments.append(('speech',para))
 if not any(k=='speech' for k,v in segments):raise ValueError('No speech')
 return segments
def check_api():
 if PROFILE=='dark-velvet':return drew_check()
 if PROFILE in ('whisper-v2','whisper-v3'):return v2_check()
 try:
  with urllib.request.urlopen(BASE+'/health',timeout=8) as r:d=json.load(r)
 except (OSError, ValueError) as e:
  raise RuntimeError('POCKET_API_UNREACHABLE at 127.0.0.1:10205. SSH succeeded; inspect existing Windows scheduled task Ritsu Pocket Repertoire Watchdog and Pocket supervisor, without starting a replacement engine. Cause: '+str(e)[:140]) from e
 if d.get('model')!='loaded' or d.get('engine')!='pocket-tts' or d.get('stateSha256',{}).get(PROFILE,'').upper()!=VOICE_SHA:
  raise RuntimeError('Approved whisper model/state mismatch')
 return d
def inspect_watchdog():
 """Read only: distinguish missing task, running supervisor, and missing listener."""
 name='Ritsu Pocket Repertoire Watchdog'
 ps=r"""
$ErrorActionPreference='Stop'
$task=Get-ScheduledTask -TaskName 'Ritsu Pocket Repertoire Watchdog' -ErrorAction SilentlyContinue
$state=$null;$lastResult=$null;$lastRun=$null;$actionPaths=@()
if($task){
 $state=[string]$task.State
 $info=Get-ScheduledTaskInfo -TaskName $task.TaskName -ErrorAction SilentlyContinue
 if($info){$lastResult=$info.LastTaskResult;$lastRun=[string]$info.LastRunTime}
 $actionPaths=@($task.Actions | ForEach-Object { [pscustomobject]@{execute=$_.Execute;arguments=$_.Arguments} })
}
$listener=@(Get-NetTCPConnection -State Listen -LocalPort 10205 -ErrorAction SilentlyContinue | ForEach-Object {$_.OwningProcess} | Sort-Object -Unique)
$related=@(Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object {$_.CommandLine -match 'ritsu_warm_api_supervisor[.]py|ritsu_pocket_repertoire_server_v2[.]py'} | ForEach-Object {[pscustomobject]@{pid=$_.ProcessId;name=$_.Name;commandline='[OMITTED]'}})
[pscustomobject]@{taskPresent=($null -ne $task);taskState=$state;lastResult=$lastResult;lastRun=$lastRun;taskActions=$actionPaths;listenerPids=$listener;relatedProcesses=$related} | ConvertTo-Json -Depth 5 -Compress
"""
 p=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command',ps],capture_output=True,text=True,timeout=25)
 if p.returncode:raise RuntimeError('WATCHDOG_INSPECT_FAILED: '+p.stderr[-180:])
 try:return json.loads(p.stdout)
 except json.JSONDecodeError as e:raise RuntimeError('WATCHDOG_INSPECT_BAD_JSON') from e
def recover_watchdog():
 """Only ask the already installed canonical watchdog task to start; never spawn TTS ourselves."""
 before=inspect_watchdog()
 if not before.get('taskPresent'):raise RuntimeError('WATCHDOG_TASK_MISSING; no bootstrap or substitute authorized')
 if before.get('listenerPids'):raise RuntimeError('PORT_ALREADY_LISTENING; use doctor to verify model')
 if before.get('relatedProcesses'):raise RuntimeError('POCKET_OR_SUPERVISOR_PROCESS_ALREADY_PRESENT; inspect before requesting another launch')
 if before.get('taskState') in ('Running','Queued'):raise RuntimeError('WATCHDOG_ALREADY_RUNNING; not dispatching duplicate')
 if before.get('taskState') not in ('Ready',):raise RuntimeError('WATCHDOG_NOT_READY: '+str(before.get('taskState')))
 proc=subprocess.run(['schtasks.exe','/run','/tn','Ritsu Pocket Repertoire Watchdog'],capture_output=True,text=True,timeout=15)
 if proc.returncode:raise RuntimeError('WATCHDOG_TASK_START_REFUSED: '+proc.stderr[-180:])
 # The task was requested, not proof Pocket loaded: bounded verification required.
 for attempt in range(10):
  time.sleep(2)
  try:return {'recovery':'existing_watchdog_verified','doctor':check_api(),'before':before}
  except RuntimeError as e:
   if 'POCKET_API_UNREACHABLE' not in str(e):raise
 raise RuntimeError('WATCHDOG_REQUESTED_BUT_POCKET_NOT_READY; inspect without dispatching a duplicate')
def synth(text):
 if PROFILE in ('dark-velvet','whisper-v2','whisper-v3'):return drew_synth(text)
 data=json.dumps({'text':text,'profile':PROFILE}).encode()
 req=urllib.request.Request(BASE+'/tts',data=data,headers={'Content-Type':'application/json'},method='POST')
 with urllib.request.urlopen(req,timeout=240) as r:
  if r.headers.get('X-TTS-Engine')!='pocket-tts' or r.headers.get('X-Ritsu-Voice-SHA256','').upper()!=VOICE_SHA:raise RuntimeError('Returned voice identity mismatch')
  audio=r.read(12*1024*1024+1)
 if len(audio)>12*1024*1024:raise RuntimeError('Segment exceeds maximum size')
 with wave.open(io.BytesIO(audio),'rb') as w:
  if (w.getnchannels(),w.getsampwidth(),w.getframerate())!=(1,2,24000) or not w.getnframes():raise RuntimeError('Invalid Pocket WAV')
 return audio
def render(ep):
 folder=folder_for(ep);payload=(folder/'transcript.txt').read_bytes()
 text=payload.decode('utf-8-sig');plan=parse(text);request=json.loads((folder/'request.json').read_text())
 if request['textSha256']!=sha(payload):raise RuntimeError('Transcript changed after commissioning')
 check_api();state(folder,phase='rendering',total=len(plan),lastError=None)
 with wave.open(str(folder/'mix.partial.wav'),'wb') as out:
  out.setnchannels(1);out.setsampwidth(2);out.setframerate(24000)
  for i,(kind,value) in enumerate(plan):
   if (folder/'STOP').exists():state(folder,phase='stopped',completed=i);return
   if kind=='pause':out.writeframes(b'\0\0'*(24000*value//1000))
   else:
    path=folder/('segment-%04d.wav'%i);meta=folder/('segment-%04d.json'%i)
    key=sha((VOICE_SHA+'\0'+value).encode())
    valid=False
    if path.exists() and meta.exists():
     try:
      m=json.loads(meta.read_text());valid=m.get('key')==key and m.get('wavSha256')==sha(path.read_bytes())
     except (OSError,ValueError):pass
    if not valid:
     if path.exists() or meta.exists():raise RuntimeError('Ambiguous or corrupted cached segment '+str(i))
     audio=synth(value)
     with path.open('xb') as f:f.write(audio);f.flush();os.fsync(f.fileno())
     atomic(meta,{'key':key,'wavSha256':sha(audio),'profile':PROFILE,'voiceSha256':VOICE_SHA})
    with wave.open(str(path),'rb') as clip:
     if (clip.getnchannels(),clip.getsampwidth(),clip.getframerate())!=(1,2,24000):raise RuntimeError('Cached audio format mismatch')
     out.writeframes(clip.readframes(clip.getnframes()))
   state(folder,phase='rendering',completed=i+1)
 dest=folder/(ep+'.wav')
 if dest.exists():raise RuntimeError('Output collision: refusing overwrite')
 os.replace(drew_mix(folder) if PROFILE=='dark-velvet' else folder/'mix.partial.wav',dest)
 with wave.open(str(dest),'rb') as w:duration=w.getnframes()/w.getframerate()
 receipt={'phase':'rendered_not_delivered','episodeId':ep,'profile':PROFILE,'voiceSha256':VOICE_SHA,'wavPath':str(dest),'wavSha256':sha(dest.read_bytes()),'bytes':dest.stat().st_size,'durationSeconds':round(duration,3),'textSha256':sha(payload),'segments':len(plan),'wordCount':len(text.split()),'sourceCommit':os.environ.get('RITSU_ASMR_SOURCE_COMMIT',''),'rendererSha256':sha(Path(__file__).read_bytes())}
 if PROFILE=='dark-velvet':receipt['presetSha256']=DREW_CONFIG_SHA
 atomic(folder/'receipt.json',receipt);state(folder,**receipt)
def task_name(ep):
 return 'RitsuASMR-Offline-'+ep
def task_command(ep,operation,program=None):
 # Task action is immutable per launch, on behalf of the current Windows user.
 # Never use SYSTEM, stored passwords, or a task belonging to another subsystem.
 prefix="$ErrorActionPreference='Stop';$n='"+task_name(ep)+"';"
 common=r"""
$t=Get-ScheduledTask -TaskName $n -TaskPath '\' -ErrorAction SilentlyContinue
if($t){
 $a=@($t.Actions)
 if($a.Count -ne 1 -or $a[0].Arguments -notmatch ('ritsu_asmr_windows[.]py" work --episode '+[regex]::Escape($ep)+'$') -or $a[0].Arguments -notmatch '[\\/]RitsuASMR[\\/]code[\\/]'){
  throw 'TASK_IDENTITY_MISMATCH'
 }
}
"""
 # $ep is tightly validated by folder_for; file paths are quoted as literal data.
 def q(x):return "'"+str(x).replace("'","''")+"'"
 prefix+="$ep="+q(ep)+";"
 if operation=='query':
  body=r"""
 $rows=@(Get-CimInstance Win32_Process | Where-Object {
  $_.Name -match '^python(w)?[.]exe$' -and $_.CommandLine -match 'ritsu_asmr_windows[.]py' -and $_.CommandLine -match ('\bwork\s+--episode\s+'+[regex]::Escape($ep)+'(?:\s|$)')
 } | ForEach-Object {$_.ProcessId})
 $st=if($t){[string]$t.State}else{'Missing'}
 [pscustomobject]@{taskState=$st;workerPids=$rows}|ConvertTo-Json -Compress
"""
 elif operation=='launch':
  body="$exe="+q(sys.executable)+";$program="+q(program)+";"+r"""
 if($t -and [string]$t.State -in @('Running','Queued')){throw 'TASK_ALREADY_ACTIVE'}
 $action=New-ScheduledTaskAction -Execute $exe -Argument ('"'+$program+'" work --episode '+$ep) -WorkingDirectory (Split-Path -Parent $program)
 $principal=New-ScheduledTaskPrincipal -UserId ([Security.Principal.WindowsIdentity]::GetCurrent().Name) -LogonType Interactive -RunLevel Limited
 $settings=New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Hours 12) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
 Register-ScheduledTask -TaskName $n -TaskPath '\' -Action $action -Principal $principal -Settings $settings -Force | Out-Null
 Start-ScheduledTask -TaskName $n -TaskPath '\'
 Write-Output '{"taskRequested":true}'
"""
 elif operation=='stop':
  body=r"""
 if($t -and [string]$t.State -in @('Running','Queued')){Stop-ScheduledTask -TaskName $n -TaskPath '\'}
 Write-Output '{"stopRequested":true}'
"""
 else:raise ValueError('Unknown task operation')
 out=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command',prefix+common+body],capture_output=True,text=True,timeout=45)
 if out.returncode:raise RuntimeError('ASMR_TASK_'+operation.upper()+'_FAILED: '+(out.stderr or out.stdout)[-350:])
 return json.loads(out.stdout)
def worker_active(ep):
 row=task_command(ep,'query')
 return row.get('taskState') in ('Running','Queued') or bool(row.get('workerPids')),row
def heartbeat(folder,done):
 while not done.is_set():
  atomic(folder/'heartbeat.json',{'pid':os.getpid(),'utc':datetime.datetime.now(datetime.timezone.utc).isoformat()})
  done.wait(5)
def run_worker(ep):
 import contextlib, threading, traceback
 folder=folder_for(ep);done=threading.Event()
 with (folder/'worker.log').open('a',encoding='utf-8',buffering=1) as log,contextlib.redirect_stdout(log),contextlib.redirect_stderr(log):
  # A scheduled-task launch uses a pinned code path; source provenance survives SSH exit.
  request=json.loads((folder/'request.json').read_text(encoding='utf-8'))
  if request.get('rendererSha256')!=sha(Path(__file__).read_bytes()):
   state(folder,phase='failed',lastError='Pinned worker source digest mismatch');return 2
  os.environ['RITSU_ASMR_SOURCE_COMMIT']=request['sourceCommit']
  print('WORKER_STARTED',os.getpid(),flush=True)
  state(folder,phase='rendering',pid=os.getpid(),lastError=None)
  thread=threading.Thread(target=heartbeat,args=(folder,done),daemon=True);thread.start()
  try:
   render(ep);return 0
  except Exception as e:
   traceback.print_exc()
   state(folder,phase='failed',lastError=type(e).__name__+': '+str(e)[:300]);return 2
  finally:
   done.set();thread.join(timeout=6)
def start(ep,source):
 # Serialize start/resume across independent SSH sessions on Windows.
 import msvcrt
 folder_for(ep)
 ROOT.mkdir(parents=True,exist_ok=True)
 with (ROOT/('launch-'+ep+'.lock')).open('a+b') as lock:
  lock.seek(0);lock.write(b'0');lock.flush();lock.seek(0)
  try:msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
  except OSError as e:raise RuntimeError('Another launch request owns this episode') from e
  try:return start_locked(ep,source)
  finally:lock.seek(0);msvcrt.locking(lock.fileno(),msvcrt.LK_UNLCK,1)
def start_locked(ep,source):
 folder=folder_for(ep)
 active,row=worker_active(ep)
 if active:raise RuntimeError('Previous worker is active; use status or stop')
 check_api()
 if folder.exists():
  old=json.loads((folder/'request.json').read_text(encoding='utf-8'))
  if old.get('voiceSha256')!=VOICE_SHA:raise RuntimeError('Episode voice changed')
  if source is not None and sha(Path(source).read_bytes())!=old['textSha256']:raise RuntimeError('Episode ID has different source')
  if (folder/'receipt.json').exists():
   print((folder/'receipt.json').read_text(encoding='utf-8'));return
  if (folder/(ep+'.wav')).exists():raise RuntimeError('Unreceipted final WAV; inspect without overwriting')
  data=(folder/'transcript.txt').read_bytes()
  if sha(data)!=old['textSha256']:raise RuntimeError('Saved transcript digest mismatch')
 else:
  data=Path(source).read_bytes() if source else SAMPLE.encode()
  parse(data.decode('utf-8-sig'));folder.mkdir(parents=True)
  (folder/'transcript.txt').write_bytes(data)
  old={'episodeId':ep,'textSha256':sha(data),'voiceSha256':VOICE_SHA}
 parse(data.decode('utf-8-sig'))
 old.update(sourceCommit=os.environ.get('RITSU_ASMR_SOURCE_COMMIT',''),rendererSha256=sha(Path(__file__).read_bytes()))
 if not re.fullmatch(r'[0-9a-f]{40}',old['sourceCommit']):raise RuntimeError('Missing pinned source commit')
 atomic(folder/'request.json',old)
 (folder/'STOP').unlink(missing_ok=True)
 (folder/'heartbeat.json').unlink(missing_ok=True)
 state(folder,phase='scheduled',pid=None,lastError=None,taskName=task_name(ep))
 try:task_command(ep,'launch',Path(__file__).resolve())
 except Exception as e:
  # Scheduler can accept a task even when its caller loses the acknowledgement.
  # Never retry automatically without a fresh process/task query.
  raise RuntimeError('Task scheduling not confirmed; inspect status before retry: '+str(e)) from e
 print(json.dumps({'phase':'scheduled','taskName':task_name(ep),'previousWorkerAbsent':True,'renderNotInferred':True}))
def status_report(ep):
 folder=folder_for(ep)
 st=json.loads((folder/'status.json').read_text(encoding='utf-8'))
 active,row=worker_active(ep);st.update(row)
 if (folder/'heartbeat.json').exists():
  beat=json.loads((folder/'heartbeat.json').read_text(encoding='utf-8'))
  st['heartbeatAgeSeconds']=round((datetime.datetime.now(datetime.timezone.utc)-datetime.datetime.fromisoformat(beat['utc'])).total_seconds(),1)
 if not active and st.get('phase') in ('launched','scheduled','rendering'):
  st['recordedPhase']=st['phase'];st['phase']='abandoned'
 if (folder/'worker.log').exists() and st.get('phase') in ('failed','abandoned'):
  st['workerLogTail']=(folder/'worker.log').read_text(encoding='utf-8',errors='replace')[-1200:]
 return st
def stop_worker(ep):
 folder=folder_for(ep)
 if not folder.exists():raise RuntimeError('No run to stop')
 (folder/'STOP').write_text('stop requested\n')
 task_command(ep,'stop')
 for _ in range(10):
  active,row=worker_active(ep)
  if not active:
   if not (folder/'receipt.json').exists():state(folder,phase='stopped',stopRequested=True)
   return status_report(ep)
  time.sleep(1)
 raise RuntimeError('STOP_NOT_CONFIRMED: worker still present; no unrelated process killed')
def main():
 p=argparse.ArgumentParser();p.add_argument('verb',choices=['doctor','inspect','recover','start','work','status','resume','stop','receipts']);p.add_argument('--episode',default='RITSU_ASMR_CANARY');p.add_argument('--input');a=p.parse_args();folder=folder_for(a.episode);select_voice(a.episode)
 try:
  if a.verb=='doctor':
   h=check_api();print(json.dumps({'doctor':'PASS','engine':h.get('engine'),'voiceSha256':VOICE_SHA,'sampleRate':h.get('sampleRate')}))
  elif a.verb=='inspect':print(json.dumps({'inspect':inspect_watchdog()}))
  elif a.verb=='recover':print(json.dumps(recover_watchdog()))
  elif a.verb=='start':start(a.episode,a.input)
  elif a.verb=='resume':
   if not folder.exists():raise RuntimeError('No run to resume')
   start(a.episode,None)
  elif a.verb=='work':return run_worker(a.episode)
  elif a.verb=='stop':print(json.dumps(stop_worker(a.episode)))
  elif a.verb=='status':print(json.dumps(status_report(a.episode)))
  else:print((folder/'receipt.json').read_text(encoding='utf-8'))
  return 0
 except Exception as e:
  print(json.dumps({'phase':'blocked','error':type(e).__name__+': '+str(e)[:250]}),file=sys.stderr);return 2
if __name__=='__main__':sys.exit(main())
