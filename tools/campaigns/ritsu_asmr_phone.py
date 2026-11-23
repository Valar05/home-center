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
def ps(script,quiet=False,stage='remote'):
 cmd=base64.b64encode(script.encode('utf-16le')).decode('ascii')
 if len(cmd)>6500:raise RuntimeError('SSH_COMMAND_BUDGET_EXCEEDED stage='+stage+' encodedChars='+str(len(cmd)))
 p=subprocess.run(['cauldron','powershell.exe','-NoLogo','-NoProfile','-NonInteractive','-EncodedCommand',cmd],text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=180)
 output=p.stdout or ''
 # Retain terminal output privately; never copy transcript chunks or encoded commands into receipts.
 (STATE/'last-remote-transport.txt').write_text(output,encoding='utf-8')
 (STATE/'last-remote-stage.txt').write_text(stage+' encodedChars='+str(len(cmd))+' exit='+str(p.returncode),encoding='utf-8')
 clean=re.sub(r'\x1b\][^\x07]*(?:\x07|\x1b\\)', '', output)
 clean=re.sub(r'\x1b\[[0-?]*[ -/]*[@-~]', '', clean)
 if not quiet:print(output[-12000:],flush=True)
 if p.returncode or 'RITSU_ASMR_REMOTE_OK=1' not in [line.strip() for line in clean.splitlines()]:
  safe=[x.strip() for x in clean.splitlines() if any(k in x.lower() for k in ('exec request failed','connection timed out','connection refused','permission denied','staging offset collision','staged transcript digest mismatch','pinned source digest mismatch','approved python runtime not found','private_repo_','fullyqualifiederrorid','"error"'))]
  detail=next((x[:220] for x in reversed(safe) if len(x)<500),'remote success marker missing; inspect private transport log')
  if quiet:print(output[-8000:],flush=True)
  raise RemoteFailure('CAULDRON_REMOTE_BLOCKED stage='+stage+' encodedChars='+str(len(cmd))+' exit='+str(p.returncode)+': '+detail)
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
 for off in range(0,len(coded),600):
  piece=coded[off:off+600]
  script="$ErrorActionPreference='Stop';$p="+quote(target)+";$p=$ExecutionContext.InvokeCommand.ExpandString($p);$dir=Split-Path $p;New-Item -ItemType Directory -Force -Path $dir|Out-Null;"
  script+="$s=if(Test-Path -LiteralPath $p){[IO.File]::ReadAllText($p)}else{''};$o="+str(off)+";$chunk="+quote(piece)+";"
  script+="if($s.Length -eq $o){[IO.File]::AppendAllText($p,$chunk,[Text.Encoding]::ASCII)}elseif($s.Length -ge ($o+$chunk.Length) -and $s.Substring($o,$chunk.Length) -ceq $chunk){}else{throw 'Staging offset collision'};"
  script+="Write-Output ('STAGED='+[IO.File]::ReadAllText($p).Length);Write-Output 'RITSU_ASMR_REMOTE_OK=1'"
  # Staging commands print the exact success marker only after validating the offset.
  ps(script,quiet=True,stage='transcript-chunk offset='+str(off))
  print('STAGING_PROGRESS='+str(min(off+len(piece),len(coded)))+'/'+str(len(coded)),flush=True)
 return digest,target
