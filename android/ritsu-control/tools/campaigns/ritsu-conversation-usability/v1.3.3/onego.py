#!/usr/bin/env python3
"""Ritsu same-campaign v1.3.3: fix stuck local outbox without any auto-resend.
One invocation; no Home Center, Computer Hands, GitHub writes, Windows
mutation, journal rewrite, pairing reset, APK auto-install, or cloud API.
"""
from __future__ import annotations
import contextlib,datetime,fcntl,hashlib,json,os,pathlib,re,shutil,signal,subprocess,sys,threading,time,uuid
VERSION='1.3.3'
CAMPAIGN='ritsu-conversation-usability'
HOME=pathlib.Path.home()
STATE=HOME/'.local/state/ritsu-conversation-usability'
NOW=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
RUN=STATE/'runs'/(NOW+'-'+str(os.getpid()))
PACKET=pathlib.Path(__file__).resolve().parent
ACCEPTED_CODE22_SHA='362358e3a9bc2c35caa4f8527506b22d1cbf1e3ff95d3f5134db622199a56731'
KNOWN_CERT='c9ff64cb5558204c19300b6945dbcf88cdd32a97e43b21acbbdb8a5b08b79473'
phase='INIT';status='BLOCKED';reason='NOT_STARTED';receipts={};begin=time.monotonic();stop=threading.Event()
class Block(Exception):pass

