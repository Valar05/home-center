#!/usr/bin/env python3
from __future__ import annotations
import json, os, shutil, subprocess, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATE = Path(os.environ.get('WDT_STATE', os.environ.get('HC_STATE_DIR', str(Path.home()/'.local/state/home-center'))))
if STATE.name != 'wizard-dns-tango': STATE = STATE/'wizard-dns-tango'
STATE.mkdir(parents=True, exist_ok=True)
RECEIPTS = STATE/'receipts'; RECEIPTS.mkdir(exist_ok=True)
QUEUE = STATE/'queue.json'; EVENTS=STATE/'events.jsonl'; RELEASE=STATE/'RELEASED'
MOCK_HEARTBEAT=STATE/'mockray_heartbeat.json'; MOCK_LOG=STATE/'mockray-supervised.log'; MOCK_RELEASE=STATE/'mockray.release'

DEFAULT_QUEUE = [
  {'id':'home-center-restart-button','priority':1000,'kind':'commission','status':'owed',
   'acceptance':'physical-phone evidence: visible dedicated RESTART HC/TURN HC ON control, tap attempts recovery, truthful result'},
  {'id':'time-now-skill-census','priority':700,'kind':'campaign','status':'owed'},
]

def write_json(path,obj):
    tmp=Path(str(path)+'.tmp'); tmp.write_text(json.dumps(obj,indent=2,sort_keys=True)+'\n'); tmp.replace(path)

def emit(kind, task_id, **extra):
    rec={'at':time.time(),'kind':kind,'task_id':task_id,**extra}
    with EVENTS.open('a',encoding='utf-8') as f:f.write(json.dumps(rec,sort_keys=True)+'\n')
    return rec

def load_queue():
    if not QUEUE.exists(): write_json(QUEUE,DEFAULT_QUEUE)
    return json.loads(QUEUE.read_text())

def battery():
    p=Path('/sys/class/power_supply/battery/capacity')
    if p.exists():
        try:return int(p.read_text().strip())
        except Exception:pass
    if shutil.which('termux-battery-status'):
        try:return int(json.loads(subprocess.check_output(['termux-battery-status'],text=True,timeout=3)).get('percentage',100))
        except Exception:pass
    return 100

def charging():
    p=Path('/sys/class/power_supply/battery/status')
    if p.exists():return p.read_text().strip().lower() in {'charging','full'}
    if shutil.which('termux-battery-status'):
        try:return json.loads(subprocess.check_output(['termux-battery-status'],text=True,timeout=3)).get('status','').lower() in {'charging','full'}
        except Exception:pass
    return False

def tremorcle(kind='tick'):
    if not shutil.which('termux-vibrate'):return
    ms={'tick':18,'success':70,'warn':140,'blocked':220,'recovery':95}.get(kind,18)
    try:subprocess.run(['termux-vibrate','-d',str(ms),'-f'],timeout=2,check=False,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    except Exception:pass

def run(cmd,timeout=300):
    started=time.time(); p=subprocess.run(cmd,cwd=ROOT,text=True,capture_output=True,timeout=timeout)
    return {'cmd':cmd,'rc':p.returncode,'stdout':p.stdout[-12000:],'stderr':p.stderr[-12000:],'seconds':round(time.time()-started,2)}

def mockray_alive():
    try:
        data=json.loads(MOCK_HEARTBEAT.read_text()); t=float(data.get('heartbeat_at') or data.get('last',{}).get('at',0)); return time.time()-t<20
    except Exception:return False

def ensure_mockray():
    if mockray_alive(): return {'ok':True,'state':'alive'}
    MOCK_RELEASE.unlink(missing_ok=True)
    log=MOCK_LOG.open('ab')
    proc=subprocess.Popen([sys.executable,str(ROOT/'wizard_dns_tango/mockray_daemon.py')],cwd=ROOT,env={**os.environ,'WDT_STATE':str(STATE)},stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
    emit('dispatch','mockery-forge',verified=True,pid=proc.pid,message='OS supervisor restarted Mockery Forge')
    return {'ok':True,'state':'restarted','pid':proc.pid}

def home_center_recovery_bite():
    candidates=[['bash','tools/fortress_now_phone.sh'],['bash','tools/recover_adam_overlay_phone.sh']]
    for cmd in candidates:
        if (ROOT/cmd[1]).exists():
            tremorcle('recovery'); emit('dispatch','home-center-restart-button',verified=True,command=cmd)
            return run(cmd,timeout=900)
    return {'rc':127,'stderr':'no recovery primitive found'}

def time_now_bite():
    p=ROOT/'tools/time_now_whale_swarm.sh'
    if p.exists(): return run(['bash',str(p)],timeout=60)
    return {'rc':127,'stderr':'time_now_whale_swarm.sh absent'}

def choose(q):
    owed=[x for x in q if x.get('status') not in {'accepted','released','superseded'}]
    return max(owed,key=lambda x:x.get('priority',0)) if owed else None

def tick():
    mock=ensure_mockray(); q=load_queue(); item=choose(q); b=battery(); c=charging()
    if item is None:return {'status':'idle','battery':b,'charging':c,'mockery_forge':mock}
    if b<35 and not c:
        tremorcle('warn'); emit('blocked',item['id'],verified=True,reason='phone battery governor',battery=b)
        return {'status':'throttled','item':item['id'],'battery':b,'charging':c,'reason':'phone battery governor','mockery_forge':mock}
    emit('working',item['id'],verified=True,battery=b,charging=c)
    if item['id']=='home-center-restart-button': result=home_center_recovery_bite()
    elif item['id']=='time-now-skill-census': result=time_now_bite()
    else: result={'rc':126,'stderr':'no executor registered'}
    receipt={'ts':time.time(),'item':item,'battery':b,'charging':c,'result':result,'mockery_forge':mock}
    path=RECEIPTS/f"{int(receipt['ts']*1000)}-{item['id']}.json"; write_json(path,receipt)
    ok=result.get('rc')==0
    emit('receipt',item['id'],verified=True,receipt=str(path),rc=result.get('rc'))
    emit('canary_pass' if ok else 'canary_fail',item['id'],verified=ok,receipt=str(path))
    tremorcle('success' if ok else 'blocked')
    return receipt

def main():
    tremorcle('tick'); ensure_mockray(); emit('dispatch','wdt-kernel',verified=True,message='Wizard DNS Tango kernel online')
    while not RELEASE.exists():
        try: print(json.dumps(tick(),sort_keys=True),flush=True)
        except Exception as e:
            p=RECEIPTS/f'{int(time.time()*1000)}-kernel-error.json'; write_json(p,{'error':repr(e),'ts':time.time()}); emit('canary_fail','wdt-kernel',verified=False,receipt=str(p)); tremorcle('blocked')
        time.sleep(30)

if __name__=='__main__':main()
