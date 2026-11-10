#!/usr/bin/env python3
"""Termux phone entrypoint. Uses the owner's installed cauldron command for SSH."""
import argparse, base64, hashlib, json, os, re, shutil, subprocess, sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
STATE=Path.home()/'.local/state/ritsu-asmr'
REMOTE='tools/campaigns/ritsu_asmr_windows.py'
LOCAL='tools/campaigns/ritsu_asmr_phone.py'
REPO='Valar05/home-center'
def shell(*args):
 p=subprocess.run(args,text=True,capture_output=True,timeout=40)
 if p.returncode:raise RuntimeError((p.stderr or p.stdout)[-700:])
 return p.stdout.strip()
def sha(data):return hashlib.sha256(data).hexdigest().upper()
def ps(script):
 cmd=base64.b64encode(script.encode('utf-16le')).decode('ascii')
 p=subprocess.run(['cauldron','powershell.exe','-NoLogo','-NoProfile','-NonInteractive','-EncodedCommand',cmd],text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=180)
 output=p.stdout[-5000:]
 print(output,flush=True)
 if p.returncode:raise RuntimeError('CAULDRON_REMOTE_EXIT_'+str(p.returncode))
 return output
def quote(s):return "'"+s.replace("'","''")+"'"
def review_source():
 if not (ROOT/'AGENTS.md').is_file():raise RuntimeError('Not the intended Home Center checkout')
 url=shell('git','-C',str(ROOT),'remote','get-url','origin')
 if not re.search(r'Valar05/home-center(?:\\.git)?$',url,re.I):raise RuntimeError('Wrong Git remote')
 commit=shell('git','-C',str(ROOT),'rev-parse','HEAD')
 if not re.fullmatch(r'[0-9a-f]{40}',commit):raise RuntimeError('Invalid Git revision')
 for path in (LOCAL,REMOTE):
  data=shell('git','-C',str(ROOT),'show',commit+':'+path).encode()
  if data!= (ROOT/path).read_bytes():raise RuntimeError('Pinned source mismatch: '+path)
 return commit,sha((ROOT/REMOTE).read_bytes())
def staging(episode,data):
 digest=sha(data);coded=base64.b64encode(data).decode()
 target='$env:LOCALAPPDATA\\RitsuASMR\\incoming\\'+episode+'-'+digest+'.b64'
 # Each chunk is independently idempotent, verified by offset and expected bytes.
 for off in range(0,len(coded),3000):
  piece=coded[off:off+3000]
  script="$ErrorActionPreference='Stop';$p="+quote(target)+";$p=$ExecutionContext.InvokeCommand.ExpandString($p);$dir=Split-Path $p;New-Item -ItemType Directory -Force -Path $dir|Out-Null;"
  script+="$s=if(Test-Path -LiteralPath $p){[IO.File]::ReadAllText($p)}else{''};$o="+str(off)+";$chunk="+quote(piece)+";"
  script+="if($s.Length -eq $o){[IO.File]::AppendAllText($p,$chunk,[Text.Encoding]::ASCII)}elseif($s.Length -ge ($o+$chunk.Length) -and $s.Substring($o,$chunk.Length) -ceq $chunk){}else{throw 'Staging offset collision'};"
  script+="Write-Output ('STAGED='+[IO.File]::ReadAllText($p).Length)"
  ps(script)
 return digest,target
