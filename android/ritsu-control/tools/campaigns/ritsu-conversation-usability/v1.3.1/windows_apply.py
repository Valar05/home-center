#!/usr/bin/env python3
"""Windows Ritsu usability backend stage, apply and rollback.
Run ONLY by the established phone->cauldron onego campaign.
No ChatGPT send, no token read, no journal rewrite, no GitHub/Home Center.
"""
from pathlib import Path
import base64,hashlib,http.client,json,os,re,shutil,subprocess,sys,time,zipfile

VERSION='1.3.1'
BASE=Path.home()/'.ritsu-control'/'usability-packet-v1.3.1'
LIVE=Path(r'C:\Users\dclar\AppData\Local\RitsuControlBridge\release-016')
VOICE=Path.home()/'workspace'/'ritsu-faster-qwen3-tts'/'ritsu_say.py'
VOICE_SHA='3dda464df8d5e24d29db471df7c7b8d70d28741c98866996a980afe5443c6ad8'
SERVER=Path('tools/ritsu-local-server/server.mjs')
BRIDGE=Path('tools/campaigns/ritsu_control_playwright_bridge.mjs')
HOOK=Path('tools/ritsu-local-server/ritsu_pocket_voice_hook.mjs')
STATE=BASE/'stage.json'

class Block(Exception):pass

