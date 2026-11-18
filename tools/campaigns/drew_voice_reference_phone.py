#!/usr/bin/env python3
"""Taildrop-only private voice reference collection; no synthesis."""
import argparse, base64, hashlib, json, os, re, shutil, subprocess, sys
from pathlib import Path
import ritsu_asmr_phone as transport

STATE=Path.home()/'.local/state/drew-voice-reference'
SOURCE=Path.home()/'storage/downloads/drew-whisper.m4a'
REL=r'DrewVoice\references'
MAX=4*1024*1024

def sha(data):return hashlib.sha256(data).hexdigest().upper()

def source_commit():
 commit,_=transport.review_source()
 for p in ('tools/campaigns/drew_voice_reference_phone.py',):
  if subprocess.check_output(['git','-C',str(transport.ROOT),'show',commit+':'+p],timeout=40)!=(transport.ROOT/p).read_bytes():
   raise RuntimeError('Pinned ingress source mismatch')
 return commit

def remote(script,stage):
 # Reuse known Cauldron shell and terminal frame decoder, but never echo audio payload.
 cmd=base64.b64encode(script.encode('utf-16le')).decode('ascii')
 if len(cmd)>6500:raise RuntimeError('Encoded SSH budget exceeded at '+stage)
 p=subprocess.run(['cauldron','powershell.exe','-NoLogo','-NoProfile','-NonInteractive','-EncodedCommand',cmd],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=180)
 out=re.sub(r'\x1b\][^\x07]*(?:\x07|\x1b\\)','',p.stdout or '')
 out=re.sub(r'\x1b\[[0-?]*[ -/]*[@-~]','',out)
 lines=[x.strip() for x in out.splitlines()]
 if p.returncode or lines.count('DREW_REFERENCE_OK=1')!=1:
  raise RuntimeError('Remote stage blocked: '+stage+' exit='+str(p.returncode)+'; outcome may be unknown; rerun status or resume')
 return lines

def inspect(digest,size,collect=False):
 # Windows GUI receives into Downloads; never drain unrelated inbox files.
 script=r"""
$ErrorActionPreference='Stop'
$d=Join-Path $env:LOCALAPPDATA 'DrewVoice\references\__HASH__'
$f=Join-Path $d 'drew-whisper.m4a'
$n=__SIZE__;$h='__HASH__'
function valid($p){(Test-Path -LiteralPath $p -PathType Leaf) -and (Get-Item -LiteralPath $p).Length -eq $n -and (Get-FileHash -LiteralPath $p).Hash -eq $h}
$j=@{phase='awaiting_taildrop';bytes=0}
if(Test-Path -LiteralPath $f){
 if(!(valid $f)){throw 'FINAL_COLLISION'}
 $j=@{phase='reference_delivered_verified';bytes=$n;sha256=$h;path=$f}
}else{
 $roots=@((Join-Path $env:USERPROFILE 'Downloads'))
 $k=Get-ItemProperty 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders' -ErrorAction SilentlyContinue
 $v=$k.'{374DE290-123F-4565-9164-39C4925E467B}'
 if($v){$roots+=[Environment]::ExpandEnvironmentVariables($v)}
 $found=$null
 foreach($r in ($roots|Select-Object -Unique)){
  foreach($p in @($r,(Join-Path $r 'Taildrop'),(Join-Path $r 'Tailscale'))){
   if(!(Test-Path -LiteralPath $p -PathType Container)){continue}
   foreach($a in (Get-ChildItem -LiteralPath $p -File -Filter 'drew-whisper*.m4a')){
    if($a.Name -match '^drew-whisper(?: \(\d+\)|-\d+)?\.m4a$' -and (valid $a.FullName)){$found=$a.FullName;break}
   }
   if($found){break}
  }
  if($found){break}
 }
 if($found){
  $j=@{phase='taildrop_found_not_collected';bytes=$n;sha256=$h;receivedPath=$found}
  if(__COLLECT__){
   New-Item -ItemType Directory -Force -Path $d|Out-Null
   $t=Join-Path $d ([guid]::NewGuid().ToString('N')+'.incoming')
   try{Copy-Item -LiteralPath $found -Destination $t;if(!(valid $t)){throw 'COPY_MISMATCH'};[IO.File]::Move($t,$f)}
   finally{if(Test-Path -LiteralPath $t){Remove-Item -LiteralPath $t -Force}}
   if(!(valid $f)){throw 'FINAL_MISMATCH'}
   $j.phase='reference_delivered_verified';$j.path=$f
  }
 }
}
$bytes=[Text.Encoding]::UTF8.GetBytes(($j|ConvertTo-Json -Compress))
$e=[Convert]::ToBase64String($bytes)
$hash=([BitConverter]::ToString(([Security.Cryptography.SHA256]::Create()).ComputeHash($bytes))).Replace('-','')
[Console]::WriteLine(('JSTART:'+$e.Length))
for($i=0;$i -lt $e.Length;$i+=16){[Console]::WriteLine(('J:{0:D5}:{1}' -f ($i/16),$e.Substring($i,[Math]::Min(16,$e.Length-$i))))}
for($i=0;$i -lt 64;$i+=16){[Console]::WriteLine(('H:{0}:{1}' -f ($i/16),$hash.Substring($i,16)))}
Write-Output 'DREW_REFERENCE_OK=1'
"""
 script=script.replace('__SIZE__',str(size)).replace('__HASH__',digest).replace('__COLLECT__','$true' if collect else '$false')
 obj=transport.extract_result('\n'.join(remote(script,'taildrop-collect' if collect else 'taildrop-inspect')))
 phase=obj.get('phase')
 if phase not in ('reference_delivered_verified','taildrop_found_not_collected','awaiting_taildrop'):raise RuntimeError('Invalid Taildrop receipt')
 if phase!='awaiting_taildrop' and (obj.get('bytes')!=size or obj.get('sha256')!=digest):raise RuntimeError('Taildrop receipt identity mismatch')
 return obj