def repo_stage(episode,revision,relpath):
 # Private source is fetched on THECAULDRON, using only its existing Git credentials.
 if not re.fullmatch(r'[0-9a-f]{40}',revision):raise ValueError('Full private repository commit required')
 if not re.fullmatch(r'episodes/[A-Za-z0-9_-]{1,100}\.txt',relpath):raise ValueError('Invalid private episode path')
 relative='RitsuASMR\\incoming\\'+episode+'-repo-'+revision+'.txt'
 script=r"""
$ErrorActionPreference='Stop'
$env:GIT_TERMINAL_PROMPT='0'
$env:GCM_INTERACTIVE='Never'
$git=(Get-Command git.exe -ErrorAction Stop).Source
$root=Join-Path $env:LOCALAPPDATA 'RitsuASMR'
$cache=Join-Path $root 'private-episode-git'
$dest=Join-Path $env:LOCALAPPDATA '__DEST__'
New-Item -ItemType Directory -Force -Path $root,(Split-Path $dest)|Out-Null
if(!(Test-Path -LiteralPath $cache)){
 $ErrorActionPreference='Continue'
 & $git init --bare $cache 2>&1|Out-Null
 $rc=$LASTEXITCODE
 $ErrorActionPreference='Stop'
 if($rc -ne 0){throw 'PRIVATE_REPO_INIT_FAILED'}
}
$ErrorActionPreference='Continue'
& $git -C $cache -c credential.interactive=never fetch --no-tags https://github.com/Valar05/ritsu-asmr.git '__REV__' 2>&1|Out-Null
$rc=$LASTEXITCODE
$ErrorActionPreference='Stop'
if($rc -ne 0){throw 'PRIVATE_REPO_FETCH_FAILED: existing Windows Git authorization required'}
Write-Output 'RITSU_ASMR_REMOTE_OK=1'
"""
 ps(script.replace('__DEST__',relative).replace('__REV__',revision),quiet=True,stage='private-repo-fetch')
 script=r"""
$ErrorActionPreference='Stop'
$git=(Get-Command git.exe -ErrorAction Stop).Source
$root=Join-Path $env:LOCALAPPDATA 'RitsuASMR'
$cache=Join-Path $root 'private-episode-git'
$dest=Join-Path $env:LOCALAPPDATA '__DEST__'
$blob=(& $git -C $cache rev-parse '__REV__:__PATH__' 2>$null)
if($LASTEXITCODE -ne 0 -or $blob -notmatch '^[a-f0-9]{40}$'){throw 'PRIVATE_REPO_BLOB_MISSING'}
$blob=([string]$blob).Trim()
$tmp=Join-Path $root ('repo-stage-'+[guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $tmp|Out-Null
try{
 $src=Join-Path $tmp 'source.txt'
 # Windows PowerShell's > operator transcodes native stdout. Redirect via .NET binary stream instead.
 $pi=New-Object System.Diagnostics.ProcessStartInfo
 $pi.FileName=$git
 $pi.WorkingDirectory=$cache
 $pi.Arguments='cat-file blob '+$blob
 $pi.UseShellExecute=$false
 $pi.RedirectStandardOutput=$true
 $pi.RedirectStandardError=$true
 $proc=[System.Diagnostics.Process]::Start($pi)
 try{
  $err=$proc.StandardError.ReadToEndAsync()
  $out=[IO.File]::Open($src,[IO.FileMode]::CreateNew)
  try{$proc.StandardOutput.BaseStream.CopyTo($out)}finally{$out.Dispose()}
  $proc.WaitForExit()
  if($proc.ExitCode -ne 0){throw 'PRIVATE_REPO_CAT_FILE_FAILED'}
  [void]$err.GetAwaiter().GetResult()
 }finally{$proc.Dispose()}
 $actual=(& $git -C $cache hash-object --no-filters -- $src 2>$null)
 $rc=$LASTEXITCODE
 $actual=([string]$actual).Trim()
 if($rc -ne 0 -or $actual -cne $blob){throw ('PRIVATE_REPO_BLOB_MISMATCH expected='+$blob+' actual='+$actual+' exit='+$rc)}
 if((Get-Item -LiteralPath $src).Length -gt 150000){throw 'PRIVATE_REPO_INPUT_TOO_LARGE'}
 if(Test-Path -LiteralPath $dest){
  if((Get-FileHash -LiteralPath $dest).Hash -ne (Get-FileHash -LiteralPath $src).Hash){throw 'PRIVATE_REPO_STAGE_COLLISION'}
 }else{Copy-Item -LiteralPath $src -Destination $dest}
 Write-Output 'RITSU_ASMR_REMOTE_OK=1'
}finally{Remove-Item -LiteralPath $tmp -Recurse -Force}
"""
 script=script.replace('__DEST__',relative).replace('__REV__',revision).replace('__PATH__',relpath)
 ps(script,quiet=True,stage='private-repo-stage')
 return relative
