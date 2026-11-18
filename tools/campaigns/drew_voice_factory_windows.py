#!/usr/bin/env python3
"""Offline Drew voice state factory; no speech generation, no live service edits."""
import argparse, hashlib, json, os, shutil, subprocess, sys, tempfile, wave
from pathlib import Path
from datetime import datetime, timezone
import importlib.metadata

ROOT=Path(os.environ['LOCALAPPDATA'])/'DrewVoice'
EXPECTED='F2D451E6BF4FE2CDD6F8B2AFBE0D7B32E04E323463228FEAC1D187A27D08BD79'
PHONE_SHA='8EA2740EC7C77BA32A22E4AF5F9DE9B3FC2E26B57BD839F599B8AEA18BF08D61'
SIZE=179547
RUN=ROOT/'factory-v1'/EXPECTED
PRESETS={
 'natural':{'filter':'anull','semitones':0},
 'dark-velvet':{'filter':'rubberband=pitch=0.890898718:formant=preserved,highpass=f=32,bass=f=115:g=4,equalizer=f=65:t=q:w=0.9:g=2,acompressor=threshold=0.10:ratio=2:attack=20:release=150,alimiter=limit=0.89:level=false','semitones':-2},
 'midnight-purr':{'filter':'rubberband=pitch=0.793700526:tempo=0.95:formant=preserved,highpass=f=28,bass=f=95:g=6,equalizer=f=50:t=q:w=1:g=4,acompressor=threshold=0.08:ratio=2.5:attack=25:release=180,alimiter=limit=0.89:level=false','semitones':-4},
 'porcelain':{'filter':'rubberband=pitch=1.189207115:formant=shifted,highpass=f=100,treble=f=3500:g=2,alimiter=limit=0.89:level=false','semitones':3}
}
CLEAN='highpass=f=65,afftdn=nf=-45,alimiter=limit=0.89:level=false'

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest().upper()
def now():return datetime.now(timezone.utc).isoformat()
def atomic(p,obj):
 t=p.with_name(p.name+'.tmp');t.write_text(json.dumps(obj,indent=2),encoding='utf-8');os.replace(t,p)
def report(phase,**kw):
 row={'phase':phase,'updatedUtc':now(),'sourceSha256':EXPECTED,'phoneOriginalSha256':PHONE_SHA,'phoneBytesMatch':False,'speechRendered':False,'liveRitsuModified':False,**kw}
 atomic(RUN/'status.json',row);return row
def cmd(args,timeout=90):
 p=subprocess.run([str(a) for a in args],capture_output=True,text=True,timeout=timeout)
 if p.returncode:raise RuntimeError('Process failed: '+Path(str(args[0])).name+' '+p.stderr[-350:])
 return p.stdout
def ffmpeg():
 exe=shutil.which('ffmpeg')
 if not exe:raise RuntimeError('FFMPEG_NOT_FOUND in existing Windows PATH')
 filters=cmd([exe,'-hide_banner','-filters'])
 if not all(x in filters for x in ('rubberband','afftdn','alimiter','acompressor')):raise RuntimeError('FFMPEG_REQUIRED_FILTERS_MISSING')
 return exe
def source():
 for p in (Path.home()/'Downloads'/'Drew-whisper.m4a',Path.home()/'Downloads'/'Drew-whisper'):
  if p.is_file() and p.stat().st_size==SIZE and sha(p)==EXPECTED:return p
 raise RuntimeError('OWNER_APPROVED_WINDOWS_REFERENCE_MISSING_OR_CHANGED')
def wav_info(p):
 with wave.open(str(p),'rb') as w:
  if (w.getnchannels(),w.getsampwidth(),w.getframerate())!=(1,2,24000) or not w.getnframes():raise RuntimeError('Invalid prepared reference WAV')
  return w.getnframes()/24000
