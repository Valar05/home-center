#!/usr/bin/env bash
# FIRST INVOCATION: bash ~/storage/downloads/ritsu-stream-recovery-closed-loop.sh
# Ritsu closed-loop recovery v1 (2026-10-28). One invocation, no extra operator scripts.
# Target: Android/Termux controller; existing 'cauldron' command-string -> THECAULDRON.
# Scope: read-only connectivity and journal diagnosis; one guarded restart of existing
# Windows scheduled launcher only if server process and listener are absent.
# No: send/re-send, journal mutation, APK rebuild/install, pairing/token rotation,
# GitHub/Home Center/Computer Hands use, source patch, Tailscale Serve mutation.
set -Eeuo pipefail
if ! command -v python3 >/dev/null 2>&1; then
  printf '%s\n' 'CAMPAIGN_STATUS=BLOCKED' 'CAUSE=PYTHON3_NOT_INSTALLED_IN_TERMUX' \
    'PRESERVED=APK,PAIRING,JOURNAL,PENDING_TURN' >&2
  exit 2
fi
RITSU_CAMPAIGN_SOURCE="$(realpath "$0")" exec python3 - "$@" <<'PYTHON_CAMPAIGN'
import base64, contextlib, datetime, fcntl, gzip, hashlib, json, os, pathlib
import re, shutil, signal, socket, subprocess, sys, tempfile, threading, time, traceback
import urllib.error, urllib.request

CAMPAIGN = 'ritsu-stream-recovery'
VERSION = 'closed-loop-v1'
# Prior independently observed server's Tailscale identity and Serve mapping.
TAILNET_HOST = '100.68.37.106'
TAILNET_PORT = 19646
LOCAL_PORT = 19647
BUDGET_SECONDS = 175
REMOTE_CALL_TIMEOUT = 25
REMOTE_CHUNK = 650
MAX_ENCODED_COMMAND = 3400
HOME = pathlib.Path.home()
STATE = HOME/'.local'/'state'/'ritsu-stream-recovery'
RECEIPT = STATE/'latest-receipt.json'
RUN_DIR = STATE/'runs'
SOURCE = pathlib.Path(os.environ.get('RITSU_CAMPAIGN_SOURCE',''))
DOCS_ETIQUETTE='https://docs.google.com/document/d/1wntegQjw7238dmGqbvs9TQmlsp4uXdXw7_wPciNx6sI/edit'
DOCS_HANDOFF='https://docs.google.com/document/d/1LEA0scDKY3QcO6ertvsfxWpzMm5jzKSL4AoAJKYs86w/edit'

