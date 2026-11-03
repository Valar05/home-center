#!/usr/bin/env python3
"""Apply v1.3.5 fixes ONLY to a private, previously versioned Android source copy."""
from pathlib import Path
import sys, hashlib

def one(s,a,b,label):
    count=s.count(a)
    if count!=1: raise RuntimeError('UNSUPPORTED_ANDROID_ANCHOR_'+label+'_'+str(count))
    return s.replace(a,b,1)

def patch(root:Path):
    base=root/'app/src/main/java/com/homecenter/ritsucontrol'
    main=base/'MainActivity.java'; links=base/'RitsuConversationLinks.java'; sync=base/'RitsuLocalSync.java'; recovery=base/'RitsuTurnRecovery.java'
    if not all(x.is_file() and not x.is_symlink() for x in (main,links,sync,recovery)):
        raise RuntimeError('CURRENT_ANDROID_SOURCE_OR_LINKS_MISSING')
    m=main.read_text();l=links.read_text();s=sync.read_text();r=recovery.read_text()
    if 'RITSU_CONVERSATION_USABILITY_V1_3_1' not in m or 'RitsuTurnRecovery' not in s:
        raise RuntimeError('REQUIRES_RECOVERABLE_CODE24_STYLE_UI')
    if 'RITSU_V135_USER_SEND_FOLLOW' in m:raise RuntimeError('V135_ALREADY_APPLIED')
    m=one(m,'    private String drawnConversation=null;','    private String drawnConversation=null;\n    // RITSU_V135_USER_SEND_FOLLOW: only explicit Send forces transcript follow.\n    private boolean followAfterExplicitSend=false;','scroll field')
    m=one(m,'        final boolean follow=same && previousAtBottom;', '''        final boolean submitted=followAfterExplicitSend;
        followAfterExplicitSend=false;
        final boolean follow=submitted || (same && previousAtBottom);''','follow decision')
    m=one(m,'                feedScroll.fullScroll(View.FOCUS_DOWN);return;', '''                if(submitted){
                    feedScroll.scrollTo(0,transcriptRows.getHeight());
                    feedScroll.postDelayed(()->{
                        if(newTab.equals(workspace.active().id))
                            feedScroll.scrollTo(0,transcriptRows.getHeight());
                    },160);
                }else feedScroll.fullScroll(View.FOCUS_DOWN);
                return;''','post layout follow')
    m=one(m,'            composer.setText("");\n            if(conversationDeck!=null)conversationDeck.setDraft(active.id,"");\n            renderFeed();', '''            composer.setText("");
            if(conversationDeck!=null)conversationDeck.setDraft(active.id,"");
            followAfterExplicitSend=true;
            renderFeed();''','send intent')
    start='''        if(value==null||!value.matches("https://chatgpt\\\\.com/c/[A-Za-z0-9-]{8,120}/?"))return null;'''
    if start not in l:
        # avoid relying on Python/Java double-escaping; anchor by line
        lines=l.splitlines(keepends=True)
        candidates=[x for x in lines if 'value.matches(' in x and 'chatgpt' in x and '/c/' in x]
        if len(candidates)!=1:raise RuntimeError('CANONICAL_URL_ANCHOR_COUNT_'+str(len(candidates)))
        start=candidates[0]
    l=one(l,start,'''        // RITSU_V135_CANONICAL_LOCAL_URL: accept the *exact* browser URL as a candidate.
        // The authenticated laptop must still prove it is a writable, same-account chat.
        if(value==null||!value.matches("https://chatgpt\\\\.com/c/(?:[A-Za-z0-9-]{8,120}|local-chatgpt%3[Aa][0-9A-Fa-f-]{36})/?"))return null;
''','local URL')
    l=one(l,'            int code=c.getResponseCode();if(code!=200)throw new IllegalStateException("CATALOG_HTTP_"+code);', '''            int code=c.getResponseCode();
            if(code!=200){
                String detail="";
                java.io.InputStream trouble=c.getErrorStream();
                if(trouble!=null)try(java.io.InputStream in=trouble){
                    byte[] bytes=new byte[1000];int n=in.read(bytes);
                    if(n>0){
                        String body=new String(bytes,0,n,java.nio.charset.StandardCharsets.UTF_8);
                        detail=new JSONObject(body).optString("error","");
                    }
                }
                detail=detail.replaceAll("[^A-Za-z0-9_.:-]","_");
                if(detail.length()>72)detail=detail.substring(0,72);
                throw new IllegalStateException("CATALOG_HTTP_"+code+(detail.isEmpty()?"":"_"+detail));
            }''','specific server rejection')
    l=one(l,'        return e.getClass().getSimpleName();','''        String message=e.getMessage();
        if(message!=null){
            if(message.startsWith("CATALOG_HTTP_"))return message;
            if(message.contains("PAIRING_REQUIRED"))return "PAIRING_REQUIRED";
            if(message.contains("Unverified catalog"))return "CATALOG_NOT_VERIFIED";
        }
        return e.getClass().getSimpleName();''','useful discovery error')
    m=one(m,'TextView state=label(entry.state,11,false);',        'TextView state=label("LOCAL_UNCERTAIN".equals(entry.state)?"Delivery not verified · original preserved":entry.state,11,false);',
        'uncertain status text')
        # Previously installed synchronous turn audit blocked the outbound sender for up
    # to 2 x 48 seconds. Move it onto the already-provisioned audit scheduler.
    old='''        auditTimer.scheduleWithFixedDelay(this::requestNow,20,45,
            java.util.concurrent.TimeUnit.SECONDS);'''
    new='''        auditTimer.scheduleWithFixedDelay(this::runReadOnlyAudit,20,90,
            java.util.concurrent.TimeUnit.SECONDS);'''
    s=one(s,old,new,'nonblocking audit scheduler')
    a=s.index('        long now=android.os.SystemClock.elapsedRealtime();', s.index('    private void sendPending() {'))
    b=s.index('        RitsuPairing.Pair p;',a)
    block=s[a:b]
    if 'RitsuTurnRecovery.reconcile(app,ledger,paired)' not in block:
        raise RuntimeError('EXPECTED_ORIGINAL_RECONCILIATION_BLOCK_NOT_FOUND')
    s=s[:a]+s[b:]
    # Audit on independent executor; errors must not hold new user requests hostage.
    s=one(s,'    private void sendPending() {', '''    private void runReadOnlyAudit(){
        if(stopped)return;
        try{
            RitsuPairing.Pair paired=RitsuPairing.load(app);
            if(paired==null)return;
            RitsuTurnRecovery.Result audit=RitsuTurnRecovery.reconcile(app,ledger,paired);
            if(audit.recovered>0||audit.notAccepted>0||audit.submitted>0){
                status=audit.message();updated();
            }
        }catch(Exception error){
            status="Turn audit: "+error.getClass().getSimpleName()+"; no resend";
            updated();
        }
    }
    private void sendPending() {''','background read only audit')
    from hashlib import sha256
    expected='78d115ed5df4612c912df38297d3eb1d12780a5a7956fddbb3abaa71bf6c074e'
    if sha256(r.encode()).hexdigest()!=expected:raise RuntimeError('RECOVERY_SOURCE_NOT_PREVIOUSLY_ACCEPTED')
    corrected=(Path(__file__).resolve().parent/'RitsuTurnRecovery.java').read_text()
    if 'definitelyNotAccepted' not in corrected or 'String tryBrowserRecovery' not in corrected:
        raise RuntimeError('RECOVERY_FIX_SOURCE_NOT_COMPATIBLE')
    # All source anchors above must succeed before touching files.
    for f,body in ((main,m),(links,l),(sync,s),(recovery,corrected)):
        f.write_text(body)
        print('PATCHED_ANDROID='+f.name+' SHA256='+hashlib.sha256(body.encode()).hexdigest())
    print('RITSU_V135_ANDROID_PATCH=SCROLL_LOCAL_URL_ERRORS_NONBLOCKING_AUDIT')
if __name__=='__main__':
    patch(Path(sys.argv[1]).resolve())
