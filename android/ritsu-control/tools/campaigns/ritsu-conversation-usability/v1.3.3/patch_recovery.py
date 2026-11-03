#!/usr/bin/env python3
"""Source-anchored addendum to verified code22 Android project, isolated-copy only."""
from pathlib import Path
import sys,hashlib

def one(s,a,b,name):
    n=s.count(a)
    if n!=1:raise RuntimeError(name+' anchor '+str(n))
    return s.replace(a,b,1)

def patch(project,packet):
    java=project/'app/src/main/java/com/homecenter/ritsucontrol'
    sync=java/'RitsuLocalSync.java';main=java/'MainActivity.java'
    recovery=java/'RitsuTurnRecovery.java'
    if not sync.is_file() or not main.is_file() or recovery.exists():raise RuntimeError('source missing or recovery already patched')
    s=sync.read_text();m=main.read_text()
    if 'RITSU_CONVERSATION_USABILITY_V1_3_1' not in m:raise RuntimeError('requires accepted v1.3.1 UI source')
    if 'RitsuTurnRecovery' in s or 'LOCAL_NOT_ACCEPTED' in m:raise RuntimeError('duplicate patch')
    s=one(s,'    private volatile boolean stopped;', '''    // Recovery is read-only and runs on the existing serialized outbox executor.
    private volatile boolean stopped;
    private long lastAuditAt=0;
    private final java.util.concurrent.ScheduledExecutorService auditTimer =
        java.util.concurrent.Executors.newSingleThreadScheduledExecutor(r -> {
            Thread t=new Thread(r,"RitsuTurnAuditTick");t.setDaemon(true);return t;
        });''','audit members')
    s=one(s,'    void start(){input.execute(this::receiveLoop);requestNow();}', '''    void start(){
        input.execute(this::receiveLoop);requestNow();
        auditTimer.scheduleWithFixedDelay(this::requestNow,20,45,
            java.util.concurrent.TimeUnit.SECONDS);
    }''','audit schedule')
    s=one(s,'    private void sendPending() {\n        if(stopped)return;', '''    private void sendPending() {
        if(stopped)return;
        long now=android.os.SystemClock.elapsedRealtime();
        if(now-lastAuditAt>30000){
            lastAuditAt=now;
            try {
                RitsuPairing.Pair paired=RitsuPairing.load(app);
                if(paired!=null){
                    RitsuTurnRecovery.Result audit=RitsuTurnRecovery.reconcile(app,ledger,paired);
                    if(audit.recovered>0||audit.notAccepted>0||audit.submitted>0){
                        status=audit.message();updated();
                    }
                }
            } catch(Exception error){
                status="Turn audit unavailable: "+error.getClass().getSimpleName()+" · no retry";
                updated();
            }
        }''','audit before send')
    s=one(s,'        stopped=true;\n        HttpURLConnection c=activeStream;', '''        stopped=true;
        auditTimer.shutdownNow();
        HttpURLConnection c=activeStream;''','close audit timer')
    m=one(m,'            content.setTextIsSelectable(true);bubble.addView(content);', '''            content.setTextIsSelectable(true);bubble.addView(content);
            if("You".equals(entry.who)&&"LOCAL_NOT_ACCEPTED".equals(entry.state)){
                TextView notice=label("No linked-server receipt. Original preserved; not resent.",12,false);
                bubble.addView(notice);
            }''','visible no-duplicate notice')
    src=(packet/'RitsuTurnRecovery.java').read_text()
    if 'setRequestMethod("POST")' in src or 'ledger.updateState(owner.id,"LOCAL_QUEUED")' in src:
        raise RuntimeError('recovery class attempts remote submission')
    # All anchor checks have passed. Only isolated staged files change.
    sync.write_text(s);main.write_text(m);recovery.write_text(src)
    for f in [sync,main,recovery]:
        print('RECOVERY_SOURCE='+f.name+' SHA256='+hashlib.sha256(f.read_bytes()).hexdigest())
    print('ANDROID_RECOVERY_PATCH=READ_ONLY_ID_RECONCILIATION_AND_EXPLICIT_RETRY')

if __name__=='__main__':
    try:patch(Path(sys.argv[1]).resolve(),Path(sys.argv[2]).resolve())
    except Exception as e:
        print('ANDROID_RECOVERY_PATCH=BLOCKED '+str(e)[:260]);raise SystemExit(1)