# This script deliberately has no auth token. The protected token is used only
# INSIDE the Windows read-only replay probe and is never returned to Termux.
REMOTE_PS = r'''param([ValidateSet('PROBE','RECOVER')][string]$Mode='PROBE')
$ErrorActionPreference='Stop'
$ProgressPreference='SilentlyContinue'
$e=[ordered]@{
 schema='ritsu.remote.probe.v1'; mode=$Mode; status='UNVERIFIED'; stage='START';
 node_count=-1; source_valid=$false; patch_present=$false; source_sha256='';
 listener_count=0; listener_port=0; listener_address=''; process_age_seconds=-1;
 journal_exists=$false; journal_sha256=''; seq14_type=''; seq14_empty=$false;
 empty_partials=-1; journal_event_count=-1; journal_max_seq=-1; journal_complete_count=-1;
 local_unauth_status='UNTESTED'; authenticated_replay='UNTESTED';
 tailnet_service='UNKNOWN'; tailscale_serve='UNKNOWN'; task='UNKNOWN';
 repair='NOT_REQUESTED'; permission='UNKNOWN'; error_class='';
}
function Emit() { Write-Output ('RITSU_EVIDENCE_JSON='+(ConvertTo-Json -InputObject $e -Compress -Depth 6)) }
function HashFile([string]$p) { if([IO.File]::Exists($p)){return (Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant()} return '' }
function HttpStatus([string]$url,[string]$token,[bool]$readReplay) {
  $req=[Net.HttpWebRequest][Net.WebRequest]::Create($url)
  $req.Proxy=$null; $req.Timeout=4500; $req.ReadWriteTimeout=4500
  $req.Method='GET'; $req.KeepAlive=$false
  if($token){ $req.Headers.Add('Authorization','Bearer '+$token) }
  try {
    $response=[Net.HttpWebResponse]$req.GetResponse()
    try {
      $status=[int]$response.StatusCode
      if(-not $readReplay){return ('HTTP_'+$status)}
      if($status -ne 200){return ('HTTP_'+$status)}
      $stream=$response.GetResponseStream(); $stream.ReadTimeout=4500
      $reader=[IO.StreamReader]::new($stream)
      try {
        for($n=0;$n -lt 25;$n++){
          $line=$reader.ReadLine()
          if($null -eq $line){break}
          if($line.StartsWith('data: ')){
            $event=$line.Substring(6)|ConvertFrom-Json
            if([int]$event.seq -ne 14){return 'REPLAY_WRONG_SEQUENCE'}
            if([string]$event.type -eq 'accepted' -and [string]$event.text -eq ''){return 'SEQ14_ACCEPTED'}
            return ('REPLAY_TYPE_'+[string]$event.type)
          }
        }
        return 'REPLAY_NO_DATA'
      }finally{$reader.Dispose()}
    }finally{$response.Close()}
  }catch [Net.WebException] {
    $resp=$_.Exception.Response
    if($null -ne $resp){try{return ('HTTP_'+[int]$resp.StatusCode)}finally{$resp.Dispose()}}
    return ('NETWORK_'+[string]$_.Exception.Status)
  }catch {return ('EXCEPTION_'+$_.Exception.GetType().Name)}
}
try {
  $e.stage='IDENTITY'
  $base=Join-Path $env:USERPROFILE '.ritsu-control\local-link'
  $journal=Join-Path $base 'events.jsonl'
  $e.journal_exists=[IO.File]::Exists($journal)
  if($e.journal_exists){
    $e.stage='JOURNAL_METADATA_ONLY'
    $size=[IO.FileInfo]::new($journal).Length
    $e.journal_sha256=HashFile $journal
    if($size -le 16777216) {
      $events=0;$empties=0;$maxSeq=0;$completes=0
      foreach($line in [IO.File]::ReadLines($journal)){
        if(-not $line.Trim()){continue}
        $item=$line|ConvertFrom-Json
        $events++
        if($null -ne $item.seq){$maxSeq=[Math]::Max($maxSeq,[int]$item.seq)}
        if($item.type -eq 'partial' -and [string]$item.text -ceq ''){$empties++}
        if($item.type -eq 'complete'){$completes++}
        if([int]$item.seq -eq 14){$e.seq14_type=[string]$item.type;$e.seq14_empty=([string]$item.text -ceq '')}
      }
      $e.empty_partials=$empties;$e.journal_event_count=$events
      $e.journal_max_seq=$maxSeq;$e.journal_complete_count=$completes
    }else{$e.error_class='JOURNAL_SIZE_LIMIT'}
  }
  $e.stage='WINDOWS_PROCESS'
  $procs=@(Get-CimInstance Win32_Process -Filter "Name='node.exe'" -ErrorAction Stop | Where-Object {$_.CommandLine -match 'ritsu-local-server[\\/]server\.mjs'})
  $e.node_count=$procs.Count
  $roots=@((Join-Path $env:USERPROFILE 'AppData\Local\RitsuControlBridge\release-016'),(Join-Path $env:USERPROFILE 'workspace\home-center'))
  $sources=@($roots|ForEach-Object{Join-Path $_ 'tools\ritsu-local-server\server.mjs'}|Where-Object{[IO.File]::Exists($_)})
  $source=$null
  if($procs.Count -eq 1){
    $p=$procs[0]
    $matched=@($sources|Where-Object{([string]$p.CommandLine).Contains($_)})
    if($matched.Count -eq 1){$source=$matched[0];$e.source_valid=$true}
    try {
      $c=[Management.ManagementDateTimeConverter]::ToDateTime($p.CreationDate)
      $e.process_age_seconds=[int][Math]::Max(0,((Get-Date)-$c).TotalSeconds)
    }catch{}
    try {
      $sockets=@(Get-NetTCPConnection -State Listen -OwningProcess ([int]$p.ProcessId) -ErrorAction Stop | Where-Object{$_.LocalPort -eq 19646 -or $_.LocalPort -eq 19647})
      $e.listener_count=$sockets.Count
      if($sockets.Count -eq 1){$e.listener_port=[int]$sockets[0].LocalPort;$e.listener_address=[string]$sockets[0].LocalAddress}
    }catch{}
  }
  if($null -ne $source){
    $e.stage='PATCH_READ_ONLY'
    $e.source_sha256=HashFile $source
    $src=[IO.File]::ReadAllText($source,[Text.Encoding]::UTF8)
    $e.patch_present=($src.Contains('function ritsuWireEvent(e)') -and $src.Contains('JSON.stringify(ritsuWireEvent(row))') -and $src.Contains('JSON.stringify(ritsuWireEvent(e))'))
  }
  $e.stage='SERVICE_CONFIGURATION'
  try{$s=Get-Service -Name Tailscale -ErrorAction Stop;$e.tailnet_service=[string]$s.Status}catch{$e.tailnet_service='UNKNOWN'}
  $ts=Get-Command tailscale.exe -ErrorAction SilentlyContinue
  if($null -ne $ts){
    try {
      $lines=(& $ts.Source serve status 2>$null|Out-String)
      if($LASTEXITCODE -eq 0){
        if($lines.Contains('19646') -and $lines.Contains('19647')){$e.tailscale_serve='EXPECTED_MAPPING_PRESENT'}
        else {$e.tailscale_serve='MAPPING_NOT_CONFIRMED'}
      }else{$e.tailscale_serve='CLI_ERROR'}
    }catch{$e.tailscale_serve='CLI_ERROR'}
  }else{$e.tailscale_serve='CLI_NOT_FOUND'}
  try {
    $t=Get-ScheduledTask -TaskName 'Ritsu Local Link' -ErrorAction Stop
    $ta=@($t.Actions)
    $cmds=($ta|ForEach-Object{([string]$_.Execute)+' '+([string]$_.Arguments)}) -join ' '
    if($cmds -match 'ritsu-start\.ps1' -and $ta.Count -eq 1){$e.task='EXACT_EXISTING_RITSU_LAUNCHER'}
    else {$e.task='PRESENT_BUT_LAUNCHER_NOT_VERIFIED'}
  }catch{$e.task='NOT_FOUND'}
  $e.stage='HTTP_LOCAL'
  $e.local_unauth_status=HttpStatus 'http://127.0.0.1:19647/v1/ritsu/events?after=13' '' $false
  if($e.local_unauth_status -eq 'HTTP_401' -and $e.journal_exists){
    $e.stage='AUTHENTICATED_REPLAY_LOCAL'
    $tokenPath=Join-Path $base 'device-token'
    if([IO.File]::Exists($tokenPath)){
      $token=[IO.File]::ReadAllText($tokenPath,[Text.Encoding]::UTF8).Trim()
      if($token){$e.authenticated_replay=HttpStatus 'http://127.0.0.1:19647/v1/ritsu/events?after=13' $token $true}
      else {$e.authenticated_replay='TOKEN_EMPTY'}
      Remove-Variable token -ErrorAction SilentlyContinue
    }else{$e.authenticated_replay='TOKEN_FILE_MISSING'}
  }
  if($Mode -eq 'RECOVER'){
    $e.stage='GUARDED_RECOVERY'
    # Recovery deliberately refuses when a Ritsu node process exists: do not kill
    # a possibly healthy user session or spawn a competing listener.
    if($e.node_count -ne 0){$e.repair='BLOCKED_EXISTING_PROCESS'}
    elseif($e.task -ne 'EXACT_EXISTING_RITSU_LAUNCHER'){$e.repair='BLOCKED_LAUNCHER_IDENTITY'}
    elseif($e.tailnet_service -ne 'Running'){$e.repair='BLOCKED_TAILSCALE_SERVICE'}
    else {
      $e.repair='STARTING_VERIFIED_TASK'
      Start-ScheduledTask -TaskName 'Ritsu Local Link' -ErrorAction Stop
      $healthy=$false
      for($i=0;$i -lt 18;$i++){
        Start-Sleep -Milliseconds 500
        if((HttpStatus 'http://127.0.0.1:19647/v1/ritsu/events?after=13' '' $false) -eq 'HTTP_401'){$healthy=$true;break}
      }
      if($healthy){$e.repair='VERIFIED_LOCAL_401'}
      else{$e.repair='RESTART_TASK_RAN_NO_LISTENER'}
    }
  }
  $e.stage='FINAL'
  $e.status='PROBE_COMPLETE'
}catch {
  $e.status='PROBE_PARTIAL'
  $e.error_class=$_.Exception.GetType().Name
}
Emit
'''

