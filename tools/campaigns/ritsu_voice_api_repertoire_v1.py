import sys
if sys.stdout is None:sys.stdout=open(r'C:\Users\dclar\workspace\ritsu-faster-qwen3-tts\api-warm-headless.stdout.log','a',buffering=1,encoding='utf-8')
if sys.stderr is None:sys.stderr=open(r'C:\Users\dclar\workspace\ritsu-faster-qwen3-tts\api-warm-headless.stderr.log','a',buffering=1,encoding='utf-8')
import json,time,queue,uuid,threading,secrets,urllib.request,shutil,os,hmac
from pathlib import Path
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
ROOT=Path(r'C:\Users\dclar\workspace\ritsu-faster-qwen3-tts')
WEIGHTS=Path(r'C:\Users\dclar\workspace\ritsu-qwen3-tts\models\Qwen3-TTS-12Hz-0.6B-Base')
RELAY=Path(r'C:\Users\dclar\Documents\Codex\Venice\PocketTTS\embodiment_campaign')
AUDIO=Path(r'C:\Users\dclar\workspace\ritsu-chatterbox-turbo\generated')
OUT=ROOT/'ritsu-api-output'
PROFILE_CATALOG=json.loads((ROOT/'ritsu_voice_profiles.json').read_text(encoding='utf-8'))
PROFILE_REGISTRY=PROFILE_CATALOG['profiles']
VOICES=tuple(PROFILE_REGISTRY.keys())+('warm',)
REFS=Path(r'C:\Users\dclar\workspace\ritsu-expresso-auditions')
OUT.mkdir(exist_ok=True)
tok=ROOT/'ritsu-api-token.txt'
if not tok.exists():tok.write_text(secrets.token_urlsafe(32),encoding='utf-8')
TOKEN=tok.read_text().strip()
jobs={};q=queue.Queue(maxsize=12);lock=threading.RLock();state={'model':'unloaded','error':None};model=None
def worker():
 global model
 while True:
  jid=q.get()
  try:
   with lock:jobs[jid]['state']='generating'
   if model is None:
    state['model']='loading'
    import torch
    from faster_qwen3_tts import FasterQwen3TTS
    if not torch.cuda.is_available():raise RuntimeError('CUDA unavailable')
    model=FasterQwen3TTS.from_pretrained(str(WEIGHTS),device='cuda',dtype=torch.bfloat16,attn_implementation='sdpa',max_seq_len=512,local_files_only=True)
    state['model']='loaded'
   import soundfile as sf
   t=time.monotonic()
   with lock:job=dict(jobs[jid])
   chosen=job['speaker']
   if chosen=='warm':
    ref_audio=AUDIO/'ritsu-turbo-maxwarm-20261022.wav'
    ref_text=(AUDIO/'ritsu-turbo-maxwarm-20261022.txt').read_text(encoding='utf-8').replace('[chuckle]','').strip()
    shift=0
   else:
    profile=PROFILE_REGISTRY[chosen]
    ref_audio=REFS/profile['referenceFile']
    ref_text=profile['referenceText']
    shift=int(profile['pitchSemitones'])
   if not ref_audio.is_file():raise FileNotFoundError('Registered reference is unavailable: '+chosen)
   clips,sr=model.generate_voice_clone(text=job['text'],language='English',ref_audio=str(ref_audio),ref_text=ref_text,xvec_only=False,max_new_tokens=384)
   if shift:
    import numpy as np
    import librosa
    clips[0]=librosa.effects.pitch_shift(np.asarray(clips[0],dtype=np.float32),sr=sr,n_steps=shift)
   path=OUT/(jid+'.wav');sf.write(str(path),clips[0],sr,subtype='PCM_16')
   with lock:jobs[jid].update(state='completed',generation_seconds=round(time.monotonic()-t,3),audio_seconds=round(len(clips[0])/sr,3),bytes=path.stat().st_size)
  except Exception as e:
   state['model']='error';state['error']=str(e)[:200]
   with lock:jobs[jid].update(state='failed',error=str(e)[:200])
  finally:q.task_done()