def say(msg):print(str(msg),flush=True)
def sha(file):
    h=hashlib.sha256()
    with open(file,'rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()
def stage(n):
    global phase
    phase=n;say('RITSU_PROGRESS='+n)
def pulse():
    while not stop.wait(12):say('RITSU_HEARTBEAT=phase:'+phase+',elapsed:'+str(int(time.monotonic()-begin)))
def command(args,timeout=60,cwd=None,env=None):
    p=subprocess.Popen(args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL,
                      cwd=cwd,env=env,start_new_session=True)
    try: data=p.communicate(timeout=timeout)[0]
    except subprocess.TimeoutExpired:
        with contextlib.suppress(ProcessLookupError):os.killpg(p.pid,signal.SIGTERM)
        try:data=p.communicate(timeout=3)[0]
        except subprocess.TimeoutExpired:
            with contextlib.suppress(ProcessLookupError):os.killpg(p.pid,signal.SIGKILL)
            data=p.communicate()[0]
        raise Block('COMMAND_TIMEOUT_'+pathlib.Path(args[0]).name)
    s=data.decode('utf8','replace')
    if p.returncode!=0:
        (RUN/'last-command-redacted.log').write_text(re.sub(r'(?i)(--ks-pass|password|token)\S*','[REDACTED]',s[-10000:]))
        say('FAILED_COMMAND='+pathlib.Path(args[0]).name+',exit:'+str(p.returncode)+',tail:'+re.sub('[\r\n]+',' ',s[-450:]))
        raise Block('COMMAND_FAILED_'+pathlib.Path(args[0]).name+'_'+str(p.returncode))
    return s

def verify_packet():
    stage('VERIFY_IMMUTABLE_PACKET')
    m=json.loads((PACKET/'manifest.json').read_text())
    if m.get('campaign')!=CAMPAIGN or m.get('version')!=VERSION:raise Block('PACKET_ID_OR_VERSION_MISMATCH')
    for name,digest in m['files'].items():
        p=PACKET/name
        if not p.is_file() or p.is_symlink() or sha(p)!=digest:raise Block('PACKET_SHA_MISMATCH_'+name)
    if 'never' not in (PACKET/'ETIQUETTE_ENFORCEMENT.md').read_text().lower() or 'downloads' not in (PACKET/'ETIQUETTE_ENFORCEMENT.md').read_text().lower():
        raise Block('CAMPAIGN_ETIQUETTE_CONTRACT_UNAVAILABLE')
    say('CAMPAIGN_ETIQUETTE=REVIEWED_AND_PACKAGED')
    receipts['verified_packet_sources']=len(m['files'])

def fingerprint(source):
    files={}
    for name in ('app/src','app/build.gradle','build.gradle','settings.gradle','gradle.properties','gradle','buildSrc'):
        p=source/name
        items=[p] if p.is_file() else sorted(p.rglob('*')) if p.is_dir() else []
        for f in items:
            if not f.is_file():continue
            rel=f.relative_to(source)
            if any(part in ('build','.gradle','.git','.idea','.cxx') for part in rel.parts):continue
            if f.is_symlink():raise Block('SYMLINK_IN_ACCEPTED_SOURCE_'+str(rel))
            files[str(rel)]=sha(f)
    return hashlib.sha256(json.dumps(files,sort_keys=True).encode()).hexdigest(),files

def choose_accepted_source(candidates):
    if not candidates:raise Block('ACCEPTED_CODE22_BUILD_SOURCE_NOT_FOUND')
    rows=[(p,*fingerprint(p)) for p in sorted(candidates)]
    receipts['accepted_code22_candidates']=len(rows)
    if len({row[1] for row in rows})!=1:
        paths=set().union(*(set(row[2]) for row in rows))
        diffs=[k for k in sorted(paths) if len({row[2].get(k) for row in rows})>1]
        say('RITSU_SOURCE_CONFLICTS='+','.join(diffs[:18]))
        raise Block('CODE22_SOURCE_COPIES_NOT_EQUIVALENT')
    chosen=rows[0][0]
    say('RITSU_SOURCE_REPLICAS='+str(len(rows)))
    say('RITSU_SOURCE_SELECTED='+str(chosen))
    say('RITSU_BUILD_INPUT_FINGERPRINT='+rows[0][1])
    return chosen

def locate():
    stage('RECOVER_VERIFIED_CODE22_SOURCE_AND_SIGNER')
    candidates=[];runs=STATE/'runs'
    for run in sorted(runs.iterdir()) if runs.is_dir() else []:
        if not run.is_dir() or run.is_symlink():continue
        signed=run/'signed.apk';project=run/'staged-android'
        if not signed.is_file() or not project.is_dir() or signed.is_symlink() or project.is_symlink():continue
        if sha(signed)!=ACCEPTED_CODE22_SHA:continue
        gradle=project/'app/build.gradle'
        main=project/'app/src/main/java/com/homecenter/ritsucontrol/MainActivity.java'
        sync=project/'app/src/main/java/com/homecenter/ritsucontrol/RitsuLocalSync.java'
        if not all(p.is_file() and not p.is_symlink() for p in (gradle,main,sync)):continue
        g=gradle.read_text();m=main.read_text()
        if not re.search(r'\bversionCode\s+22\b',g) or 'com.ritsucontrol.fresh' not in g:continue
        if 'RITSU_CONVERSATION_USABILITY_V1_3_1' not in m:continue
        candidates.append(project)
    src=choose_accepted_source(candidates)
    sign=HOME/'.local/share/ritsu-fresh-signing'
    for n in ('release.p12','release-password.txt','cert-sha256.txt'):
        f=sign/n
        if not f.is_file() or f.is_symlink() or f.stat().st_size==0:raise Block('ACCEPTED_SIGNER_MISSING_'+n)
    if (sign/'cert-sha256.txt').read_text().strip().lower()!=KNOWN_CERT:
        raise Block('ACCEPTED_SIGNER_CERT_CHANGED')
    receipts['accepted_code22_sha256']=ACCEPTED_CODE22_SHA
    receipts['accepted_signer_sha256']=KNOWN_CERT
    return src,sign

def prepare(src):
    stage('STAGE_ISOLATED_RECOVERY_SOURCE')
    target=RUN/'staged-android'
    def ignore(base,names):return set(names)&{'build','.gradle','.git','node_modules','.idea','.cxx'}
    shutil.copytree(src,target,ignore=ignore,symlinks=False)
    dest=target/'tools/campaigns/ritsu-conversation-usability/v1.3.3'
    shutil.copytree(PACKET,dest,ignore=shutil.ignore_patterns('*.pyc','__pycache__'))
    if sha(PACKET/'manifest.json')!=sha(dest/'manifest.json'):
        raise Block('CAMPAIGN_SOURCE_PACKET_READBACK_FAILED')
    out=command([sys.executable,str(PACKET/'patch_recovery.py'),str(target),str(PACKET)],timeout=20)
    say(out.strip())
    if 'ANDROID_RECOVERY_PATCH=READ_ONLY_ID_RECONCILIATION_AND_EXPLICIT_RETRY' not in out:
        raise Block('RECOVERY_PATCH_COMPLETION_MISSING')
    receipts['isolated_source']=str(target)
    receipts['live_source_changed']=False
    return target

def build_sign(staged,sign):
    stage('BUILD_CODE24_WITH_ACCEPTED_SIGNER')
    gradle=shutil.which('gradle');align=shutil.which('zipalign')
    signer=shutil.which('apksigner');aapt=shutil.which('aapt')
    if not all((gradle,align,signer,aapt)):raise Block('PREVIOUSLY_PROVEN_BUILD_TOOL_MISSING')
    sdk=pathlib.Path(os.environ.get('ANDROID_SDK_ROOT',os.environ.get('ANDROID_HOME',str(HOME/'android-sdk'))))
    if not (sdk/'platforms/android-35/android.jar').exists():raise Block('ANDROID_SDK35_MISSING')
    build=staged/'app/build.gradle';content=build.read_text()
    if len(re.findall(r'\bversionCode\s+22\b',content))!=1:raise Block('CODE22_VERSION_ANCHOR_CHANGED')
    if len(re.findall(r'\bversionName\s+["\'][^"\']+["\']',content))!=1:raise Block('VERSION_NAME_ANCHOR_CHANGED')
    content=re.sub(r'\bversionCode\s+22\b','versionCode 24',content,count=1)
    content=re.sub(r'\bversionName\s+["\'][^"\']+["\']','versionName "0.19.4"',content,count=1)
    build.write_text(content)
    env=os.environ.copy();env['ANDROID_HOME']=str(sdk);env['ANDROID_SDK_ROOT']=str(sdk)
    options=[HOME/'.local/share/ritsu-campaigns/sticky-phone-v018/aapt2-official/aapt2-scoped',
             HOME/'.local/share/ritsu-campaigns/sticky-phone-v018/aapt2-official/aapt2']
    installed=[p for p in options if p.is_file() and os.access(p,os.X_OK)]
    if not installed:raise Block('PROVEN_NATIVE_AAPT2_WRAPPER_UNAVAILABLE')
    wrapper=RUN/'aapt2';wrapper.write_text('#!'+(shutil.which('bash') or '/data/data/com.termux/files/usr/bin/bash')+'\nexec "'+str(installed[0])+'" "$@"\n');wrapper.chmod(0o700)
    cmd=[gradle,'--no-daemon','--console=plain','-PritsuStickyInstall=true',
         '-Pandroid.aapt2FromMavenOverride='+str(wrapper),':app:testDebugUnitTest',':app:assembleRelease']
    out=command(cmd,timeout=480,cwd=staged,env=env)
    (RUN/'gradle-build.log').write_text(out)
    classes=staged/'app/build/intermediates/javac/release/compileReleaseJavaWithJavac/classes/com/homecenter/ritsucontrol'
    for c in ('MainActivity.class','RitsuLocalSync.class','RitsuTurnRecovery.class','RitsuConversationDeck.class'):
        if not (classes/c).is_file():raise Block('NEW_CLASS_MISSING_'+c)
    unsigned=staged/'app/build/outputs/apk/release/app-release-unsigned.apk'
    if not unsigned.is_file():raise Block('UNSIGNED_RELEASE_MISSING')
    aligned=RUN/'aligned.apk';signed=RUN/'signed.apk'
    command([align,'-f','-p','4',str(unsigned),str(aligned)],timeout=30)
    command([signer,'sign','--ks',str(sign/'release.p12'),'--ks-type','PKCS12',
          '--ks-key-alias','ritsu-fresh-release','--ks-pass','file:'+str(sign/'release-password.txt'),
          '--out',str(signed),str(aligned)],timeout=75)
    cert=command([signer,'verify','--verbose','--print-certs',str(signed)],timeout=20)
    m=re.search(r'Signer #1 certificate SHA-256 digest:\s*([0-9a-fA-F]{64})',cert)
    if not m or m.group(1).lower()!=KNOWN_CERT:raise Block('SIGNED_CERT_FINGERPRINT_MISMATCH')
    badge=command([aapt,'dump','badging',str(signed)],timeout=20)
    if "package: name='com.ritsucontrol.fresh'" not in badge or "versionCode='24'" not in badge:
        raise Block('SIGNED_PACKAGE_OR_VERSION_MISMATCH')
    receipts['signed_apk_sha256']=sha(signed)
    receipts['signed_apk_private']=str(signed)
    return signed

def publish(signed):
    stage('COPY_ONLY_TO_ANDROID_DOWNLOADS')
    dl=HOME/'storage/downloads'
    if not dl.is_dir():raise Block('TERMUX_SHARED_DOWNLOADS_MISSING')
    expected=sha(signed);name=f'Ritsu-Conversation-Recovery-v0.19.4-code24-{expected[:12]}.apk'
    target=dl/name
    if target.exists():
        if target.is_symlink() or sha(target)!=expected:raise Block('DOWNLOADS_EXISTING_FILENAME_COLLISION')
    else:
        temp=dl/('.'+name+'.'+uuid.uuid4().hex+'.tmp')
        try:
            with temp.open('xb') as out,signed.open('rb') as source:
                shutil.copyfileobj(source,out);out.flush();os.fsync(out.fileno())
            if sha(temp)!=expected:raise Block('DOWNLOADS_TEMP_SHA_MISMATCH')
            if target.exists():raise Block('DOWNLOADS_COLLISION_BEFORE_RENAME')
            os.rename(temp,target)
        finally:
            with contextlib.suppress(FileNotFoundError):temp.unlink()
    if target.stat().st_size!=signed.stat().st_size or sha(target)!=expected:
        raise Block('DOWNLOADS_APK_SHA_READBACK_FAILED')
    receipts['downloads_apk']=str(target);receipts['downloads_apk_sha256']=expected
    say('SOURCE_APK='+str(signed));say('DOWNLOADS_APK='+str(target))
    say('SOURCE_SHA256='+expected);say('DOWNLOADS_SHA256='+expected)
    say('COPY_VERIFIED=PASS')
    # Historical campaign behavior: refresh the EXACT final file, not 5000 others.
    scan=shutil.which('termux-media-scan')
    if not scan:
        say('MEDIA_REFRESH=UNAVAILABLE_TERMUX_MEDIA_SCAN_MISSING')
        receipts['media_refresh']='UNAVAILABLE'
    else:
        try:
            report=command([scan,str(target)],timeout=24)
            receipts['media_refresh']='REQUESTED'
            say('MEDIA_REFRESH=REQUESTED')
            say('MEDIA_REFRESH_PATH='+str(target))
            say('MEDIA_REFRESH_REPORT='+re.sub('[\r\n]+',' ',report.strip()[-180:]))
        except Block as failure:
            receipts['media_refresh']='FAILED'
            say('MEDIA_REFRESH=FAILED_REASON_'+str(failure)[:120])
    say('INSTALLATION=NOT_ATTEMPTED')

def print_receipt():
    RUN.mkdir(parents=True,exist_ok=True)
    content={'campaign':CAMPAIGN,'version':VERSION,'phase':phase,'status':status,'reason':reason,
             'evidence':receipts,'existing_user_turns_resent':False,
             'journal_mutated':False,'browser_mutated':False,'pairing_mutated':False,
             'apks_installed':False,'acceptance':'INSTALL_AND_PHYSICAL_FIELD_TEST_PENDING'}
    path=RUN/'final-receipt.json';path.write_text(json.dumps(content,indent=2,sort_keys=True)+'\n')
    say('RITSU_CONVERSATION_USABILITY_FINAL')
    for k,v in [('CAMPAIGN_VERSION',VERSION),('CAMPAIGN_STATUS',status),('LAST_STAGE',phase),
                ('REASON',reason),('PROMPT_RESUBMITTED','NO'),('JOURNAL_MODIFIED','NO'),
                ('PAIRING_MODIFIED','NO'),('INSTALLATION','NOT_ATTEMPTED'),('RECEIPT',path)]:say(str(k)+'='+str(v))
    for k,v in receipts.items():
        if isinstance(v,(str,int,float)):say('RESULT_'+k.upper()+'='+str(v)[:240])

def execute():
    global status,reason
    say('RITSU_CAMPAIGN='+CAMPAIGN);say('CAMPAIGN_VERSION='+VERSION)
    say('ACTUAL_ENTRYPOINT='+str(pathlib.Path(__file__).resolve()))
    STATE.mkdir(parents=True,exist_ok=True)
    with (STATE/'campaign.lock').open('a+') as lock:
        try:fcntl.flock(lock.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:raise Block('ANOTHER_RITSU_CAMPAIGN_IS_RUNNING')
        RUN.mkdir(parents=True,exist_ok=False)
        threading.Thread(target=pulse,daemon=True).start()
        verify_packet()
        stage('RUN_REGRESSION_TESTS')
        out=command([sys.executable,'-m','unittest','discover','-s','tests','-v'],timeout=70,cwd=PACKET)
        if 'FAILED' in out or 'ERROR' in out:raise Block('BUNDLED_REGRESSIONS_FAILED')
        receipts['regression_tests']='PASS'
        if len(sys.argv)>1 and sys.argv[1]=='--selftest':
            status='HOST_TESTS_ONLY';reason='NO_DEVICE_OR_WINDOWS_ACTIONS';return
        src,sign=locate()
        staged=prepare(src)
        signed=build_sign(staged,sign)
        stage('BACKEND_READ_ONLY_BROWSER_TO_JOURNAL_RECONCILIATION')
        import cauldron_courier
        try:
            receipts['windows_backend']=cauldron_courier.apply(PACKET,say)
        except cauldron_courier.RemoteBlocked as error:
            raise Block('WINDOWS_BACKEND_'+str(error)[:240])
        publish(signed)
        status='APK_DELIVERED_INSTALLATION_NOT_ATTEMPTED'
        reason='OWNER_INSTALL_CODE24_FROM_DOWNLOADS_AND_VERIFY_ORIGINAL_TURN_STATUS'

if __name__=='__main__':
    try:execute()
    except Block as e:reason=str(e)
    except Exception as e:reason='UNEXPECTED_'+type(e).__name__+'_'+str(e)[:120]
    finally:stop.set();print_receipt()
    sys.exit(0 if status in ('HOST_TESTS_ONLY','APK_DELIVERED_INSTALLATION_NOT_ATTEMPTED') else 1)