def remote_run(commit,expected,verb,episode,input_data,repo_input=None):
 # The remote file is downloaded from exactly the checked-in SHA and verified
 # before execution. No local Windows checkout, agent, or live relay is altered.
 input_path=''
 if input_data is not None:
  digest,encoded_path=staging(episode,input_data)
  input_path='$env:LOCALAPPDATA\\RitsuASMR\\incoming\\'+episode+'-'+digest+'.txt'
 install=r"""
$ErrorActionPreference='Stop'
$d=Join-Path $env:LOCALAPPDATA 'RitsuASMR\code\__SHA__'
New-Item -ItemType Directory -Force -Path $d|Out-Null
$p=Join-Path $d 'ritsu_asmr_windows.py'
if(!(Test-Path -LiteralPath $p)){
 $tmp=$p+'.'+[guid]::NewGuid().ToString('N')+'.incoming'
 Invoke-WebRequest -Uri 'https://raw.githubusercontent.com/Valar05/home-center/__COMMIT__/tools/campaigns/ritsu_asmr_windows.py' -OutFile $tmp -TimeoutSec 40
 if((Get-FileHash -LiteralPath $tmp -Algorithm SHA256).Hash -ne '__SHA__'){throw 'Pinned source digest mismatch'}
 Move-Item -LiteralPath $tmp -Destination $p
}
if((Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash -ne '__SHA__'){throw 'Pinned source digest mismatch'}
[Console]::WriteLine('RITSU_ASMR_REMOTE_OK=1')
"""
 check=r"""
$ErrorActionPreference='Stop'
$p=Join-Path $env:LOCALAPPDATA 'RitsuASMR\code\__HASH__\ritsu_asmr_windows.py'
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
  return extract_result(ps(check.replace('__HASH__',expected),quiet=True,stage='renderer-install-check'))
 found=installed()
 if found['present'] and not found['matches']:raise RuntimeError('Existing pinned Windows source differs; preserve it')
 if not found['matches']:
  try:ps(install.replace('__SHA__',expected).replace('__COMMIT__',commit),quiet=True,stage='renderer-install')
  except (RemoteFailure,subprocess.TimeoutExpired):
   if not installed()['matches']:raise
  if not installed()['matches']:raise RuntimeError('Windows source installation not verified')
 script=r"""
