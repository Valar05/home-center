#!/data/data/com.termux/files/usr/bin/bash
# Ritsu conversation usability integration, exact-source guarded, no premature APK.
set -u
NAME=RITSU_CONVERSATION_INTEGRATION_V2_3_0
ROOT="$HOME/.local/state/ritsu-conversation-integration-v2.3.0"
SELF="${BASH_SOURCE[0]}"
MODE="${1:-start}"
status(){
  printf 'CAMPAIGN=%s\n' "$NAME"
  [ ! -f "$ROOT/status" ] || cat "$ROOT/status"
  [ ! -f "$ROOT/heartbeat" ] || { printf 'HEARTBEAT_UTC='; cat "$ROOT/heartbeat"; }
  if [ -f "$ROOT/pid" ]; then
    pid="$(cat "$ROOT/pid")"
    if kill -0 "$pid" 2>/dev/null; then printf 'PROCESS=RUNNING PID=%s\n' "$pid"; else echo 'PROCESS=NOT_RUNNING'; fi
  fi
  [ ! -f "$ROOT/report.txt" ] || cat "$ROOT/report.txt"
  echo "LOG=$ROOT/log.txt"
  [ ! -f "$ROOT/log.txt" ] || { echo '--- RECENT LOG ---'; tail -n 25 "$ROOT/log.txt"; }
}
if [ "$MODE" = status ]; then status; return 0 2>/dev/null || exit 0; fi
if [ "$MODE" = start ]; then
  umask 077; mkdir -p "$ROOT"
  if [ -e "$ROOT/started" ]; then echo 'ALREADY_STARTED_NO_DUPLICATE=YES'; status; return 0 2>/dev/null || exit 0; fi
  date -u '+%Y-%m-%dT%H:%M:%SZ' > "$ROOT/started"
  printf 'STATE=STARTING\n' > "$ROOT/status"
  command -v termux-wake-lock >/dev/null 2>&1 && termux-wake-lock >/dev/null 2>&1 || :
  nohup bash "$SELF" worker </dev/null >> "$ROOT/log.txt" 2>&1 &
  printf '%s\n' "$!" > "$ROOT/pid"
  echo "CAMPAIGN=$NAME"; echo "DETACHED_PID=$!"; echo "STATUS_COMMAND=bash '$SELF' status"
  return 0 2>/dev/null || exit 0
fi
if [ "$MODE" != worker ]; then echo 'Usage: start or status'; return 2 2>/dev/null || exit 2; fi
umask 077
export RITSU_INT_ROOT="$ROOT" RITSU_INT_SCRIPT="$SELF"
python3 - <<'PY'
import datetime,hashlib,json,os,re,shutil,subprocess,sys,time
from pathlib import Path
root=Path(os.environ['RITSU_INT_ROOT']); ownscript=Path(os.environ['RITSU_INT_SCRIPT'])
home=Path.home();repo=home/'storage/documents/GodotProjects/home-center'
private=home/'.local/state/ritsu-fresh-canonical-v2.2.0/git-source'
source_commit='16c3ca66920ac75a4742b8e680c19d585e8f9aff'
main_commit='762e8f318740da6c5ea73d21db1d2252c9becaa1'
backend_commit='b66177865439e67d1d2544e7cc358aae351b9599'
backend=home/'.local/state/ritsu-feature-campaign/source-20261103T112146Z-25999'
branch='campaign/ritsu-conversation-integration-20261103-v2-3-0'
work=root/'source-worktree';status=root/'status';beat=root/'heartbeat';report=root/'report.txt';readme=root/'runbook.txt'
E={};commands=[]
sha=lambda b:hashlib.sha256(b).hexdigest()
now=lambda:datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds')
class Gate(Exception):pass
def gate(ok,s):
 if not ok:raise Gate(s)