def factory():
 # Windows kernel lock serializes actual workers; safe after process death.
 import msvcrt
 RUN.mkdir(parents=True,exist_ok=True)
 with (RUN/'worker.lock').open('a+b') as lock:
  if lock.tell()==0:lock.write(b'0');lock.flush()
  lock.seek(0)
  try:msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
  except OSError:raise RuntimeError('FACTORY_ALREADY_RUNNING')
  try:
   receipt=RUN/'receipt.json'
   if receipt.exists():
    r=json.loads(receipt.read_text(encoding='utf-8'))
    for name,digest in r['artifacts'].items():
     if sha(RUN/name)!=digest:raise RuntimeError('Existing artifact digest mismatch; preserve files')
    return report('voice_state_ready_not_auditioned',**{k:v for k,v in r.items() if k not in ('phase','updatedUtc','sourceSha256','phoneOriginalSha256','phoneBytesMatch','speechRendered','liveRitsuModified')})
   report('preflight')
   src=source();exe=ffmpeg()
   version=importlib.metadata.version('pocket-tts')
   # Existing cached model only. Never download or install a replacement.
   os.environ['HF_HUB_OFFLINE']='1';os.environ['TRANSFORMERS_OFFLINE']='1'
   from pocket_tts import TTSModel, export_model_state
   from safetensors import safe_open
   with tempfile.TemporaryDirectory(prefix='factory-',dir=RUN) as t:
    t=Path(t);original=t/'original.m4a';shutil.copyfile(src,original)
    if sha(original)!=EXPECTED:raise RuntimeError('Source changed during copy')
    clean=t/'clean.wav'
    report('preparing_reference',pocketVersion=version)
    cmd([exe,'-hide_banner','-nostdin','-v','error','-i',original,'-vn','-af',CLEAN,'-ac','1','-ar','24000','-c:a','pcm_s16le',clean])
    duration=wav_info(clean)
    report('exporting_conditioning',referenceSeconds=duration,pocketVersion=version)
    model=TTSModel.load_model(language='english')
    state=model.get_state_for_audio_prompt(str(clean))
    output=t/'drew-whisper.safetensors'
    export_model_state(state,str(output))
    with safe_open(str(output),framework='pt',device='cpu') as f:
     if not list(f.keys()):raise RuntimeError('Empty voice state')
    # Reload conditioning only; no generate_audio call.
    model.get_state_for_audio_prompt(str(output))
    profiles={'version':1,'status':'provisional DSP; not exact audition reconstruction','voiceStateSha256':sha(output),'referenceFilter':CLEAN,'profiles':PRESETS}
    atomic(t/'profiles.json',profiles)
    names=('original.m4a','clean.wav','drew-whisper.safetensors','profiles.json')
    hashes={n:sha(t/n) for n in names}
    for n,h in hashes.items():
     dest=RUN/n
     if dest.exists() and sha(dest)!=h:raise RuntimeError('Artifact collision: '+n)
    for n in names:
     if not (RUN/n).exists():os.rename(t/n,RUN/n)
    if any(sha(RUN/n)!=h for n,h in hashes.items()):raise RuntimeError('Final artifact readback mismatch')
    row=report('voice_state_ready_not_auditioned',pocketVersion=version,referenceSeconds=duration,artifacts=hashes,profiles=list(PRESETS),directory=str(RUN))
    atomic(receipt,row);return row
  except Exception as e:
   report('blocked',error=type(e).__name__+': '+str(e)[:350]);raise
  finally:
   lock.seek(0);msvcrt.locking(lock.fileno(),msvcrt.LK_UNLCK,1)

def postprocess(profile,source_path,destination):
 src=Path(source_path).resolve();dst=Path(destination).resolve()
 if src==dst or dst.exists():raise RuntimeError('Refuse in-place or overwrite')
 if src.suffix.lower()!='.wav' or dst.suffix.lower()!='.wav':raise RuntimeError('WAV input and output required')
 if not (RUN/'receipt.json').is_file():raise RuntimeError('Factory receipt missing')
 r=json.loads((RUN/'receipt.json').read_text(encoding='utf-8'))
 if sha(RUN/'profiles.json')!=r['artifacts']['profiles.json']:raise RuntimeError('Profile hash mismatch')
 config=json.loads((RUN/'profiles.json').read_text(encoding='utf-8'))
 exe=ffmpeg()
 with tempfile.TemporaryDirectory(dir=dst.parent) as t:
  out=Path(t)/'processed.wav'
  cmd([exe,'-hide_banner','-nostdin','-v','error','-i',src,'-af',config['profiles'][profile]['filter'],'-ac','1','-ar','24000','-c:a','pcm_s16le',out],timeout=600)
  duration=wav_info(out);os.rename(out,dst)
 return {'phase':'postprocessed_not_auditioned','profile':profile,'sha256':sha(dst),'durationSeconds':duration,'path':str(dst)}
def main():
 p=argparse.ArgumentParser();p.add_argument('verb',choices=['work','status','process']);p.add_argument('--profile',choices=PRESETS);p.add_argument('--input');p.add_argument('--output');a=p.parse_args()
 if a.verb=='status':
  f=RUN/'status.json';row=json.loads(f.read_text(encoding='utf-8')) if f.exists() else {'phase':'not_started'}
 elif a.verb=='work':row=factory()
 else:
  if not all((a.profile,a.input,a.output)):p.error('process requires profile, input and output')
  row=postprocess(a.profile,a.input,a.output)
 print(json.dumps(row,ensure_ascii=True))
if __name__=='__main__':main()
