#!/usr/bin/env python3
"""Ritsu Conversation Usability v1.3.1, one supervised Termux invocation.
Fails closed before deployment on unknown Windows/Android/voice/signing state.
No GitHub writes, no Home Center/Computer Hands, no ChatGPT prompt dispatch.
"""
from __future__ import annotations
import base64,contextlib,datetime,fcntl,gzip,hashlib,json,os,pathlib,re,shutil,signal,subprocess,sys,tempfile,threading,time,zipfile

VERSION='1.3.1'
CAMPAIGN='ritsu-conversation-usability'
HOME=pathlib.Path.home()
STATE=HOME/'.local/state/ritsu-conversation-usability'
NOW=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
RUN=STATE/'runs'/(NOW+'-'+str(os.getpid()))
PACKET=pathlib.Path(__file__).resolve().parent
KNOWN_GRADLE='3f6c579239cbdfd47d0429fa33d26205e2df8155bb9f67522d4fb2b985cc82ae'
KNOWN_CERT='c9ff64cb5558204c19300b6945dbcf88cdd32a97e43b21acbbdb8a5b08b79473'
VOICE_SHA='3dda464df8d5e24d29db471df7c7b8d70d28741c98866996a980afe5443c6ad8'
WINDOWS_ROOT=r'C:\Users\dclar\AppData\Local\RitsuControlBridge\release-016'
FILES=['patch_android.py','patch_backend.py','RitsuConversationDeck.java','RitsuConversationLinks.java','ritsu_pocket_voice_hook.mjs']
phase='INIT';terminal_status='BLOCKED';reason='NOT_STARTED';receipts={}
started=time.monotonic();stop=threading.Event();LOCK=None

class Block(Exception):pass

def sha(path):
    d=hashlib.sha256()
    with open(path,'rb') as f:
        for block in iter(lambda:f.read(1<<20),b''):d.update(block)
    return d.hexdigest()

def log(message):
    print(str(message),flush=True)

def stage(name,note=''):
    global phase
    phase=name
    log('RITSU_PROGRESS='+name+(' '+note if note else ''))

def heartbeat():
    while not stop.wait(12):
        log('RITSU_HEARTBEAT=phase:'+phase+',elapsed_seconds:'+str(int(time.monotonic()-started)))

def receipt():
    body={'campaign':CAMPAIGN,'version':VERSION,'run':str(RUN),'status':terminal_status,
      'reason':reason,'last_stage':phase,'evidence':receipts,
      'accepted':{'ui_scroll':'NEEDS_PHONE','pocket_tts':'NEEDS_HEARD','chat_bind':'NEEDS_OWNER_CANARY'},
      'preserved':['installed_apk','signing_key','journal','pairing','pending_turn','existing_browser_chats'],
      'no_prompt_submitted':True,'apk_installed':False}
    RUN.mkdir(parents=True,exist_ok=True)
    out=RUN/'final-receipt.json';out.write_text(json.dumps(body,indent=2,sort_keys=True)+'\n')
    log('RITSU_CONVERSATION_USABILITY_FINAL')
    for k,v in [('CAMPAIGN_VERSION',VERSION),('CAMPAIGN_STATUS',terminal_status),('LAST_STAGE',phase),('REASON',reason),
      ('APK_INSTALLED','NO'),('EXISTING_CHATS_MODIFIED','NO'),('PROMPT_RESUBMITTED','NO'),
      ('PHONE_UI_ACCEPTANCE','PENDING'),('POCKET_OWNER_HEARD','PENDING'),('EXISTING_CHAT_CONTINUED','PENDING'),('RECEIPT',out)]:
        log(k+'='+str(v))
    for name,value in receipts.items():
        if isinstance(value,(str,int,float,bool)):
            log('RESULT_'+name.upper()+'='+str(value)[:180])

