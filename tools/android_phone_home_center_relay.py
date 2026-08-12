#!/data/data/com.termux/files/usr/bin/python
from __future__ import annotations
import json, os, secrets, subprocess, sys, time, urllib.request, urllib.error
from pathlib import Path
CFG=Path(os.path.expanduser('~/.config/home-center')); PAIR=CFG/'codex-hub.json'; NODE=CFG/'phone-relay.json'
BASE=os.getenv('HC_PHONE_RELAY_BASE','https://us-central1-home-center-dclar.cloudfunctions.net/phoneHandsRelay'); DEVICE_ID=os.getenv('HC_PHONE_DEVICE_ID','primary-phone'); POLL=float(os.getenv('HC_PHONE_RELAY_POLL_SECONDS','2.0')); OVERLAY_HEARTBEAT_SECONDS=float(os.getenv('HC_OPERATOR_OVERLAY_HEARTBEAT_SECONDS','10.0'))
ROOT=Path(__file__).resolve().parent.parent; sys.path.insert(0,str(ROOT/'tools'))
from android_phone_hands_bridge import observe as hands_observe, act as hands_act
from android_phone_local_executive import execute as local_execute
from android_phone_factory_tools import execute as factory_execute
from android_armory_driver import execute as armory_execute
from android_window_composer import execute as window_execute
from android_phone_status_tts import execute as status_tts_execute
from android_phone_termux_shell import execute as termux_shell_execute
from android_phone_diagnostics import execute as diagnostics_execute
from android_operator_overlay import execute as overlay_execute, heartbeat as overlay_heartbeat, control_gate as overlay_control_gate, screen_activity as overlay_screen_activity
from venice_reactor import execute as venice_execute
FACTORY_ACTIONS={'file_stat','file_hash','file_list','file_mkdir','file_copy','file_move','armory_inventory','armory_ingest'}; ARMORY_ACTIONS={'armory_doctor','armory_slice'}; WINDOW_ACTIONS={'window_status','window_probe','window_compose','window_focus','window_swap'}; STATUS_TTS_ACTIONS={'status_tts_doctor','status_say'}; TERMUX_SHELL_ACTIONS={'phone_shell'}; DIAGNOSTIC_ACTIONS={'phone_diagnostics'}; OVERLAY_ACTIONS={'operator_overlay_status','operator_overlay_start','operator_overlay_update'}; VENICE_ACTIONS={'venice_ingest','venice_observe','venice_mine','venice_status'}
SCREEN_DIRECT_ACTIONS={'tap','swipe','text','keyevent','home','back','recents','launch','force_stop'}; SCREEN_WINDOW_ACTIONS={'window_compose','window_focus','window_swap'}
DEVICE_CAPABILITIES=['phone_hands','phone_files','armory_worker','window_composer','status_tts','termux_shell','operator_overlay','local_qwen','coding_dungeon','voice','phone_diagnostics_readonly','venice_reactor','venice_audio_features']
def http(path,body=None,token=''):
 data=None if body is None else json.dumps(body).encode(); req=urllib.request.Request(BASE+path,data=data,method='GET' if body is None else 'POST'); req.add_header('Content-Type','application/json');
 if token:req.add_header('Authorization','Bearer '+token)
 try:
  with urllib.request.urlopen(req,timeout=45) as r:return json.loads(r.read().decode())
 except urllib.error.HTTPError as e: raise RuntimeError(f'HTTP {e.code} {path}: {e.read().decode("utf-8","replace")[:2000]}')
def load_pair():
 if not PAIR.exists():raise RuntimeError(f'Home Center pairing missing: {PAIR}')
 return json.loads(PAIR.read_text())
def save_pair(cfg): PAIR.write_text(json.dumps(cfg,indent=2)+'\n');os.chmod(PAIR,0o600)
def access_token():
 cfg=load_pair()
 if cfg.get('accessToken') and int(cfg.get('expiresAtMs',0))>int(time.time()*1000)+60000:return cfg['accessToken']
 refresh=cfg.get('refreshToken');
 if not refresh:raise RuntimeError('Home Center refresh token missing; re-pair Termux once')
 gateway=cfg.get('gatewayBase','https://us-central1-home-center-dclar.cloudfunctions.net');req=urllib.request.Request(gateway+'/termuxTokenRefresh',data=json.dumps({'refreshToken':refresh}).encode(),method='POST',headers={'Content-Type':'application/json'})
 with urllib.request.urlopen(req,timeout=30) as r:out=json.loads(r.read().decode())
 cfg['accessToken']=out['access_token'];cfg['refreshToken']=out.get('refresh_token',refresh);cfg['expiresAtMs']=int(time.time()*1000)+int(out.get('expires_in',3300))*1000;save_pair(cfg);return cfg['accessToken']
