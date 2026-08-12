#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import json
import os
import re
import subprocess

WINDOWS_TARGETS={'THECAULDRON'}

def decode_job(value):
 padding='='*((4-len(value)%4)%4)
 return json.loads(base64.urlsafe_b64decode((value+padding).encode()).decode())

def env_key(target): return re.sub(r'[^A-Za-z0-9]+','_',target).upper()
def host_for(target): return os.environ.get(f'HC_HANDS_SSH_HOST_{env_key(target)}',target).strip()
def encoded_ps(script): return base64.b64encode(script.encode('utf-16le')).decode('ascii')

def run_ps(host,script,timeout):
 ssh=os.environ.get('HC_HANDS_SSH_BIN','ssh')
 command=[ssh,'-o','BatchMode=yes','-o',f'ConnectTimeout={min(15,max(2,int(timeout)))}',host,'powershell.exe','-NoLogo','-NoProfile','-NonInteractive','-EncodedCommand',encoded_ps(script)]
 p=subprocess.run(command,text=True,capture_output=True,timeout=timeout)
 return {'rc':p.returncode,'stdout':p.stdout[-12000:],'stderr':p.stderr[-6000:]}

def ps_quote(value): return "'"+str(value).replace("'","''")+"'"

def step_script(step):
 op=step['op']; args=step.get('args') or {}
 if op=='system.status':
  return "$ErrorActionPreference='Stop'; [ordered]@{ok=$true;machine=$env:COMPUTERNAME;user=[Environment]::UserName;interactive=[Environment]::UserInteractive;ps=$PSVersionTable.PSVersion.ToString()}|ConvertTo-Json -Compress"
 if op=='process.list':
  return "$ErrorActionPreference='Stop'; [ordered]@{ok=$true;processes=@(Get-Process|Select-Object -First 250 Id,ProcessName,MainWindowTitle)}|ConvertTo-Json -Depth 5 -Compress"
 if op=='process.start':
  command=str(args.get('command') or '').strip(); arguments=str(args.get('arguments') or ''); cwd=str(args.get('workingDirectory') or '')
  if not command: raise ValueError('process.start command required')
  extra=f" -ArgumentList {ps_quote(arguments)}" if arguments else ''
  extra+=f" -WorkingDirectory {ps_quote(cwd)}" if cwd else ''
  return f"$ErrorActionPreference='Stop'; $p=Start-Process -FilePath {ps_quote(command)}{extra} -PassThru; [ordered]@{{ok=$true;pid=$p.Id}}|ConvertTo-Json -Compress"
 if op=='process.stop':
  pid=int(args.get('pid') or 0)
  if pid<1: raise ValueError('process.stop pid required')
  return f"$ErrorActionPreference='Stop'; Stop-Process -Id {pid} -ErrorAction Stop; [ordered]@{{ok=$true;pid={pid}}}|ConvertTo-Json -Compress"
 if op=='shell.exec':
  command=str(args.get('command') or '').strip()
  if not command: raise ValueError('shell.exec command required')
  return "$ErrorActionPreference='Stop'; try { & {\n"+command+"\n}; if($LASTEXITCODE -is [int] -and $LASTEXITCODE -ne 0){exit $LASTEXITCODE} } catch { [Console]::Error.WriteLine($_.Exception.Message); exit 1 }"
 raise NotImplementedError(op)

def parse_last_json(text):
 for line in reversed(str(text or '').splitlines()):
  try:
   value=json.loads(line.strip())
   if isinstance(value,dict): return value
  except Exception: pass
 return None

def expectation_failure(step,result):
 expected=step.get('expect') or {}
 if not expected:return None
 actual=parse_last_json(result.get('stdout')) or {'ok':result.get('rc')==0,'rc':result.get('rc')}
 for key,value in expected.items():
  if actual.get(key)!=value:return f'expect_mismatch:{key}'
 return None

def execute(job):
 target=str(job.get('target') or '')
 if target not in WINDOWS_TARGETS:return {'rc':78,'status':'unconfigured','reason':'ssh_target_unsupported','safeToFallback':True}
 host=host_for(target)
 if not host:return {'rc':78,'status':'unconfigured','reason':'ssh_host_missing','safeToFallback':True}
 timeout=max(5,min(int(job.get('maxRuntimeSeconds') or 120),300)); results=[]; scripts=[]
 # Preflight the complete operation vocabulary before any remote side effect.
 for step in job.get('steps') or []:
  try:scripts.append(step_script(step))
  except NotImplementedError:return {'rc':78,'status':'unsupported','reason':f"ssh_op_unsupported:{step.get('op')}",'safeToFallback':True}
  except Exception as exc:return {'rc':64,'status':'invalid','reason':f'{type(exc).__name__}: {exc}','safeToFallback':False}
 try:
  probe=run_ps(host,"[ordered]@{ok=$true;probe='hands-router'}|ConvertTo-Json -Compress",min(timeout,15))
 except FileNotFoundError:return {'rc':78,'status':'unconfigured','reason':'ssh_binary_missing','safeToFallback':True}
 except subprocess.TimeoutExpired:return {'rc':78,'status':'unavailable','reason':'ssh_probe_timeout','safeToFallback':True}
 if probe['rc']!=0:return {'rc':78,'status':'unavailable','reason':'ssh_probe_failed','probe':probe,'safeToFallback':True}
 for index,(step,script) in enumerate(zip(job.get('steps') or [],scripts)):
  try:result=run_ps(host,script,timeout)
  except subprocess.TimeoutExpired:return {'rc':124,'status':'timeout','reason':'ssh_timeout_after_execution_started','steps':results,'safeToFallback':False}
  mismatch=expectation_failure(step,result); row={'index':index,'op':step.get('op'),**result,'expectFailure':mismatch}; results.append(row)
  if result['rc']!=0 or mismatch:return {'rc':result['rc'] or 65,'status':'failed','steps':results,'reason':mismatch or 'remote_step_failed','safeToFallback':False}
 return {'rc':0,'status':'completed','host':host,'steps':results,'safeToFallback':False}

def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--job-b64',required=True); args=ap.parse_args()
 try:result=execute(decode_job(args.job_b64))
 except Exception as exc:result={'rc':125,'status':'failed','reason':f'{type(exc).__name__}: {exc}','safeToFallback':False}
 print(json.dumps(result,ensure_ascii=False,sort_keys=True)); return int(result.get('rc') or 0)
if __name__=='__main__':raise SystemExit(main())
