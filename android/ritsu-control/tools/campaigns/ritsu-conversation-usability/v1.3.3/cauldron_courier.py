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

def apply(packet,progress=print):
    candidates=['windows_apply.ps1','server_recovery_patch.js','ritsu_browser_recover_v133.mjs']
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
        f"$folder=Join-Path $d 'v1.3.3-{digest[:16]}';"+\
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
        check=(common+f"$folder=Join-Path $d 'v1.3.3-{digest[:16]}';$member=Join-Path $folder '{name}';"+
               f"if(-not [IO.File]::Exists($member)){{throw 'MISSING_EXTRACTED_{name}'}};"+
               "$got=([BitConverter]::ToString([Security.Cryptography.SHA256]::Create().ComputeHash([IO.File]::ReadAllBytes($member)))).Replace('-','').ToLowerInvariant();"+
               f"if($got -ne '{expected}'){{throw 'EXTRACTED_SHA_MISMATCH_{name}'}};"+
               f"Write-Output 'RITSU_EXTRACTED_{n}=PASS'")
        receipt=invoke('VERIFY_FILE_'+str(n),check,seconds=25)
        if f'RITSU_EXTRACTED_{n}=PASS' not in receipt:raise RemoteBlocked('REMOTE_EXTRACTED_SOURCE_SHA_NOT_VERIFIED_'+name)
    progress('CAULDRON_PACKET_FILE_HASHES=VERIFIED')
    remoteScript=common+f"$folder=Join-Path $d 'v1.3.3-{digest[:16]}';"+r"& (Join-Path $folder 'windows_apply.ps1');exit $LASTEXITCODE"
    result=invoke('APPLY',remoteScript,seconds=120)
    for line in result.splitlines():
        if re.match(r'^(SERVER_PATCH|RITSU_WINDOWS_PATCH|SERVER_RESTART|READ_ONLY_RECOVERY_ROUTE|PROMPT_RESUBMITTED|JOURNAL_REWRITTEN|WINDOWS_FAILURE|RITSU_WINDOWS_BLOCKED)=',line):progress(line)
    if 'RITSU_WINDOWS_PATCH=PASS' not in result or 'READ_ONLY_RECOVERY_ROUTE=AUTHENTICATED_TEST_PASS' not in result:
        raise RemoteBlocked('REMOTE_PATCH_NOT_FIELD_VERIFIED')
    return 'WINDOWS_RECOVERY_ENDPOINT_VERIFIED'