def command(argv,timeout,redact=False,cwd=None,env=None):
    p=subprocess.Popen(argv,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
                       start_new_session=True,cwd=cwd,env=env)
    try:data=p.communicate(timeout=timeout)[0]
    except subprocess.TimeoutExpired:
        with contextlib.suppress(ProcessLookupError):os.killpg(p.pid,signal.SIGTERM)
        try:data=p.communicate(timeout=2)[0]
        except subprocess.TimeoutExpired:
            with contextlib.suppress(ProcessLookupError):os.killpg(p.pid,signal.SIGKILL)
            data=p.communicate()[0]
        raise Block('SUBPROCESS_TIMEOUT_'+pathlib.Path(argv[0]).name)
    output=data.decode('utf8','replace')[-16000:]
    if p.returncode!=0:
        safe=re.sub(r'(?i)(bearer|password|token)[^\s]{0,100}', '[REDACTED]',output)
        receipts['last_command_failure_excerpt']=safe[-1000:]
        raise Block('COMMAND_FAILED_'+pathlib.Path(argv[0]).name+'_'+str(p.returncode))
    return output

def ps_command(text):
    blob=base64.b64encode(gzip.compress(text.encode('utf8'),mtime=0)).decode()
    wrapper=("$m=[IO.MemoryStream]::new([Convert]::FromBase64String('"+blob+"'));"
        "$z=[IO.Compression.GzipStream]::new($m,[IO.Compression.CompressionMode]::Decompress);"
        "& ([ScriptBlock]::Create(([IO.StreamReader]::new($z)).ReadToEnd()))")
    c='powershell.exe -NoProfile -NonInteractive -EncodedCommand '+base64.b64encode(wrapper.encode('utf-16le')).decode()
    if len(c)>3400:raise Block('POWERSHELL_ENCODED_SIZE_LIMIT_'+str(len(c)))
    return c

