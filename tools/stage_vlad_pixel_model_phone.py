#!/data/data/com.termux/files/usr/bin/python
from __future__ import annotations
import hashlib,json,os,time,urllib.request
from pathlib import Path
REPO=os.environ.get('HC_PIXEL_MODEL_REPO','darkmaniac7/TokForge-SD15-LCM-Style-Pixelart')
STATE=Path(os.environ.get('HC_PIXEL_FORGE_STATE','~/.local/state/home-center/pixel-forge')).expanduser()
MODEL_DIR=Path(os.environ.get('HC_PIXEL_MODEL_DIR','~/.local/share/home-center/pixel-forge/models/tokforge-pixelart')).expanduser()
MAX_BYTES=int(os.environ.get('HC_PIXEL_MODEL_MAX_BYTES',str(6*1024**3)))
FILES=('unet.mnn','unet.mnn.weight','text_encoder.mnn','text_encoder.mnn.weight','vae_decoder.mnn','vae_decoder.mnn.weight','vocab.json','merges.txt','alphas.txt')
def get_json(url):
    with urllib.request.urlopen(url,timeout=30) as r:return json.load(r)
def remote_size(url):
    req=urllib.request.Request(url,method='HEAD')
    with urllib.request.urlopen(req,timeout=30) as r:return int(r.headers.get('Content-Length') or 0)
def sha256(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()
def download(url,dest):
    tmp=dest.with_suffix(dest.suffix+'.partial'); tmp.unlink(missing_ok=True)
    with urllib.request.urlopen(url,timeout=60) as r,tmp.open('wb') as f:
        while True:
            b=r.read(1024*1024)
            if not b:break
            f.write(b)
    os.replace(tmp,dest);return {'name':dest.name,'bytes':dest.stat().st_size,'sha256':sha256(dest)}
def main():
    STATE.mkdir(parents=True,exist_ok=True);MODEL_DIR.mkdir(parents=True,exist_ok=True)
    api=get_json(f'https://huggingface.co/api/models/{REPO}'); siblings={i.get('rfilename'):i for i in api.get('siblings',[])}
    missing=[n for n in FILES if n not in siblings]
    if missing:raise SystemExit(f'model bundle missing expected files: {missing}')
    rows=[];total=0
    for name in FILES:
        url=f'https://huggingface.co/{REPO}/resolve/main/{name}?download=true';size=int(siblings[name].get('size') or 0) or remote_size(url);total+=size;rows.append({'name':name,'url':url,'remoteBytes':size})
    plan={'schema':'vlad.pixel-forge.model-stage-plan.v1','repo':REPO,'files':rows,'plannedBytes':total,'hardLimitBytes':MAX_BYTES,'withinBudget':total<=MAX_BYTES,'ciUsed':False,'device':'primary-phone','recordedAtEpoch':int(time.time())}
    (STATE/'model-stage-plan.json').write_text(json.dumps(plan,indent=2,sort_keys=True)+'\n',encoding='utf-8');print(json.dumps(plan,indent=2,sort_keys=True))
    if total>MAX_BYTES:return 20
    completed=[]
    for row in rows:
        dest=MODEL_DIR/row['name']
        if dest.exists() and row['remoteBytes'] and dest.stat().st_size==row['remoteBytes']:completed.append({'name':dest.name,'bytes':dest.stat().st_size,'sha256':sha256(dest),'reused':True});continue
        completed.append({**download(row['url'],dest),'reused':False})
    receipt={'schema':'vlad.pixel-forge.model-stage.v1','ok':True,'repo':REPO,'modelDir':str(MODEL_DIR),'files':completed,'totalBytes':sum(i['bytes'] for i in completed),'ciUsed':False,'device':'primary-phone','recordedAtEpoch':int(time.time())}
    (STATE/'model-stage.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n',encoding='utf-8');print(json.dumps(receipt,indent=2,sort_keys=True));return 0
if __name__=='__main__':raise SystemExit(main())