def stage(s):
 print('STAGE='+s,flush=True);beat.write_text(now()+'\n');status.write_text('STATE=RUNNING\nSTAGE='+s+'\nUPDATED_UTC='+now()+'\n')
def cmd(args,cwd=None,timeout=120,optional=False):
 p=subprocess.run([str(x) for x in args],cwd=cwd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=timeout,env={**os.environ,'GIT_LFS_SKIP_SMUDGE':'1'})
 if p.returncode and not optional:
  E['FAILED_COMMAND']=' '.join(map(str,args[:5]));E['FAILED_EXIT']=p.returncode
  E['FAILED_STDERR']=p.stderr.decode('utf-8','replace')[-350:].replace('\n',' ')
  E['FAILED_STDOUT']=p.stdout.decode('utf-8','replace')[-350:].replace('\n',' ')
  raise Gate('COMMAND_FAILED_'+str(args[0])+'_'+str(p.returncode))
 return p
def gout(args,cwd=None,timeout=120):return cmd(args,cwd,timeout).stdout.decode('utf-8','replace').strip()
def blob(path):return gout(['git','-C',str(work),'rev-parse',f'HEAD:{path}'])
def edit_exact(s,needle,replacement,ident):
 count=s.count(needle);gate(count==1,'ANCHOR_'+ident+'_COUNT_'+str(count));return s.replace(needle,replacement,1)
def write_changed(path,transform):
 p=work/path;before=p.read_text();p.write_text(transform(before));gate(p.read_text()!=before,'NO_SOURCE_CHANGE_'+str(path))
 return str(path)
