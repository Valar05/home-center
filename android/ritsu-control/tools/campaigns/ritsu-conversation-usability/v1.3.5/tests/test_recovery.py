import contextlib,io,json,pathlib,re,shutil,sys,tempfile,unittest,subprocess
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import onego,patch_recovery
P=Path(__file__).resolve().parents[1]

class ReleaseContract(unittest.TestCase):
    def test_same_campaign_new_version(self):
        self.assertEqual(onego.VERSION,'1.3.5')
        self.assertEqual(onego.CAMPAIGN,'ritsu-conversation-usability')
        self.assertIn('ACCEPTED_CODE22_SHA',onego.locate.__code__.co_names)
    def test_do_not_autoinstall(self):
        code=Path(onego.__file__).read_text()
        self.assertNotRegex(code,r'(?m)^\s*(?:subprocess|command)\([^\n]*(?:termux-open|pm install|am start)')
        self.assertIn('INSTALLATION=NOT_ATTEMPTED',code)
        self.assertIn("'COPY_ONLY_TO_ANDROID_DOWNLOADS'",code)
    def test_exact_apk_sha_locked(self):
        self.assertEqual(onego.ACCEPTED_CODE22_SHA,'362358e3a9bc2c35caa4f8527506b22d1cbf1e3ff95d3f5134db622199a56731')
    def test_recovery_no_remote_post(self):
        s=(P/'RitsuTurnRecovery.java').read_text()
        self.assertIn('RitsuPairing.validateOrigin',s)
        self.assertIn('GET',s)
        self.assertNotIn('setRequestMethod("POST")',s)
        self.assertIn('status(pair)!=count',s)
        self.assertIn('seq',s)
        self.assertIn('LOCAL_NOT_ACCEPTED',s)
        self.assertIn('owner.tabId.equals(tab)',s)
    def test_retry_requires_user_action(self):
        s=(P/'patch_recovery.py').read_text()
        self.assertNotIn('setPositiveButton("Retry original"',s)
        self.assertNotIn('ledger.updateState(entry.id,"LOCAL_QUEUED")',s)
        self.assertNotIn('ledger.updateState(owner.id,"LOCAL_QUEUED")',(P/'RitsuTurnRecovery.java').read_text())
    def test_cauldron_backend_recovery(self):
        s=Path(onego.__file__).read_text()
        self.assertIn("import cauldron_courier",s)
        self.assertIn('cauldron_courier.apply(PACKET,say)',s)
        self.assertIn('BACKEND_GUARDED_RECOVERY_RECONCILIATION',s)
    def test_proven_source_fingerprint(self):
        with tempfile.TemporaryDirectory() as td:
            roots=[]
            for name in ('old','copy'):
                d=Path(td)/name
                p=d/'app/src/main/java/MainActivity.java';p.parent.mkdir(parents=True);p.write_text('accepted source')
                g=d/'app/build.gradle';g.write_text('versionCode 22')
                roots.append(d)
            with contextlib.redirect_stdout(io.StringIO()): out=onego.choose_accepted_source(roots[::-1])
            self.assertEqual(out,roots[1]) # alphabetical copy before old
            (roots[0]/'app/build.gradle').write_text('versionCode 23')
            with self.assertRaises(onego.Block):onego.choose_accepted_source(roots)
    def test_missing_source_blocks(self):
        with self.assertRaisesRegex(onego.Block,'ACCEPTED_CODE22_BUILD_SOURCE_NOT_FOUND'):
            onego.choose_accepted_source([])

class AndroidPatch(unittest.TestCase):
    def synthetic(self,d):
        j=Path(d)/'app/src/main/java/com/homecenter/ritsucontrol';j.mkdir(parents=True)
        (j/'RitsuLocalSync.java').write_text('''class RitsuLocalSync {
    private volatile boolean stopped;
    void start(){input.execute(this::receiveLoop);requestNow();}
    private void sendPending() {
        if(stopped)return;
    }
    void close(){
        stopped=true;
        HttpURLConnection c=activeStream;
    }
}
''')
        (j/'MainActivity.java').write_text('''class MainActivity {
    // RITSU_CONVERSATION_USABILITY_V1_3_1
    void draw() {
            TextView origin=label(entry.who,12,true);bubble.addView(origin);
            content.setTextIsSelectable(true);bubble.addView(content);
    }
}
''')
        return j
    def test_patch_atomic_source_anchor_and_double_apply_refusal(self):
        with tempfile.TemporaryDirectory() as d:
            j=self.synthetic(d)
            with contextlib.redirect_stdout(io.StringIO()):patch_recovery.patch(Path(d),P)
            s=(j/'RitsuLocalSync.java').read_text();m=(j/'MainActivity.java').read_text()
            self.assertIn('RitsuTurnRecovery.reconcile(app,ledger,paired)',s)
            self.assertIn('scheduleWithFixedDelay',s)
            self.assertIn('Original preserved; not resent',m)
            self.assertNotIn('Button retry=button("Retry original"',m)
            self.assertTrue((j/'RitsuTurnRecovery.java').is_file())
            with self.assertRaises(RuntimeError):patch_recovery.patch(Path(d),P)
    def test_anchor_mismatch_no_partial_mutation(self):
        with tempfile.TemporaryDirectory() as d:
            j=self.synthetic(d)
            file=j/'MainActivity.java';file.write_text('wrong UI generation')
            before=(j/'RitsuLocalSync.java').read_bytes()
            with self.assertRaises(RuntimeError):patch_recovery.patch(Path(d),P)
            self.assertEqual(before,(j/'RitsuLocalSync.java').read_bytes())
            self.assertFalse((j/'RitsuTurnRecovery.java').exists())

class JavaSyntax(unittest.TestCase):
    @unittest.skipUnless(shutil.which('javac'),'java compiler unavailable')
    def test_recovery_compiles_against_bounded_stubs(self):
        with tempfile.TemporaryDirectory() as td:
            d=Path(td);pkg=d/'com/homecenter/ritsucontrol';pkg.mkdir(parents=True)
            (pkg/'RitsuTurnRecovery.java').write_bytes((P/'RitsuTurnRecovery.java').read_bytes())
            (pkg/'RitsuPairing.java').write_text('''package com.homecenter.ritsucontrol;
final class RitsuPairing {static class Pair {String origin="",token="";}
static String validateOrigin(String s){return s;}}
''')
            (pkg/'ConversationLedger.java').write_text('''package com.homecenter.ritsucontrol;
import java.util.*;
final class ConversationLedger {static class Entry {
String id="",tabId="",text="",state="";}
List<Entry> unsent(){return new ArrayList<>();}
void updateState(String a,String b){}
void upsertStreamingReply(String a,String b,int c,boolean d){}
}
''')
            (d/'android/content').mkdir(parents=True)
            (d/'android/content/Context.java').write_text('package android.content; public class Context {}')
            (d/'org/json').mkdir(parents=True)
            (d/'org/json/JSONObject.java').write_text('''package org.json; public class JSONObject {
 public JSONObject(String s){} public boolean optBoolean(String k){return false;}
 public long optLong(String k,long d){return d;}
 public String optString(String k,String d){return d;} public String optString(String k){return "";}
 public int optInt(String k,int d){return d;}
}''')
            sources=[str(x) for x in d.rglob('*.java')]
            res=subprocess.run(['javac','-d',str(d/'out'),*sources],capture_output=True,timeout=20,text=True)
            self.assertEqual(res.returncode,0,res.stderr)

if __name__=='__main__':unittest.main()
