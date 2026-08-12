#!/data/data/com.termux/files/usr/bin/python
from __future__ import annotations
import hashlib,json,os,shutil,time,urllib.request
from pathlib import Path

REPO=os.environ.get('HC_PIXEL_MODEL_REPO','darkmaniac7/TokForge-SD15-LCM-Style-Pixelart')
STATE=Path(os.environ.get('HC_PIXEL_FORGE_STATE','~/.local/state/home-center/pixel-forge')).expanduser()
MODEL_DIR=Path(os.environ.get('HC_PIXEL_MODEL_DIR','~/.local/share/home-center/pixel-forge/models/tokforge-pixelart')).expanduser()
MAX_BYTES=int(os.environ.get('HC_PIXEL_MODEL_MAX_BYTES',str(6*1024**3)))
MIN_FREE_MARGIN=int(os.environ.get('HC_PIXEL_MODEL_FREE_MARGIN_BYTES',str(1024**3)))
FILES=('unet.mnn','unet.mnn.weight','text_encoder.mnn','text_encoder.mnn.weight','vae_decoder.mnn','vae_decoder.mnn.weight','vocab.json','merges.txt','alphas.txt')

def get_json(url):
    with urllib.request.urlopen(url,timeout=30) as r:return json.load(r)
def sha256(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()
def download(url,dest,expected_size,expected_sha):
    tmp=dest.with_suffix(dest.suffix+'.partial'); tmp.unlink(missing_ok=True)
    h=hashlib.sha256(); total=0
    try:
        with urllib.request.urlopen(url,timeout=90) as r,tmp.open('wb') as f:
            while True:
                b=r.read(1024*1024)
                if not b:break
                total+=len(b)
                if total>MAX_BYTES: raise RuntimeError('single model file exceeded hard model budget')
                h.update(b); f.write(b)
        actual=h.hexdigest()
        if expected_size and total!=expected_size: raise RuntimeError(f'download size mismatch for {dest.name}: expected={expected_size} actual={total}')
        if expected_sha and actual!=expected_sha: raise RuntimeError(f'download sha256 mismatch for {dest.name}: expected={expected_sha} actual={actual}')
        os.replace(tmp,dest)
        return {'name':dest.name,'bytes':total,'sha256':actual}
    finally:
        tmp.unlink(missing_ok=True)

def main():
    STATE.mkdir(parents=True,exist_ok=True);MODEL_DIR.mkdir(parents=True,exist_ok=True)
    # blobs=true requests per-file size/LFS metadata. Pin downloads to the exact
    # repository commit returned by the Hub rather than mutable main.
    api=get_json(f'https://huggingface.co/api/models/{REPO}?blobs=true')
    revision=str(api.get('sha') or '').strip()
    if len(revision)!=40 or any(c not in '0123456789abcdef' for c in revision.lower()):
        raise SystemExit('model API did not return a valid pinned commit SHA')
    siblings={i.get('rfilename'):i for i in api.get('siblings',[])}
    missing=[n for n in FILES if n not in siblings]
    if missing:raise SystemExit(f'model bundle missing expected files: {missing}')
    rows=[];total=0
    for name in FILES:
        meta=siblings[name]
        lfs=meta.get('lfs') or {}
        size=int(lfs.get('size') or meta.get('size') or 0)
        oid=str(lfs.get('oid') or '').lower()
        expected_sha=oid if len(oid)==64 and all(c in '0123456789abcdef' for c in oid) else ''
        if size<=0: raise SystemExit(f'Hub metadata lacks a positive size for {name}; refusing unbounded download')
        total+=size
        rows.append({'name':name,'remoteBytes':size,'sha256':expected_sha,'lfsVerified':bool(expected_sha)})
    plan={'schema':'vlad.pixel-forge.model-stage-plan.v2','repo':REPO,'repoRevision':revision,'files':rows,'plannedBytes':total,'hardLimitBytes':MAX_BYTES,'withinBudget':total<=MAX_BYTES,'ciUsed':False,'device':'primary-phone','godotRuntimeUsed':False,'recordedAtEpoch':int(time.time())}
    (STATE/'model-stage-plan.json').write_text(json.dumps(plan,indent=2,sort_keys=True)+'\n',encoding='utf-8');print(json.dumps(plan,indent=2,sort_keys=True))
    if total>MAX_BYTES:return 20
    free=shutil.disk_usage(MODEL_DIR).free
    if free < total + MIN_FREE_MARGIN:
        raise SystemExit(f'insufficient free storage for pinned model: free={free} need={total + MIN_FREE_MARGIN}')
    completed=[]
    for row in rows:
        dest=MODEL_DIR/row['name']
        if dest.exists() and dest.stat().st_size==row['remoteBytes']:
            actual=sha256(dest)
            if not row['sha256'] or actual==row['sha256']:
                completed.append({'name':dest.name,'bytes':dest.stat().st_size,'sha256':actual,'expectedSha256':row['sha256'] or None,'reused':True});continue
        url=f'https://huggingface.co/{REPO}/resolve/{revision}/{row["name"]}?download=true'
        got=download(url,dest,row['remoteBytes'],row['sha256'])
        completed.append({**got,'expectedSha256':row['sha256'] or None,'reused':False})
    # At least all LFS-backed weight files must have Hub SHA-256 truth; text
    # tokenizer files may be ordinary git blobs and are still pinned by revision.
    weight_rows=[r for r in rows if r['name'].endswith(('.mnn','.weight'))]
    if any(not r['lfsVerified'] for r in weight_rows):
        raise SystemExit('one or more model weight files lacked LFS SHA-256 metadata')
    manifest={'schema':'vlad.pixel-forge.model-stage.v2','ok':True,'repo':REPO,'repoRevision':revision,'modelDir':str(MODEL_DIR),'files':completed,'totalBytes':sum(i['bytes'] for i in completed),'ciUsed':False,'device':'primary-phone','godotRuntimeUsed':False,'recordedAtEpoch':int(time.time())}
    encoded=json.dumps(manifest,sort_keys=True,separators=(',',':')).encode(); manifest['manifestSha256']=hashlib.sha256(encoded).hexdigest()
    (STATE/'model-stage.json').write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n',encoding='utf-8');print(json.dumps(manifest,indent=2,sort_keys=True));return 0
if __name__=='__main__':raise SystemExit(main())
