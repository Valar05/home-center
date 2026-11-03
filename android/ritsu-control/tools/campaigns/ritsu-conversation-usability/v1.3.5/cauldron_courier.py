"""Existing Termux cauldron string transport only. One command, bounded packets,
remote SHA reconciliation, visible error reasons, no manual log courier."""
import base64,gzip,hashlib,io,os,pathlib,re,signal,subprocess,threading,zipfile
class RemoteBlocked(RuntimeError):pass

def sha(s):return hashlib.sha256(s).hexdigest()
def ps_cmd(src):return 'powershell.exe -NoProfile -NonInteractive -EncodedCommand '+base64.b64encode(src.encode('utf-16le')).decode('ascii')
def invoke(label,script,seconds=50):
    cmd=ps_cmd(script)
    if len(cmd)>3400:raise RemoteBlocked('REMOTE_COMMAND_EXCEEDS_KNOWN_LIMIT_'+label)
    try:p=subprocess.Popen(['cauldron',cmd],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
    except OSError as e:raise RemoteBlocked('CAULDRON_NOT_AVAILABLE_'+type(e).__name__)
    out,err=bytearray(),bytearray()
    def read(s,b):
        while True:
            chunk=s.read(8192)
            if not chunk:break
            if len(b)<30000:b.extend(chunk[:30000-len(b)])
    threads=[threading.Thread(target=read,args=(p.stdout,out),daemon=True),threading.Thread(target=read,args=(p.stderr,err),daemon=True)]
    for t in threads:t.start()
    try:rc=p.wait(timeout=seconds)
    except subprocess.TimeoutExpired:
        with __import__('contextlib').suppress(ProcessLookupError):os.killpg(p.pid,signal.SIGTERM)
        try:p.wait(timeout=3)
        except subprocess.TimeoutExpired:
            with __import__('contextlib').suppress(ProcessLookupError):os.killpg(p.pid,signal.SIGKILL)
            p.wait()
        raise RemoteBlocked('CAULDRON_TIMEOUT_'+label)
    finally:
        if p.stdin:p.stdin.close()
    for t in threads:t.join(2)
    visible=re.sub(r'\x1b\[[0-9;]*[A-Za-z]','',out.decode('utf8','replace')).replace('\r','')
    if rc:
        public=[]
        for line in visible.splitlines():
            if re.match(r'^(RITSU_WINDOWS_BLOCKED|WINDOWS_FAILURE_PHASE|WINDOWS_FAILURE_CLASS|WINDOWS_ROLLBACK_LISTENER)=',line):public.append(line)
        hint=';'.join(public[:6]) or ('cauldron_rc_'+str(rc)+'_output_bytes_'+str(len(out))+'_stderr_bytes_'+str(len(err)))
        raise RemoteBlocked('CAULDRON_'+label+'_FAILED_'+hint[:250])
    return visible

def verify_endpoint(progress=print):
    """Read-only, independently authenticated zero-turn canary.
    Never probes an actual user turn or resends text.
    """
    script=(
      "$ErrorActionPreference='Stop';try{"
      "$p=@(Get-CimInstance Win32_Process -Filter \"Name='node.exe'\"|Where-Object{$_.CommandLine -match 'ritsu-local-server[\\/]server\\.mjs'});"
      "if($p.Count -ne 1){Write-Output ('RECOVERY_PROBE=SERVER_COUNT_'+$p.Count);exit 0};"
      "$l=@(Get-NetTCPConnection -OwningProcess $p[0].ProcessId -State Listen -ErrorAction Stop|Where-Object{$_.LocalPort -in @(19646,19647)});"
      "if($l.Count -ne 1){Write-Output ('RECOVERY_PROBE=LISTENER_COUNT_'+$l.Count);exit 0};"
      "$token=[IO.File]::ReadAllText((Join-Path $env:USERPROFILE '.ritsu-control\\local-link\\device-token')).Trim();"
      "$url='http://'+$l[0].LocalAddress+':'+$l[0].LocalPort+'/v1/ritsu/recover?turnId=00000000-0000-0000-0000-000000000000&tabId=main&promptSha256='+('0'*64);"
      "$r=Invoke-RestMethod -Uri $url -Headers @{Authorization='Bearer '+$token} -TimeoutSec 8;"
      "if($r.ok -eq $true -and $r.state -eq 'no_server_receipt'){Write-Output 'RITSU_RECOVERY_ROUTE=VERIFIED'}else{Write-Output 'RECOVERY_PROBE=UNEXPECTED_RESPONSE'}"
      "}catch{Write-Output ('RECOVERY_PROBE=ERROR_'+$_.Exception.GetType().Name)}"
    )
    data=invoke('READ_ONLY_ENDPOINT_PROBE',script,seconds=25)
    for line in data.splitlines():
        if line.startswith(('RECOVERY_PROBE=','RITSU_RECOVERY_ROUTE=')):
            progress(line)
    if 'RITSU_RECOVERY_ROUTE=VERIFIED' not in data:return False
    catalog=(
      "$ErrorActionPreference='Stop';try{"
      "$p=@(Get-CimInstance Win32_Process -Filter \"Name='node.exe'\"|Where-Object{$_.CommandLine -match 'ritsu-local-server[\\/]server\\.mjs'});"
      "if($p.Count -ne 1){Write-Output 'CATALOG_PROBE=SERVER_IDENTITY';exit 0};"
      "$l=@(Get-NetTCPConnection -OwningProcess $p[0].ProcessId -State Listen|Where-Object{$_.LocalPort -in @(19646,19647)});"
      "if($l.Count -ne 1){Write-Output 'CATALOG_PROBE=LISTENER';exit 0};"
      "$t=[IO.File]::ReadAllText((Join-Path $env:USERPROFILE '.ritsu-control\\local-link\\device-token')).Trim();"
      "$u='http://'+$l[0].LocalAddress+':'+$l[0].LocalPort+'/v1/ritsu/catalog?probe=1';"
      "try{$r=Invoke-WebRequest -Uri $u -Headers @{Authorization='Bearer '+$t} -UseBasicParsing -TimeoutSec 40;"
      "$c=[int]$r.StatusCode}catch{$c=if($_.Exception.Response){[int]$_.Exception.Response.StatusCode}else{0}};"
      "Write-Output ('CATALOG_PROBE_HTTP='+$c)"
      "}catch{Write-Output ('CATALOG_PROBE=ERROR_'+$_.Exception.GetType().Name)}"
    )
    c=invoke('CATALOG_ROUTE_PROBE',catalog,seconds=53)
    for line in c.splitlines():
        if line.startswith(('CATALOG_PROBE=', 'CATALOG_PROBE_HTTP=')):progress(line)
    return 'CATALOG_PROBE_HTTP=200' in c

def inspect_apply_receipt(digest,progress=print):
    path=f'v1.3.5-{digest[:16]}'
    script=(
      "$d=Join-Path $env:USERPROFILE '.ritsu-control\\campaign-packets';"
      f"$f=Join-Path (Join-Path $d '{path}') 'apply-receipt-v1.3.5.txt';"
      "if(-not [IO.File]::Exists($f)){Write-Output 'REMOTE_APPLY_RECEIPT=ABSENT';exit 0};"
      "$rows=@([IO.File]::ReadAllLines($f,[Text.Encoding]::UTF8));"
      "foreach($r in $rows){if($r -match '^(RITSU_APPLY_LAUNCH|WINDOWS_PHASE|WINDOWS_FAILURE_PHASE|WINDOWS_FAILURE_CLASS|WINDOWS_ROLLBACK_LISTENER|WINDOWS_SOURCE_ROLLBACK|RITSU_WINDOWS_BLOCKED|RITSU_WINDOWS_PATCH|SERVER_RESTART|READ_ONLY_RECOVERY_ROUTE)='){Write-Output $r}}"
    )
    try:
        got=invoke('READBACK_WINDOWS_PHASE',script,seconds=25)
        for line in got.splitlines():
            if line.startswith(('RITSU_APPLY_LAUNCH=','WINDOWS_PHASE=','WINDOWS_FAILURE_','WINDOWS_ROLLBACK_', 'WINDOWS_SOURCE_ROLLBACK=','RITSU_WINDOWS_BLOCKED=','RITSU_WINDOWS_PATCH=', 'SERVER_RESTART=', 'READ_ONLY_RECOVERY_ROUTE=', 'REMOTE_APPLY_RECEIPT=')):
                progress(line)
        return got
    except RemoteBlocked as e:
        progress('WINDOWS_PHASE_READBACK=BLOCKED_'+str(e)[:130])
        return ''

def apply(packet,progress=print):
    if verify_endpoint(progress):
        progress('WINDOWS_PATCH=ALREADY_OPERATIONAL_NO_MUTATION')
        return 'WINDOWS_RECOVERY_ENDPOINT_VERIFIED_EXISTING'
    candidates=['windows_apply.ps1','server_recovery_patch.js','ritsu_browser_recover_v133.mjs','ritsu_browser_catalog_v135.mjs','server_catalog_functions.js','server_catalog_routes.js']
    root=pathlib.Path(packet)
    blob=io.BytesIO()
    with zipfile.ZipFile(blob,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for name in candidates:z.write(root/name,name)
    raw=blob.getvalue();digest=sha(raw)
    b64=base64.b64encode(raw).decode('ascii');chunks=[b64[i:i+590] for i in range(0,len(b64),590)]
    progress('CAULDRON_PACKET_SHA256='+digest)
    probe=invoke('PREFLIGHT',"Write-Output 'RITSU_CAULDRON_PREFLIGHT=PASS'")
    if 'RITSU_CAULDRON_PREFLIGHT=PASS' not in probe:raise RemoteBlocked('CAULDRON_PREFLIGHT_UNVERIFIED')
    progress('CAULDRON_TRANSPORT=PROVEN_STRING_CHANNEL')
    common=r"$ErrorActionPreference='Stop';$d=Join-Path $env:USERPROFILE '.ritsu-control\campaign-packets';[IO.Directory]::CreateDirectory($d)|Out-Null;"
    filename='ritsu-recovery-'+digest[:16]+'.b64'
    for i,chunk in enumerate(chunks):
        prefix=common+f"$f=Join-Path $d '{filename}';"
        if i==0:
            step=prefix+f"[IO.File]::WriteAllText($f,'{chunk}',[Text.Encoding]::ASCII);"
        else:
            expected=sha(''.join(chunks[:i]).encode('ascii'))
            step=prefix+("$got=([BitConverter]::ToString([Security.Cryptography.SHA256]::Create().ComputeHash([Text.Encoding]::ASCII.GetBytes([IO.File]::ReadAllText($f))))).Replace('-','').ToLowerInvariant();"+
                         f"if($got -ne '{expected}'){{throw 'REMOTE_TRANSFER_PRIOR_CHUNK_CHANGED'}};"+
                         f"[IO.File]::AppendAllText($f,'{chunk}',[Text.Encoding]::ASCII);")
        step+=f"Write-Output 'RITSU_CHUNK_{i}=PASS'"
        check=invoke(str(i),step)
        if f'RITSU_CHUNK_{i}=PASS' not in check:raise RemoteBlocked('CAULDRON_PACKET_RECEIPT_MISSING_'+str(i))
        progress(f'CAULDRON_TRANSFER={i+1}/{len(chunks)}')
    # Only one fixed packet for this campaign version, no user source mutation.
    finish=common+f"$f=Join-Path $d '{filename}';"+r"$raw=[Convert]::FromBase64String([IO.File]::ReadAllText($f));"+\
        f"$got=([BitConverter]::ToString([Security.Cryptography.SHA256]::Create().ComputeHash($raw))).Replace('-','').ToLowerInvariant();if($got -ne '{digest}'){{throw 'REMOTE_ZIP_SHA_MISMATCH'}};"+\
        f"$folder=Join-Path $d 'v1.3.5-{digest[:16]}';"+\
        r"$zip=Join-Path $d ('ritsu-recovery-'+$got.Substring(0,16)+'.zip');"+\
        r"if(-not [IO.File]::Exists($zip)){[IO.File]::WriteAllBytes($zip,$raw)}else{$actual=([BitConverter]::ToString([Security.Cryptography.SHA256]::Create().ComputeHash([IO.File]::ReadAllBytes($zip)))).Replace('-','').ToLowerInvariant();if($actual -ne $got){throw 'PACKET_NAME_COLLISION'}};"+\
        r"if(-not [IO.Directory]::Exists($folder)){[IO.Compression.ZipFile]::ExtractToDirectory($zip,$folder)};"+\
        r"$src=Join-Path $folder 'windows_apply.ps1';if(-not [IO.File]::Exists($src)){throw 'EXTRACTED_APPLY_MISSING'};"+\
        r"Write-Output 'RITSU_REMOTE_ZIP_EXTRACTED=PASS'"
    # Use .NET System.IO.Compression.FileSystem in Windows PowerShell 5.
    finish="Add-Type -AssemblyName System.IO.Compression.FileSystem;"+finish
    archiveReceipt=invoke('EXTRACT',finish,seconds=40)
    if 'RITSU_REMOTE_ZIP_EXTRACTED=PASS' not in archiveReceipt:raise RemoteBlocked('REMOTE_ZIP_EXTRACTION_UNVERIFIED')
    manifest={name:sha((root/name).read_bytes()) for name in candidates}
    for n,(name,expected) in enumerate(manifest.items()):
        check=(common+f"$folder=Join-Path $d 'v1.3.5-{digest[:16]}';$member=Join-Path $folder '{name}';"+
               f"if(-not [IO.File]::Exists($member)){{throw 'MISSING_EXTRACTED_{name}'}};"+
               "$got=([BitConverter]::ToString([Security.Cryptography.SHA256]::Create().ComputeHash([IO.File]::ReadAllBytes($member)))).Replace('-','').ToLowerInvariant();"+
               f"if($got -ne '{expected}'){{throw 'EXTRACTED_SHA_MISMATCH_{name}'}};"+
               f"Write-Output 'RITSU_EXTRACTED_{n}=PASS'")
        receipt=invoke('VERIFY_FILE_'+str(n),check,seconds=25)
        if f'RITSU_EXTRACTED_{n}=PASS' not in receipt:raise RemoteBlocked('REMOTE_EXTRACTED_SOURCE_SHA_NOT_VERIFIED_'+name)
    progress('CAULDRON_PACKET_FILE_HASHES=VERIFIED')
    # The previous script invoked a .ps1 file directly. Local PowerShell
    # execution policy can reject that even while cauldron returns rc=0.
    # Execute the already SHA-verified file as an in-memory ScriptBlock.
    # Do not modify the system execution policy or create another transport.
    remoteScript=(common+
        f"$folder=Join-Path $d 'v1.3.5-{digest[:16]}';"+
        "$src=Join-Path $folder 'windows_apply.ps1';"+
        "$env:RITSU_RECOVERY_PACKET_DIR=$folder;"+
        "$env:RITSU_RECOVERY_RECEIPT_PATH=Join-Path $folder 'apply-receipt-v1.3.5.txt';"+
        "[IO.File]::WriteAllText($env:RITSU_RECOVERY_RECEIPT_PATH,'RITSU_APPLY_LAUNCH=STARTED'+[char]10,[Text.Encoding]::UTF8);"+
        "$script=[ScriptBlock]::Create([IO.File]::ReadAllText($src,[Text.Encoding]::UTF8));"+
        "& $script")
    result='';failure=''
    try:
        result=invoke('APPLY',remoteScript,seconds=120)
    except RemoteBlocked as e:
        failure=str(e)[:220]
        progress('WINDOWS_APPLY_TRANSPORT='+failure)
    for line in result.splitlines():
        if re.match(r'^(SERVER_PATCH|RITSU_WINDOWS_PATCH|SERVER_RESTART|READ_ONLY_RECOVERY_ROUTE|PROMPT_RESUBMITTED|JOURNAL_REWRITTEN|WINDOWS_FAILURE|RITSU_WINDOWS_BLOCKED|WINDOWS_PHASE)=',line):progress(line)
    receipt=inspect_apply_receipt(digest,progress)
    if verify_endpoint(progress):
        progress('RITSU_WINDOWS_PATCH=PASS_VERIFIED_BY_INDEPENDENT_ENDPOINT')
        return 'WINDOWS_RECOVERY_ENDPOINT_VERIFIED'
    if failure:raise RemoteBlocked('REMOTE_PATCH_NOT_FIELD_VERIFIED_'+failure[:160])
    status=''.join(x+';' for x in receipt.splitlines() if x.startswith(('RITSU_WINDOWS_BLOCKED=','WINDOWS_FAILURE_PHASE=','WINDOWS_FAILURE_CLASS=','WINDOWS_SOURCE_ROLLBACK=','WINDOWS_ROLLBACK_LISTENER=')))
    raise RemoteBlocked('REMOTE_PATCH_NOT_FIELD_VERIFIED_'+(status or 'NO_LIVE_RECOVERY_ENDPOINT')[:190])