def ensure_device():
 CFG.mkdir(parents=True,exist_ok=True)
 if NODE.exists():
  data=json.loads(NODE.read_text());token=str(data.get('deviceToken') or '')
  if token:
   try:data['registration']=http('/register',{'deviceId':DEVICE_ID,'deviceToken':token,'label':'Drew Android Phone','capabilities':DEVICE_CAPABILITIES},access_token());NODE.write_text(json.dumps(data,indent=2)+'\n');os.chmod(NODE,0o600)
   except Exception as exc:print('phone-relay registration refresh warning: '+str(exc),file=sys.stderr,flush=True)
   return data
 token=secrets.token_urlsafe(48);reg=http('/register',{'deviceId':DEVICE_ID,'deviceToken':token,'label':'Drew Android Phone','capabilities':DEVICE_CAPABILITIES},access_token());data={'deviceId':DEVICE_ID,'deviceToken':token,'registeredAt':time.time(),'registration':reg};NODE.write_text(json.dumps(data,indent=2)+'\n');os.chmod(NODE,0o600);return data
def dungeon_run(p):
 m=str(p.get('manifest') or '').strip();
 if not m:raise RuntimeError('dungeon_run requires manifest')
 q=subprocess.run([os.path.expanduser('~/bin/dungeon'),'run',m],text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=int(p.get('timeoutSeconds',600)));return {'exit':q.returncode,'output':q.stdout[-20000:]}
def dispatch(a):
 k=a.get('action')
 if k=='observe':return hands_observe(bool(a.get('ui',True)),bool(a.get('screen',False)))
 if k=='local_ask':return local_execute(str(a.get('intent') or a.get('prompt') or 'What is on my screen?'))
 if k=='dungeon_run':return dungeon_run(a)
 if k in VENICE_ACTIONS:return venice_execute({'action':'observe' if k in {'venice_ingest','venice_observe'} else k.replace('venice_',''),'features':a.get('features') or a.get('audio') or {},'source':a.get('source','phone-playback'),'speak':a.get('speak',True),'limit':a.get('limit',200)})
 if k in FACTORY_ACTIONS:return factory_execute(a)
 if k in ARMORY_ACTIONS:return armory_execute(a)
 if k in WINDOW_ACTIONS:return window_execute(a)
 if k in STATUS_TTS_ACTIONS:return status_tts_execute(a)
 if k in TERMUX_SHELL_ACTIONS:return termux_shell_execute(a)
 return hands_act(a)
def execute_action(a):
 k=a.get('action')
 if k in DIAGNOSTIC_ACTIONS:return diagnostics_execute(a)
 if k in OVERLAY_ACTIONS:return overlay_execute(a)
 gate=overlay_control_gate()
 if k=='status_say' and gate.get('muted'):return {'ok':True,'action':'status_say','muted':True,'skipped':True}
 return dispatch(a)
def loop(once=False):
 dev=ensure_device();did=dev['deviceId'];secret=dev['deviceToken'];print(f'Home Center phone relay online: {did}',flush=True);last=0.0
 while True:
  try:
   now=time.monotonic()
   if now-last>=OVERLAY_HEARTBEAT_SECONDS:
    try:overlay_heartbeat()
    except Exception as exc:print('operator-overlay heartbeat warning: '+str(exc),file=sys.stderr,flush=True)
    last=now
   pulled=http('/pull',{'deviceId':did,'deviceToken':secret,'leaseMs':90000});cmd=pulled.get('command')
   if cmd:
    cid=cmd['commandId']
    try:result=execute_action(cmd.get('action') or {});http('/complete',{'deviceId':did,'deviceToken':secret,'commandId':cid,'status':'completed','result':result});print(json.dumps({'commandId':cid,'status':'completed'}),flush=True)
    except Exception as exc:http('/complete',{'deviceId':did,'deviceToken':secret,'commandId':cid,'status':'failed','error':str(exc)[:4000]});print(json.dumps({'commandId':cid,'status':'failed','error':str(exc)}),flush=True)
   if once:return
  except KeyboardInterrupt:raise
  except Exception as exc:
   print('phone-relay error: '+str(exc),file=sys.stderr,flush=True)
   if once:raise
  time.sleep(POLL)
if __name__=='__main__':loop('--once' in sys.argv)