def remote_run(commit,expected,verb,episode,input_data):
 # The remote file is downloaded from exactly the checked-in SHA and verified
 # before execution. No local Windows checkout, agent, or live relay is altered.
 input_path=''
 if input_data is not None:
  digest,encoded_path=staging(episode,input_data)
  input_path='$env:LOCALAPPDATA\\RitsuASMR\\incoming\\'+episode+'-'+digest+'.txt'
 script="""$ErrorActionPreference='Stop'
$root=Join-Path $env:LOCALAPPDATA 'RitsuASMR'
$code=Join-Path $root 'code'
New-Item -ItemType Directory -Force -Path $code | Out-Null
$program=Join-Path $code 'ritsu_asmr_windows.py'
$expected='__SHA__'
if (!(Test-Path -LiteralPath $program) -or ((Get-FileHash -Algorithm SHA256 -LiteralPath $program).Hash -ne $expected)) {
 $temporary=$program+'.incoming'
 Invoke-WebRequest -Uri 'https://raw.githubusercontent.com/Valar05/home-center/__COMMIT__/tools/campaigns/ritsu_asmr_windows.py' -OutFile $temporary -TimeoutSec 40
 if ((Get-FileHash -Algorithm SHA256 -LiteralPath $temporary).Hash -ne $expected) {Remove-Item -LiteralPath $temporary -Force;throw 'Pinned source digest mismatch'}
 Move-Item -LiteralPath $temporary -Destination $program -Force
}
$python=Join-Path $env:USERPROFILE 'workspace\\ritsu-faster-qwen3-tts\\.venv\\Scripts\\python.exe'
if (!(Test-Path -LiteralPath $python)) {throw 'Approved Python runtime not found'}
$arguments=@($program,'__VERB__','--episode','__EP__')
__INPUT__
& $python @arguments
if ($LASTEXITCODE -ne 0) {exit $LASTEXITCODE}
"""
 if input_data is not None:
  extra="""$encoded=Join-Path $env:LOCALAPPDATA '__ENCODED__'
$incoming=Join-Path $env:LOCALAPPDATA '__INCOMING__'
$raw=[IO.File]::ReadAllText($encoded)
$bytes=[Convert]::FromBase64String($raw)
$actual=([BitConverter]::ToString(([Security.Cryptography.SHA256]::Create()).ComputeHash($bytes))).Replace('-','')
if($actual -ne '__DIGEST__'){throw 'Staged transcript digest mismatch'}
[IO.File]::WriteAllBytes($incoming,$bytes)
$arguments+=@('--input',$incoming)
"""
  extra=extra.replace('__ENCODED__','RitsuASMR\\incoming\\'+episode+'-'+digest+'.b64').replace('__INCOMING__','RitsuASMR\\incoming\\'+episode+'-'+digest+'.txt').replace('__DIGEST__',digest)
 else:extra=''
 script=script.replace('__SHA__',expected).replace('__COMMIT__',commit).replace('__VERB__',verb).replace('__EP__',episode).replace('__INPUT__',extra)
 return ps(script)
def main():
 p=argparse.ArgumentParser()
 p.add_argument('verb',nargs='?',default='doctor',choices=['doctor','start','status','resume','stop','receipts'])
 p.add_argument('--episode',default='RITSU_ASMR_CANARY')
 p.add_argument('--input',type=Path)
 a=p.parse_args()
 STATE.mkdir(parents=True,exist_ok=True)
 lines=['CAMPAIGN=RITSU_ASMR_OFFLINE_v1','EPISODE='+a.episode,'VERB='+a.verb]
 try:
  if not re.fullmatch(r'[A-Za-z0-9_-]{1,64}',a.episode):raise ValueError('Invalid episode ID')
  if a.input and a.verb!='start':raise ValueError('--input only allowed with start')
  if not shutil.which('cauldron'):raise RuntimeError('Existing cauldron command unavailable; no SSH substitution')
  commit,hashvalue=review_source()
  lines+=['SOURCE_COMMIT='+commit,'WINDOWS_SOURCE_SHA256='+hashvalue]
  data=a.input.read_bytes() if a.input else None
  if data is not None and len(data)>150000:raise ValueError('Input exceeds 150 kB')
  if data is not None:data.decode('utf-8-sig')
  remote_run(commit,hashvalue,a.verb,a.episode,data)
  lines+=['SSH_COMMAND_RETURNED=YES','RENDER_NOT_INFERRED=YES']
  result=0
 except Exception as e:
  lines+=['STATUS=BLOCKED','ERROR='+type(e).__name__+': '+str(e)[:500]]
  result=2
 receipt='\\n'.join(lines)+'\\n'
 # Do not put transcript, keys, or credentials in the receipt or clipboard.
 (STATE/'latest.txt').write_text(receipt,encoding='utf-8')
 print(receipt,flush=True)
 if shutil.which('termux-clipboard-set'):
  subprocess.run(['termux-clipboard-set'],input=receipt,text=True,capture_output=True,timeout=5)
 else:print('CLIPBOARD_UNAVAILABLE=1')
 return result
if __name__=='__main__':sys.exit(main())
