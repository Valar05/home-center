#!/usr/bin/env python3
"""Detached Windows voice factory control via existing cauldron; no audio transfers."""
import argparse,json,shutil,subprocess,sys
from pathlib import Path
import ritsu_asmr_phone as t
STATE=Path.home()/'.local/state/ritsu-whisper-v2'
WORKER='tools/campaigns/ritsu_whisper_v2_windows.py'
SELF='tools/campaigns/ritsu_whisper_v2_phone.py'
def main():
 p=argparse.ArgumentParser();p.add_argument('verb',choices=['start','resume','status']);a=p.parse_args()
 STATE.mkdir(parents=True,exist_ok=True);t.STATE=STATE
 lines=['CAMPAIGN=RITSU_WHISPER_V2_CANDIDATE','VERB='+a.verb];rc=2
 try:
  if not shutil.which('cauldron'):raise RuntimeError('Cauldron unavailable')
  commit,_=t.review_source()
  for name in (WORKER,SELF):
   blob=subprocess.check_output(['git','-C',str(t.ROOT),'show',commit+':'+name],timeout=40)
   if blob!=(t.ROOT/name).read_bytes():raise RuntimeError('Source mismatch: '+name)
  digest=t.sha((t.ROOT/WORKER).read_bytes())
  lines+=['SOURCE_COMMIT='+commit,'WORKER_SHA256='+digest]
  if a.verb!='status':
   install=r"""
$ErrorActionPreference='Stop'
$d=Join-Path $env:LOCALAPPDATA 'RitsuWhisperV2\code\__HASH__'
New-Item -ItemType Directory -Force -Path $d|Out-Null
$p=Join-Path $d 'ritsu_whisper_v2_windows.py'
if(!(Test-Path $p)){
 $tmp=$p+'.'+[guid]::NewGuid().ToString('N')+'.incoming'
 Invoke-WebRequest -Uri 'https://raw.githubusercontent.com/Valar05/home-center/__COMMIT__/tools/campaigns/ritsu_whisper_v2_windows.py' -OutFile $tmp -TimeoutSec 40
 if((Get-FileHash -LiteralPath $tmp).Hash -ne '__HASH__'){throw 'SOURCE_DIGEST_MISMATCH'}
 Move-Item -LiteralPath $tmp -Destination $p
}
if((Get-FileHash -LiteralPath $p).Hash -ne '__HASH__'){throw 'SOURCE_DIGEST_MISMATCH'}
[Console]::WriteLine('RITSU_ASMR_REMOTE_OK=1')
"""
   check=r"""
$ErrorActionPreference='Stop'
$p=Join-Path $env:LOCALAPPDATA 'RitsuWhisperV2\code\__HASH__\ritsu_whisper_v2_windows.py'
$j=@{present=(Test-Path -LiteralPath $p -PathType Leaf);matches=$false}
if($j.present){$j.matches=((Get-FileHash -Algorithm SHA256 -LiteralPath $p).Hash -eq '__HASH__')}
$b=[Text.Encoding]::UTF8.GetBytes(($j|ConvertTo-Json -Compress))
$e=[Convert]::ToBase64String($b)
$h=([BitConverter]::ToString(([Security.Cryptography.SHA256]::Create()).ComputeHash($b))).Replace('-','')
[Console]::WriteLine(('JSTART:'+$e.Length))
for($i=0;$i -lt $e.Length;$i+=16){[Console]::WriteLine(('J:{0:D5}:{1}' -f ($i/16),$e.Substring($i,[Math]::Min(16,$e.Length-$i))))}
for($i=0;$i -lt 64;$i+=16){[Console]::WriteLine(('H:{0}:{1}' -f ($i/16),$h.Substring($i,16)))}
[Console]::WriteLine('RITSU_ASMR_REMOTE_OK=1')
"""
   def installed():
    return t.extract_result(t.ps(check.replace('__HASH__',digest),quiet=True,stage='factory-install-check'))
   found=installed()
   if found['present'] and not found['matches']:raise RuntimeError('Existing pinned Windows source differs; preserve it')
   if not found['matches']:
    try:t.ps(install.replace('__HASH__',digest).replace('__COMMIT__',commit),quiet=True,stage='factory-install')
    except (t.RemoteFailure,subprocess.TimeoutExpired):
     if not installed()['matches']:raise
    if not installed()['matches']:raise RuntimeError('Windows source installation not verified')
   lines+=['WINDOWS_SOURCE_VERIFIED=YES']
   launch=r"""
$ErrorActionPreference='Stop'
$n='RitsuWhisperV2-Factory-v1'
$r=Join-Path $env:LOCALAPPDATA 'RitsuWhisperV2'
$p=Join-Path $r 'code\__HASH__\ritsu_whisper_v2_windows.py'
$py=Join-Path $env:USERPROFILE 'Documents\Codex\Venice\PocketTTS\.venv\Scripts\python.exe'
if(!(Test-Path $py)){throw 'EXISTING_POCKET_PYTHON_MISSING'}
if((Get-FileHash -LiteralPath $p).Hash -ne '__HASH__'){throw 'SOURCE_DIGEST_MISMATCH'}
$t=Get-ScheduledTask -TaskName $n -ErrorAction SilentlyContinue
if($t -and $t.State -in @('Running','Queued')){throw 'FACTORY_TASK_ALREADY_ACTIVE'}
if($t -and ($t.Actions.Count -ne 1 -or $t.Actions[0].Execute -ne $py -or $t.Actions[0].Arguments -notmatch 'RitsuWhisperV2\\code\\[A-Fa-f0-9]{64}\\ritsu_whisper_v2_windows\.py" work$')){throw 'FACTORY_TASK_IDENTITY_MISMATCH'}
$act=New-ScheduledTaskAction -Execute $py -Argument ('"'+$p+'" work') -WorkingDirectory $r
$principal=New-ScheduledTaskPrincipal -UserId ([Security.Principal.WindowsIdentity]::GetCurrent().Name) -LogonType Interactive -RunLevel Limited
$settings=New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 30)
Register-ScheduledTask -TaskName $n -Action $act -Principal $principal -Settings $settings -Force|Out-Null
Start-ScheduledTask -TaskName $n
[Console]::WriteLine('RITSU_ASMR_REMOTE_OK=1')
"""
   t.ps(launch.replace('__HASH__',digest),quiet=True,stage='factory-schedule')
   lines+=['DISPATCH_REQUESTED=YES']
  script=r"""
$ErrorActionPreference='Stop'
$n='RitsuWhisperV2-Factory-v1'
$t=Get-ScheduledTask -TaskName $n -ErrorAction SilentlyContinue
$f=Join-Path $env:LOCALAPPDATA 'RitsuWhisperV2\factory-v1\65E99200D19FD2F021F972CD3EAFF3D33F440D8BD78131E243876AA8CE673FA7\status.json'
$j=@{phase='not_started'}
if(Test-Path -LiteralPath $f){$j=Get-Content -Raw -LiteralPath $f|ConvertFrom-Json}
$r=@{factory=$j;taskState='Missing'}
if($t){$r.taskState=[string]$t.State;$r.lastTaskResult=(Get-ScheduledTaskInfo -TaskName $n).LastTaskResult}
$b=[Text.Encoding]::UTF8.GetBytes(($r|ConvertTo-Json -Depth 8 -Compress))
$e=[Convert]::ToBase64String($b)
$h=([BitConverter]::ToString(([Security.Cryptography.SHA256]::Create()).ComputeHash($b))).Replace('-','')
[Console]::WriteLine(('JSTART:'+$e.Length))
for($i=0;$i -lt $e.Length;$i+=16){[Console]::WriteLine(('J:{0:D5}:{1}' -f ($i/16),$e.Substring($i,[Math]::Min(16,$e.Length-$i))))}
for($i=0;$i -lt 64;$i+=16){[Console]::WriteLine(('H:{0}:{1}' -f ($i/16),$h.Substring($i,16)))}
[Console]::WriteLine('RITSU_ASMR_REMOTE_OK=1')
"""
  out=t.ps(script,quiet=True,stage='factory-status')
  lines+=['WINDOWS_RESULT='+json.dumps(t.extract_result(out),separators=(',',':')),'SPEECH_RENDERED=NO','LIVE_RITSU_MODIFIED=NO'];rc=0
 except Exception as e:lines+=['STATUS=BLOCKED','ERROR='+type(e).__name__+': '+str(e)[:350],'NEXT=Check status before retry']
 receipt='\n'.join(lines)+'\n';(STATE/'latest.txt').write_text(receipt,encoding='utf-8')
 with (STATE/'history.txt').open('a',encoding='utf-8') as f:f.write(receipt+'\n')
 print(receipt)
 if shutil.which('termux-clipboard-set'):
  try:subprocess.run(['termux-clipboard-set'],input=receipt,text=True,timeout=5,check=True)
  except (OSError,subprocess.SubprocessError):pass
 return rc
if __name__=='__main__':sys.exit(main())
