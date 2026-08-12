#!/data/data/com.termux/files/usr/bin/python
from __future__ import annotations
import argparse, hashlib, json, os, subprocess, time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
STATE=Path(os.path.expanduser(os.getenv('HC_PIXEL_FORGE_STATE','~/.local/state/home-center/pixel-forge')))
MODEL_DIR=Path(os.path.expanduser(os.getenv('HC_PIXEL_MODEL_DIR','~/.local/share/home-center/pixel-forge/models/tokforge-pixelart')))
MAX_SECONDS=int(os.environ.get('HC_PIXEL_GENERATE_TIMEOUT','900'))


def canonical_request(req:dict)->bytes:
    body={k:v for k,v in req.items() if k!='requestSha256'}
    return json.dumps(body,sort_keys=True,separators=(',',':')).encode()


def load_request(path:Path)->dict:
    req=json.loads(path.read_text(encoding='utf-8'))
    if req.get('schema')!='vlad.pixel.request.v1': raise ValueError('unsupported request schema')
    expected=hashlib.sha256(canonical_request(req)).hexdigest()
    if req.get('requestSha256')!=expected: raise ValueError('request hash mismatch')
    if not 1 <= int(req.get('steps',0)) <= 8: raise ValueError('steps out of bounds')
    if int(req.get('width',0)) not in (256,384,512) or int(req.get('height',0)) not in (256,384,512): raise ValueError('dimensions out of bounds')
    return req


def main():
    ap=argparse.ArgumentParser(prog='vlad-pixel-generate-mnn')
    ap.add_argument('request')
    ap.add_argument('--canonical-size',type=int,default=32,choices=(8,16,24,32,48,64))
    ap.add_argument('--colors',type=int,default=16,choices=(2,4,8,16,32))
    a=ap.parse_args()
    STATE.mkdir(parents=True,exist_ok=True)
    req=load_request(Path(a.request))

    required=('unet.mnn','unet.mnn.weight','text_encoder.mnn','text_encoder.mnn.weight','vae_decoder.mnn','vae_decoder.mnn.weight','vocab.json','merges.txt','alphas.txt')
    missing=[name for name in required if not (MODEL_DIR/name).is_file()]
    if missing: raise SystemExit(f'model not staged; missing: {missing}')

    demo_path=(STATE/'diffusion-demo.path')
    if not demo_path.is_file(): raise SystemExit('MNN diffusion_demo path receipt missing; run bootstrap first')
    demo=Path(demo_path.read_text(encoding='utf-8').strip())
    if not demo.is_file(): raise SystemExit(f'MNN diffusion_demo missing: {demo}')

    job=req['requestSha256'][:16]
    outdir=STATE/'generations'/job
    outdir.mkdir(parents=True,exist_ok=True)
    intermediate=outdir/'neural.jpg'
    canonical=outdir/'sprite.vpx'
    receipt_path=outdir/'generation.json'

    # MNN official diffusion_demo contract: resource, SD1.5 model type 0,
    # memory-saving mode 0, OpenCL backend 3, iterations, seed, output, prompt.
    lib_dirs={str(p.parent) for p in demo.parent.rglob('*.so')}
    env=os.environ.copy()
    inherited=env.get('LD_LIBRARY_PATH','')
    env['LD_LIBRARY_PATH']=':'.join(sorted(lib_dirs)+([inherited] if inherited else []))
    cmd=[str(demo),str(MODEL_DIR),'0','0','3',str(req['steps']),str(req['seed']),str(intermediate),str(req['prompt'])]
    started=time.monotonic()
    proc=subprocess.run(cmd,cwd=str(outdir),env=env,text=True,capture_output=True,timeout=MAX_SECONDS)
    elapsed=time.monotonic()-started
    if proc.returncode!=0 or not intermediate.is_file() or intermediate.stat().st_size<=0:
        receipt={'schema':'vlad.pixel.generate.v1','ok':False,'request':req,'cmd':cmd,'rc':proc.returncode,'stdout':proc.stdout[-6000:],'stderr':proc.stderr[-6000:],'elapsedSeconds':elapsed,'device':'primary-phone','ciUsed':False}
        receipt_path.write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n',encoding='utf-8')
        print(json.dumps(receipt,indent=2,sort_keys=True))
        return 20

    pack=subprocess.run([
        os.environ.get('PYTHON','python3'),str(ROOT/'tools/vlad_pixel_pack.py'),str(intermediate),str(canonical),
        '--size',str(a.canonical_size),'--colors',str(a.colors),
    ],cwd=str(ROOT),text=True,capture_output=True,timeout=120)
    pack_receipt=canonical.with_suffix(canonical.suffix+'.receipt.json')
    packed=json.loads(pack_receipt.read_text(encoding='utf-8')) if pack_receipt.is_file() else {}
    ok=pack.returncode==0 and canonical.is_file() and packed.get('intermediateDeleted') is True and not intermediate.exists()
    receipt={
        'schema':'vlad.pixel.generate.v1','ok':ok,'request':req,'cmd':cmd,'rc':proc.returncode,
        'stdout':proc.stdout[-6000:],'stderr':proc.stderr[-6000:],'elapsedSeconds':elapsed,
        'canonical':str(canonical),'canonicalBytes':canonical.stat().st_size if canonical.is_file() else 0,
        'pack':packed,'packRc':pack.returncode,'packStdout':pack.stdout[-3000:],'packStderr':pack.stderr[-3000:],
        'intermediateDeleted':not intermediate.exists(),'device':'primary-phone','ciUsed':False,'godotRuntimeUsed':False,
        'recordedAtEpoch':int(time.time()),
    }
    receipt_path.write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    print(json.dumps(receipt,indent=2,sort_keys=True))
    return 0 if ok else 21

if __name__=='__main__': raise SystemExit(main())
