#!/usr/bin/env python3
"""Rebuild independent Pocket voice candidates from exact approved deep-clean WAVs."""
import hashlib,json,os,shutil,subprocess,sys,tempfile,wave,math
from pathlib import Path
from datetime import datetime,timezone
from importlib.metadata import version
ROOT=Path(os.environ['LOCALAPPDATA'])/'ASMRDeepCleanPair'
RUN=ROOT/'factory-v1'
SOURCES={
 'drew-whisper-clean-v2':('drew-whisper-deep-clean.wav',1056812,'24296F90B9B5495A8A263284B50C8C625CFF821035F4498AADC6D687F1651DF0'),
 'ritsu-whisper-clean-v3':('ritsu-whisper-v2-deep-clean.wav',3168044,'EE32917C653AF17AE3A30C6447F97DD9BD4E874F8D4C174A5399DAD0DFFD7255')
}
OLD_DREW=ROOT.parent/'DrewVoice'/'factory-v1'/'F2D451E6BF4FE2CDD6F8B2AFBE0D7B32E04E323463228FEAC1D187A27D08BD79'
OLD_PROFILES_SHA='D04489AB5EA5822660E82FE5D5F2207C47C5958BCA8CBB4C8E215BA3DB2ED944'
OLD_DREW_SHA='12F022B4CD21E116640393132BF1F4268E0F6B5F787FB76969E4ACA44FC5BC10'
OLD_RITSU_SHA='0141A450D8A370495D84755B4E620A718CB955F1139643F62F7C5CD147515FF7'
def sha(p):
 return hashlib.sha256(p.read_bytes()).hexdigest().upper()
def atomic(p,row):
 t=p.with_suffix('.tmp')
 with t.open('w',encoding='utf-8') as f:
  json.dump(row,f,indent=2);f.flush();os.fsync(f.fileno())
 os.replace(t,p)
def status(phase,voices,**kw):
 r={'phase':phase,'updatedUtc':datetime.now(timezone.utc).isoformat(),'voices':voices,'speechRendered':False,'liveRitsuModified':False,**kw}
 atomic(RUN/'status.json',r);return r
def receive_dirs():
 import winreg
 roots=[Path.home()/'Downloads']
 try:
  with winreg.OpenKey(winreg.HKEY_CURRENT_USER,r'Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders') as k:
   value,_=winreg.QueryValueEx(k,'{374DE290-123F-4565-9164-39C4925E467B}')
   roots.append(Path(os.path.expandvars(value)))
 except OSError:pass
 return list(dict.fromkeys(p for r in roots for p in (r,r/'Taildrop',r/'Tailscale')))
def find_source(spec):
 name,size,h=spec
 for root in receive_dirs():
  if not root.is_dir():continue
  for p in root.iterdir():
   if p.is_file() and p.stat().st_size==size and sha(p)==h:return p
 raise RuntimeError('EXACT_TAILDROP_REFERENCE_MISSING: '+name+' SHA256='+h)
def validate_wave(p):
 with wave.open(str(p),'rb') as w:
  if (w.getnchannels(),w.getsampwidth(),w.getframerate())!=(1,2,24000) or not w.getnframes():raise RuntimeError('Invalid Pocket reference PCM')
  return w.getnframes()/24000
def verify_receipt(folder,spec):
 f=folder/'receipt.json'
 if not f.exists():return None
 r=json.loads(f.read_text(encoding='utf-8'))
 if r.get('sourceSha256')!=spec[2]:raise RuntimeError('Existing source receipt differs')
 expected={'original.wav','reference.wav','voice.safetensors'}
 if folder.name.startswith('drew'):expected.add('profiles.json')
 if set(r.get('artifacts',{}))!=expected:raise RuntimeError('Incomplete artifact receipt')
 for name,h in r['artifacts'].items():
  if sha(folder/name)!=h:raise RuntimeError('Existing artifact hash mismatch: '+name)
 return r