$ErrorActionPreference='Stop'
$program=Join-Path $env:LOCALAPPDATA 'RitsuASMR\code\__SHA__\ritsu_asmr_windows.py'
if((Get-FileHash -LiteralPath $program -Algorithm SHA256).Hash -ne '__SHA__'){throw 'Pinned source digest mismatch'}
$python=Join-Path $env:USERPROFILE 'workspace\ritsu-faster-qwen3-tts\.venv\Scripts\python.exe'
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
  finalize=r"""
$ErrorActionPreference='Stop'
$encoded=Join-Path $env:LOCALAPPDATA '__ENCODED__'
$incoming=Join-Path $env:LOCALAPPDATA '__INCOMING__'
$raw=[IO.File]::ReadAllText($encoded)
$bytes=[Convert]::FromBase64String($raw)
$actual=([BitConverter]::ToString(([Security.Cryptography.SHA256]::Create()).ComputeHash($bytes))).Replace('-','')
if($actual -ne '__DIGEST__'){throw 'Staged transcript digest mismatch'}
[IO.File]::WriteAllBytes($incoming,$bytes)
Write-Output 'RITSU_ASMR_REMOTE_OK=1'
"""
  finalize=finalize.replace('__ENCODED__','RitsuASMR\\incoming\\'+episode+'-'+digest+'.b64').replace('__INCOMING__','RitsuASMR\\incoming\\'+episode+'-'+digest+'.txt').replace('__DIGEST__',digest)
  ps(finalize,quiet=True,stage='transcript-finalize')
  extra="$arguments+=@('--input',(Join-Path $env:LOCALAPPDATA "+quote('RitsuASMR\\incoming\\'+episode+'-'+digest+'.txt')+"))"
 elif repo_input is not None:
  extra="$arguments+=@('--input',(Join-Path $env:LOCALAPPDATA "+quote(repo_input)+"))"
 else:extra=''
 script=script.replace('__SHA__',expected).replace('__COMMIT__',commit).replace('__VERB__',verb).replace('__EP__',episode).replace('__INPUT__',extra)
 if episode.startswith(('DREW_DARK_VELVET_','RITSU_WHISPER_V2_','DREW_CLEAN_DARK_VELVET_','RITSU_WHISPER_V3_','DREW_QUIET_DARK_VELVET_','DREW_LOW_VELVET_','DREW_LOW_DEEP_VELVET_','DREW_DRY_V2_','DREW_GROWL_CONSERVATIVE_','DREW_GROWL_FOCUSED_')):
  script=script.replace(r'workspace\ritsu-faster-qwen3-tts\.venv\Scripts\python.exe',r'Documents\Codex\Venice\PocketTTS\.venv\Scripts\python.exe')
 output=ps(script,quiet=True,stage='renderer-'+verb)
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
# Exact enrolled handset previously used for Taildrop. Do not guess partial names.
TAILDROP_DEVICE='pixel-10-pro-xl-1'
TAILDROP_IP='100.93.128.108'
def rendered_identity(commit,expected,episode):
 remote=extract_result(remote_run(commit,expected,'receipts',episode,None))
 if not remote or remote.get('phase')!='rendered_not_delivered' or remote.get('episodeId')!=episode:
  raise RuntimeError('No verified rendered receipt for this episode')
 digest=str(remote.get('wavSha256','')).upper();size=remote.get('bytes')
 growl=episode.startswith(('DREW_GROWL_CONSERVATIVE_','DREW_GROWL_FOCUSED_'))
 deep=episode.startswith('DREW_LOW_DEEP_VELVET_')
 dry=episode.startswith('DREW_DRY_V2_')
 low=episode.startswith('DREW_LOW_VELVET_')
 clean=episode.startswith('DREW_CLEAN_DARK_VELVET_')
 quiet=episode.startswith('DREW_QUIET_DARK_VELVET_')
 drew=deep or dry or low or quiet or clean or episode.startswith('DREW_DARK_VELVET_')
 voice='12F022B4CD21E116640393132BF1F4268E0F6B5F787FB76969E4ACA44FC5BC10' if drew else 'B99EB2E16612E8B8C3E3A96F74BD631676CC79071779537FD94C564DB5796BE5'
 if deep or dry:voice='DA4D803B4F1FF35CEE909D533B978969B78AEC51178EC88C82D8883383293268'
 if low:voice='DA4D803B4F1FF35CEE909D533B978969B78AEC51178EC88C82D8883383293268'
 if quiet:voice='DEF7111C0ACE93EDD63436E3E7BD8A1D61C01256BD5FA707C45975C9A6108893'
 if clean:voice='DA4D803B4F1FF35CEE909D533B978969B78AEC51178EC88C82D8883383293268'
 if episode.startswith('RITSU_WHISPER_V3_'):
  voice='F6A787F1D58D11694676A2A4D44A89840F77B0D56A0585A5FB4DAC52F0C1FE97'
  if remote.get('profile')!='whisper-v3':raise RuntimeError('Unexpected Whisper V3 profile')
 if episode.startswith('RITSU_WHISPER_V2_'):
  voice='0141A450D8A370495D84755B4E620A718CB955F1139643F62F7C5CD147515FF7'
  if remote.get('profile')!='whisper-v2':raise RuntimeError('Unexpected Whisper V2 profile')
 if growl:
  expected_ref='9E4B6C5A98FC7AF2CDA95BC2BD4C20852F4844C79A9B7763851BD530EC1C2E45' if episode.startswith('DREW_GROWL_CONSERVATIVE_') else '83BC4A4A79652AA54ECAFFA01618CF523FDC38B1FD672718D3820E0E1FB5C694'
  voice=str(remote.get('voiceSha256','')).upper()
  if remote.get('profile')!='growl-dry' or remote.get('sourceReferenceSha256')!=expected_ref or not re.fullmatch(r'[A-F0-9]{64}',voice) or not re.fullmatch(r'[A-F0-9]{64}',str(remote.get('presetSha256',''))):raise RuntimeError('Growl reference/voice-state provenance mismatch')
 if str(remote.get('voiceSha256','')).upper()!=voice:raise RuntimeError('Unexpected voice identity')
 if deep and (remote.get('profile')!='low-deep-velvet' or remote.get('presetSha256')!='DB024ECE87CC6D8661BF25B28531D7E25AE26D498408E7679AEA8FBA40A4EDC6' or remote.get('presetParentSha256')!='396F91083E773062C7BA27C044FB57362D35AA01070E4DBA12699C0ADB965233'):raise RuntimeError('Unexpected Low Deep preset identity')
 if dry and (remote.get('profile')!='dry-v2' or remote.get('presetSha256')!='8BA518F9C12B31B1662B3668E579B66F2251EF30BA86FC2332143202240EAE38' or remote.get('presetParentSha256')!='396F91083E773062C7BA27C044FB57362D35AA01070E4DBA12699C0ADB965233'):raise RuntimeError('Unexpected Dry V2 identity')
 if low and (remote.get('profile')!='low-velvet' or remote.get('presetSha256')!='EC6E554C224685F8C19C4011665F05DFCB7A4DE4FCCBFDA76CFDEE40F9EF8229' or remote.get('presetParentSha256')!='396F91083E773062C7BA27C044FB57362D35AA01070E4DBA12699C0ADB965233'):raise RuntimeError('Unexpected Low Velvet identity')
 if drew and not (low or deep or dry or growl) and (remote.get('profile')!='dark-velvet' or remote.get('presetSha256')!=('9CCCC513FF398D10E998A25A394EBE788BA97B2697429E0BB4C3FD8DFA5B7CB5' if quiet else '396F91083E773062C7BA27C044FB57362D35AA01070E4DBA12699C0ADB965233' if clean else 'D04489AB5EA5822660E82FE5D5F2207C47C5958BCA8CBB4C8E215BA3DB2ED944')):raise RuntimeError('Unexpected Drew preset identity')
 if not re.fullmatch(r'[A-F0-9]{64}',digest) or not isinstance(size,int) or not 44<size<=512*1024*1024:raise RuntimeError('Invalid remote WAV receipt')
 return remote,digest,size