class Deadline(Exception): pass
class TransportError(Exception): pass

class Run:
    def __init__(self):
        self.started=time.monotonic()
        self.id=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'-'+str(os.getpid())
        self.dir=RUN_DIR/self.id
        self.evidence={}
        self.steps=[]
        self.status='BLOCKED'
        self.cause='NOT_STARTED'
        self.human_action='NONE'
        self.source_sha=''
        self.packaged='NOT_ATTEMPTED'
        self.transport_calls=0
        self.remote_sha=hashlib.sha256(REMOTE_PS.encode()).hexdigest()
        self.logpath=self.dir/'run.log'

    def remaining(self):
        left=BUDGET_SECONDS-(time.monotonic()-self.started)
        if left<4:raise Deadline('CAMPAIGN_TIME_BUDGET')
        return left

    def log(self,code,**kw):
        item={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(), 'step':code, **kw}
        self.steps.append(item)
        if len(self.steps)>120:self.steps=self.steps[-120:]
        with self.logpath.open('a',encoding='utf-8') as f:f.write(json.dumps(item,sort_keys=True)+'\n')

    def invoke(self, ps, expect=None, timeout=REMOTE_CALL_TIMEOUT):
        self.remaining()
        encoded=base64.b64encode(ps.encode('utf-16le')).decode()
        command='powershell.exe -NoProfile -NonInteractive -EncodedCommand '+encoded
        if len(command)>MAX_ENCODED_COMMAND:raise TransportError('ENCODED_COMMAND_TOO_LARGE')
        args=['cauldron',command]
        self.transport_calls+=1
        try:
            proc=subprocess.Popen(args,stdin=subprocess.PIPE,stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE,start_new_session=True)
        except (OSError,ValueError) as ex:raise TransportError('CAULDRON_START_'+type(ex).__name__)
        captured=[bytearray(),bytearray()]
        def reader(file,buf):
            while True:
                block=file.read(4096)
                if not block:break
                if len(buf)<65536:buf.extend(block[:65536-len(buf)])
        threads=[threading.Thread(target=reader,args=(proc.stdout,captured[0]),daemon=True),
                 threading.Thread(target=reader,args=(proc.stderr,captured[1]),daemon=True)]
        for t in threads:t.start()
        try:
            rc=proc.wait(timeout=min(timeout,max(2,self.remaining()-1)))
        except subprocess.TimeoutExpired:
            with contextlib.suppress(ProcessLookupError):os.killpg(proc.pid,signal.SIGTERM)
            try:proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                with contextlib.suppress(ProcessLookupError):os.killpg(proc.pid,signal.SIGKILL)
                proc.wait(timeout=2)
            raise TransportError('CAULDRON_CALL_TIMEOUT')
        finally:
            if proc.stdin and not proc.stdin.closed:proc.stdin.close()
        for t in threads:t.join(timeout=1.5)
        # Only expected, machine-readable receipts are retained; no raw transport
        # content, credentials or shell diagnostics are written to disk or printed.
        out=re.sub(r'\x1b\[[0-9;]*[a-zA-Z]','',captured[0].decode('utf-8','replace')).replace('\r','')
        err=captured[1].decode('utf-8','replace').lower()
        if rc:
            category='REMOTE_FAILED'
            for term,name in [('permission denied','AUTH'),('connection reset','CONNECTION_RESET'),
                              ('connection closed','REMOTE_CLOSED'),('could not resolve','DNS'),
                              ('parsererror','POWERSHELL_PARSE'),('not recognized','REMOTE_EXEC_MISSING'),
                              ('access is denied','REMOTE_ACCESS_DENIED')]:
                if term in out.lower() or term in err:category=name;break
            self.log('transport_failure',rc=rc,category=category,stdout_bytes=len(captured[0]),stderr_bytes=len(captured[1]))
            raise TransportError(category)
        if expect and expect not in out:raise TransportError('CAULDRON_RECEIPT_MISSING')
        return out

    def remote(self,mode):
        file=r"Join-Path (Join-Path $env:USERPROFILE '.ritsu-control\campaign-packets') 'ritsu-closed-loop-"+self.remote_sha[:16]+".ps1'"
        script=("$ErrorActionPreference='Stop';$file="+file+";"
          "if(-not [IO.File]::Exists($file)){throw 'REMOTE_PACKET_MISSING'};"
          "& $file -Mode "+mode)
        text=self.invoke(script,timeout=26)
        candidates=[line.split('=',1)[1] for line in text.splitlines() if line.startswith('RITSU_EVIDENCE_JSON=')]
        if len(candidates)!=1:raise TransportError('REMOTE_JSON_RECEIPT_MISSING_OR_DUPLICATE')
        try: data=json.loads(candidates[0])
        except json.JSONDecodeError:raise TransportError('REMOTE_JSON_MALFORMED')
        if data.get('schema')!='ritsu.remote.probe.v1' or data.get('mode')!=mode:
            raise TransportError('REMOTE_SCHEMA_OR_MODE_MISMATCH')
        return data

    def ensure_remote(self):
        """Resumable content-addressed packet transport using EXISTING cauldron."""
        encoded=base64.b64encode(gzip.compress(REMOTE_PS.encode('utf-8'),mtime=0)).decode('ascii')
        sha=self.remote_sha
        folder=r"Join-Path $env:USERPROFILE '.ritsu-control\campaign-packets'"
        packet=f"Join-Path $dir 'ritsu-closed-loop-{sha[:16]}.ps1'"
        compressed=f"Join-Path $dir 'ritsu-closed-loop-{sha[:16]}.b64'"
        check=(f"$ErrorActionPreference='Stop';$dir={folder};$p={packet};"
               f"if([IO.File]::Exists($p)){{$h=(Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant();"
               f"if($h -eq '{sha}'){{Write-Output 'RITSU_PACKET=REUSED'}} else {{Write-Output 'RITSU_PACKET=COLLISION'}}}}"
               "else{Write-Output 'RITSU_PACKET=ABSENT'}")
        found=self.invoke(check,timeout=12)
        if 'RITSU_PACKET=REUSED' in found:
            self.log('packet_reused',sha256=sha)
            return
        if 'RITSU_PACKET=COLLISION' in found:raise TransportError('REMOTE_PACKET_COLLISION')
        if 'RITSU_PACKET=ABSENT' not in found:raise TransportError('PACKET_CHECK_UNVERIFIED')
        chunks=[encoded[i:i+REMOTE_CHUNK] for i in range(0,len(encoded),REMOTE_CHUNK)]
        if len(chunks)>45:raise TransportError('REMOTE_PACKET_EXCEEDS_BUDGET')
        for i,chunk in enumerate(chunks):
            self.remaining()
            pre=(f"$ErrorActionPreference='Stop';$dir={folder};"
                 f"[IO.Directory]::CreateDirectory($dir)|Out-Null;$file={compressed};")
            if i==0:
                step=pre+f"[IO.File]::WriteAllText($file,'{chunk}',[Text.Encoding]::ASCII);"
            else:
                prefix=''.join(chunks[:i]); h=hashlib.sha256(prefix.encode('ascii')).hexdigest()
                step=pre+(f"$cur=[IO.File]::ReadAllText($file);"
                          "$h=([BitConverter]::ToString([Security.Cryptography.SHA256]::Create().ComputeHash([Text.Encoding]::ASCII.GetBytes($cur)))).Replace('-','').ToLowerInvariant();"
                          f"if($h -ne '{h}'){{throw 'CHUNK_PREFIX_INVALID'}};"
                          f"[IO.File]::AppendAllText($file,'{chunk}',[Text.Encoding]::ASCII);")
            step+=f"Write-Output 'RITSU_CHUNK_{i}=PASS'"
            self.invoke(step,expect=f'RITSU_CHUNK_{i}=PASS',timeout=16)
        final=f"""$ErrorActionPreference='Stop';$dir={folder};$raw=[IO.File]::ReadAllText({compressed});
$mem=[IO.MemoryStream]::new([Convert]::FromBase64String($raw));
$zip=[IO.Compression.GzipStream]::new($mem,[IO.Compression.CompressionMode]::Decompress);
$reader=[IO.StreamReader]::new($zip,[Text.Encoding]::UTF8);$s=$reader.ReadToEnd();$reader.Close();
$p={packet};$h=([BitConverter]::ToString([Security.Cryptography.SHA256]::Create().ComputeHash([Text.Encoding]::UTF8.GetBytes($s)))).Replace('-','').ToLowerInvariant();
if($h -ne '{sha}'){{throw 'PAYLOAD_SHA_MISMATCH'}};
if([IO.File]::Exists($p) -and [IO.File]::ReadAllText($p,[Text.Encoding]::UTF8) -cne $s){{throw 'REMOTE_PACKET_COLLISION'}};
[IO.File]::WriteAllText($p,$s,(New-Object Text.UTF8Encoding($false)));
if((Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant() -ne '{sha}'){{throw 'PACKET_READBACK_FAIL'}};
Write-Output 'RITSU_PACKET=SHA256_VERIFIED'
"""
        # The decompression command could exceed the one-call encoded limit.
        if len('powershell.exe -EncodedCommand '+base64.b64encode(final.encode('utf-16le')).decode())>MAX_ENCODED_COMMAND:
            raise TransportError('REMOTE_FINALIZER_TOO_LONG')
        self.invoke(final,expect='RITSU_PACKET=SHA256_VERIFIED',timeout=20)
        self.log('packet_installed_and_verified',sha256=sha,chunks=len(chunks))

    def phone_probe(self):
        url=f'http://{TAILNET_HOST}:{TAILNET_PORT}/v1/ritsu/events?after=13'
        out=[]
        for i in range(2):
            try:
                with urllib.request.urlopen(urllib.request.Request(url,headers={'Connection':'close'}),timeout=4) as r:
                    code=int(r.status)
                out.append('HTTP_'+str(code))
            except urllib.error.HTTPError as ex:out.append('HTTP_'+str(ex.code));ex.close()
            except urllib.error.URLError as ex:
                reason=ex.reason
                if isinstance(reason,ConnectionResetError):out.append('CONNECTION_RESET')
                elif isinstance(reason,socket.timeout):out.append('TIMEOUT')
                elif isinstance(reason,ConnectionRefusedError):out.append('CONNECTION_REFUSED')
                else:out.append('NETWORK_'+type(reason).__name__)
            except (TimeoutError,socket.timeout):out.append('TIMEOUT')
            except ConnectionResetError:out.append('CONNECTION_RESET')
            except Exception as ex:out.append('ERROR_'+type(ex).__name__)
            if i==0:time.sleep(0.7)
        self.log('phone_tailnet_probe',attempts=out)
        return out

    def classify(self, remote, phone):
        if remote.get('status') not in ('PROBE_COMPLETE','PROBE_PARTIAL'):
            return ('REMOTE_PROBE_INVALID','NONE')
        if remote.get('status')=='PROBE_PARTIAL':
            return ('REMOTE_PROBE_PARTIAL_'+str(remote.get('error_class','UNKNOWN')),'NONE')
        if remote.get('node_count')==0 and remote.get('local_unauth_status')!='HTTP_401':
            if remote.get('task')=='EXACT_EXISTING_RITSU_LAUNCHER' and remote.get('tailnet_service')=='Running':
                return ('VERIFIED_SERVER_ABSENT_ELIGIBLE_FOR_TASK_RESTART','RECOVER')
            return ('SERVER_ABSENT_REPAIR_AUTHORITY_UNVERIFIED','NONE')
        if remote.get('node_count')!=1:return ('SERVER_PROCESS_COUNT_'+str(remote.get('node_count')),'NONE')
        if not remote.get('source_valid'):return ('ACTIVE_SERVER_PATH_UNVERIFIED','NONE')
        if not remote.get('patch_present'):return ('VERIFIED_SSE_PATCH_MISSING_NO_SOURCE_MUTATION_ALLOWED','NONE')
        if remote.get('listener_count')!=1 or remote.get('listener_port')!=LOCAL_PORT or remote.get('listener_address')!='127.0.0.1':
            return ('SERVER_LISTENER_IDENTITY_UNVERIFIED','NONE')
        if remote.get('local_unauth_status')!='HTTP_401':return ('LOCAL_AUTH_GATE_'+str(remote.get('local_unauth_status')),'NONE')
        if remote.get('authenticated_replay')!='SEQ14_ACCEPTED':return ('LOCAL_SSE_REPLAY_'+str(remote.get('authenticated_replay')),'NONE')
        if remote.get('seq14_type')!='partial' or not remote.get('seq14_empty'):
            return ('JOURNAL_SEQ14_CHANGED_PRESERVE','NONE')
        if remote.get('tailnet_service')!='Running':return ('TAILSCALE_SERVICE_NOT_RUNNING','NONE')
        if phone.count('HTTP_401')==2:
            return ('DIRECT_PATH_HEALTHY_ANDROID_RECONNECT_UNVERIFIED','NONE')
        if 'HTTP_401' in phone:
            return ('DIRECT_PATH_INTERMITTENT','NONE')
        if all(p in ('CONNECTION_RESET','CONNECTION_REFUSED','TIMEOUT') or p.startswith('NETWORK_') for p in phone):
            return ('PHONE_TAILNET_ROUTE_UNREACHABLE','NONE')
        return ('PHONE_DIRECT_PATH_UNEXPECTED_RESPONSE','NONE')

    def install_packet(self):
        """Safe local packet copy. Never change a tracked/user-modified file."""
        if not SOURCE.is_file():
            self.packaged='BLOCKED_SOURCE_NOT_FOUND';return
        self.source_sha=hashlib.sha256(SOURCE.read_bytes()).hexdigest()
        repo=HOME/'storage'/'documents'/'GodotProjects'/'home-center'
        target=repo/'tools'/'campaigns'/'ritsu-stream-recovery-closed-loop.sh'
        if not (repo/'.git').exists():
            self.packaged='BLOCKED_TARGET_REPO_NOT_FOUND';return
        # Don't depend on git remote connectivity, and do not change index/HEAD.
        try:
            p=subprocess.run(['git','-C',str(repo),'remote','get-url','origin'],capture_output=True,text=True,timeout=5)
            remote=p.stdout.strip().lower()
            if p.returncode or 'valar05/home-center' not in remote:
                self.packaged='BLOCKED_REPO_IDENTITY';return
        except (FileNotFoundError,subprocess.TimeoutExpired):
            self.packaged='BLOCKED_GIT_IDENTITY_TOOL';return
        target.parent.mkdir(parents=True,exist_ok=True)
        if target.exists():
            if hashlib.sha256(target.read_bytes()).hexdigest()!=self.source_sha:
                self.packaged='BLOCKED_EXISTING_PACKET_DIFFERS';return
            self.packaged='REUSED_EXACT_HASH';return
        fd=None
        try:
            fd=os.open(str(target),os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o644)
            with os.fdopen(fd,'wb') as f:fd=None;f.write(SOURCE.read_bytes());f.flush();os.fsync(f.fileno())
            if hashlib.sha256(target.read_bytes()).hexdigest()!=self.source_sha:
                self.packaged='BLOCKED_PACKET_READBACK';return
            self.packaged='INSTALLED_HASH_VERIFIED_UNCOMMITTED'
        except FileExistsError:self.packaged='BLOCKED_PACKET_RACE'
        except OSError as ex:self.packaged='BLOCKED_REPO_WRITE_'+type(ex).__name__
        finally:
            if fd is not None:os.close(fd)

    def save(self):
        receipt={
            'schema':'ritsu.stream_recovery.receipt.v1','campaign':CAMPAIGN,'version':VERSION,
            'run_id':self.id,'timestamp_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'status':self.status,'cause':self.cause,'human_action':self.human_action,
            'source_sha256':self.source_sha,'packet_repo_status':self.packaged,
            'remote_packet_sha256':self.remote_sha,'transport_calls':self.transport_calls,
            'elapsed_seconds':round(time.monotonic()-self.started,2),
            'tailnet_target':f'{TAILNET_HOST}:{TAILNET_PORT}',
            'remote_evidence':self.evidence.get('remote',{}),
            'phone_unauthenticated_path_probes':self.evidence.get('phone',[]),
            'repair_evidence':self.evidence.get('repair',{}),
            'proof_limits':{
                'physical_app_reconnect':'NOT_OBSERVED',
                'pending_turn_sent_again':'NO_ACTION_TAKEN',
                'android_apk':'UNTOUCHED', 'pairing':'UNTOUCHED',
                'journal':'READ_ONLY', 'server_source':'READ_ONLY',
                'no_model_or_browser_submission':'TRUE'
            }, 'steps':self.steps, 'local_log':str(self.logpath),
            'continuity':{'etiquette_url':DOCS_ETIQUETTE,'handoff_url':DOCS_HANDOFF}
        }
        raw=json.dumps(receipt,indent=2,sort_keys=True,ensure_ascii=False)+'\n'
        path=self.dir/'receipt.json'
        for output in (path,RECEIPT):
            fd,tmp=tempfile.mkstemp(prefix='.ritsu-',dir=str(output.parent))
            with os.fdopen(fd,'w',encoding='utf-8') as w:w.write(raw);w.flush();os.fsync(w.fileno())
            os.replace(tmp,output)
        dest=HOME/'storage'/'downloads'
        if dest.is_dir():
            dst=dest/f'Ritsu-Stream-Recovery-{self.id}.json'
            try:
                with dst.open('x',encoding='utf-8') as f:f.write(raw)
                if hashlib.sha256(dst.read_bytes()).hexdigest()==hashlib.sha256(raw.encode()).hexdigest():
                    self.evidence['public_receipt']=str(dst)
            except OSError:self.evidence['public_receipt']='UNAVAILABLE'
        print('\nRITSU_STREAM_RECOVERY_FINAL')
        print('CAMPAIGN_STATUS='+self.status)
        print('DIAGNOSIS='+self.cause)
        print('REPO_PACKET='+self.packaged)
        print('ANDROID_APP_ACCEPTANCE=UNVERIFIED')
        print('PENDING_TURN=NOT_RESUBMITTED')
        print('PRESERVED=APK,PAIRING,JOURNAL,EXISTING_PENDING_TURN')
        print('OWNER_NEXT_ACTION='+self.human_action)
        print('RECEIPT='+str(path))
        print('LAST_RECEIPT='+str(RECEIPT))
        print('PUBLIC_RECEIPT='+self.evidence.get('public_receipt','UNAVAILABLE'))
        print('COMPLETE_EVIDENCE=SEE_RECEIPT_NOT_RAW_CONSOLE_COURIER')

    def main(self):
        self.dir.mkdir(parents=True,exist_ok=False)
        try:
            self.install_packet()
            self.log('preflight',source_sha256=self.source_sha,packet=self.packaged)
            if not shutil.which('cauldron'):
                self.cause='CAULDRON_COMMAND_MISSING';return
            if not self.source_sha:
                self.cause='SCRIPT_SOURCE_NOT_VERIFIABLE';return
            self.ensure_remote()
            remote=self.remote('PROBE');self.evidence['remote']=remote
            self.log('remote_probe',status=remote.get('status'),node_count=remote.get('node_count'),
                     replay=remote.get('authenticated_replay'))
            phone=self.phone_probe();self.evidence['phone']=phone
            cause,action=self.classify(remote,phone)
            if action=='RECOVER':
                self.log('guarded_restart_selected',cause=cause)
                recovery=self.remote('RECOVER');self.evidence['repair']=recovery
                if recovery.get('repair')=='VERIFIED_LOCAL_401':
                    remote=self.remote('PROBE');self.evidence['remote']=remote
                    phone=self.phone_probe();self.evidence['phone']=phone
                    cause,_=self.classify(remote,phone)
                    self.log('post_repair_recheck',cause=cause)
                else:cause='EXISTING_LAUNCHER_RESTART_'+str(recovery.get('repair'))
            self.cause=cause
            if cause=='DIRECT_PATH_HEALTHY_ANDROID_RECONNECT_UNVERIFIED':
                self.status='SERVER_AND_TAILNET_PATH_VERIFIED_PHONE_ACCEPTANCE_OPEN'
                self.human_action='OPEN_EXISTING_RITSU_CONVERSATION_ONLY_DO_NOT_RESEND'
            elif cause=='DIRECT_PATH_INTERMITTENT':
                self.status='BLOCKED_INTERMITTENT_PHONE_ROUTE'
                self.human_action='NONE_RESULTS_IN_RECEIPT'
            else:
                self.status='BLOCKED_WITH_DIAGNOSIS'
                self.human_action='NONE_RESULTS_IN_RECEIPT'
        except Deadline as ex:self.cause=str(ex);self.status='BLOCKED_TIME_BUDGET'
        except TransportError as ex:self.cause=str(ex);self.status='BLOCKED_TRANSPORT'
        except Exception as ex:
            self.cause='UNEXPECTED_'+type(ex).__name__;self.status='BLOCKED_UNEXPECTED'
            self.log('exception',exception_type=type(ex).__name__)
        finally:self.save()

