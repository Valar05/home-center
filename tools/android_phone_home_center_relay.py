#!/data/data/com.termux/files/usr/bin/python
from __future__ import annotations
import json, os, secrets, subprocess, sys, time, urllib.request, urllib.error
from pathlib import Path

CFG=Path(os.path.expanduser('~/.config/home-center'))
PAIR=CFG/'codex-hub.json'
NODE=CFG/'phone-relay.json'
BASE=os.getenv('HC_PHONE_RELAY_BASE','https://us-central1-home-center-dclar.cloudfunctions.net/phoneHandsRelay')
DEVICE_ID=os.getenv('HC_PHONE_DEVICE_ID','primary-phone')
POLL=float(os.getenv('HC_PHONE_RELAY_POLL_SECONDS','2.0'))
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/'tools'))
from android_phone_hands_bridge import observe as hands_observe, act as hands_act
from android_phone_local_executive import execute as local_execute
from android_phone_factory_tools import execute as factory_execute
from android_armory_driver import execute as armory_execute

FACTORY_ACTIONS={
    'file_stat','file_hash','file_list','file_mkdir','file_copy','file_move',
    'armory_inventory','armory_ingest',
}
ARMORY_ACTIONS={'armory_doctor','armory_slice'}


def http(path, body=None, token=''):
    data=None if body is None else json.dumps(body).encode()
    req=urllib.request.Request(BASE+path,data=data,method='GET' if body is None else 'POST')
    req.add_header('Content-Type','application/json')
    if token: req.add_header('Authorization','Bearer '+token)
    try:
        with urllib.request.urlopen(req,timeout=45) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        text=e.read().decode('utf-8','replace')
        raise RuntimeError(f'HTTP {e.code} {path}: {text[:2000]}')


def load_pair():
    if not PAIR.exists(): raise RuntimeError(f'Home Center pairing missing: {PAIR}')
    return json.loads(PAIR.read_text())


def save_pair(cfg):
    PAIR.write_text(json.dumps(cfg,indent=2)+'\n'); os.chmod(PAIR,0o600)


def access_token():
    cfg=load_pair()
    if cfg.get('accessToken') and int(cfg.get('expiresAtMs',0)) > int(time.time()*1000)+60000:
        return cfg['accessToken']
    refresh=cfg.get('refreshToken')
    if not refresh: raise RuntimeError('Home Center refresh token missing; re-pair Termux once')
    gateway=cfg.get('gatewayBase','https://us-central1-home-center-dclar.cloudfunctions.net')
    req=urllib.request.Request(gateway+'/termuxTokenRefresh',data=json.dumps({'refreshToken':refresh}).encode(),method='POST',headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=30) as r: out=json.loads(r.read().decode())
    cfg['accessToken']=out['access_token']; cfg['refreshToken']=out.get('refresh_token',refresh); cfg['expiresAtMs']=int(time.time()*1000)+int(out.get('expires_in',3300))*1000
    save_pair(cfg); return cfg['accessToken']


def ensure_device():
    CFG.mkdir(parents=True,exist_ok=True)
    if NODE.exists(): return json.loads(NODE.read_text())
    token=secrets.token_urlsafe(48)
    reg=http('/register',{
        'deviceId':DEVICE_ID,'deviceToken':token,'label':'Drew Android Phone',
        'capabilities':['phone_hands','phone_files','armory_worker','local_qwen','coding_dungeon','voice']
    },access_token())
    data={'deviceId':DEVICE_ID,'deviceToken':token,'registeredAt':time.time(),'registration':reg}
    NODE.write_text(json.dumps(data,indent=2)+'\n'); os.chmod(NODE,0o600); return data


def dungeon_run(payload):
    manifest=str(payload.get('manifest') or '').strip()
    if not manifest: raise RuntimeError('dungeon_run requires manifest')
    p=subprocess.run([os.path.expanduser('~/bin/dungeon'),'run',manifest],text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=int(payload.get('timeoutSeconds',600)))
    return {'exit':p.returncode,'output':p.stdout[-20000:]}


def execute_action(action):
    kind=action.get('action')
    if kind=='observe': return hands_observe(bool(action.get('ui',True)),bool(action.get('screen',False)))
    if kind=='local_ask': return local_execute(str(action.get('intent') or action.get('prompt') or 'What is on my screen?'))
    if kind=='dungeon_run': return dungeon_run(action)
    if kind in FACTORY_ACTIONS: return factory_execute(action)
    if kind in ARMORY_ACTIONS: return armory_execute(action)
    return hands_act(action)


def loop(once=False):
    dev=ensure_device(); did=dev['deviceId']; secret=dev['deviceToken']
    print(f'Home Center phone relay online: {did}',flush=True)
    while True:
        try:
            pulled=http('/pull',{'deviceId':did,'deviceToken':secret,'leaseMs':90000})
            cmd=pulled.get('command')
            if cmd:
                cid=cmd['commandId']
                try:
                    result=execute_action(cmd.get('action') or {})
                    http('/complete',{'deviceId':did,'deviceToken':secret,'commandId':cid,'status':'completed','result':result})
                    print(json.dumps({'commandId':cid,'status':'completed'},ensure_ascii=False),flush=True)
                except Exception as exc:
                    http('/complete',{'deviceId':did,'deviceToken':secret,'commandId':cid,'status':'failed','error':str(exc)[:4000]})
                    print(json.dumps({'commandId':cid,'status':'failed','error':str(exc)},ensure_ascii=False),flush=True)
            if once: return
        except KeyboardInterrupt: raise
        except Exception as exc:
            print('phone-relay error: '+str(exc),file=sys.stderr,flush=True)
            if once: raise
        time.sleep(POLL)

if __name__=='__main__': loop('--once' in sys.argv)
