#!/data/data/com.termux/files/usr/bin/python
from __future__ import annotations
import argparse, hashlib, json, time
from pathlib import Path

MAX_BYTES = 64 * 1024
EXPECTED_SCHEMAS = {'overlay':'adam-overlay-recovery-v1','probe':'vlad.pixel-forge.probe.v1'}
EXPECTED_MODEL_REPO='darkmaniac7/TokForge-SD15-LCM-Style-Pixelart'


def read_json(path: Path) -> dict:
    raw = path.read_bytes()
    if len(raw) > MAX_BYTES: raise ValueError(f'evidence file too large: {path} ({len(raw)} bytes)')
    return json.loads(raw.decode('utf-8'))
def digest_file(path: Path) -> str:
    h=hashlib.sha256(); h.update(path.read_bytes()); return h.hexdigest()
def require(obj: dict, key: str, expected=None):
    if key not in obj: raise ValueError(f'missing evidence field: {key}')
    if expected is not None and obj.get(key) != expected: raise ValueError(f'evidence field {key} expected {expected!r}, got {obj.get(key)!r}')
def phone_no_ci(obj: dict, kind: str):
    require(obj,'device','primary-phone'); require(obj,'ciUsed',False)
    if obj.get('godotRuntimeUsed') not in (None,False): raise ValueError(f'{kind} evidence claims Godot runtime use')
def valid_hex(value:str,n:int)->bool:
    return len(value)==n and all(c in '0123456789abcdef' for c in value.lower())


def summary(path: Path, kind: str) -> dict:
    obj=read_json(path); out={'kind':kind,'path':str(path),'sha256':digest_file(path),'schema':obj.get('schema')}
    if kind=='overlay':
        require(obj,'schema',EXPECTED_SCHEMAS[kind]); require(obj,'ok',True); phone_no_ci(obj,kind)
        out.update(ok=True,mode=obj.get('mode'),device='primary-phone',runtime=obj.get('runtime'),ciUsed=False,godotRuntimeUsed=False)
    elif kind=='probe':
        require(obj,'schema',EXPECTED_SCHEMAS[kind]); require(obj,'ok',True); phone_no_ci(obj,kind)
        out.update(ok=True,device='primary-phone',memory=obj.get('memory'),storage=obj.get('storage'),thermal=obj.get('thermal'),recommendation=obj.get('recommendation'),ciUsed=False,godotRuntimeUsed=False)
    elif kind=='mnn':
        require(obj,'ok',True); phone_no_ci(obj,kind)
        if not str(obj.get('schema') or '').startswith('vlad.pixel-forge.mnn-bootstrap.v'): raise ValueError('unexpected MNN bootstrap schema')
        if obj.get('mnnRef')!='3.4.1': raise ValueError('MNN evidence is not pinned to 3.4.1')
        demo=str(obj.get('diffusionDemo') or '')
        if not demo: raise ValueError('MNN evidence has no diffusion_demo path')
        out.update(ok=True,mnnRef='3.4.1',buildSignature=obj.get('buildSignature'),diffusionDemo=demo,device='primary-phone',ciUsed=False,godotRuntimeUsed=False)
    elif kind=='model':
        require(obj,'schema','vlad.pixel-forge.model-stage.v2'); require(obj,'ok',True); phone_no_ci(obj,kind)
        require(obj,'repo',EXPECTED_MODEL_REPO)
        revision=str(obj.get('repoRevision') or '')
        if not valid_hex(revision,40): raise ValueError('model evidence lacks pinned commit SHA')
        manifest_sha=str(obj.get('manifestSha256') or '')
        if not valid_hex(manifest_sha,64): raise ValueError('model evidence lacks manifest SHA-256')
        files=obj.get('files') or []
        if len(files)!=9: raise ValueError('model evidence does not contain nine files')
        weight_files=[x for x in files if str(x.get('name') or '').endswith(('.mnn','.weight'))]
        if len(weight_files)!=6 or any(not valid_hex(str(x.get('expectedSha256') or ''),64) for x in weight_files):
            raise ValueError('model weight evidence lacks Hub LFS SHA-256 truth')
        out.update(ok=True,repo=EXPECTED_MODEL_REPO,repoRevision=revision,manifestSha256=manifest_sha,totalBytes=obj.get('totalBytes'),device='primary-phone',ciUsed=False,godotRuntimeUsed=False)
    elif kind=='generation':
        require(obj,'ok',True); require(obj,'intermediateDeleted',True); phone_no_ci(obj,kind)
        if not str(obj.get('schema') or '').startswith('vlad.pixel.generate.v'): raise ValueError('unexpected generation schema')
        size=int(obj.get('canonicalBytes') or 0)
        if size <= 0: raise ValueError('canonical artifact is empty')
        request=(obj.get('request') or {}).get('requestSha256')
        if not request or not valid_hex(str(request),64): raise ValueError('generation evidence lacks request identity')
        out.update(ok=True,device='primary-phone',canonical=obj.get('canonical'),canonicalBytes=size,intermediateDeleted=True,elapsedSeconds=obj.get('elapsedSeconds'),request=request,backendUsed=obj.get('backendUsed'),ciUsed=False,godotRuntimeUsed=False)
    else: raise ValueError(f'unknown evidence kind: {kind}')
    return out


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--overlay',required=True); ap.add_argument('--probe',required=True); ap.add_argument('--mnn',required=True); ap.add_argument('--model',required=True); ap.add_argument('--generation',required=True); ap.add_argument('--out',required=True)
    a=ap.parse_args()
    entries=[summary(Path(a.overlay),'overlay'),summary(Path(a.probe),'probe'),summary(Path(a.mnn),'mnn'),summary(Path(a.model),'model'),summary(Path(a.generation),'generation')]
    body={'schema':'fortress.phone-evidence.v2','ok':True,'device':'primary-phone','ciUsed':False,'godotRuntimeUsed':False,'evidence':entries,'recordedAtEpoch':int(time.time())}
    encoded=json.dumps(body,sort_keys=True,separators=(',',':')).encode(); body['evidenceSha256']=hashlib.sha256(encoded).hexdigest()
    out=Path(a.out); out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(body,indent=2,sort_keys=True)+'\n',encoding='utf-8'); print(json.dumps(body,indent=2,sort_keys=True)); return 0
if __name__=='__main__': raise SystemExit(main())