java='android/ritsu-control/app/src/main/java/com/homecenter/ritsucontrol/'
expected={
 'MainActivity.java':'6600f0552301bdb0c943040c8c853731c98443b4',
 'RitsuLocalSync.java':'608cbc2d6dbdcd44ca514afa182937c1e4748c42',
 'ConversationLedger.java':'e5e846403947f70ed3e0f6625ea3aab5d61243f0',
 'RitsuConversationLinks.java':'d9cbabe04b287b2ffe82b3fa410d088c3e98f653'
}
stop_java=r'''package com.homecenter.ritsucontrol;

import android.app.Activity;
import android.app.AlertDialog;
import android.os.Handler;
import android.os.Looper;
import org.json.JSONObject;
import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;

/** One deliberate owner-requested remote browser Stop. Never relabels a turn
 * stopped unless the existing paired service verifies the exact turn ID. */
final class RitsuRemoteStop {
    private static final Handler MAIN=new Handler(Looper.getMainLooper());
    static void request(Activity activity,ConversationLedger ledger,
                        ConversationLedger.Entry turn,Runnable redraw){
        final String id=turn.id,tab=turn.tabId;
        new Thread(()->{
            String message=null;boolean stopped=false;
            HttpURLConnection connection=null;
            try{
                RitsuPairing.Pair pair=RitsuPairing.load(activity);
                if(pair==null)throw new IllegalStateException("PAIRING_REQUIRED");
                String origin=RitsuPairing.validateOrigin(pair.origin);
                byte[] request=new JSONObject().put("turnId",id).put("tabId",tab)
                    .toString().getBytes(StandardCharsets.UTF_8);
                connection=(HttpURLConnection)new URL(origin+"/v1/ritsu/turn/stop").openConnection();
                connection.setInstanceFollowRedirects(false);
                connection.setConnectTimeout(7000);connection.setReadTimeout(30000);
                connection.setUseCaches(false);connection.setRequestMethod("POST");
                connection.setRequestProperty("Authorization","Bearer "+pair.token);
                connection.setRequestProperty("Content-Type","application/json");
                connection.setDoOutput(true);
                connection.setFixedLengthStreamingMode(request.length);
                try(OutputStream out=connection.getOutputStream()){out.write(request);}
                int code=connection.getResponseCode();
                if(code!=200)throw new IllegalStateException("REMOTE_STOP_HTTP_"+code);
                ByteArrayOutputStream out=new ByteArrayOutputStream();
                try(InputStream in=connection.getInputStream()){
                    byte[] buf=new byte[1024];int n;
                    while((n=in.read(buf))!=-1){
                        if(out.size()+n>2048)throw new SecurityException("STOP_RECEIPT_OVERSIZED");
                        out.write(buf,0,n);
                    }
                }
                JSONObject result=new JSONObject(out.toString(StandardCharsets.UTF_8.name()));
                if(!result.optBoolean("stopped",false)||!id.equals(result.optString("turnId")))
                    throw new SecurityException("STOP_RECEIPT_NOT_VERIFIED");
                stopped=true;
            }catch(Exception e){
                message=e.getMessage()==null?e.getClass().getSimpleName():e.getMessage();
            }finally{if(connection!=null)connection.disconnect();}
            final boolean verified=stopped;
            final String error=message;
            MAIN.post(()->{
                if(verified){
                    ledger.updateState(id,"STOPPED");
                    RitsuControlService.feedRevision++;
                    redraw.run();
                }else{
                    new AlertDialog.Builder(activity).setTitle("Remote Stop unconfirmed")
                        .setMessage("No browser cancellation was confirmed. The original turn was preserved. " +
                            String.valueOf(error).replaceAll("[^a-zA-Z0-9 _.:/-]"," ").substring(0,
                            Math.min(110,String.valueOf(error).length())))
                        .setPositiveButton("OK",null).show();
                }
            });
        },"RitsuRemoteStopRequest").start();
    }
}
'''
def main_patch(s):
 s=edit_exact(s,'private Button listenButton, muteButton, sendButton, stickyButton;',
 'private Button listenButton, muteButton, sendButton, stickyButton;\n    private Button stopReplyButton, voiceReplyButton;', 'BUTTON_FIELDS')
 s=edit_exact(s,'        root.addView(compose);\n\n        LinearLayout controls=',
 '''        root.addView(compose);
        LinearLayout replyActions=new LinearLayout(this);
        replyActions.setOrientation(LinearLayout.HORIZONTAL);
        stopReplyButton=button("Stop generating",v->stopSelectedGenerating());
        stopReplyButton.setContentDescription("Request remote ChatGPT browser Stop Generating; not audio stop");
        voiceReplyButton=button("Pocket voice request",v->{
            RitsuConversationLinks.voicePreference(this,workspace.active().id,conversationDeck);
        });
        voiceReplyButton.setContentDescription("Toggle per-chat Pocket voice preference, separate from microphone mute");
        replyActions.addView(stopReplyButton,new LinearLayout.LayoutParams(0,dp(48),1));
        replyActions.addView(voiceReplyButton,new LinearLayout.LayoutParams(0,dp(48),1));
        root.addView(replyActions);

        LinearLayout controls=''', 'ACTION_ROW')
 s=edit_exact(s,'            content.setTextIsSelectable(true);bubble.addView(content);',
 '''            content.setTextIsSelectable(true);bubble.addView(content);
            Button copyMessage=button("Copy",v->{
                ClipboardManager clipboard=(ClipboardManager)getSystemService(CLIPBOARD_SERVICE);
                if(clipboard!=null)clipboard.setPrimaryClip(
                    ClipData.newPlainText("Ritsu message",entry.text));
            });
            copyMessage.setContentDescription("Copy complete "+entry.who+" message");
            bubble.addView(copyMessage,new LinearLayout.LayoutParams(dp(92),dp(44)));''','COPY_ALL')
 target='    private void queueTyped() {'
 insert='''    private ConversationLedger.Entry latestStoppableTurn(){
        java.util.List<ConversationLedger.Entry> pending=ledger.unsent();
        String selected=workspace.active().id;
        for(int i=pending.size()-1;i>=0;i--){
            ConversationLedger.Entry e=pending.get(i);
            if(selected.equals(e.tabId)&&
               ("LOCAL_SUBMITTED".equals(e.state)||"LOCAL_UNCERTAIN".equals(e.state)))
                return e;
        }
        return null;
    }
    private void stopSelectedGenerating(){
        ConversationLedger.Entry turn=latestStoppableTurn();
        if(turn==null){new AlertDialog.Builder(this).setMessage(
            "No active or uncertain remote generation to stop in this tab.")
            .setPositiveButton("OK",null).show();return;}
        new AlertDialog.Builder(this).setTitle("Stop ChatGPT generation?")
            .setMessage("Requests Stop for the selected turn in the real ChatGPT browser. " +
                "It will not erase partial text or stop Pocket audio. " +
                "If browser confirmation fails, the turn remains unresolved.")
            .setPositiveButton("Stop generation",(dialog,which)->
                RitsuRemoteStop.request(this,ledger,turn,()->{renderFeed();refreshStatus();}))
            .setNegativeButton("Cancel",null).show();
    }

'''
 s=edit_exact(s,target,insert+target,'STOP_ACTION')
 s=edit_exact(s,'        if(sendButton!=null){\n            sendButton.setText("Send");',
 '''        if(stopReplyButton!=null){
            stopReplyButton.setEnabled(latestStoppableTurn()!=null);
        }
        if(voiceReplyButton!=null){
            boolean requested=getSharedPreferences("ritsu_conversation_links_v1",MODE_PRIVATE)
                .getBoolean("voice_"+workspace.active().id,false);
            voiceReplyButton.setText(requested?"Pocket requested ON":"Pocket requested OFF");
        }
        if(sendButton!=null){
            sendButton.setText("Send");''','STATUS_CONTROLS')
 return s
