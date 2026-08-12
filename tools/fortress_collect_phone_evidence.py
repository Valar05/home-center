#!/data/data/com.termux/files/usr/bin/python
from __future__ import annotations
import argparse, hashlib, json, os, time
from pathlib import Path

MAX_BYTES = 64 * 1024


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


def summary(path: Path, kind: str) -> dict:
    obj=read_json(path)
    out={'kind':kind,'path':str(path),'sha256':digest_file(path),'schema':obj.get('schema')}
    if kind=='overlay':
        require(obj,'ok',True)
        out.update(ok=True,mode=obj.get('mode'),device=obj.get('device'),runtime=obj.get('runtime'),ciUsed=obj.get('ciUsed'),godotRuntimeUsed=obj.get('godotRuntimeUsed'))
        if obj.get('device') not in (None,'primary-phone'): raise ValueError('overlay evidence device mismatch')
        if obj.get('ciUsed') is not False: raise ValueError('overlay evidence used CI')
    elif kind=='probe':
        # Probe schema may evolve; preserve only bounded, decision-relevant fields.
        out.update(ok=obj.get('ok',True),device=obj.get('device','primary-phone'),memory=obj.get('memory'),storage=obj.get('storage'),thermal=obj.get('thermal'),recommendation=obj.get('recommendation'))
    elif kind=='mnn':
        require(obj,'ok',True)
        if obj.get('mnnRef')!='3.4.1': raise ValueError('MNN evidence is not pinned to 3.4.1')
        if obj.get('ciUsed') is not False: raise ValueError('MNN evidence used CI')
        out.update(ok=True,mnnRef=obj.get('mnnRef'),diffusionDemo=obj.get('diffusionDemo'),device=obj.get('device'),ciUsed=False)
    elif kind=='generation':
        require(obj,'ok',True); require(obj,'intermediateDeleted',True)
        if obj.get('device')!='primary-phone': raise ValueError('generation evidence device mismatch')
        if obj.get('ciUsed') is not False: raise ValueError('generation evidence used CI')
        size=int(obj.get('canonicalBytes') or 0)
        if size <= 0: raise ValueError('canonical artifact is empty')
        out.update(ok=True,device='primary-phone',canonical=obj.get('canonical'),canonicalBytes=size,intermediateDeleted=True,elapsedSeconds=obj.get('elapsedSeconds'),request=(obj.get('request') or {}).get('requestSha256'),ciUsed=False,godotRuntimeUsed=obj.get('godotRuntimeUsed'))
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
    entries=[
        summary(Path(a.overlay),'overlay'),
        summary(Path(a.probe),'probe'),
        summary(Path(a.mnn),'mnn'),
        summary(Path(a.generation),'generation'),
    ]
    body={'schema':'fortress.phone-evidence.v1','ok':all(e.get('ok') is not False for e in entries),'device':'primary-phone','ciUsed':False,'godotRuntimeUsed':False,'evidence':entries,'recordedAtEpoch':int(time.time())}
    encoded=json.dumps(body,sort_keys=True,separators=(',',':')).encode()
    body['evidenceSha256']=hashlib.sha256(encoded).hexdigest()
    out=Path(a.out); out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(body,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    print(json.dumps(body,indent=2,sort_keys=True))
    return 0 if body['ok'] else 1

if __name__=='__main__': raise SystemExit(main())