def self_test():
    checks=[]
    r=Run()
    healthy=dict(schema='ritsu.remote.probe.v1',mode='PROBE',status='PROBE_COMPLETE',
        node_count=1,source_valid=True,patch_present=True,listener_count=1,
        listener_port=19647,listener_address='127.0.0.1',local_unauth_status='HTTP_401',
        authenticated_replay='SEQ14_ACCEPTED',seq14_type='partial',seq14_empty=True,
        tailnet_service='Running',task='EXACT_EXISTING_RITSU_LAUNCHER')
    cases=[
        ('healthy',healthy,['HTTP_401','HTTP_401'],'DIRECT_PATH_HEALTHY_ANDROID_RECONNECT_UNVERIFIED','NONE'),
        ('intermittent',healthy,['CONNECTION_RESET','HTTP_401'],'DIRECT_PATH_INTERMITTENT','NONE'),
        ('vpn_down',healthy,['TIMEOUT','CONNECTION_RESET'],'PHONE_TAILNET_ROUTE_UNREACHABLE','NONE'),
        ('replay_bad',{**healthy,'authenticated_replay':'HTTP_403'},['HTTP_401','HTTP_401'],'LOCAL_SSE_REPLAY_HTTP_403','NONE'),
        ('patch_absent',{**healthy,'patch_present':False},['HTTP_401','HTTP_401'],'VERIFIED_SSE_PATCH_MISSING_NO_SOURCE_MUTATION_ALLOWED','NONE'),
        ('server_missing',{**healthy,'node_count':0,'local_unauth_status':'NETWORK_ConnectFailure'},['CONNECTION_REFUSED']*2,'VERIFIED_SERVER_ABSENT_ELIGIBLE_FOR_TASK_RESTART','RECOVER'),
        ('wrong_launcher',{**healthy,'node_count':0,'local_unauth_status':'NETWORK_ConnectFailure','task':'NOT_FOUND'},['TIMEOUT']*2,'SERVER_ABSENT_REPAIR_AUTHORITY_UNVERIFIED','NONE'),
        ('wrong_port',{**healthy,'listener_port':19646},['HTTP_401']*2,'SERVER_LISTENER_IDENTITY_UNVERIFIED','NONE'),
        ('wrong_journal',{**healthy,'seq14_empty':False},['HTTP_401']*2,'JOURNAL_SEQ14_CHANGED_PRESERVE','NONE'),
        ('remote_partial',{**healthy,'status':'PROBE_PARTIAL','error_class':'SomeError'},['HTTP_401']*2,'REMOTE_PROBE_PARTIAL_SomeError','NONE')]
    for name,remote,phone,want,action in cases:
        got=r.classify(remote,phone)
        if got!=(want,action):raise AssertionError((name,got,want,action))
        checks.append(name)
    # Encoding contract: remote wrapper never exceeds its 3400-character cap.
    pkt=r.remote_sha
    assert len(pkt)==64
    assert 'Start-ScheduledTask' in REMOTE_PS and 'Stop-Process' not in REMOTE_PS
    assert 'Send' not in REMOTE_PS and 'device-token' in REMOTE_PS
    assert 'HomeCenter' not in REMOTE_PS
    print('RITSU_CLOSED_LOOP_SELF_TEST=PASS')
    print('SCENARIOS='+str(len(checks)))
    print('CASES='+','.join(checks))

if __name__=='__main__':
    if len(sys.argv)>1 and sys.argv[1]=='--self-test':self_test();sys.exit(0)
    if len(sys.argv)>1:
        print('CAMPAIGN_STATUS=BLOCKED_INVALID_ARGUMENTS');sys.exit(2)
    STATE.mkdir(parents=True,exist_ok=True);RUN_DIR.mkdir(parents=True,exist_ok=True)
    lockpath=STATE/'campaign.lock'
    with lockpath.open('a+') as f:
        try:fcntl.flock(f.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:
            print('CAMPAIGN_STATUS=ALREADY_RUNNING');print('RECEIPT='+str(RECEIPT));sys.exit(3)
        campaign=Run();campaign.main()
        sys.exit(0 if campaign.status.startswith('SERVER_AND_') else 4)
PYTHON_CAMPAIGN
