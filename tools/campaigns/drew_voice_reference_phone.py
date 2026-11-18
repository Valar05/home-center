#!/usr/bin/env python3
"""Private, resumable phone-to-Cauldron voice reference ingress; no synthesis."""
import argparse, base64, hashlib, json, os, re, shutil, subprocess, sys
from pathlib import Path
import ritsu_asmr_phone as transport

STATE=Path.home()/'.local/state/drew-voice-reference'
SOURCE=Path.home()/'storage/downloads/drew-whisper.m4a'
REL=r'DrewVoice\references'
MAX=4*1024*1024
CHUNK=600

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

def prefix(digest):
 return "$ErrorActionPreference='Stop';$d=Join-Path $env:LOCALAPPDATA 'DrewVoice\\references\\"+digest+"';$f=Join-Path $d 'drew-whisper.m4a';$p=$f+'.partial';"

def inspect(digest,size):
 lines=remote(prefix(digest)+r"""
if(Test-Path -LiteralPath $f){
 if((Get-Item -LiteralPath $f).Length -ne __SIZE__ -or (Get-FileHash -LiteralPath $f -Algorithm SHA256).Hash -ne '__HASH__'){throw 'FINAL_COLLISION'}
 $j=@{final=$true;bytes=__SIZE__;sha256='__HASH__'}
}elseif(Test-Path -LiteralPath $p){
 $j=@{final=$false;bytes=(Get-Item -LiteralPath $p).Length;sha256=(Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash}
}else{$j=@{final=$false;bytes=0;sha256=$null}}
$bytes=[Text.Encoding]::UTF8.GetBytes(($j|ConvertTo-Json -Compress))
$encoded=[Convert]::ToBase64String($bytes)
$hash=([BitConverter]::ToString(([Security.Cryptography.SHA256]::Create()).ComputeHash($bytes))).Replace('-','')
[Console]::WriteLine(('JSTART:'+ $encoded.Length))
for($i=0;$i -lt $encoded.Length;$i+=16){[Console]::WriteLine(('J:{0:D5}:{1}' -f ($i/16),$encoded.Substring($i,[Math]::Min(16,$encoded.Length-$i))))}
for($i=0;$i -lt 64;$i+=16){[Console]::WriteLine(('H:{0}:{1}' -f ($i/16),$hash.Substring($i,16)))}
Write-Output 'DREW_REFERENCE_OK=1'
""".replace('__SIZE__',str(size)).replace('__HASH__',digest),'inspect')
 obj=transport.extract_result('\n'.join(lines))
 final,n,h=obj.get('final'),obj.get('bytes'),obj.get('sha256')
 if type(final) is not bool or type(n) is not int or not 0<=n<=size:raise RuntimeError('Invalid remote reference receipt fields')
 if final and (n!=size or h!=digest):raise RuntimeError('Invalid final reference identity')
 if n and (not isinstance(h,str) or not re.fullmatch(r'[A-Fa-f0-9]{64}',h)):raise RuntimeError('Invalid remote prefix digest')
 return final,n,h.upper() if h else None

def append(digest,offset,chunk):
 coded=base64.b64encode(chunk).decode('ascii')
 script=prefix(digest)+r"""
New-Item -ItemType Directory -Force -Path $d|Out-Null
if(Test-Path -LiteralPath $f){throw 'FINAL_ALREADY_EXISTS'}
$b=[Convert]::FromBase64String('__CHUNK__')
$s=[IO.File]::Open($p,[IO.FileMode]::OpenOrCreate,[IO.FileAccess]::ReadWrite,[IO.FileShare]::None)
try{
 $o=__OFFSET__
 if($s.Length -eq $o){$s.Position=$o;$s.Write($b,0,$b.Length);$s.Flush()}
 elseif($s.Length -ge ($o+$b.Length)){
  $s.Position=$o;$old=New-Object byte[] $b.Length
  if($s.Read($old,0,$old.Length) -ne $old.Length -or [Convert]::ToBase64String($old) -cne '__CHUNK__'){throw 'CHUNK_COLLISION'}
 }else{throw 'OFFSET_COLLISION'}
}finally{$s.Dispose()}
Write-Output 'DREW_REFERENCE_OK=1'
"""
 # Avoid duplicating the full payload in the encoded command.
 script=script.replace("-cne '__CHUNK__'","-cne [Convert]::ToBase64String($b)")
 remote(script.replace('__CHUNK__',coded).replace('__OFFSET__',str(offset)),'append offset='+str(offset))

def finalize(digest,size):
 remote(prefix(digest)+r"""
if(!(Test-Path -LiteralPath $f)){
 if((Get-Item -LiteralPath $p).Length -ne __SIZE__ -or (Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash -ne '__HASH__'){throw 'REFERENCE_DIGEST_MISMATCH'}
 [IO.File]::Move($p,$f)
}
if((Get-Item -LiteralPath $f).Length -ne __SIZE__ -or (Get-FileHash -LiteralPath $f -Algorithm SHA256).Hash -ne '__HASH__'){throw 'FINAL_DIGEST_MISMATCH'}
Write-Output 'DREW_REFERENCE_OK=1'
""".replace('__SIZE__',str(size)).replace('__HASH__',digest),'finalize')

def main():
 p=argparse.ArgumentParser()
 p.add_argument('verb',choices=['deliver','resume','status'])
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
   final,n,h=inspect(digest,size)
   if n and not final and h!=sha(data[:n]):raise RuntimeError('Remote partial differs; preserve it, do not overwrite')
   if a.verb!='status' and not final:
    for off in range(n,size,CHUNK):
     append(digest,off,data[off:off+CHUNK])
     print('TRANSFER_BYTES='+str(min(off+CHUNK,size))+'/'+str(size),flush=True)
    finalize(digest,size)
    final,n,h=inspect(digest,size)
    if not final:raise RuntimeError('Final readback missing')
   lines+=['WINDOWS_REFERENCE=%LOCALAPPDATA%\\'+REL+'\\'+digest+'\\drew-whisper.m4a','VERIFIED_BYTES='+str(n),'PHASE='+('reference_delivered_verified' if final else 'reference_partial'),'CLONED=NO','RENDERED=NO']
  rc=0
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