def build(name,spec,src,model,ff,export_model_state,safe_open,pocket_version,prior_profiles):
 folder=RUN/name;folder.mkdir(exist_ok=True)
 done=verify_receipt(folder,spec)
 if done:return done
 with tempfile.TemporaryDirectory(prefix='candidate-',dir=folder) as tmp:
  t=Path(tmp);original=t/'original.wav';ref=t/'reference.wav';statefile=t/'voice.safetensors'
  shutil.copyfile(src,original)
  if sha(original)!=spec[2]:raise RuntimeError('Source changed during copy')
  # No second denoise, pitch shift, gain or limiter. Only Pocket format conversion.
  p=subprocess.run([ff,'-hide_banner','-nostdin','-v','error','-i',str(original),'-ac','1','-ar','24000','-c:a','pcm_s16le',str(ref)],capture_output=True,text=True,timeout=90)
  if p.returncode:raise RuntimeError('PCM conversion failed: '+p.stderr[-200:])
  duration=validate_wave(ref)
  state=model.get_state_for_audio_prompt(str(ref))
  export_model_state(state,str(statefile))
  with safe_open(str(statefile),framework='pt',device='cpu') as f:
   if not list(f.keys()):raise RuntimeError('Empty conditioning')
  model.get_state_for_audio_prompt(str(statefile))
  names=['original.wav','reference.wav','voice.safetensors']
  if name.startswith('drew'):
   profiles=dict(prior_profiles)
   profiles['voiceStateSha256']=sha(statefile)
   profiles['referenceFilter']='already deep-cleaned externally; PCM resample only'
   profiles['previousProfilesSha256']=OLD_PROFILES_SHA
   atomic(t/'profiles.json',profiles);names.append('profiles.json')
  hashes={n:sha(t/n) for n in names}
  for n,h in hashes.items():
   if (folder/n).exists() and sha(folder/n)!=h:raise RuntimeError('Artifact collision; preserve existing '+n)
  for n in names:
   if not (folder/n).exists():os.rename(t/n,folder/n)
  if any(sha(folder/n)!=h for n,h in hashes.items()):raise RuntimeError('Final hash readback mismatch')
  row={'phase':'voice_state_ready_not_auditioned','voice':name,'sourceSha256':spec[2],'referenceSeconds':duration,'pocketVersion':pocket_version,'artifacts':hashes,'directory':str(folder),'speechRendered':False}
  atomic(folder/'receipt.json',row);return row
def work():
 import msvcrt
 RUN.mkdir(parents=True,exist_ok=True)
 with (RUN/'worker.lock').open('a+b') as lock:
  lock.seek(0);lock.write(b'0');lock.flush();lock.seek(0)
  msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
  voices={}
  try:
   status('preflight',voices)
   pending={}
   for name,spec in SOURCES.items():
    folder=RUN/name
    done=verify_receipt(folder,spec)
    if done:voices[name]=done
    else:
     src=find_source(spec)
     pending[name]=(spec,src)
     voices[name]={'phase':'reference_verified','sourceSha256':spec[2]}
   if not pending:return status('both_states_ready_not_auditioned',voices)
   profilepath=OLD_DREW/'profiles.json'
   if sha(profilepath)!=OLD_PROFILES_SHA:raise RuntimeError('Existing Drew profile config changed')
   profiles=json.loads(profilepath.read_text(encoding='utf-8'))
   if profiles.get('voiceStateSha256')!=OLD_DREW_SHA:raise RuntimeError('Prior Drew voice binding mismatch')
   if set(profiles.get('profiles',{}))!={'natural','dark-velvet','midnight-purr','porcelain'}:raise RuntimeError('Prior profile set mismatch')
   ff=shutil.which('ffmpeg')
   if not ff:raise RuntimeError('FFMPEG_NOT_FOUND')
   os.environ['HF_HUB_OFFLINE']='1';os.environ['TRANSFORMERS_OFFLINE']='1'
   from pocket_tts import TTSModel,export_model_state
   from safetensors import safe_open
   pv=version('pocket-tts')
   if pv!='2.1.0':raise RuntimeError('Expected proven Pocket 2.1.0, got '+pv)
   status('loading_existing_pocket',voices)
   model=TTSModel.load_model(language='english')
   for name,(spec,src) in pending.items():
    voices[name]={'phase':'exporting_conditioning','sourceSha256':spec[2]}
    status('exporting_conditioning',voices)
    voices[name]=build(name,spec,src,model,ff,export_model_state,safe_open,pv,profiles)
    status('conditioning_checkpoint',voices)
   row=status('both_states_ready_not_auditioned',voices,previousDrewState=OLD_DREW_SHA,previousRitsuState=OLD_RITSU_SHA,transport='Taildrop only; exact reference bytes verified')
   atomic(RUN/'receipt.json',row)
   return row
  except Exception as e:
   status('blocked',voices,error=type(e).__name__+': '+str(e)[:350])
   raise
  finally:
   lock.seek(0);msvcrt.locking(lock.fileno(),msvcrt.LK_UNLCK,1)
if __name__=='__main__':
 if sys.argv[1:]!=['work']:raise SystemExit('Expected work')
 print(json.dumps(work()))
