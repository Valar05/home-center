#!/usr/bin/env python3
"""Independent Ritsu Whisper V2 candidate. No live changes or sample speech."""
import os,sys,json,hashlib,shutil,subprocess,tempfile,wave,importlib.metadata
from datetime import datetime,timezone
from pathlib import Path
EXPECTED='65E99200D19FD2F021F972CD3EAFF3D33F440D8BD78131E243876AA8CE673FA7'
SIZE=6336044
NAME='513411__veromarengere__woman-whispering-asmr-02.wav'
ROOT=Path(os.environ['LOCALAPPDATA'])/'RitsuWhisperV2'
RUN=ROOT/'factory-v1'/EXPECTED
SOURCE_URL='https://freesound.org/people/vero.marengere/sounds/513411/'
FILTER='highpass=f=55,volume=15dB'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest().upper()
def atomic(p,row):
 t=p.with_suffix('.tmp');t.write_text(json.dumps(row,indent=2),encoding='utf-8');os.replace(t,p)
def status(phase,**fields):
 r=dict(phase=phase,updatedUtc=datetime.now(timezone.utc).isoformat(),sourceSha256=EXPECTED,sourceUrl=SOURCE_URL,recordingLicense='CC0',speechRendered=False,liveRitsuModified=False,**fields)
 atomic(RUN/'status.json',r);return r
def source():
 # Look by bytes, not name: Android native share sometimes removes extension.
 base=Path.home()/'Downloads'
 for root in (base,base/'Taildrop',base/'Tailscale'):
  if not root.is_dir():continue
  for p in root.iterdir():
   if p.is_file() and p.stat().st_size==SIZE and sha(p)==EXPECTED:return p
 raise RuntimeError('EXACT_REFERENCE_NOT_FOUND; send original via Taildrop, no SSH fallback')
def work():
 import msvcrt
 RUN.mkdir(parents=True,exist_ok=True)
 with (RUN/'worker.lock').open('a+b') as lock:
  lock.seek(0);lock.write(b'0');lock.flush();lock.seek(0)
  try:msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
  except OSError:raise RuntimeError('FACTORY_ALREADY_RUNNING')
  try:
   receipt=RUN/'receipt.json'
   if receipt.exists():
    r=json.loads(receipt.read_text(encoding='utf-8'))
    for name,digest in r['artifacts'].items():
     if sha(RUN/name)!=digest:raise RuntimeError('Artifact mismatch; no overwrite')
    return r
   status('preflight')
   src=source();ff=shutil.which('ffmpeg')
   if not ff:raise RuntimeError('FFMPEG_NOT_FOUND')
   os.environ['HF_HUB_OFFLINE']='1';os.environ['TRANSFORMERS_OFFLINE']='1'
   from pocket_tts import TTSModel,export_model_state
   from safetensors import safe_open
   version=importlib.metadata.version('pocket-tts')
   with tempfile.TemporaryDirectory(dir=RUN,prefix='candidate-') as tmp:
    t=Path(tmp);raw=t/'original.wav';clean=t/'reference.wav';voice=t/'ritsu-whisper-v2.safetensors'
    shutil.copyfile(src,raw)
    if sha(raw)!=EXPECTED:raise RuntimeError('Source changed')
    status('preparing_reference')
    p=subprocess.run([ff,'-hide_banner','-nostdin','-v','error','-i',str(raw),'-af',FILTER,'-ac','1','-ar','24000','-c:a','pcm_s16le',str(clean)],capture_output=True,text=True,timeout=90)
    if p.returncode:raise RuntimeError('FFmpeg preparation failed: '+p.stderr[-200:])
    with wave.open(str(clean),'rb') as w:
     if (w.getnchannels(),w.getsampwidth(),w.getframerate())!=(1,2,24000) or not w.getnframes():raise RuntimeError('Invalid reference')
     duration=w.getnframes()/24000
    status('exporting_conditioning',referenceSeconds=duration,pocketVersion=version)
    model=TTSModel.load_model(language='english')
    state=model.get_state_for_audio_prompt(str(clean))
    export_model_state(state,str(voice))
    with safe_open(str(voice),framework='pt',device='cpu') as f:
     if not list(f.keys()):raise RuntimeError('Empty voice state')
    model.get_state_for_audio_prompt(str(voice))
    names=['original.wav','reference.wav','ritsu-whisper-v2.safetensors']
    hashes={n:sha(t/n) for n in names}
    for n,h in hashes.items():
     if (RUN/n).exists() and sha(RUN/n)!=h:raise RuntimeError('Artifact collision: '+n)
    for n in names:
     if not (RUN/n).exists():os.rename(t/n,RUN/n)
    if any(sha(RUN/n)!=h for n,h in hashes.items()):raise RuntimeError('Final readback mismatch')
    r=status('voice_state_ready_not_auditioned',referenceSeconds=duration,pocketVersion=version,filter=FILTER,artifacts=hashes,directory=str(RUN))
    atomic(receipt,r);return r
  except Exception as e:
   status('blocked',error=type(e).__name__+': '+str(e)[:300]);raise
  finally:
   lock.seek(0);msvcrt.locking(lock.fileno(),msvcrt.LK_UNLCK,1)
if __name__=='__main__':
 if sys.argv[1:]!=['work']:raise SystemExit('Expected work')
 print(json.dumps(work()))