def sync_patch(s):
 s=edit_exact(s,'if(text.isEmpty()||text.length()>5000||revision<1||',
              'if(text.isEmpty()||text.length()>64000||revision<1||','LARGE_REPLY_SSE')
 s=edit_exact(s,'            }else if("uncertain".equals(type)){',
 '''            }else if("stopped".equals(type)){
                ledger.updateState(turnId,"STOPPED");
                status="ChatGPT generation stopped on remote browser";
            }else if("stop_unconfirmed".equals(type)){
                status="Remote Stop was not confirmed; turn preserved";
            }else if("uncertain".equals(type)){''','STOP_SSE')
 return s
def ledger_patch(s):
 s=edit_exact(s,'message.length()>5000)throw new IllegalArgumentException("invalid streaming reply");',
              'message.length()>64000)throw new IllegalArgumentException("invalid streaming reply");','REPLY_LEDGER_LIMIT')
 s=edit_exact(s,'"COMPLETED".equals(row.optString("state")))count++;',
              '("COMPLETED".equals(row.optString("state")) || "STOPPED".equals(row.optString("state"))))count++;','NEVER_EXPECTED') if False else s
 s=edit_exact(s,'!"COMPLETED".equals(row.optString("state")))count++;',
              '!"COMPLETED".equals(row.optString("state")) && !"STOPPED".equals(row.optString("state")))count++;','PENDING_STOPPED')
 s=edit_exact(s,'"COMPLETED".equals(row.optString("state")))continue;',
              '("COMPLETED".equals(row.optString("state")) || "STOPPED".equals(row.optString("state"))))continue;','UNSENT_STOPPED')
 return s