def taildrop_peers():
 # Read-only discovery. No auto-enrollment, no file send.
 script=r"""
$ErrorActionPreference='Stop'
$c=Get-Command tailscale.exe -ErrorAction SilentlyContinue
if($c){$exe=$c.Source}else{$exe=Join-Path $env:ProgramFiles 'Tailscale\tailscale.exe'}
$raw=& $exe status --json
if($LASTEXITCODE -ne 0){throw 'Tailscale status failed'}
$t=($raw -join [Environment]::NewLine)|ConvertFrom-Json
$rows=@(foreach($prop in $t.Peer.PSObject.Properties){
 $v=$prop.Value
 if($v.HostName -match 'pixel' -or $v.DNSName -match 'pixel' -or $v.TailscaleIPs -contains '100.93.128.108'){
  [pscustomobject]@{host=$v.HostName;dnsLabel=([string]$v.DNSName -split '\.')[0];ips=@($v.TailscaleIPs);online=$v.Online;os=$v.OS;id=$v.ID}
 }
})
$joined=@{phase='taildrop_peer_discovery';backend=$t.BackendState;peers=$rows}|ConvertTo-Json -Compress -Depth 6
$bytes=[Text.Encoding]::UTF8.GetBytes($joined)
$encoded=[Convert]::ToBase64String($bytes)
$hash=([BitConverter]::ToString(([Security.Cryptography.SHA256]::Create()).ComputeHash($bytes))).Replace('-','')
# ConsoleHost can wrap at the remote PTY width. Use numbered 16-character frames.
[Console]::WriteLine(('JSTART:'+ $encoded.Length))
for($i=0;$i -lt $encoded.Length;$i+=16){[Console]::WriteLine(('J:{0:D5}:{1}' -f ($i/16),$encoded.Substring($i,[Math]::Min(16,$encoded.Length-$i))))}
for($i=0;$i -lt 64;$i+=16){[Console]::WriteLine(('H:{0}:{1}' -f ($i/16),$hash.Substring($i,16)))}
Write-Output 'RITSU_ASMR_REMOTE_OK=1'
"""
 return extract_result(ps(script,quiet=True))
