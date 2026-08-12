#!/data/data/com.termux/files/usr/bin/python
from __future__ import annotations
import argparse, hashlib, json, time
from pathlib import Path

MAX_BYTES = 64 * 1024
EXPECTED_SCHEMAS = {
    'overlay':'adam-overlay-recovery-v1',
    'probe':'vlad.pixel-forge.probe.v1',
}


def read_json(path: Path) -> dict:
    raw = path.read_bytes()
    if len(raw) > MAX_BYTES:
        raise ValueError(f'evidence file too large: {path} ({len(raw)} bytes)')
    return json.loads(raw.decode('utf-8'))


def digest_file(path: Path) -> str:
    h=hashlib.sha256(); h.update(path.read_bytes()); return h.hexdigest()


def require(obj: dict, key: str, expected=None):
    if key not in obj:
        raise ValueError(f'missing evidence field: {key}')
    if expected is not None and obj.get(key) != expected:
        raise ValueError(f'evidence field {key} expected {expected!r}, got {obj.get(key)!r}')


def phone_no_ci(obj: dict, kind: str):
    require(obj,'device','primary-phone')
    require(obj,'ciUsed',False)
    if obj.get('godotRuntimeUsed') not in (None,False):
        raise ValueError(f'{kind} evidence claims Godot runtime use')


def summary(path: Path, kind: str) -> dict:
    obj=read_json(path)
    out={'kind':kind,'path':str(path),'sha256':digest_file(path),'schema':obj.get('schema')}
    if kind=='overlay':
        require(obj,'schema',EXPECTED_SCHEMAS[kind]); require(obj,'ok',True); phone_no_ci(obj,kind)
        out.update(ok=True,mode=obj.get('mode'),device='primary-phone',runtime=obj.get('runtime'),ciUsed=False,godotRuntimeUsed=False)
    elif kind=='probe':
        require(obj,'schema',EXPECTED_SCHEMAS[kind]); require(obj,'ok',True); phone_no_ci(obj,kind)
        out.update(ok=True,device='primary-phone',memory=obj.get('memory'),storage=obj.get('storage'),thermal=obj.get('thermal'),recommendation=obj.get('recommendation'),ciUsed=False,godotRuntimeUsed=False)
    elif kind=='mnn':
        require(obj,'ok',True); phone_no_ci(obj,kind)
        if not str(obj.get('schema') or '').startswith('vlad.pixel-forge.mnn-bootstrap.v'):
            raise ValueError('unexpected MNN bootstrap schema')
        if obj.get('mnnRef')!='3.4.1': raise ValueError('MNN evidence is not pinned to 3.4.1')
        demo=str(obj.get('diffusionDemo') or '')
        if not demo: raise ValueError('MNN evidence has no diffusion_demo path')
        out.update(ok=True,mnnRef='3.4.1',diffusionDemo=demo,device='primary-phone',ciUsed=False,godotRuntimeUsed=False)
    elif kind=='generation':
        require(obj,'ok',True); require(obj,'intermediateDeleted',True); phone_no_ci(obj,kind)
        if not str(obj.get('schema') or '').startswith('vlad.pixel.generate.v'):
            raise ValueError('unexpected generation schema')
        size=int(obj.get('canonicalBytes') or 0)
        if size <= 0: raise ValueError('canonical artifact is empty')
        request=(obj.get('request') or {}).get('requestSha256')
        if not request: raise ValueError('generation evidence lacks request identity')
        out.update(ok=True,device='primary-phone',canonical=obj.get('canonical'),canonicalBytes=size,intermediateDeleted=True,elapsedSeconds=obj.get('elapsedSeconds'),request=request,ciUsed=False,godotRuntimeUsed=False)
    else:
        raise ValueError(f'unknown evidence kind: {kind}')
    return out


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--overlay',required=True)
    ap.add_argument('--probe',required=True)
    ap.add_argument('--mnn',required=True)
    ap.add_argument('--generation',required=True)
    ap.add_argument('--out',required=True)
    a=ap.parse_args()
    entries=[summary(Path(a.overlay),'overlay'),summary(Path(a.probe),'probe'),summary(Path(a.mnn),'mnn'),summary(Path(a.generation),'generation')]
    body={'schema':'fortress.phone-evidence.v1','ok':True,'device':'primary-phone','ciUsed':False,'godotRuntimeUsed':False,'evidence':entries,'recordedAtEpoch':int(time.time())}
    encoded=json.dumps(body,sort_keys=True,separators=(',',':')).encode()
    body['evidenceSha256']=hashlib.sha256(encoded).hexdigest()
    out=Path(a.out); out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(body,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    print(json.dumps(body,indent=2,sort_keys=True))
    return 0

if __name__=='__main__': raise SystemExit(main())