threading.Thread(target=worker,daemon=True).start()
jobs['__boot_prewarm__']={'id':'__boot_prewarm__','state':'queued','text':'Hello, darling.','speaker':'warm','delivery':None}
q.put_nowait('__boot_prewarm__')
class Handler(BaseHTTPRequestHandler):
 def send(self,status,data):
  raw=json.dumps(data).encode()
  self.send_response(status);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(raw)));self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(raw)
 def auth(self):
  # API authentication: bearer token only
  if not hmac.compare_digest(self.headers.get('Authorization',''),'Bearer '+TOKEN):
   self.send(401,{'error':'unauthorized'});return False
  return True
 def body(self):
  n=int(self.headers.get('Content-Length','0'))
  if n<1 or n>4096:raise ValueError('invalid body size')
  obj=json.loads(self.rfile.read(n))
  if not isinstance(obj,dict):raise ValueError('expected object')
  return obj
 def do_GET(self):
  if not self.auth():return
  p=self.path.split('?')[0]
  if p=='/v1/health':return self.send(200,{'ok':True,'model':state['model'],'error':state['error'],'queue':q.qsize()})
  if p=='/v1/voices':return self.send(200,{'speakers':VOICES,'default':PROFILE_CATALOG['defaultProfile'],'repertoireVersion':PROFILE_CATALOG['version'],'profiles':{name:{'status':entry['status'],'pitchSemitones':entry['pitchSemitones']} for name,entry in PROFILE_REGISTRY.items()}})
  if p.startswith('/v1/jobs/'):
   jid=p.rsplit('/',1)[-1]
   with lock:item=jobs.get(jid)
   return self.send(200,item) if item else self.send(404,{'error':'unknown job'})
  return self.send(404,{'error':'not found'})
 def do_POST(self):
  if not self.auth():return
  try:
   obj=self.body();p=self.path.split('?')[0]
   if p=='/v1/speak':
    if set(obj)-{'text','speaker'}:raise ValueError('unknown fields')
    s=obj.get('speaker','warm');t=obj.get('text')
    if s not in VOICES:raise ValueError('invalid voice')
    if not isinstance(t,str) or not t.strip() or len(t)>450:raise ValueError('invalid text')
    if q.full():return self.send(429,{'error':'queue full'})
    jid=uuid.uuid4().hex
    with lock:jobs[jid]={'id':jid,'state':'queued','text':t,'speaker':s,'delivery':None}
    q.put_nowait(jid);return self.send(202,jobs[jid])
   if p=='/v1/deliver':
    if set(obj)!={'job_id'}:raise ValueError('job_id only')
    jid=obj['job_id']
    with lock:j=jobs.get(jid)
    if not j or j['state']!='completed':raise ValueError('job not completed')
    if j.get('delivery'):return self.send(200,j['delivery'])
    src=OUT/(jid+'.wav')
    if not src.is_file():raise ValueError('audio missing')
    name='ritsu-api-'+jid+'.wav'
    shutil.copyfile(src,AUDIO/name)
    key=(RELAY/'relay-token.txt').read_text().strip()
    data=json.dumps({'text':'__TURBO_WAV__:'+name,'character':'ritsu'}).encode()
    req=urllib.request.Request('http://127.0.0.1:19643/enqueue',data=data,headers={'Authorization':'Bearer '+key,'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=15) as resp:receipt=json.load(resp)
    if not receipt.get('id'):raise RuntimeError('relay receipt missing')
    with lock:
     jobs[jid]['delivery']={'state':'enqueued','relay_id':receipt['id']}
     result=jobs[jid]['delivery']
    return self.send(200,result)
   self.send(404,{'error':'not found'})
  except (ValueError,KeyError) as e:self.send(400,{'error':str(e)[:150]})
  except Exception as e:self.send(500,{'error':str(e)[:150]})
if __name__=='__main__':
 print('Ritsu Voice API listening on 127.0.0.1:19645',flush=True)
 ThreadingHTTPServer(('127.0.0.1',19645),Handler).serve_forever()
