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
class RemoteFailure(RuntimeError):
 pass
def ps(script,quiet=False):
 cmd=base64.b64encode(script.encode('utf-16le')).decode('ascii')
 p=subprocess.run(['cauldron','powershell.exe','-NoLogo','-NoProfile','-NonInteractive','-EncodedCommand',cmd],text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=180)
 output=p.stdout
 if not quiet:print(output[-12000:],flush=True)
 if p.returncode or 'RITSU_ASMR_REMOTE_OK=1' not in output.splitlines():
  detail=next((x[:500] for x in reversed(output.splitlines()) if '"error"' in x),'remote success marker missing')
  if quiet:print(output[-8000:],flush=True)
  raise RemoteFailure('CAULDRON_REMOTE_BLOCKED: '+detail)
 return output
def quote(s):return "'"+s.replace("'","''")+"'"
def is_canonical_origin(url):
 # Do not accept a lookalike host, a parent repository, or a token-bearing URL.
 allowed=(r'https://github\.com/Valar05/home-center(?:\.git)?/?',
          r'git@github\.com:Valar05/home-center(?:\.git)?',
          r'ssh://git@github\.com/Valar05/home-center(?:\.git)?/?')
 return any(re.fullmatch(pattern,url.strip(),re.I) for pattern in allowed)
def review_source():
 if not (ROOT/'AGENTS.md').is_file():raise RuntimeError('Not the intended Home Center checkout')
 url=shell('git','-C',str(ROOT),'remote','get-url','origin')
 if not is_canonical_origin(url):
  raise RuntimeError('Wrong Git remote (expected Valar05/home-center on github.com)')
 commit=shell('git','-C',str(ROOT),'rev-parse','HEAD')
 if not re.fullmatch(r'[0-9a-f]{40}',commit):raise RuntimeError('Invalid Git revision')
 for path in (LOCAL,REMOTE):
  data=subprocess.check_output(['git','-C',str(ROOT),'show',commit+':'+path],timeout=40)
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
  script+="Write-Output ('STAGED='+[IO.File]::ReadAllText($p).Length);Write-Output 'RITSU_ASMR_REMOTE_OK=1'"
  # Staging commands print the exact success marker only after validating the offset.
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
$code=Join-Path (Join-Path $root 'code') '__SHA__'
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
$env:RITSU_ASMR_SOURCE_COMMIT='__COMMIT__'
$arguments=@($program,'__VERB__','--episode','__EP__')
__INPUT__
$result=@(& $python @arguments)
$rc=$LASTEXITCODE
if($rc -ne 0){$result | Write-Output;exit $rc}
$joined=$result -join [Environment]::NewLine
$bytes=[Text.Encoding]::UTF8.GetBytes($joined)
$encoded=[Convert]::ToBase64String($bytes)
$hash=([BitConverter]::ToString(([Security.Cryptography.SHA256]::Create()).ComputeHash($bytes))).Replace('-','')
# ConsoleHost can wrap at the remote PTY width. Use numbered 16-character frames.
[Console]::WriteLine(('JSTART:'+ $encoded.Length))
for($i=0;$i -lt $encoded.Length;$i+=16){[Console]::WriteLine(('J:{0:D5}:{1}' -f ($i/16),$encoded.Substring($i,[Math]::Min(16,$encoded.Length-$i))))}
for($i=0;$i -lt 64;$i+=16){[Console]::WriteLine(('H:{0}:{1}' -f ($i/16),$hash.Substring($i,16)))}
Write-Output 'RITSU_ASMR_REMOTE_OK=1'
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
 output=ps(script,quiet=True)
 (STATE/'last-remote-transport.txt').write_text(output,encoding='utf-8')
 return output
