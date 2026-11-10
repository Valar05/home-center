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
 with urllib.request.urlopen(BASE+'/health',timeout=8) as r:d=json.load(r)
 if d.get('model')!='loaded' or d.get('engine')!='pocket-tts' or d.get('stateSha256',{}).get(PROFILE,'').upper()!=VOICE_SHA:
  raise RuntimeError('Approved whisper model/state mismatch')
 return d
def synth(text):
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
 os.replace(folder/'mix.partial.wav',dest)
 with wave.open(str(dest),'rb') as w:duration=w.getnframes()/w.getframerate()
 receipt={'phase':'rendered_not_delivered','episodeId':ep,'profile':PROFILE,'voiceSha256':VOICE_SHA,'wavPath':str(dest),'wavSha256':sha(dest.read_bytes()),'bytes':dest.stat().st_size,'durationSeconds':round(duration,3),'textSha256':sha(payload),'segments':len(plan),'wordCount':len(text.split())}
 atomic(folder/'receipt.json',receipt);state(folder,**receipt)
def start(ep,source):
 folder=folder_for(ep)
 if folder.exists():
  old=json.loads((folder/'request.json').read_text())
  if source is not None and sha(Path(source).read_bytes())!=old['textSha256']:raise RuntimeError('Episode ID has different source')
  if (folder/'receipt.json').exists():print(json.dumps({'phase':'already_rendered','episodeId':ep}));return
  previous=json.loads((folder/'status.json').read_text())
  if previous.get('phase') in ('launched','rendering'):raise RuntimeError('Previous worker uncertain; do not duplicate launch')
 else:
  check_api();data=Path(source).read_bytes() if source else SAMPLE.encode()
  parse(data.decode('utf-8-sig'));folder.mkdir(parents=True)
  (folder/'transcript.txt').write_bytes(data)
  atomic(folder/'request.json',{'episodeId':ep,'textSha256':sha(data),'voiceSha256':VOICE_SHA})
 (folder/'STOP').unlink(missing_ok=True);state(folder,phase='launched',completed=0)
 log=open(folder/'worker.log','ab',buffering=0)
 try:
  flags=getattr(subprocess,'DETACHED_PROCESS',0)|getattr(subprocess,'CREATE_NEW_PROCESS_GROUP',0)
  proc=subprocess.Popen([sys.executable,str(Path(__file__).resolve()),'work','--episode',ep],cwd=str(folder),stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,close_fds=True,creationflags=flags)
 finally:log.close()
 print(json.dumps(state(folder,pid=proc.pid,phase='launched')))
def main():
 p=argparse.ArgumentParser();p.add_argument('verb',choices=['doctor','start','work','status','resume','stop','receipts']);p.add_argument('--episode',default='RITSU_ASMR_CANARY');p.add_argument('--input');a=p.parse_args();folder=folder_for(a.episode)
 try:
  if a.verb=='doctor':
   h=check_api();print(json.dumps({'doctor':'PASS','engine':h.get('engine'),'voiceSha256':VOICE_SHA,'sampleRate':h.get('sampleRate')}))
  elif a.verb=='start':start(a.episode,a.input)
  elif a.verb=='resume':
   if not folder.exists():raise RuntimeError('No run to resume')
   st=json.loads((folder/'status.json').read_text())
   if st.get('phase') in ('launched','rendering'):raise RuntimeError('Previous worker unresolved')
   start(a.episode,None)
  elif a.verb=='work':
   try:render(a.episode)
   except Exception as e:state(folder,phase='failed',lastError=type(e).__name__+': '+str(e)[:250]);raise
  elif a.verb=='stop':
   if not folder.exists():raise RuntimeError('No run to stop')
   (folder/'STOP').write_text('cooperative stop requested\n');print(json.dumps(state(folder,stopRequested=True)))
  else:
   file='receipt.json' if a.verb=='receipts' else 'status.json'
   print((folder/file).read_text(encoding='utf-8'))
  return 0
 except Exception as e:
  print(json.dumps({'phase':'blocked','error':type(e).__name__+': '+str(e)[:250]}),file=sys.stderr);return 2
if __name__=='__main__':sys.exit(main())
