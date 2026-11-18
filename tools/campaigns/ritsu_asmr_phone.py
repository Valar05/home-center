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
$python=Join-Path $env:USERPROFILE 'workspace\\ritsu-faster-qwen3-tts\.venv\\Scripts\\python.exe'
if (!(Test-Path -LiteralPath $python)) {throw 'Approved Python runtime not found'}
$env:RITSU_ASMR_SOURCE_COMMIT='__COMMIT__'
$arguments=@($program,'__VERB__','--episode','__EP__')
__INPUT__
& $python @arguments
if ($LASTEXITCODE -ne 0) {exit $LASTEXITCODE}
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
 return ps(script)
def extract_result(output):
 # Only JSON objects emitted by the offline tool, never raw SSH banners or transcript.
 decoder=json.JSONDecoder()
 for i,line in enumerate(output.splitlines()):
  if not line.lstrip().startswith('{'):continue
  try:
   obj,_=decoder.raw_decode('\n'.join(output.splitlines()[i:]).lstrip())
   if isinstance(obj,dict) and any(k in obj for k in ('phase','doctor','inspect','recovery')):return obj
  except ValueError:continue
 return None
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
 def file_sha(path):
  h=hashlib.sha256()
  with path.open('rb') as f:
   for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
  return h.hexdigest().upper()
 if dest.exists():
  if dest.stat().st_size!=size or file_sha(dest)!=digest:raise RuntimeError('Destination collision; existing WAV preserved')
 else:
  if partial.exists():raise RuntimeError('Previous partial transfer preserved: '+str(partial)+'; inspect or move aside before retry')
  print('FETCH_BYTES='+str(size)+' DESTINATION='+str(dest),flush=True)
  # Frame size stays below a 63-column Windows SSH terminal. Full digest is
  # checked before publishing; partial files are never claimed as delivered.
  chunk_size=192*1024
  with partial.open('xb') as f:
   for offset in range(0,size,chunk_size):
    count=min(chunk_size,size-offset)
    script=r"""
$ErrorActionPreference='Stop'
$p=Join-Path $env:LOCALAPPDATA 'RitsuASMR\runs\__EP__\__EP__.wav'
$s=[IO.File]::OpenRead($p)
try{
 if($s.Length -ne __SIZE__){throw 'WAV size changed'}
 $s.Position=__OFFSET__
 $buf=New-Object byte[] __COUNT__
 $n=0
 while($n -lt $buf.Length){$r=$s.Read($buf,$n,$buf.Length-$n);if($r -eq 0){throw 'Unexpected EOF'};$n+=$r}
 $b=[Convert]::ToBase64String($buf)
 for($i=0;$i -lt $b.Length;$i+=48){Write-Output ('B:'+ $b.Substring($i,[Math]::Min(48,$b.Length-$i)))}
}finally{$s.Dispose()}
Write-Output 'RITSU_ASMR_REMOTE_OK=1'
"""
    script=script.replace('__EP__',episode).replace('__SIZE__',str(size)).replace('__OFFSET__',str(offset)).replace('__COUNT__',str(count))
    out=ps(script,quiet=True)
    frames=[line[2:] for line in out.splitlines() if re.fullmatch(r'B:[A-Za-z0-9+/=]{1,48}',line)]
    data=base64.b64decode(''.join(frames),validate=True)
    if len(data)!=count:raise RuntimeError('Incomplete WAV chunk; refusing publication')
    f.write(data);f.flush();os.fsync(f.fileno())
    print('FETCH_PROGRESS='+str(offset+count)+'/'+str(size),flush=True)
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
  if a.verb=='fetch':details=fetch_wav(commit,hashvalue,a.episode)
  else:details=extract_result(remote_run(commit,hashvalue,a.verb,a.episode,data))
  if details is not None:lines+=['WINDOWS_RESULT='+json.dumps(details,ensure_ascii=True,separators=(',',':'))]
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
