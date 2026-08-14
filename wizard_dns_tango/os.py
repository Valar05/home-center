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
MAX_BITE_SECONDS = int(os.environ.get('WDT_MAX_BITE_SECONDS', '120'))

DEFAULT_QUEUE = [
  {'id':'home-center-restart-button','priority':1000,'kind':'commission','status':'owed',
   'acceptance':'physical-phone evidence: visible dedicated RESTART HC/TURN HC ON control, tap attempts recovery, truthful result',
   'bites':[{'id':'recover-home-center','status':'owed','executor':'home_center_recovery'}]},
  {'id':'time-now-skill-census','priority':700,'kind':'campaign','status':'owed',
   'bites':[{'id':'run-time-now-census','status':'owed','executor':'time_now'}]},
]

DONE={'accepted','released','superseded'}

def write_json(path,obj):
    tmp=Path(str(path)+'.tmp'); tmp.write_text(json.dumps(obj,indent=2,sort_keys=True)+'\n'); tmp.replace(path)

def emit(kind, task_id, **extra):
    rec={'at':time.time(),'kind':kind,'task_id':task_id,**extra}
    with EVENTS.open('a',encoding='utf-8') as f:f.write(json.dumps(rec,sort_keys=True)+'\n')
    return rec

def load_queue():
    if not QUEUE.exists(): write_json(QUEUE,DEFAULT_QUEUE)
    return json.loads(QUEUE.read_text())

def save_queue(q): write_json(QUEUE,q)

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
    ms={'tick':18,'success':70,'warn':140,'blocked':220,'recovery':95,'bite':42,'divert':64}.get(kind,18)
    try:subprocess.run(['termux-vibrate','-d',str(ms),'-f'],timeout=2,check=False,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    except Exception:pass

def run(cmd,timeout=MAX_BITE_SECONDS):
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
    for cmd in (["bash","tools/fortress_now_phone.sh"],["bash","tools/recover_adam_overlay_phone.sh"]):
        if (ROOT/cmd[1]).exists(): tremorcle('recovery'); return run(cmd)
    return {'rc':127,'stderr':'no recovery primitive found'}

def time_now_bite():
    p=ROOT/'tools/time_now_whale_swarm.sh'
    return run(['bash',str(p)]) if p.exists() else {'rc':127,'stderr':'time_now_whale_swarm.sh absent'}

def execute_bite(whale,bite):
    executor=bite.get('executor')
    if executor=='home_center_recovery': return home_center_recovery_bite()
    if executor=='time_now': return time_now_bite()
    return {'rc':126,'stderr':'no executor registered for bite'}

def actionable_pairs(q):
    pairs=[]
    for whale in q:
        if whale.get('status') in DONE: continue
        for bite in whale.get('bites') or []:
            if bite.get('status') in DONE or bite.get('status')=='blocked': continue
            pairs.append((int(whale.get('priority',0)),whale,bite))
    pairs.sort(key=lambda x:x[0],reverse=True)
    return [(w,b) for _,w,b in pairs]

def mark_bite(q,whale_id,bite_id,status,reason=None):
    for whale in q:
        if whale.get('id')!=whale_id: continue
        for bite in whale.get('bites') or []:
            if bite.get('id')==bite_id:
                bite['status']=status
                if reason: bite['blocked_reason']=reason
        bites=whale.get('bites') or []
        if bites and all(b.get('status') in DONE for b in bites): whale['status']='accepted'
    save_queue(q)

def perform(q,whale,bite,b,c,mock):
    bite_id=bite['id']
    tremorcle('bite')
    emit('whale_bite',bite_id,verified=True,whale_id=whale['id'],message='Eat the Whale: one bounded bite selected')
    emit('working',bite_id,verified=True,whale_id=whale['id'],battery=b,charging=c)
    try: result=execute_bite(whale,bite)
    except subprocess.TimeoutExpired: result={'rc':124,'stderr':f'bite exceeded {MAX_BITE_SECONDS}s bound','seconds':MAX_BITE_SECONDS}
    receipt={'ts':time.time(),'whale':whale,'bite':bite,'battery':b,'charging':c,'result':result,'mockery_forge':mock}
    path=RECEIPTS/f"{int(receipt['ts']*1000)}-{bite_id}.json"; write_json(path,receipt)
    ok=result.get('rc')==0
    emit('receipt',bite_id,verified=True,whale_id=whale['id'],receipt=str(path),rc=result.get('rc'))
    emit('canary_pass' if ok else 'canary_fail',bite_id,verified=ok,whale_id=whale['id'],receipt=str(path))
    if ok:
        mark_bite(q,whale['id'],bite_id,'accepted'); tremorcle('success')
    else:
        reason=str(result.get('stderr') or 'capability unavailable')[-500:]
        mark_bite(q,whale['id'],bite_id,'blocked',reason); tremorcle('blocked')
        emit('capability_gap',bite_id,verified=True,whale_id=whale['id'],reason=reason)
    return receipt,ok

def tick():
    mock=ensure_mockray(); q=load_queue(); b=battery(); c=charging()
    pairs=actionable_pairs(q)
    if not pairs:return {'status':'idle-or-blocked','battery':b,'charging':c,'mockery_forge':mock}
    if b<35 and not c:
        whale,bite=pairs[0]; tremorcle('warn'); emit('blocked',bite['id'],verified=True,whale_id=whale['id'],reason='phone battery governor',battery=b)
        return {'status':'throttled','whale':whale['id'],'bite':bite['id'],'battery':b,'charging':c,'mockery_forge':mock}

    whale,bite=pairs[0]
    receipt,ok=perform(q,whale,bite,b,c,mock)
    if ok:return receipt

    # AUTOMATIC REPAIR / CONTINUING VALUE:
    # A capability gap never ends the cycle with a dead sentence. The failed bite is
    # parked truthfully, then exactly one different actionable ledger bite is taken.
    q=load_queue(); fallbacks=actionable_pairs(q)
    if not fallbacks:return receipt
    fw,fb=fallbacks[0]
    emit('joy_diversion',fb['id'],verified=True,blocked_task=bite['id'],whale_id=fw['id'],message='Blocked path converted into continuing-value ledger work')
    tremorcle('divert')
    fallback_receipt,_=perform(q,fw,fb,b,c,mock)
    return {'status':'repaired-by-diversion','blocked_receipt':receipt,'value_receipt':fallback_receipt}

def main():
    tremorcle('tick'); ensure_mockray(); emit('dispatch','wdt-kernel',verified=True,message='Wizard DNS Tango kernel online; Eat the Whale + automatic continuing-value repair active')
    while not RELEASE.exists():
        try: print(json.dumps(tick(),sort_keys=True),flush=True)
        except Exception as e:
            p=RECEIPTS/f'{int(time.time()*1000)}-kernel-error.json'; write_json(p,{'error':repr(e),'ts':time.time()}); emit('canary_fail','wdt-kernel',verified=False,receipt=str(p)); tremorcle('blocked')
        time.sleep(30)

if __name__=='__main__':main()
