import argparse,json,pathlib,re,time,urllib.request
ROOT=pathlib.Path(__file__).parent
BASE='http://127.0.0.1:10205'
key=(ROOT/'ritsu-api-token.txt').read_text().strip()
http=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def call(method,path,obj=None):
 data=None if obj is None else json.dumps(obj).encode()
 req=urllib.request.Request(BASE+path,data=data,method=method,headers={'Authorization':'Bearer '+key,'Content-Type':'application/json'})
 with http.open(req,timeout=20) as response:return json.load(response)
def chunks(text,limit=350):
 out=[]; buf=''
 for sentence in re.split(r'(?<=[.!?])\s+',text.strip()):
  for word in sentence.split():
   if len(word)>limit:raise ValueError('An unsplittable word exceeds speech chunk size')
   if len(buf)+len(word)+1>limit:
    out.append(buf);buf=''
   buf=(buf+' '+word).strip()
 if buf:out.append(buf)
 return out
ap=argparse.ArgumentParser();g=ap.add_mutually_exclusive_group(required=True);g.add_argument('--text');g.add_argument('--text-file');ap.add_argument('--timeout',type=int,default=180);ap.add_argument('--profile',choices=('normal','whisper','amused','happy','delighted','upset','somber','warm'),default='normal')
a=ap.parse_args();speech=a.text if a.text is not None else pathlib.Path(a.text_file).read_text(encoding='utf-8')
segments=chunks(speech)
if not segments:raise SystemExit('Empty speech')
print('SPEECH_CHUNKS',len(segments),flush=True)
for i,segment in enumerate(segments,1):
 job=call('POST','/v1/speak',{'text':segment,'speaker':a.profile});jid=job['id'];end=time.monotonic()+a.timeout
 while time.monotonic()<end:
  state=call('GET','/v1/jobs/'+jid)
  if state['state'] in ('completed','failed'):break
  time.sleep(.5)
 else:raise TimeoutError('generation timeout for chunk '+str(i))
 if state['state']!='completed':raise RuntimeError('chunk failed '+str(i)+' '+str(state.get('error')))
 delivered=call('POST','/v1/deliver',{'job_id':jid})
 print('ENQUEUED_CHUNK',i,'of',len(segments),'relay',delivered.get('relay_id'),'audio_sec',state.get('audio_seconds'),'gen_sec',state.get('generation_seconds'),flush=True)
print('ALL_CHUNKS_ENQUEUED_NOT_HEARD',flush=True)