def drop_status(commit,expected,episode):
 remote,digest,size=rendered_identity(commit,expected,episode)
 script=r"""
$ErrorActionPreference='Stop'
$p=Join-Path $env:LOCALAPPDATA 'RitsuASMR\runs\__EP__\taildrop-__DIGEST__-__IP__.json'
$busy=$false
if(Test-Path -LiteralPath ($p+'.lock')){
 try{$g=[IO.File]::Open(($p+'.lock'),[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::None);$g.Dispose()}
 catch [IO.IOException]{$busy=$true}
}
$record=$null
if(Test-Path -LiteralPath $p){
 try{$record=Get-Content -LiteralPath $p -Raw|ConvertFrom-Json}catch{$record=@{phase='ledger_unreadable'}}
}
$procs=@(Get-CimInstance Win32_Process|Where-Object {
 $_.Name -ieq 'tailscale.exe' -and $_.CommandLine -match '\bfile\s+cp\b' -and $_.CommandLine -match '__EP__[.]wav' -and $_.CommandLine -match [regex]::Escape('__IP__:') 
}|ForEach-Object {$_.ProcessId})
$t=Get-ScheduledTask -TaskName 'RitsuASMR-Taildrop-__EP__' -TaskPath '\' -ErrorAction SilentlyContinue
$taskState=if($t){[string]$t.State}else{'Missing'}
$lastResult=if($t){(Get-ScheduledTaskInfo -TaskName $t.TaskName -TaskPath '\').LastTaskResult}else{$null}
$tail=if(Test-Path -LiteralPath ($p+'.log')){((Get-Content -LiteralPath ($p+'.log') -Tail 8)-join ' ')}else{''}
if($tail.Length -gt 600){$tail=$tail.Substring($tail.Length-600)}
$joined=@{phase='taildrop_status';episodeId='__EP__';sendLockHeld=$busy;senderPids=$procs;ledger=$record;taskState=$taskState;lastTaskResult=$lastResult;logTail=$tail}|ConvertTo-Json -Compress -Depth 6
$bytes=[Text.Encoding]::UTF8.GetBytes($joined)
$encoded=[Convert]::ToBase64String($bytes)
$hash=([BitConverter]::ToString(([Security.Cryptography.SHA256]::Create()).ComputeHash($bytes))).Replace('-','')
# ConsoleHost can wrap at the remote PTY width. Use numbered 16-character frames.
[Console]::WriteLine(('JSTART:'+ $encoded.Length))
for($i=0;$i -lt $encoded.Length;$i+=16){[Console]::WriteLine(('J:{0:D5}:{1}' -f ($i/16),$encoded.Substring($i,[Math]::Min(16,$encoded.Length-$i))))}
for($i=0;$i -lt 64;$i+=16){[Console]::WriteLine(('H:{0}:{1}' -f ($i/16),$hash.Substring($i,16)))}
Write-Output 'RITSU_ASMR_REMOTE_OK=1'
"""
 script=script.replace('__EP__',episode).replace('__DIGEST__',digest).replace('__IP__',TAILDROP_IP)
 return extract_result(ps(script,quiet=True))