def digest(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()

def run(argv,timeout=30):
 try:r=subprocess.run(argv,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=timeout,check=False)
 except subprocess.TimeoutExpired:raise Block('COMMAND_TIMEOUT')
 if r.returncode!=0:raise Block('COMMAND_FAILED_'+str(r.returncode))
 return r.stdout.decode('utf8','replace')

def ps(body,timeout=20):
 # No script from ChatGPT text becomes an arbitrary shell tool here; fixed command list.
 enc=base64.b64encode(body.encode('utf-16le')).decode('ascii')
 return run(['powershell.exe','-NoProfile','-NonInteractive','-EncodedCommand',enc],timeout)

def voice():
 if not VOICE.is_file() or digest(VOICE)!=VOICE_SHA:raise Block('VOICE_SENDER_HASH_MISMATCH')
 py=VOICE.parent/'.venv'/'Scripts'/'python.exe'
 if not py.is_file():raise Block('VOICE_PYTHON_MISSING')

def source():
 for item in (SERVER,BRIDGE):
  if not (LIVE/item).is_file():raise Block('LIVE_SOURCE_MISSING_'+item.name)

def inspect_process():
 # Reuse the exact live process contract proven by the accepted SSE v4 repair.
 # No Task Scheduler invocation or guessed service restart command.
 script=r'''$expected='C:\Users\dclar\AppData\Local\RitsuControlBridge\release-016\tools\ritsu-local-server\server.mjs';
$items=@(Get-CimInstance Win32_Process -Filter "Name='node.exe'" | Where-Object {$_.CommandLine -match 'ritsu-local-server[\\/]server\.mjs'});
if($items.Count -ne 1){Write-Output 'NOT_UNIQUE';exit 0};
$p=$items[0];$exe=[string]$p.ExecutablePath;$cmd=([string]$p.CommandLine).Trim();
if(-not [IO.File]::Exists($exe)){Write-Output 'EXE_MISSING';exit 0};
$pattern='^\s*"?'+[regex]::Escape($exe)+'"?\s+"?'+[regex]::Escape($expected)+'"?\s*$';
if($cmd -notmatch $pattern){Write-Output 'NONSTANDARD_LAUNCH';exit 0};
$ports=@(Get-NetTCPConnection -State Listen -OwningProcess ([int]$p.ProcessId) -ErrorAction SilentlyContinue | Where-Object {$_.LocalPort -eq 19647 -or $_.LocalPort -eq 19646});
if($ports.Count -ne 1){Write-Output 'PORT_AMBIGUOUS';exit 0};
$port=[int]$ports[0].LocalPort;$ip=[string]$ports[0].LocalAddress;
if(($port -eq 19647 -and $ip -ne '127.0.0.1') -or ($port -eq 19646 -and $ip -notmatch '^100\.')){Write-Output 'PORT_BIND_INVALID';exit 0};
$o=@{pid=[int]$p.ProcessId;exe=$exe;script=$expected;port=$port;ip=$ip};
Write-Output ([Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes(($o|ConvertTo-Json -Compress))))'''
 text=ps(script).strip()
 try:
  obj=json.loads(base64.b64decode(text,validate=True))
 except Exception:raise Block('VERIFIED_NODE_RESTART_CONTRACT_FAILED_'+text[:30])
 if (not isinstance(obj,dict) or obj.get('script')!=str(LIVE/SERVER)
  or not Path(str(obj.get('exe',''))).is_file()
  or (obj.get('port'),obj.get('ip')) not in ((19647,'127.0.0.1'),(19646,'100.68.37.106'))
  or not isinstance(obj.get('pid'),int) or obj['pid']<1):
  raise Block('SERVER_RESTART_IDENTITY_NOT_VERIFIED')
 return obj

def journal_quiescent():
 p=Path.home()/'.ritsu-control'/'local-link'/'events.jsonl'
 if not p.is_file() or p.stat().st_size>16*1024*1024:raise Block('JOURNAL_UNAVAILABLE_OR_OVERSIZE')
 turns={};seq=0
 for row in p.read_text(encoding='utf8').splitlines():
  if not row.strip():continue
  v=json.loads(row)
  if v.get('seq')!=seq+1:raise Block('JOURNAL_SEQUENCE_AMBIGUOUS')
  seq+=1
  if v.get('turnId'):turns[v['turnId']]=v.get('type')
 if any(x in ('accepted','partial') for x in turns.values()):
  raise Block('INFLIGHT_TURN_REFUSE_SERVER_RESTART')
 return seq

def stage():
 BASE.mkdir(parents=True,exist_ok=True)
 packet=BASE/'packet.zip'
 if not packet.is_file():raise Block('TRANSFER_PACKET_NOT_FOUND')
 unpack=BASE/'packet';dest=BASE/'staged-tree'
 if STATE.exists():
  d=json.loads(STATE.read_text())
  if d.get('version')==VERSION and all((dest/name).is_file() for name in (SERVER,BRIDGE,HOOK)):
   return 'ALREADY_STAGED_VERIFIED_EXPECTED'
  raise Block('PREEXISTING_STAGE_AMBIGUOUS')
 if dest.exists():raise Block('UNRECORDED_STAGE_EXISTS')
 with zipfile.ZipFile(packet) as z:
  names=z.namelist()
  if set(names)!={'patch_backend.py','ritsu_pocket_voice_hook.mjs','windows_apply.py'}:
   raise Block('BACKEND_PACKET_UNEXPECTED_MEMBERS')
  for info in z.infolist():
   if info.file_size>90000 or info.filename.startswith('/') or '..' in Path(info.filename).parts:
    raise Block('BACKEND_PACKET_UNSAFE_MEMBER')
  if unpack.exists():
   for item in names:
    if not (unpack/item).is_file() or hashlib.sha256((unpack/item).read_bytes()).digest()!=hashlib.sha256(z.read(item)).digest():
     raise Block('EXISTING_BOOTSTRAP_EXTRACTION_DIFFERS')
  else:z.extractall(unpack)
 source();voice();inspect_process();journal_quiescent()
 before={str(x):digest(LIVE/x) for x in (SERVER,BRIDGE)}
 for name in (SERVER,BRIDGE):
  p=dest/name;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(LIVE/name,p)
 run([sys.executable,str(unpack/'patch_backend.py'),str(dest)],timeout=18)
 for name in (SERVER,BRIDGE,HOOK):run(['node.exe','--check',str(dest/name)],timeout=12)
 after={str(x):digest(dest/x) for x in (SERVER,BRIDGE,HOOK)}
 data={'version':VERSION,'before':before,'after':after,'journal_seq':journal_quiescent(),'state':'STAGED'}
 tmp=STATE.with_suffix('.tmp');tmp.write_text(json.dumps(data,sort_keys=True));os.replace(tmp,STATE)
 return 'STAGED_AND_NODE_SYNTAX_VERIFIED'

def listener():
 try:
  conn=http.client.HTTPConnection('127.0.0.1',19647,timeout=5)
  conn.request('GET','/v1/ritsu/status',headers={'Connection':'close'})
  resp=conn.getresponse();code=resp.status;resp.read(1000);conn.close();return code
 except Exception:return None

def restart():
 # launch.json is captured before any source mutations. It is the durable
 # rollback identity, even if the attempted new process died after stop.
 launch_file=BASE/'verified-launch.json'
 if not launch_file.is_file():raise Block('VERIFIED_LAUNCH_RECIPE_MISSING')
 a=json.loads(launch_file.read_text())
 if a.get('script')!=str(LIVE/SERVER) or (a.get('port'),a.get('ip')) not in ((19647,'127.0.0.1'),(19646,'100.68.37.106')):
  raise Block('LAUNCH_RECIPE_INVALID')
 if not Path(a['exe']).is_file():raise Block('NODE_EXECUTABLE_GONE')
 # A previous launch failure can leave no process, but a foreign/live
 # process must NEVER be stopped. Check exact PID and executable identity.
 script=r'''$ErrorActionPreference='Stop';
$exe='__EXE__';$path='__PATH__';$previous=__PID__;$port=__PORT__;$ip='__IP__';
$active=@(Get-CimInstance Win32_Process -Filter "Name='node.exe'" | Where-Object {$_.CommandLine -match 'ritsu-local-server[\\/]server\.mjs'});
if($active.Count -gt 1){throw 'AMBIGUOUS_NODE_PROCESSES'};
if($active.Count -eq 1){
 $p=$active[0];$cmd=([string]$p.CommandLine).Trim();
 $pattern='^\s*"?'+[regex]::Escape($exe)+'"?\s+"?'+[regex]::Escape($path)+'"?\s*$';
 if($cmd -notmatch $pattern -or [string]$p.ExecutablePath -ne $exe){throw 'CHANGED_NODE_LAUNCH'};
 $ports=@(Get-NetTCPConnection -State Listen -OwningProcess ([int]$p.ProcessId) -ErrorAction SilentlyContinue | Where-Object {$_.LocalPort -eq $port -and $_.LocalAddress -eq $ip});
 if($ports.Count -eq 1 -and [int]$p.ProcessId -ne $previous){Write-Output 'ALREADY_RESTARTED';exit 0};
 Stop-Process -Id ([int]$p.ProcessId) -ErrorAction Stop;
 Start-Sleep -Milliseconds 650;
};
if($port -eq 19647){$env:RITSU_TAILSCALE_SERVE='1'};
$next=Start-Process -FilePath $exe -ArgumentList @('"'+$path+'"') -WorkingDirectory (Split-Path $path) -PassThru -WindowStyle Hidden;
$live=$false;
for($i=0;$i -lt 30;$i++){
 Start-Sleep -Milliseconds 350;
 try{$check=@(Get-NetTCPConnection -OwningProcess $next.Id -State Listen -ErrorAction Stop | Where-Object {$_.LocalPort -eq $port -and $_.LocalAddress -eq $ip});if($check.Count -gt 0){$live=$true;break}}catch{};
 if($next.HasExited){break};
};
if(-not $live){throw 'VERIFIED_NODE_DID_NOT_LISTEN'};
Write-Output 'LISTENER_RESTARTED';'''
 for marker,value in (('__EXE__',a['exe']),('__PATH__',a['script']),('__PID__',str(a['pid'])),('__PORT__',str(a['port'])),('__IP__',a['ip'])):
  if "'" in value:raise Block('UNSAFE_QUOTE_IN_RESTART_PATH')
  script=script.replace(marker,value)
 output=ps(script,timeout=35).strip()
 if output not in ('LISTENER_RESTARTED','ALREADY_RESTARTED'):
  raise Block('RESTART_UNEXPECTED_RECEIPT')
 if listener()!=401:raise Block('RESTART_AUTH_GATE_NOT_VERIFIED')

def backup_dir():return BASE/'original-backup'

def rollback_files():
 folder=backup_dir()
 for name in (SERVER,BRIDGE):
  f=folder/name
  if not f.is_file():raise Block('BACKUP_MISSING_'+name.name)
 for name in (SERVER,BRIDGE):
  src=folder/name;dest=LIVE/name
  temp=dest.with_name(dest.name+'.v131.rollback');shutil.copy2(src,temp);os.replace(temp,dest)
 # New hook isn't needed by original server, but keep it as an inert retained file
 # rather than deleting any preexisting file on an ambiguous rollback.

def apply():
 if not STATE.is_file():raise Block('STAGE_RECEIPT_MISSING')
 state=json.loads(STATE.read_text())
 if state.get('version')!=VERSION:raise Block('STAGE_VERSION_MISMATCH')
 if state.get('state')=='DEPLOYED':return 'ALREADY_DEPLOYED'
 if state.get('state')!='STAGED':raise Block('STAGE_STATUS_NOT_APPLICABLE')
 source();voice();inspect_process();journal_quiescent()
 for name in (SERVER,BRIDGE):
  if digest(LIVE/name)!=state['before'][str(name)]:raise Block('LIVE_SOURCE_CHANGED_SINCE_PREFLIGHT')
  if digest(BASE/'staged-tree'/name)!=state['after'][str(name)]:raise Block('STAGED_SOURCE_CHANGED')
 if digest(BASE/'staged-tree'/HOOK)!=state['after'][str(HOOK)]:raise Block('VOICE_HOOK_STAGE_CHANGED')
 # Pin exact executable, process command, bind and port before changing sources.
 recipe=inspect_process()
 launch_file=BASE/'verified-launch.json'
 if launch_file.exists():
  if json.loads(launch_file.read_text())!=recipe:
   raise Block('VERIFIED_LAUNCH_RECIPE_COLLISION')
 else:
  tmp=launch_file.with_suffix('.new');tmp.write_text(json.dumps(recipe,sort_keys=True));os.replace(tmp,launch_file)
 dest=backup_dir();
 if dest.exists():raise Block('BACKUP_ALREADY_PRESENT_RECONCILE')
 dest.mkdir(parents=True)
 for name in (SERVER,BRIDGE):
  p=dest/name;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(LIVE/name,p)
 state['state']='APPLY_STARTED';STATE.write_text(json.dumps(state))
 try:
  for name in (SERVER,BRIDGE,HOOK):
   original=BASE/'staged-tree'/name;target=LIVE/name;target.parent.mkdir(parents=True,exist_ok=True)
   if name==HOOK and target.exists():raise Block('HOOK_ALREADY_EXISTS')
   temp=target.with_name(target.name+'.v131.new');shutil.copy2(original,temp)
   if digest(temp)!=state['after'][str(name)]:raise Block('PRE_REPLACE_HASH_MISMATCH')
   os.replace(temp,target)
  restart()
  state['state']='DEPLOYED';STATE.write_text(json.dumps(state))
  return 'DEPLOYED_AND_LISTENER_401_VERIFIED'
 except Exception:
  rollback_files()
  with __import__('contextlib').suppress(Exception):restart()
  state['state']='ROLLED_BACK_AFTER_FAILURE';STATE.write_text(json.dumps(state))
  raise

def rollback():
 if not STATE.is_file():raise Block('STAGE_RECEIPT_MISSING')
 state=json.loads(STATE.read_text())
 if state.get('state') not in ('APPLY_STARTED','DEPLOYED','ROLLED_BACK_AFTER_FAILURE'):
  return 'NO_LIVE_CHANGE_TO_ROLL_BACK'
 if state.get('state')=='ROLLED_BACK_AFTER_FAILURE':return 'ALREADY_ROLLED_BACK'
 rollback_files();restart();state['state']='ROLLED_BACK_AFTER_FAILURE';STATE.write_text(json.dumps(state))
 return 'ORIGINAL_SOURCES_RESTORED_AND_RESTART_VERIFIED'

if __name__=='__main__':
 if len(sys.argv)!=2 or sys.argv[1] not in ('stage','apply','rollback'):
  raise SystemExit('usage windows_apply.py stage|apply|rollback')
 op=sys.argv[1];p={'stage':'WINDOWS_BACKEND_STAGE','apply':'WINDOWS_BACKEND_APPLY','rollback':'WINDOWS_BACKEND_ROLLBACK'}[op]
 try:
  result=globals()[op]()
  obj={'phase':p,'result':result,'error':''}
 except Block as e:obj={'phase':p,'result':'','error':str(e)[:100]}
 except Exception as e:obj={'phase':p,'result':'','error':'UNEXPECTED_'+type(e).__name__}
 print('RITSU_UX_RECEIPT='+base64.b64encode(json.dumps(obj,separators=(',',':')).encode()).decode(),flush=True)
 sys.exit(0) # Structured receipt carries the failure classification.