try:
 stage('VERIFY_OWNER_RULES_SOURCE_AND_GIT_PROVENANCE')
 gate(repo.is_dir() and private.is_dir() and backend.is_dir(),'DOCUMENTED_GIT_REPOSITORY_MISSING')
 gate(gout(['git','-C',repo,'rev-parse','HEAD'])==main_commit,'PROTECTED_MAIN_CHANGED')
 gate(gout(['git','-C',repo,'status','--porcelain'])=='','PROTECTED_MAIN_NOT_CLEAN')
 for path in ['AGENTS.md','AGENTS.base.md','docs/RITSU_PHONE_AUDIO_LAWS.md']:
  p=repo/path;gate(p.is_file(),'REQUIRED_RULES_MISSING_'+path)
  E['READ_'+path]=sha(p.read_bytes())
 gate(gout(['git','-C',private,'rev-parse','HEAD'])==source_commit,'FRESH_SOURCE_COMMIT_MISMATCH')
 gate(gout(['git','-C',backend,'rev-parse','HEAD'])==backend_commit,'RECOVERED_STOP_COMMIT_MISMATCH')
 gate(not gout(['git','-C',backend,'status','--porcelain']),'RECOVERED_STOP_SOURCE_DIRTY')
 for fn,sha1 in expected.items():
  actual=gout(['git','-C',private,'rev-parse',f'HEAD:{java}{fn}'])
  gate(actual==sha1,'SOURCE_BLOB_DRIFT_'+fn)
 stage('CREATE_ISOLATED_INTEGRATION_WORKTREE')
 if not work.is_dir():
  gate(not gout(['git','-C',private,'branch','--list',branch]),'SOURCE_BRANCH_EXISTS_OTHER_WORKTREE')
  cmd(['git','-C',private,'worktree','add','-b',branch,work,source_commit],timeout=120)
 gate(gout(['git','-C',work,'rev-parse','HEAD'])==source_commit,'INTEGRATION_BASE_DRIFT')
 gate(gout(['git','-C',work,'branch','--show-current'])==branch,'INTEGRATION_BRANCH_DRIFT')
 gate(not gout(['git','-C',work,'status','--porcelain']),'INTEGRATION_WORKTREE_DIRTY')
 stage('INTEGRATE_RECOVERED_PLAYWRIGHT_STOP_AND_SERVER')
 backend_files=['tools/campaigns/ritsu_control_playwright_bridge.mjs',
   'tools/ritsu-local-server/server.mjs',
   'tools/ritsu-local-server/ritsu_stop_regression_test.mjs']
 for name in backend_files:
  target=work/name
  gate(not target.exists(),'EXISTING_BACKEND_CONFLICT_'+name)
  payload=cmd(['git','-C',backend,'show',backend_commit+':'+name]).stdout
  gate(payload and len(payload)<200000,'BACKEND_SOURCE_INVALID_'+name)
  target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(payload)
  E['BACKEND_'+target.name+'_SHA256']=sha(payload)
 stage('IMPLEMENT_REAL_PHONE_CONTROLS_AND_LARGE_REPLY_STORAGE')
 write_changed(java+'MainActivity.java',main_patch)
 write_changed(java+'RitsuLocalSync.java',sync_patch)
 write_changed(java+'ConversationLedger.java',ledger_patch)
 new_file=work/(java+'RitsuRemoteStop.java');gate(not new_file.exists(),'STOP_JAVA_ALREADY_EXISTS')
 new_file.write_text(stop_java)
 gate('voice_"+tabId' in (work/(java+'RitsuConversationLinks.java')).read_text(), 'EXISTING_VOICE_PREF_PROTOCOL_MISSING')
 # UI preference storage name comes from the actual connected source, not a guessed system setting.
 links=(work/(java+'RitsuConversationLinks.java')).read_text()
 m=re.search(r'private static final String PREF\s*=\s*"([^"]+)"',links)
 gate(m is not None,'VOICE_PREF_STORE_NAME_NOT_VERIFIED')
 ui=work/(java+'MainActivity.java');ui.write_text(ui.read_text().replace('"ritsu_conversation_links_v1",MODE_PRIVATE','"'+m.group(1)+'",MODE_PRIVATE'))
 E['PREFERENCE_STORE_MATCHED_SOURCE']='YES'
 stage('WRITE_REGRESSION_CONTRACT_AND_OWNER_RUNBOOK')
 docs=work/'docs/ritsu-conversation-integration-v2.3.0.md';docs.parent.mkdir(parents=True,exist_ok=True)
 docs.write_text('''# Ritsu conversation integration v2.3.0

Owner-authorized Termux Git campaign. Source parent: 16c3ca66920ac75a4742b8e680c19d585e8f9aff. Recovered Stop parent: b66177865439e67d1d2544e7cc358aae351b9599 (only three backend source/test files copied; no remote service deployment).

Actual implementation: per-message Copy, accessible visible Stop Generating with authenticated exact-turn stop confirmation, SSE stopped/stop_unconfirmed semantics, 64k-character assistant stream receipt/ledger, and visible per-chat Pocket voice *preference* control on the existing tab UI. Retains existing tab strip, drawers, scroll anchors, edit-free outbox identities, signer, and paired credentials.

NOT IMPLEMENTED: ChatGPT's browser-native edit-and-regenerate/branching, confirmed Pocket WAV synthesis and user-heard playback, remote installed Windows service source reconciliation, source-to-installed Android certificate/version attestation, browser DOM Stop under live account, full long-document playback, and physical visual accessibility acceptance.

No APK may be compiled/assembled/signed until all these acceptance gates pass. Existing Fresh certificate must be reused; no auto-install. No replay of unresolved turns. This campaign is a source integration, not a released client.

Tested independently after deployment: choose a verified bound chat; normal send; progressively appearing assistant reply; 30k+ character response; authenticated Stop and retained partial; deliberate unconfirmed Stop; Copy full message; remote edit/regenerate; Pocket ON/OFF preference, full spoken answer and HEARD; closed-tab reopen/draft/scroll. All gates separate.
''')
 test=work/'tools/campaigns/ritsu_integration_source_test_v2_3_0.py';test.parent.mkdir(parents=True,exist_ok=True)
 test.write_text('''from pathlib import Path
r=Path(__file__).resolve().parents[2]
p=r/'android/ritsu-control/app/src/main/java/com/homecenter/ritsucontrol'
main=(p/'MainActivity.java').read_text();sync=(p/'RitsuLocalSync.java').read_text();ledger=(p/'ConversationLedger.java').read_text();stop=(p/'RitsuRemoteStop.java').read_text();bridge=(r/'tools/campaigns/ritsu_control_playwright_bridge.mjs').read_text();server=(r/'tools/ritsu-local-server/server.mjs').read_text()
assert 'stopSelectedGenerating()' in main
assert 'Copy complete ' in main and 'ClipData.newPlainText("Ritsu message",entry.text)' in main
assert 'Pocket requested ON' in main and 'Pocket requested OFF' in main
assert '"/v1/ritsu/turn/stop"' in stop and 'STOP_RECEIPT_NOT_VERIFIED' in stop
assert '"stopped".equals(type)' in sync and '"stop_unconfirmed".equals(type)' in sync
assert 'text.length()>64000' in sync and 'message.length()>64000' in ledger
assert '/v1/ritsu/turn/stop' in server and 'stopControlGone' in bridge
assert 'RitsuConversationDeck' in main and 'rememberReadingPosition()' in main
print('RITSU_SOURCE_INTEGRATION_REGRESSION=PASS')
''')
 campaign_copy=work/'tools/campaigns/RITSU_CONVERSATION_INTEGRATION_v2.3.0.sh'
 campaign_copy.write_bytes(ownscript.read_bytes())
 stage('RUN_INTEGRATION_AND_STOP_REGRESSION_TESTS')
 gate(cmd(['python3','-m','py_compile',test]).returncode==0,'INTEGRATION_TEST_SYNTAX')
 cmd(['python3',test],cwd=work,timeout=60)
 for file in backend_files:
  cmd(['node','--check',work/file],timeout=60)
 cmd(['node',work/'tools/ritsu-local-server/ritsu_stop_regression_test.mjs'],cwd=work,timeout=75)
 E['NODE_SYNTAX']='PASS_3';E['ACTUAL_MOCKED_SERVER_STOP_REGRESSION']='PASS'
 E['ANDROID_SOURCE_INTEGRATION_TEST']='PASS'
 # Compilation attempts are safe: they stop at Java classes, not assemble an APK.
 stage('COMPILE_ANDROID_JAVA_WITHOUT_ASSEMBLING_APK')
 gradle=shutil.which('gradle');sdk=home/'android-sdk';java_compiled=False
 if gradle and (sdk/'platforms/android-35/android.jar').exists():
  envp=root/'compile.log'
  args=[gradle,'--offline','--no-daemon',':app:compileReleaseJavaWithJavac']
  # Reuse only the documented, already-installed AAPT2 wrapper. Android
  # Gradle Plugin requires the wrapper's basename to be exactly 'aapt2'.
  aaptbase=home/'.local/share/ritsu-campaigns/sticky-phone-v018/aapt2-official'
  aapt=aaptbase/'aapt2'
  if not aapt.exists() and (aaptbase/'aapt2-scoped').is_file():
   # Copy the official cached toolchain folder into campaign-private storage.
   # This preserves relative resource/library paths inside the scoped wrapper.
   sandbox=root/'aapt2-official'
   if not sandbox.exists():shutil.copytree(aaptbase,sandbox,symlinks=False)
   renamed=sandbox/'aapt2'
   shutil.copy2(sandbox/'aapt2-scoped',renamed)
   renamed.chmod(renamed.stat().st_mode | 0o100)
   aapt=renamed
  if aapt.is_file() and os.access(aapt,os.X_OK):
   args+=['-Pandroid.aapt2FromMavenOverride='+str(aapt)]
   E['DOCUMENTED_AAPT2_WRAPPER']='VERIFIED_PATH'
  try:
   p=cmd(args,cwd=work/'android/ritsu-control',timeout=500,optional=True)
   envp.write_bytes((p.stdout[-18000:]+b'\n'+p.stderr[-8000:]))
   E['JAVA_COMPILE_RESULT']='PASS' if p.returncode==0 else 'BLOCKED_EXIT_'+str(p.returncode)
   if p.returncode:
    summary=[]
    for line in (p.stdout+b'\n'+p.stderr).decode('utf-8','replace').splitlines():
     if re.search(r'error:|FAILURE:|Execution failed for task|What went wrong|AAPT2|Could not|cannot find symbol',line,re.I):
      clean=re.sub(r'[^a-zA-Z0-9 _.:/()\[\]-]',' ',line.strip())[:150]
      if clean and len(summary)<5:summary.append(clean)
    E['JAVA_COMPILE_DIAGNOSTICS']=' || '.join(summary) or 'SEE_PRIVATE_COMPILE_LOG'
   java_compiled=p.returncode==0
  except subprocess.TimeoutExpired:
   E['JAVA_COMPILE_RESULT']='BLOCKED_TIMEOUT_500S'
 else:E['JAVA_COMPILE_RESULT']='BLOCKED_MISSING_OFFLINE_GRADLE_OR_SDK35'
 # A source-only successful integration still has independent release gates outstanding.
 stage('COMMIT_SCOPED_INTEGRATION_SOURCE')
 paths=backend_files+[java+x for x in ['MainActivity.java','RitsuLocalSync.java','ConversationLedger.java','RitsuRemoteStop.java']]+[str(docs.relative_to(work)),str(test.relative_to(work)),str(campaign_copy.relative_to(work))]
 cmd(['git','-C',work,'add','--',*paths],timeout=90)
 staged=gout(['git','-C',work,'diff','--cached','--name-only']).splitlines()
 gate(set(staged)==set(paths),'STAGED_SCOPE_MISMATCH')
 cmd(['git','-C',work,'-c','core.hooksPath=/dev/null','-c','commit.gpgsign=false','commit','-m','ritsu: integrate authenticated stop, reply length, copy and voice preference UI'],timeout=120)
 commit=gout(['git','-C',work,'rev-parse','HEAD'])
 E['INTEGRATION_COMMIT']=commit;E['INTEGRATION_BRANCH']=branch
 stage('PUBLISH_REVIEW_ONLY_INTEGRATION_BRANCH')
 origin=gout(['git','-C',private,'remote','get-url','origin'])
 gate('Valar05/home-center' in origin,'UNAPPROVED_GIT_ORIGIN')
 rem=gout(['git','ls-remote',origin,'refs/heads/main']).split()
 gate(rem and rem[0]==main_commit,'REMOTE_MAIN_CHANGED_REFUSE_PUSH')
 existing=gout(['git','ls-remote',origin,'refs/heads/'+branch]).split()
 gate(not existing or existing[0]==commit,'REMOTE_BRANCH_CONFLICT')
 if not existing:cmd(['git','-C',work,'push','origin','HEAD:refs/heads/'+branch],timeout=300)
 readback=gout(['git','ls-remote',origin,'refs/heads/'+branch]).split()
 gate(readback and readback[0]==commit,'REMOTE_SOURCE_READBACK_MISMATCH')
 E['GIT_REMOTE_PUBLICATION']='REVIEW_ONLY_BRANCH_SHA_VERIFIED'
 E['JAVA_COMPILE_GATE']='PASS' if java_compiled else 'NOT_PASSED_DRAFT_ONLY'
 E['APK_BUILDS']=0;E['APK_RELEASE_GATE']='BLOCKED_UNIMPLEMENTED_REMOTE_EDIT_POCKET_AUDIO_LIVE_DOM_AND_INSTALLED_IDENTITY'
 E['WINDOWS_DEPLOYMENT']='NOT_ATTEMPTED';E['PHONE_UI_ACCEPTANCE']='NOT_TESTED'
 gate(gout(['git','-C',repo,'rev-parse','HEAD'])==main_commit and not gout(['git','-C',repo,'status','--porcelain']),'ORIGINAL_MAIN_CHANGED')
 result='SOURCE_INTEGRATED_COMPILE_'+('PASS' if java_compiled else 'BLOCKED')+'_RELEASE_GATED'