def cauldron(label,ps,timeout=35):
    stage(label)
    if not shutil.which('cauldron'):raise Block('APPROVED_CAULDRON_COMMAND_NOT_ON_PATH')
    c=ps_command(ps)
    p=subprocess.Popen(['cauldron',c],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
    try:out,err=p.communicate(input=b'',timeout=timeout)
    except subprocess.TimeoutExpired:
        with contextlib.suppress(ProcessLookupError):os.killpg(p.pid,signal.SIGTERM)
        try:p.communicate(timeout=2)
        except subprocess.TimeoutExpired:
            with contextlib.suppress(ProcessLookupError):os.killpg(p.pid,signal.SIGKILL)
            p.communicate()
        raise Block('CAULDRON_TIMEOUT_'+label)
    raw=out.decode('utf8','replace')
    matches=re.findall(r'RITSU_UX_RECEIPT=([A-Za-z0-9+/=]+)',raw)
    if p.returncode!=0 or len(matches)!=1:
        coarse='SSH_PERMISSION_DENIED' if b'Permission denied' in err else 'MISSING_OR_MALFORMED_RECEIPT'
        log('CAULDRON_FAILURE=phase:'+label+',exit:'+str(p.returncode)+',stdout_bytes:'+str(len(out))+',stderr_bytes:'+str(len(err))+',classification:'+coarse)
        raise Block('CAULDRON_'+coarse+'_'+label)
    try:result=json.loads(base64.b64decode(matches[0],validate=True))
    except Exception:raise Block('CAULDRON_RECEIPT_PARSE_FAILED_'+label)
    if result.get('phase')!=label:raise Block('CAULDRON_PHASE_MISMATCH_'+label)
    for key in result:
        if key not in ('phase','error','sender_hash','root_hash','source_hash','node','python','result','stage','file_hashes'):
            raise Block('UNEXPECTED_REMOTE_RECEIPT_FIELD_'+key)
    if result.get('error'):raise Block('REMOTE_'+str(result['error'])+'_'+label)
    print('RITSU_REMOTE='+label+' '+json.dumps(result,sort_keys=True),flush=True)
    receipts[label]=result
    return result

PFX=r'''$ErrorActionPreference='Stop';$ProgressPreference='SilentlyContinue';
function Emit($o){$x=($o|ConvertTo-Json -Compress -Depth 5);Write-Output ('RITSU_UX_RECEIPT='+[Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($x)))}
'''

# NO remote write during inventory; locks exact existing sources & approved voice.
WIN_READ=PFX+r'''$o=@{phase='WINDOWS_READ';source_hash='';sender_hash='';node='';python='';error=''};try{
$r='C:\Users\dclar\AppData\Local\RitsuControlBridge\release-016';
$s=Join-Path $r 'tools\ritsu-local-server\server.mjs';
$b=Join-Path $r 'tools\campaigns\ritsu_control_playwright_bridge.mjs';
$v='C:\Users\dclar\workspace\ritsu-faster-qwen3-tts\ritsu_say.py';
if(!(Test-Path $s) -or !(Test-Path $b)){throw 'EXPECTED_SERVER_SOURCE_MISSING'};
if(!(Test-Path $v)){throw 'EXPECTED_POCKET_SENDER_MISSING'};
$o.sender_hash=(Get-FileHash -Algorithm SHA256 $v).Hash.ToLower();
$o.source_hash=(Get-FileHash -Algorithm SHA256 $s).Hash.ToLower();
$o.node=(Get-Command node.exe -ErrorAction Stop).Source;
$o.python=(Get-Command python.exe -ErrorAction Stop).Source;
}catch{$m=$_.Exception.Message;if($m -cmatch '^[A-Z_]+$'){$o.error=$m}else{$o.error=$_.Exception.GetType().Name}};Emit $o'''

# Staged file transfer to private Windows folder. No source, journal or pairing mutation.
WIN_INIT=PFX+r'''$o=@{phase='WINDOWS_STAGE_INIT';result='';error=''};try{
$p=Join-Path $env:USERPROFILE '.ritsu-control\usability-packet-v1.3.1';
[IO.Directory]::CreateDirectory($p)|Out-Null;
$f=Join-Path $p 'packet.b64';
if(Test-Path $f){$o.result='REUSE_OR_CHECK_EXISTING'}
else{[IO.File]::WriteAllText($f,'');$o.result='CREATED'};
}catch{$o.error=$_.Exception.GetType().Name};Emit $o'''

def windows_transfer(packet_zip:bytes):
    stage('WINDOWS_PACKET_TRANSFER')
    encoded=base64.b64encode(packet_zip).decode()
    expected=hashlib.sha256(packet_zip).hexdigest()
    cauldron('WINDOWS_STAGE_INIT',WIN_INIT)
    # Ownership-safe, idempotent fixed offset chunks, independently read back.
    # Never truncate unknown remote staged data; abort if overlapping bytes disagree.
    for number,offset in enumerate(range(0,len(encoded),330)):
        chunk=encoded[offset:offset+330]
        script=PFX+fr'''$o=@{{phase='WINDOWS_PACKET_{number}';result='';error=''}};try{{
$f=Join-Path $env:USERPROFILE '.ritsu-control\usability-packet-v1.3.1\packet.b64';
$s=[IO.File]::ReadAllText($f);$c='{chunk}';$i={offset};
if($s.Length -eq $i){{[IO.File]::AppendAllText($f,$c);$o.result='APPENDED'}}
elseif($s.Length -ge ($i+$c.Length) -and $s.Substring($i,$c.Length) -ceq $c){{$o.result='REUSED'}}
else{{$o.error='CONFLICT'}}
}}catch{{$o.error='WRITE_FAILED'}};Emit $o'''
        cauldron('WINDOWS_PACKET_'+str(number),script,timeout=20)
    # Use only installed Windows Python, never new SSH/file channel.
    script=PFX+fr'''$o=@{{phase='WINDOWS_PACKET_VERIFY';result='';error=''}};try{{
$p=Join-Path $env:USERPROFILE '.ritsu-control\usability-packet-v1.3.1';
$f=Join-Path $p 'packet.b64';
$b=[Convert]::FromBase64String([IO.File]::ReadAllText($f));
$h=([Security.Cryptography.SHA256]::Create()).ComputeHash($b);
$d=-join ($h|ForEach-Object {{$_.ToString('x2')}});
if($d -ne '{expected}'){{throw 'TRANSFER_HASH_MISMATCH'}};
[IO.File]::WriteAllBytes((Join-Path $p 'packet.zip'),$b);$o.result='HASH_VERIFIED'
}}catch{{$m=$_.Exception.Message;if($m -cmatch '^[A-Z_]+$'){{$o.error=$m}}else{{$o.error=$_.Exception.GetType().Name}}}};Emit $o'''
    cauldron('WINDOWS_PACKET_VERIFY',script)
    receipts['windows_packet_sha256']=expected


def packet_for_windows():
    out=pathlib.Path(RUN)/'windows_backend_packet.zip'
    with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for name in ['patch_backend.py','ritsu_pocket_voice_hook.mjs','windows_apply.py']:
            z.write(PACKET/name,name)
    return out.read_bytes()


def verify_packet():
    stage('VERIFY_IMMUTABLE_PACKET')
    manifest=json.loads((PACKET/'manifest.json').read_text())
    if manifest.get('campaign')!=CAMPAIGN or manifest.get('version')!=VERSION:
        raise Block('PACKET_ID_OR_VERSION_MISMATCH')
    for file,expected in manifest.get('files',{}).items():
        f=PACKET/file
        if not f.is_file() or sha(f)!=expected:raise Block('PACKET_SHA_MISMATCH_'+file)
    receipts['packet_sources_verified']=len(manifest['files'])


def source_build_fingerprint(source):
    """Reconcile duplicated *copies* of accepted source by build input content.

    The accepted APK may have been copied into more than one successful
    build run. The APK SHA alone proves the artifact, not the provenance of
    each directory. Only canonicalize when all relevant build inputs agree.
    Files unrelated to compilation, such as README and receipts, are ignored.
    """
    paths=[]
    for relative in ('app/src','app/build.gradle','build.gradle','settings.gradle',
                     'gradle.properties','gradle','buildSrc'):
        item=source/relative
        if item.is_file():paths.append(item)
        elif item.is_dir():
            for path in item.rglob('*'):
                if path.is_file():paths.append(path)
    results={}
    for path in paths:
        if path.is_symlink():raise Block('ACCEPTED_SOURCE_UNSAFE_SYMLINK_'+path.name)
        rel=path.relative_to(source).as_posix()
        # Do not accidentally compare cache output as source.
        if any(part in {'build','.gradle','.git','.idea','.cxx'} for part in path.relative_to(source).parts):continue
        results[rel]=sha(path)
    digest=hashlib.sha256(json.dumps(results,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    return digest,results


def choose_accepted_source(candidates):
    """Use one source if unique, or proven equivalent replicas. Never guess."""
    if not candidates:raise Block('ACCEPTED_V0191_SOURCE_NOT_FOUND')
    grouped=[]
    for candidate in sorted(candidates,key=lambda p:p.as_posix()):
        fingerprint,files=source_build_fingerprint(candidate)
        grouped.append((candidate,fingerprint,files))
    receipts['accepted_source_candidate_count']=len(grouped)
    receipts['accepted_source_build_fingerprints']=[x[1][:20] for x in grouped]
    if len(grouped)>1:
        variants={fp for _,fp,_ in grouped}
        if len(variants)>1:
            # Print differences in the original invocation, not a separate
            # diagnostic tool or hidden receipt-only message.
            files=set().union(*(set(d) for _,_,d in grouped))
            different=[p for p in sorted(files) if len({d.get(p) for _,_,d in grouped})>1]
            log('RITSU_SOURCE_CANDIDATES='+str(len(grouped)))
            log('RITSU_SOURCE_CONFLICTS='+','.join(different[:12]))
            receipts['source_conflicting_files']=different[:40]
            raise Block('ACCEPTED_SOURCE_REPLICAS_DIFFER_IN_BUILD_INPUTS')
        log('RITSU_SOURCE_REPLICAS=PROVEN_BUILD_INPUT_EQUIVALENT_COUNT_'+str(len(grouped)))
        receipts['source_reconciliation']='EQUIVALENT_BUILD_INPUTS_NO_GUESSED_DIFFERENCES'
    else:
        receipts['source_reconciliation']='UNIQUE_ACCEPTED_SOURCE'
    chosen=grouped[0][0]
    log('RITSU_SOURCE_SELECTED='+str(chosen))
    log('RITSU_SOURCE_BUILD_FINGERPRINT='+grouped[0][1])
    receipts['source_build_fingerprint']=grouped[0][1]
    return chosen


def android_source():
    stage('SOURCE_AND_SIGNER_PREFLIGHT')
    accepted='9d825b5471e9b13cf9d3ba1bdd50d7c3cf647f7076f289bb2729791ba0f710bf'
    candidates=[]
    root=HOME/'.local/state/ritsu-newkey-build/runs'
    # Scans the accepted runs directory only; never searches arbitrary source.
    for run in sorted(root.glob('*')) if root.exists() else []:
        if not run.is_dir() or run.is_symlink():continue
        source=run/'project';signed=run/'ritsu-fresh-signed.apk'
        if not signed.is_file() or signed.is_symlink() or not source.is_dir() or source.is_symlink():continue
        if sha(signed)!=accepted:continue
        java=source/'app/src/main/java/com/homecenter/ritsucontrol'
        required=[source/'app/build.gradle',source/'settings.gradle',
            source/'app/src/main/AndroidManifest.xml',java/'MainActivity.java',
            java/'CampaignActivity.java',java/'CampaignResultReceiver.java',
            java/'RitsuWorkspace.java',java/'RitsuLocalSync.java']
        if not all(p.is_file() and not p.is_symlink() for p in required):continue
        gradle_text=(source/'app/build.gradle').read_text()
        if 'com.ritsucontrol.fresh' not in gradle_text or 'versionCode 21' not in gradle_text:continue
        if 'CampaignActivity' not in (source/'app/src/main/AndroidManifest.xml').read_text():continue
        candidates.append(source)
    src=choose_accepted_source(candidates)
    receipts['accepted_source']=str(src)
    receipts['accepted_apk_sha256']=accepted
    receipts['accepted_gradle_sha256']=sha(src/'app/build.gradle')
    sign=HOME/'.local/share/ritsu-fresh-signing'
    for name in ('release.p12','release-password.txt','cert-sha256.txt'):
        f=sign/name
        if not f.is_file() or f.is_symlink() or f.stat().st_size==0:
            raise Block('PERSISTENT_SIGNER_MISSING_'+name)
    cert=(sign/'cert-sha256.txt').read_text().strip().lower()
    if cert!=KNOWN_CERT:raise Block('PERSISTENT_SIGNER_FINGERPRINT_DIFFERS')
    receipts['signer_cert_sha256']=cert
    return src,sign

def staged_source(src):
    stage('PREPARE_ISOLATED_SOURCE')
    dest=RUN/'staged-android'
    def ignore(folder,names):
        return {n for n in names if n in {'build','.gradle','.git','node_modules','.idea','captures','.cxx'}}
    shutil.copytree(src,dest,symlinks=False,ignore=ignore)
    packet_home=dest/'tools/campaigns/ritsu-conversation-usability/v1.3.1'
    shutil.copytree(PACKET,packet_home,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    for file in (PACKET/'manifest.json',packet_home/'manifest.json'):
        if not file.is_file():raise Block('CAMPAIGN_REPO_PACKET_MANIFEST_MISSING')
    if sha(PACKET/'manifest.json')!=sha(packet_home/'manifest.json'):
        raise Block('CAMPAIGN_REPO_PACKET_READBACK_MISMATCH')
    receipts['source_packet_staged']=str(packet_home)
    receipts['git_commit']='NOT_AUTHORIZED_NOT_ATTEMPTED'
    # Parent source always remains unmodified.
    r=command([sys.executable,str(PACKET/'patch_android.py'),str(dest),str(PACKET)],timeout=15)
    log(r.strip())
    if 'ANDROID_PATCH=UI_TABS_SCROLL_DRAWER_AND_CATALOG_CLIENT_STAGED' not in r:
        raise Block('ANDROID_PATCH_COMPLETION_RECEIPT_MISSING')
    receipts['staged_source']=str(dest)
    receipts['original_main_untouched']=True
    return dest


def windows_inventory():
    stage('WINDOWS_EXISTING_BACKEND_AND_POCKET_PREFLIGHT')
    status=cauldron('WINDOWS_READ',WIN_READ,timeout=30)
    if status.get('sender_hash')!=VOICE_SHA:
        raise Block('POCKET_SENDER_HASH_CHANGED_NO_VOICE_SUBSTITUTION')
    return status


def build_sign(staged,sign):
    stage('BUILD_AND_VERIFY_SIGNED_APK')
    gradle=shutil.which('gradle')
    align=shutil.which('zipalign')
    signer=shutil.which('apksigner')
    aapt=shutil.which('aapt')
    if not all((gradle,align,signer,aapt)):raise Block('EXISTING_ANDROID_BUILD_TOOL_MISSING')
    sdk=pathlib.Path(os.environ.get('ANDROID_SDK_ROOT',os.environ.get('ANDROID_HOME',str(HOME/'android-sdk'))))
    if not (sdk/'platforms/android-35/android.jar').exists():raise Block('ANDROID_SDK35_MISSING')
    # Do not assume build.gradle version matching the historical branch; ensure
    # this release is strictly higher than the already accepted code21.
    gradle_file=staged/'app/build.gradle'
    text=gradle_file.read_text()
    vc=re.findall(r'\bversionCode\s+(\d+)',text)
    vn=re.findall(r'\bversionName\s+["\']([^"\']+)',text)
    if len(vc)!=1 or len(vn)!=1:raise Block('ANDROID_VERSION_FIELDS_AMBIGUOUS')
    current=int(vc[0]);nextcode=max(current+1,22)
    text=re.sub(r'\bversionCode\s+\d+',f'versionCode {nextcode}',text,count=1)
    text=re.sub(r'\bversionName\s+["\'][^"\']+["\']','versionName "0.19.2"',text,count=1)
    gradle_file.write_text(text)
    receipts['new_version_code']=nextcode
    env=os.environ.copy();env['ANDROID_HOME']=str(sdk);env['ANDROID_SDK_ROOT']=str(sdk)
    # Reuse proven AAPT2 wrapper. Never install an alternative.
    wrappers=[HOME/'.local/share/ritsu-campaigns/sticky-phone-v018/aapt2-official/aapt2-scoped',
      HOME/'.local/share/ritsu-campaigns/sticky-phone-v018/aapt2-official/aapt2']
    wrappers=[p for p in wrappers if p.exists() and os.access(p,os.X_OK)]
    if not wrappers:raise Block('PROVEN_NATIVE_AAPT2_WRAPPER_UNAVAILABLE')
    gd=RUN/'aapt2-verified';gd.mkdir()
    shim=gd/'aapt2'
    shim.write_text('#!'+(shutil.which('bash') or '/data/data/com.termux/files/usr/bin/bash')+'\nexec "'+str(wrappers[0])+'" "$@"\n')
    shim.chmod(0o700)
    log('GRADLE_START=AAPT2_EXISTING_WRAPPER')
    cmd=[gradle,'--no-daemon','--console=plain','-PritsuStickyInstall=true',
      '-Pandroid.aapt2FromMavenOverride='+str(shim),':app:testDebugUnitTest',':app:assembleRelease']
    out=command(cmd,timeout=420,cwd=staged,env=env)
    (RUN/'gradle-verified.log').write_text(out)
    classes=staged/'app/build/intermediates/javac/release/compileReleaseJavaWithJavac/classes/com/homecenter/ritsucontrol'
    for c in ['MainActivity.class','RitsuConversationDeck.class','RitsuConversationLinks.class','CampaignActivity.class']:
        if not (classes/c).is_file():raise Block('COMPILED_CLASS_MISSING_'+c)
    unsigned=staged/'app/build/outputs/apk/release/app-release-unsigned.apk'
    if not unsigned.is_file():raise Block('UNSIGNED_RELEASE_NOT_FOUND')
    aligned=RUN/'aligned.apk';signed=RUN/'signed.apk'
    command([align,'-f','-p','4',str(unsigned),str(aligned)],timeout=30)
    command([signer,'sign','--ks',str(sign/'release.p12'),'--ks-type','PKCS12',
      '--ks-key-alias','ritsu-fresh-release','--ks-pass','file:'+str(sign/'release-password.txt'),
      '--out',str(signed),str(aligned)],timeout=75)
    ver=command([signer,'verify','--verbose','--print-certs',str(signed)],timeout=20)
    m=re.search(r'Signer #1 certificate SHA-256 digest:\s*([0-9a-fA-F]{64})',ver)
    if not m or m.group(1).lower()!=KNOWN_CERT:raise Block('SIGNED_FINGERPRINT_MISMATCH')
    badge=command([aapt,'dump','badging',str(signed)],timeout=20)
    if "package: name='com.ritsucontrol.fresh'" not in badge:raise Block('WRONG_SIGNED_PACKAGE')
    if f"versionCode='{nextcode}'" not in badge:raise Block('SIGNED_VERSION_CODE_MISMATCH')
    receipts['signed_apk_sha256']=sha(signed)
    receipts['signed_apk_private_path']=str(signed)
    return signed


def publish_signed(signed):
    stage('PUBLISH_SIGNED_APK')
    dl=HOME/'storage/downloads'
    if not dl.is_dir():raise Block('ANDROID_SHARED_DOWNLOADS_NOT_ACCESSIBLE')
    expected=sha(signed)
    target=dl/f'Ritsu-Usability-v0.19.2-code{receipts["new_version_code"]}-{expected[:12]}.apk'
    if target.exists():
        if target.is_symlink() or sha(target)!=expected:raise Block('PUBLISHED_FILENAME_COLLISION')
    else:
        try:
            with target.open('xb') as out, signed.open('rb') as source:
                shutil.copyfileobj(source,out)
                out.flush();os.fsync(out.fileno())
        except Exception:
            with contextlib.suppress(FileNotFoundError):target.unlink()
            raise
    if sha(target)!=expected:raise Block('DOWNLOADS_SHA_READBACK_MISMATCH')
    receipts['published_apk']=str(target)
    log('PUBLIC_APK='+str(target))
    log('PUBLIC_APK_SHA256='+expected)
    if shutil.which('mediarefresh'):
        try:command(['mediarefresh',str(target)],timeout=18)
        except Block:log('MEDIA_REFRESH=UNAVAILABLE_OR_REQUEST_FAILED_NOT_BLOCKING_HASH')


def execute():
    global terminal_status,reason,LOCK
    print('RITSU_CAMPAIGN='+CAMPAIGN,flush=True)
    print('CAMPAIGN_VERSION='+VERSION,flush=True)
    print('ACTUAL_ENTRYPOINT='+str(pathlib.Path(sys.argv[0]).resolve()),flush=True)
    STATE.mkdir(parents=True,exist_ok=True)
    lock_path=STATE/'campaign.lock';LOCK=lock_path.open('a+')
    try:fcntl.flock(LOCK.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BlockingIOError:raise Block('ALREADY_RUNNING_NO_DUPLICATE_CAMPAIGN')
    RUN.mkdir(parents=True,exist_ok=False)
    threading.Thread(target=heartbeat,daemon=True).start()
    if len(sys.argv)>1 and sys.argv[1]=='--selftest':
        stage('HOST_SELFTEST_ONLY_NO_DEVICE_ACTIONS')
        verify_packet()
        result=command([sys.executable,'-m','unittest','discover','-s','tests','-v'],timeout=60,cwd=PACKET)
        log(result)
        terminal_status='HOST_TESTS_ONLY'
        reason='NO_DEVICE_EXECUTION_PERFORMED'
        return

    verify_packet()
    stage('RUN_BUNDLED_REGRESSION_TESTS')
    test=command([sys.executable,'-m','unittest','discover','-s','tests','-q'],timeout=45,cwd=PACKET)
    if 'FAILED' in test or 'ERROR' in test:raise Block('BUNDLED_SELFTEST_FAILED')
    receipts['bundled_regression_tests']='PASS'
    src,sign=android_source()
    # Source-aware UI work is isolated and testable, no live apk mutation yet.
    staged=staged_source(src)
    signed=build_sign(staged,sign)
    # No Windows writes until an actual, signed, checked APK exists locally.
    windows_inventory()
    stage('VERIFY_BACKEND_PATCH_PACKET')
    # Content-addressed packet transfer is idempotent. No remote source write yet.
    windows_transfer(packet_for_windows())
    # Only short, fully pinned PowerShell wrappers are sent over `cauldron`.
    extract=PFX+r'''$o=@{phase='WINDOWS_BACKEND_EXTRACT';result='';error=''};try{
$p=Join-Path $env:USERPROFILE '.ritsu-control\usability-packet-v1.3.1';
$u=Join-Path $p 'packet';if(!(Test-Path $u)){Expand-Archive -Path (Join-Path $p 'packet.zip') -DestinationPath $u -ErrorAction Stop};
if(!(Test-Path (Join-Path $u 'windows_apply.py'))){throw 'WINDOWS_RUNNER_MISSING'};
$o.result='RUNNER_PRESENT';
}catch{$m=$_.Exception.Message;if($m -cmatch '^[A-Z_]+$'){$o.error=$m}else{$o.error=$_.Exception.GetType().Name}};Emit $o'''
    cauldron('WINDOWS_BACKEND_EXTRACT',extract,timeout=35)
    def wrapper(mode):
        return r'''$p=Join-Path $env:USERPROFILE '.ritsu-control\usability-packet-v1.3.1\packet\windows_apply.py';
& python.exe $p '''+mode
    cauldron('WINDOWS_BACKEND_STAGE',wrapper('stage'),timeout=55)
    stage('WINDOWS_DEPLOY_VERIFIED_PATCH')
    try:cauldron('WINDOWS_BACKEND_APPLY',wrapper('apply'),timeout=95)
    except Block as error:
        log('BACKEND_APPLY_FAILURE='+str(error))
        # Only the single campaign applies and attempts its own rollback.
        try:cauldron('WINDOWS_BACKEND_ROLLBACK',wrapper('rollback'),timeout=70)
        except Block as rollback_error:receipts['rollback_incomplete']=str(rollback_error)
        raise Block('BACKEND_DEPLOY_NOT_ACCEPTED_AND_ROLLBACK_REQUESTED')
    publish_signed(signed)
    terminal_status='APK_DELIVERED_INSTALLATION_NOT_ATTEMPTED'
    reason='OWNER_INSTALL_AND_PHYSICAL_UI_VOICE_CHAT_ACCEPTANCE_REQUIRED'
    # Actual UI tests, audible speech, and conversation canary MUST follow owner
    # install; the campaign never marks those PASS from a build or server ACK.
    return

if __name__=='__main__':
    try:execute()
    except Block as exc:reason=str(exc)
    except Exception as exc:reason='UNEXPECTED_'+type(exc).__name__
    finally:stop.set();receipt()
    sys.exit(0 if terminal_status in ('APK_DELIVERED_INSTALLATION_NOT_ATTEMPTED','HOST_TESTS_ONLY') else 1)