def drop_wav(commit,expected,episode,resend=False):
 remote,digest,size=rendered_identity(commit,expected,episode)
 # Unique to the render and phone; a successful send is never a receive receipt.
 import fcntl
 with (STATE/(episode+'.drop.lock')).open('a+b') as lock:
  try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  except OSError as e:raise RuntimeError('Another Taildrop operation owns this episode') from e
  helper='tools/campaigns/ritsu_asmr_taildrop.ps1'
  pinned=subprocess.check_output(['git','-C',str(ROOT),'show',commit+':'+helper],timeout=40)
  if pinned!=(ROOT/helper).read_bytes():raise RuntimeError('Pinned Taildrop helper mismatch')
  helper_hash=sha(pinned)
  script=r"""
$ErrorActionPreference='Stop'
$d=Join-Path $env:LOCALAPPDATA 'RitsuASMR\code\__HELPER_SHA__'
New-Item -ItemType Directory -Force -Path $d|Out-Null
$p=Join-Path $d 'ritsu_asmr_taildrop.ps1'
if(!(Test-Path -LiteralPath $p)){
 $tmp=$p+'.'+[guid]::NewGuid().ToString('N')+'.incoming'
 Invoke-WebRequest -Uri 'https://raw.githubusercontent.com/Valar05/home-center/__COMMIT__/tools/campaigns/ritsu_asmr_taildrop.ps1' -OutFile $tmp -TimeoutSec 40
 if((Get-FileHash -LiteralPath $tmp -Algorithm SHA256).Hash -ne '__HELPER_SHA__'){throw 'Taildrop helper digest mismatch'}
 Move-Item -LiteralPath $tmp -Destination $p
}
if((Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash -ne '__HELPER_SHA__'){throw 'Installed Taildrop helper digest mismatch'}
& $p -Episode '__EP__' -Size __SIZE__ -Digest '__DIGEST__' -Device '__DEVICE__' -PeerIP '__IP__' -Resend:__RESEND__
"""
  script=script.replace('__HELPER_SHA__',helper_hash).replace('__COMMIT__',commit).replace('__EP__',episode).replace('__SIZE__',str(size)).replace('__DIGEST__',digest).replace('__DEVICE__',TAILDROP_DEVICE).replace('__IP__',TAILDROP_IP).replace('__RESEND__','$true' if resend else '$false')
  if len(base64.b64encode(script.encode('utf-16le')))>6500:raise RuntimeError('Taildrop dispatch exceeds conservative SSH command budget')
  result=extract_result(ps(script,quiet=True))
  if result.get('phase') not in ('taildrop_scheduled','taildrop_sent_not_verified') or result.get('wavSha256')!=digest or result.get('bytes')!=size or result.get('device')!=TAILDROP_DEVICE or result.get('episodeId')!=episode:raise RuntimeError('Taildrop send receipt identity mismatch')
  return result
def verify_wav(commit,expected,episode,received=None):
 remote,digest,size=rendered_identity(commit,expected,episode)
 downloads=Path.home()/'storage/downloads'
 # Android UI may require accepting/saving the incoming file before Termux can read it.
 if received is not None:
  candidates=[received]
 else:
  candidates=[]
  # Android Download/Taildrop is first; support case variants and duplicate saves.
  for directory in (downloads/'Taildrop',downloads/'taildrop',downloads/'Tailscale',downloads,downloads/'RitsuASMR'):
   candidates.append(directory/(episode+'.wav'))
   candidates.extend(sorted(directory.glob(episode+' (*).wav')))
   candidates.extend(sorted(directory.glob(episode+'-*.wav')))
  candidates=list(dict.fromkeys(candidates))
 for path in candidates:
  if not path.is_file() or path.stat().st_size!=size or file_sha(path)!=digest:continue
  import wave
  with wave.open(str(path),'rb') as w:
   if (w.getnchannels(),w.getsampwidth(),w.getframerate())!=(1,2,24000):raise RuntimeError('Invalid received PCM')
  return {'phase':'delivered_to_phone_not_heard','path':str(path),'bytes':size,'wavSha256':digest,'durationSeconds':remote.get('durationSeconds'),'transport':'not_inferred_from_file'}
 raise RuntimeError('No matching received WAV; accept/save Taildrop in Android Downloads or use verify --received PATH')