def extract_result(output):
 # Strip terminal CSI/OSC controls, then check numbered frames, length and digest.
 output=re.sub(r'\x1b\][^\x07]*(?:\x07|\x1b\\)', '', output)
 output=re.sub(r'\x1b\[[0-?]*[ -/]*[@-~]', '', output)
 lines=[line.strip() for line in output.splitlines()]
 starts=[int(m.group(1)) for line in lines if (m:=re.fullmatch(r'JSTART:(\d+)',line))]
 if len(starts)!=1:raise RuntimeError('WINDOWS_RESULT_HEADER_MISSING_OR_DUPLICATE; remote operation may have executed')
 frames={};hashes={}
 for line in lines:
  m=re.fullmatch(r'J:(\d{5}):([A-Za-z0-9+/=]{1,16})',line)
  if m:
   n=int(m[1])
   if n in frames:raise RuntimeError('DUPLICATE_WINDOWS_RESULT_FRAME')
   frames[n]=m[2]
  m=re.fullmatch(r'H:([0-3]):([A-Fa-f0-9]{16})',line)
  if m:
   n=int(m[1])
   if n in hashes:raise RuntimeError('DUPLICATE_WINDOWS_RESULT_HASH')
   hashes[n]=m[2]
 length=starts[0]
 if not 0<length<=1000000 or set(frames)!=set(range((length+15)//16)) or set(hashes)!=set(range(4)):
  raise RuntimeError('WINDOWS_RESULT_INCOMPLETE; remote operation may have executed')
 coded=''.join(frames[i] for i in range(len(frames)))
 if len(coded)!=length:raise RuntimeError('WINDOWS_RESULT_LENGTH_MISMATCH')
 try:
  raw=base64.b64decode(coded,validate=True)
  if sha(raw)!=''.join(hashes[i] for i in range(4)).upper():raise RuntimeError('WINDOWS_RESULT_DIGEST_MISMATCH')
  obj=json.loads(raw.decode('utf-8-sig'))
 except (ValueError,UnicodeError) as e:raise RuntimeError('Invalid Windows result frames: '+str(e)[:120]) from e
 if not isinstance(obj,dict):raise RuntimeError('Windows result is not an object')
 return obj
def wav_read(episode,size,offset,count,prefix=False):
 # Reuse the physically proven numbered JSON protocol, not the obsolete B: frames.
 if not 0<=offset<=size or not 0<=count<=size-offset:raise ValueError('Invalid WAV range')
 script=r"""
$ErrorActionPreference='Stop'
$p=Join-Path $env:LOCALAPPDATA 'RitsuASMR\runs\__EP__\__EP__.wav'
$s=[IO.File]::OpenRead($p)
try{
 if($s.Length -ne __SIZE__){throw 'WAV size changed'}
 $s.Position=__OFFSET__
 $left=[long]__COUNT__
 if(__PREFIX__){
  $h=[Security.Cryptography.SHA256]::Create()
  try{
   $buf=New-Object byte[] 65536
   while($left -gt 0){
    $n=$s.Read($buf,0,[int][Math]::Min($left,$buf.Length))
    if($n -le 0){throw 'Unexpected EOF'}
    [void]$h.TransformBlock($buf,0,$n,$buf,0)
    $left-=$n
   }
   [void]$h.TransformFinalBlock([byte[]]@(),0,0)
   $joined=@{offset=__OFFSET__;count=__COUNT__;sha256=([BitConverter]::ToString($h.Hash)).Replace('-','')}|ConvertTo-Json -Compress
  }finally{$h.Dispose()}
 }else{
  $buf=New-Object byte[] __COUNT__
  $n=0
  while($n -lt $buf.Length){$r=$s.Read($buf,$n,$buf.Length-$n);if($r -eq 0){throw 'Unexpected EOF'};$n+=$r}
  $joined=@{offset=__OFFSET__;count=__COUNT__;data=[Convert]::ToBase64String($buf)}|ConvertTo-Json -Compress
 }
}finally{$s.Dispose()}
$bytes=[Text.Encoding]::UTF8.GetBytes($joined)
$encoded=[Convert]::ToBase64String($bytes)
$hash=([BitConverter]::ToString(([Security.Cryptography.SHA256]::Create()).ComputeHash($bytes))).Replace('-','')
# ConsoleHost can wrap at the remote PTY width. Use numbered 16-character frames.
[Console]::WriteLine(('JSTART:'+ $encoded.Length))
for($i=0;$i -lt $encoded.Length;$i+=16){[Console]::WriteLine(('J:{0:D5}:{1}' -f ($i/16),$encoded.Substring($i,[Math]::Min(16,$encoded.Length-$i))))}
for($i=0;$i -lt 64;$i+=16){[Console]::WriteLine(('H:{0}:{1}' -f ($i/16),$hash.Substring($i,16)))}
Write-Output 'RITSU_ASMR_REMOTE_OK=1'
"""
 script=script.replace('__EP__',episode).replace('__SIZE__',str(size)).replace('__OFFSET__',str(offset)).replace('__COUNT__',str(count)).replace('__PREFIX__','$true' if prefix else '$false')
 out=ps(script,quiet=True)
 try:
  obj=extract_result(out)
  if obj.get('offset')!=offset or obj.get('count')!=count:raise RuntimeError('WAV range identity mismatch')
  if prefix:
   digest=obj.get('sha256','').upper()
   if not re.fullmatch(r'[A-F0-9]{64}',digest):raise RuntimeError('Invalid prefix digest')
   return digest
  data=base64.b64decode(obj['data'],validate=True)
  if len(data)!=count:raise RuntimeError('Incomplete WAV range')
  return data
 except (ValueError,KeyError,RuntimeError) as e:
  (STATE/'last-fetch-transport.txt').write_text(out,encoding='utf-8')
  raise RuntimeError('WAV_RANGE_BLOCKED offset='+str(offset)+' count='+str(count)+': '+str(e)) from e
def file_sha(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
 return h.hexdigest().upper()
def fetch_wav(commit,expected,episode):
 # Same installed cauldron command for every read. No SCP shortcut, relay, or cloud upload.
 remote=extract_result(remote_run(commit,expected,'receipts',episode,None))
 if not remote or remote.get('phase')!='rendered_not_delivered' or remote.get('episodeId')!=episode:
  raise RuntimeError('No verified rendered receipt for this episode')
 digest=remote.get('wavSha256','').upper();size=remote.get('bytes')
 if remote.get('voiceSha256','').upper()!='B99EB2E16612E8B8C3E3A96F74BD631676CC79071779537FD94C564DB5796BE5':raise RuntimeError('Unexpected whisper identity')
 if not re.fullmatch(r'[A-F0-9]{64}',digest) or not isinstance(size,int) or not 44<size<=512*1024*1024:
  raise RuntimeError('Invalid remote WAV receipt')
 destdir=Path.home()/'storage/downloads/RitsuASMR'
 if not destdir.parent.is_dir():raise RuntimeError('Termux Downloads storage unavailable')
 destdir.mkdir(exist_ok=True)
 dest=destdir/(episode+'.wav');partial=destdir/(episode+'.'+digest+'.partial')
 if dest.exists():
  if dest.stat().st_size!=size or file_sha(dest)!=digest:raise RuntimeError('Destination collision; existing WAV preserved')
 else:
  import fcntl,time
  # Per-file exclusive lock; verified existing prefix can be resumed, never truncated.
  with (STATE/(episode+'.fetch.lock')).open('a+b') as lock:
   try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
   except OSError as e:raise RuntimeError('Another fetch owns this episode') from e
   if dest.exists():raise RuntimeError('Destination appeared; rerun fetch to verify')
   offset=partial.stat().st_size if partial.exists() else 0
   if offset>size:raise RuntimeError('Partial exceeds expected size; preserved')
   if offset and file_sha(partial)!=wav_read(episode,size,0,offset,prefix=True):
    raise RuntimeError('Existing partial prefix does not match remote WAV; preserved')
   print('FETCH_RESUME='+str(offset)+'/'+str(size),flush=True)
   chunk=48*1024
   with partial.open('ab' if partial.exists() else 'xb') as f:
    while offset<size:
     count=min(chunk,size-offset)
     for attempt in range(4):
      try:data=wav_read(episode,size,offset,count);break
      except (RuntimeError,subprocess.SubprocessError) as e:
       if attempt==3:raise
       chunk=max(4096,chunk//2);count=min(chunk,size-offset)
       print('FETCH_RETRY offset='+str(offset)+' count='+str(count)+' reason='+str(e)[:160],flush=True)
       time.sleep(attempt+1)
     f.write(data);f.flush();os.fsync(f.fileno())
     offset+=len(data)
     print('FETCH_PROGRESS='+str(offset)+'/'+str(size),flush=True)
   if partial.stat().st_size!=size or file_sha(partial)!=digest:raise RuntimeError('Final WAV checksum mismatch; partial preserved')
   import wave
   with wave.open(str(partial),'rb') as w:
    if (w.getnchannels(),w.getsampwidth(),w.getframerate())!=(1,2,24000):raise RuntimeError('Invalid received PCM')
   if dest.exists():raise RuntimeError('Destination appeared during transfer; partial preserved')
   partial.rename(dest)
 return {'phase':'delivered_to_phone_not_heard','path':str(dest),'bytes':size,'wavSha256':digest,'durationSeconds':remote.get('durationSeconds')}
def main():
 p=argparse.ArgumentParser()
 p.add_argument('verb',nargs='?',default='doctor',choices=['doctor','inspect','recover','start','status','resume','stop','receipts','fetch'])
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
  print('CONTACTING_THECAULDRON='+a.verb,flush=True)
  if a.verb=='fetch':details=fetch_wav(commit,hashvalue,a.episode)
  else:details=extract_result(remote_run(commit,hashvalue,a.verb,a.episode,data))
  if details is None:raise RuntimeError('Missing structured Windows result')
  lines+=['WINDOWS_RESULT='+json.dumps(details,ensure_ascii=True,separators=(',',':'))]
  lines+=['SSH_COMMAND_RETURNED=YES','REMOTE_OPERATION_CONFIRMED=YES','RENDER_NOT_INFERRED=YES']
  result=0
 except Exception as e:
  lines+=['STATUS=BLOCKED','ERROR='+type(e).__name__+': '+str(e)[:500]]
  result=2
 receipt='\n'.join(lines)+'\n'
 # Do not put transcript, keys, or credentials in the receipt or clipboard.
 (STATE/'latest.txt').write_text(receipt,encoding='utf-8')
 with (STATE/'history.txt').open('a',encoding='utf-8') as history:history.write(receipt+'\n')
 print(receipt,flush=True)
 if shutil.which('termux-clipboard-set'):
  try:subprocess.run(['termux-clipboard-set'],input=receipt,text=True,capture_output=True,timeout=5,check=True)
  except (OSError,subprocess.SubprocessError):print('CLIPBOARD_UNAVAILABLE=1')
 else:print('CLIPBOARD_UNAVAILABLE=1')
 return result
if __name__=='__main__':sys.exit(main())
