#!/usr/bin/env python3
from __future__ import annotations
import json, subprocess, tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
COLLECTOR=ROOT/'tools/fortress_collect_phone_evidence.py'

def write(path:Path,obj:dict): path.write_text(json.dumps(obj),encoding='utf-8')

def run_case(root:Path,mutate=None):
    overlay={'schema':'adam-overlay-recovery-v1','ok':True,'device':'primary-phone','runtime':'android-native-overlay','ciUsed':False,'godotRuntimeUsed':False}
    probe={'schema':'vlad.pixel-forge.probe.v1','ok':True,'device':'primary-phone','ciUsed':False,'godotRuntimeUsed':False,'memory':{},'storage':{},'thermal':{},'recommendation':{}}
    mnn={'schema':'vlad.pixel-forge.mnn-bootstrap.v5','ok':True,'device':'primary-phone','ciUsed':False,'godotRuntimeUsed':False,'mnnRef':'3.4.1','buildSignature':'sig','diffusionDemo':'/tmp/diffusion_demo'}
    files=[]
    for name in ('unet.mnn','unet.mnn.weight','text_encoder.mnn','text_encoder.mnn.weight','vae_decoder.mnn','vae_decoder.mnn.weight','vocab.json','merges.txt','alphas.txt'):
        files.append({'name':name,'bytes':1,'sha256':'b'*64,'expectedSha256':('b'*64 if name.endswith(('.mnn','.weight')) else None)})
    model={'schema':'vlad.pixel-forge.model-stage.v2','ok':True,'repo':'darkmaniac7/TokForge-SD15-LCM-Style-Pixelart','repoRevision':'c'*40,'manifestSha256':'d'*64,'files':files,'totalBytes':9,'device':'primary-phone','ciUsed':False,'godotRuntimeUsed':False}
    gen={'schema':'vlad.pixel.generate.v3','ok':True,'device':'primary-phone','ciUsed':False,'godotRuntimeUsed':False,'intermediateDeleted':True,'canonicalBytes':321,'canonical':'/tmp/a.vpx','request':{'requestSha256':'a'*64},'backendUsed':3}
    objs={'overlay':overlay,'probe':probe,'mnn':mnn,'model':model,'generation':gen}
    if mutate: mutate(objs)
    paths={}
    for key,obj in objs.items(): paths[key]=root/f'{key}.json'; write(paths[key],obj)
    out=root/'out.json'
    p=subprocess.run(['python3',str(COLLECTOR),'--overlay',str(paths['overlay']),'--probe',str(paths['probe']),'--mnn',str(paths['mnn']),'--model',str(paths['model']),'--generation',str(paths['generation']),'--out',str(out)],text=True,capture_output=True)
    return p,out

with tempfile.TemporaryDirectory() as d:
    root=Path(d)
    p,out=run_case(root)
    assert p.returncode==0,p.stderr
    result=json.loads(out.read_text(encoding='utf-8'))
    assert result['schema']=='fortress.phone-evidence.v2'
    assert result['ok'] is True and result['device']=='primary-phone' and result['ciUsed'] is False

    bad_cases=[
        lambda x: x['probe'].__setitem__('device','laptop'),
        lambda x: x['overlay'].__setitem__('ciUsed',True),
        lambda x: x['mnn'].__setitem__('mnnRef','master'),
        lambda x: x['model'].__setitem__('repoRevision','main'),
        lambda x: x['model'].__setitem__('repo','wrong/model'),
        lambda x: x['model']['files'][0].__setitem__('expectedSha256',None),
        lambda x: x['generation'].__setitem__('intermediateDeleted',False),
        lambda x: x['generation'].__setitem__('canonicalBytes',0),
        lambda x: x['generation'].__setitem__('request',{}),
        lambda x: x['generation'].__setitem__('godotRuntimeUsed',True),
    ]
    for i,mutate in enumerate(bad_cases):
        case=root/f'bad{i}'; case.mkdir()
        p,_=run_case(case,mutate)
        assert p.returncode!=0,f'bad evidence case {i} unexpectedly passed'
print('Fortress phone evidence synthetic acceptance/rejection: PASS')