def launch_share(path):
 # Supported Termux native file sharing grants a readable content URI to the selected app.
 # Android Tailscale owns the peer picker; no guessed taps or arbitrary default receiver.
 tool=shutil.which('termux-open')
 if not tool:raise RuntimeError('termux-open unavailable; cannot initiate native Taildrop share')
 subprocess.run([tool,'--send','--chooser','--content-type','audio/mp4',str(path.resolve())],check=True,timeout=20)

def main():
 p=argparse.ArgumentParser()
 p.add_argument('verb',choices=['deliver','resume','status','send'])
 p.add_argument('--input',type=Path,default=SOURCE)
 a=p.parse_args()
 STATE.mkdir(mode=0o700,parents=True,exist_ok=True)
 lines=['CAMPAIGN=DREW_VOICE_REFERENCE_v1','VERB='+a.verb]
 rc=2
 try:
  if not shutil.which('cauldron'):raise RuntimeError('Existing cauldron command missing')
  lines+=['SOURCE_COMMIT='+source_commit()]
  if not a.input.is_file() or not 0<a.input.stat().st_size<=MAX:raise RuntimeError('Missing or oversized original M4A')
  data=a.input.read_bytes()
  if len(data)<12 or data[4:8]!=b'ftyp':raise RuntimeError('Original is not an ISO base media file')
  digest=sha(data);size=len(data)
  lines+=['REFERENCE_SHA256='+digest,'REFERENCE_BYTES='+str(size)]
  import fcntl
  with (STATE/'transfer.lock').open('a') as lock:
   fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
   obj=inspect(digest,size,a.verb!='status')
   lines+=['TRANSPORT=TAILDROP_ONLY','WINDOWS_RESULT='+json.dumps(obj,ensure_ascii=True,separators=(',',':')),'CLONED=NO','RENDERED=NO']
   if obj['phase']=='awaiting_taildrop':
    if a.verb=='send':
     launch_share(a.input)
     lines+=['SHARE_UI_REQUESTED=YES','NEXT=Select Tailscale then THECAULDRON; return and run resume']
    else:lines+=['NEXT=Run send only if no previous transfer is pending; resume checks delivery']
   elif obj['phase']=='taildrop_found_not_collected':
    lines+=['NEXT=resume to collect verified reference']
  rc=0 if obj['phase']=='reference_delivered_verified' else 3
 except subprocess.TimeoutExpired:lines+=['STATUS=BLOCKED','ERROR=SSH_TIMEOUT; reconcile with status or resume']
 except Exception as e:lines+=['STATUS=BLOCKED','ERROR='+type(e).__name__+': '+str(e)[:220]]
 receipt='\n'.join(lines)+'\n'
 (STATE/'latest.txt').write_text(receipt,encoding='utf-8')
 with (STATE/'history.txt').open('a',encoding='utf-8') as f:f.write(receipt+'\n')
 print(receipt,flush=True)
 if shutil.which('termux-clipboard-set'):
  try:subprocess.run(['termux-clipboard-set'],input=receipt,text=True,timeout=5,check=True)
  except (OSError,subprocess.SubprocessError):pass
 return rc

if __name__=='__main__':sys.exit(main())