except BaseException as e:
 E['BLOCKED_GATE']=str(e)[:220];result='BLOCKED'
 print('BLOCKED_GATE='+E['BLOCKED_GATE'],flush=True)
finally:
 E['CAMPAIGN_STATUS']=result;E['FINAL_UTC']=now();E['APK_BUILDS']=0
 E['SIGNER_MUTATED']='NO';E['JOURNALS_MUTATED']='NO';E['INSTALLED_APP_MUTATED']='NO'
 payload='\n'.join(k+'='+str(v).replace('\n',' ') for k,v in E.items())+'\n'
 tmp=report.with_suffix('.pending');tmp.write_text(payload);os.replace(tmp,report)
 try:
  dest=home/'storage/downloads/Ritsu-Integration-v2.3.0-REPORT.txt';dest.parent.mkdir(parents=True,exist_ok=True)
  pend=dest.with_suffix('.pending');shutil.copyfile(report,pend);os.replace(pend,dest)
  print('DOWNLOADS_REPORT='+str(dest),flush=True)
 except Exception as ex:print('REPORT_EXPORT_BLOCKED='+type(ex).__name__,flush=True)
 status.write_text('STATE='+('BLOCKED' if result=='BLOCKED' else 'COMPLETE')+'\nRESULT='+result+'\nUPDATED_UTC='+now()+'\n')
 beat.write_text(now()+'\n');print('CAMPAIGN_STATUS='+result,flush=True)
sys.exit(2 if result=='BLOCKED' else 0)
PY