def main():
 p=argparse.ArgumentParser()
 p.add_argument('verb',nargs='?',default='doctor',choices=['doctor','inspect','recover','start','status','resume','stop','receipts','fetch','drop','verify','peers','drop-status'])
 p.add_argument('--episode',default='RITSU_ASMR_CANARY')
 p.add_argument('--input',type=Path)
 p.add_argument('--repo-transcript',nargs=2,metavar=('COMMIT','PATH'))
 p.add_argument('--repo-check',action='store_true',help='Stage and verify private Git input without starting render')
 p.add_argument('--received',type=Path)
 p.add_argument('--resend',action='store_true')
 a=p.parse_args()
 STATE.mkdir(parents=True,exist_ok=True)
 lines=['CAMPAIGN=RITSU_ASMR_OFFLINE_v1','EPISODE='+a.episode,'VERB='+a.verb]
 try:
  if not re.fullmatch(r'[A-Za-z0-9_-]{1,64}',a.episode):raise ValueError('Invalid episode ID')
  if a.received is not None and a.verb!='verify':raise ValueError('--received only allowed with verify')
  if a.resend and a.verb!='drop':raise ValueError('--resend only allowed with drop')
  if a.verb=='fetch':raise ValueError('Binary media must use Taildrop; use drop and verify')
  if a.repo_transcript and (a.input or a.verb!='start'):raise ValueError('--repo-transcript requires start and excludes --input')
  if a.repo_check and not a.repo_transcript:raise ValueError('--repo-check requires --repo-transcript')
  if a.input and a.verb!='start':raise ValueError('--input only allowed with start')
  if not shutil.which('cauldron'):raise RuntimeError('Existing cauldron command unavailable; no SSH substitution')
  commit,hashvalue=review_source()
  lines+=['SOURCE_COMMIT='+commit,'WINDOWS_SOURCE_SHA256='+hashvalue]
  data=a.input.read_bytes() if a.input else None
  if data is not None and len(data)>150000:raise ValueError('Input exceeds 150 kB')
  if data is not None:data.decode('utf-8-sig')
  print('CONTACTING_THECAULDRON='+a.verb,flush=True)
  repo_input=None
  if a.repo_transcript:
   revision,relpath=a.repo_transcript
   lines+=['TRANSCRIPT_REPO=Valar05/ritsu-asmr','TRANSCRIPT_COMMIT='+revision,'TRANSCRIPT_PATH='+relpath]
   repo_input=repo_stage(a.episode,revision,relpath)
  if a.repo_check:details={'phase':'private_repo_staged_not_rendered','commit':revision,'path':relpath}
  elif a.verb=='fetch':details=fetch_wav(commit,hashvalue,a.episode)
  elif a.verb=='peers':details=taildrop_peers()
  elif a.verb=='drop-status':details=drop_status(commit,hashvalue,a.episode)
  elif a.verb=='drop':details=drop_wav(commit,hashvalue,a.episode,a.resend)
  elif a.verb=='verify':details=verify_wav(commit,hashvalue,a.episode,a.received)
  else:details=extract_result(remote_run(commit,hashvalue,a.verb,a.episode,data,repo_input))
  if details is None:raise RuntimeError('Missing structured Windows result')
  lines+=['WINDOWS_RESULT='+json.dumps(details,ensure_ascii=True,separators=(',',':'))]
  lines+=['SSH_COMMAND_RETURNED=YES','REMOTE_OPERATION_CONFIRMED=YES','RENDER_NOT_INFERRED=YES']
  result=0
 except subprocess.TimeoutExpired as e:
  lines+=['STATUS=BLOCKED','ERROR=CAULDRON_TIMEOUT after '+str(e.timeout)+' seconds; remote outcome unknown','NEXT=drop-status (for drop) or status (for render); do not resend blindly']
  result=2
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
