import contextlib,hashlib,io,sys,tempfile,unittest,subprocess,shutil
from pathlib import Path
from unittest import mock
P=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(P))
import patch_ui_v135,cauldron_courier,onego

class AndroidFixes(unittest.TestCase):
 def fixture(self,root):
  base=root/'app/src/main/java/com/homecenter/ritsucontrol';base.mkdir(parents=True)
  main='''public class MainActivity {
    private String drawnConversation=null;
    void redraw(){
        final boolean follow=same && previousAtBottom;
                feedScroll.fullScroll(View.FOCUS_DOWN);return;
            composer.setText("");
            if(conversationDeck!=null)conversationDeck.setDraft(active.id,"");
            renderFeed();
            TextView state=label(entry.state,11,false);
    }
    // RITSU_CONVERSATION_USABILITY_V1_3_1
}'''
  links='''class RitsuConversationLinks {
    static String canonical(String value){
        if(value==null||!value.matches("https://chatgpt\\\\.com/c/[A-Za-z0-9-]{8,120}/?"))return null;
        return value;
    }
    static String coarse(Exception e){
        return e.getClass().getSimpleName();
    }
    void request(){
            int code=c.getResponseCode();if(code!=200)throw new IllegalStateException("CATALOG_HTTP_"+code);
    }
}'''
  sync='''class RitsuLocalSync {
    // known existing RitsuTurnRecovery
    private void sendPending() {
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
        }
        RitsuPairing.Pair p;
    }
        auditTimer.scheduleWithFixedDelay(this::requestNow,20,45,
            java.util.concurrent.TimeUnit.SECONDS);
}'''
  for name,s in [('MainActivity.java',main),('RitsuConversationLinks.java',links),('RitsuLocalSync.java',sync)]: (base/name).write_text(s)
  # Previously accepted recovery source (before v135 correction).
  prev=P/'tests/fixtures/RitsuTurnRecovery_code24.java'
  if not prev.exists():self.skipTest('prior packet not available')
  (base/'RitsuTurnRecovery.java').write_bytes(prev.read_bytes())
  return base
 def test_bounded_full_source_patch_and_idempotent_refusal(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);base=self.fixture(root)
   patch_ui_v135.patch(root)
   m=(base/'MainActivity.java').read_text();sync=(base/'RitsuLocalSync.java').read_text();links=(base/'RitsuConversationLinks.java').read_text()
   self.assertIn('followAfterExplicitSend=true',m)
   self.assertIn('postDelayed',m)
   self.assertIn('this::runReadOnlyAudit',sync)
   self.assertNotIn('scheduleWithFixedDelay(this::requestNow',sync)
   self.assertIn('local-chatgpt%3[Aa]',links)
   self.assertIn('CATALOG_HTTP_',links)
   self.assertIn('definitelyNotAccepted',(base/'RitsuTurnRecovery.java').read_text())
   with self.assertRaisesRegex(RuntimeError,'V135_ALREADY_APPLIED'):patch_ui_v135.patch(root)
 def test_wrong_source_kept_unchanged(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);base=self.fixture(root)
   m=base/'MainActivity.java';m.write_text(m.read_text().replace('final boolean follow=same && previousAtBottom;', 'final boolean follow=false;'))
   initial={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in base.glob('*.java')}
   with self.assertRaisesRegex(RuntimeError,'UNSUPPORTED_ANDROID_ANCHOR_follow decision'):patch_ui_v135.patch(root)
   self.assertEqual(initial,{f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in base.glob('*.java')})
 def test_not_automatically_resending_uncertain_prompt(self):
  src=(P/'RitsuTurnRecovery.java').read_text()
  self.assertNotIn('setRequestMethod("POST")',src)
  self.assertIn('if("no_server_receipt".equals(state))',src)
  self.assertIn('status(pair)!=count',src)

class BrowserRouteFixes(unittest.TestCase):
 @unittest.skipUnless(shutil.which('node'),'Node not present')
 def test_actual_node_parse_injected_helpers_and_routes(self):
  code="""import http from 'node:http';import path from 'node:path';import {spawn} from 'node:child_process';
const BRIDGE='demo';async function test(){
"""+(P/'server_catalog_functions.js').read_text()+"\n"""+'''const server=http.createServer(async(req,res)=>{
const send=(code,obj)=>{};const url=new URL(req.url,'http://localhost');
const tabPattern=/^[A-Za-z0-9_-]{4,80}$/;
'''+(P/'server_catalog_routes.js').read_text()+"\n});}\n"
  with tempfile.TemporaryDirectory() as d:
   src=Path(d)/'server.mjs';src.write_text(code)
   for f in (src,P/'ritsu_browser_catalog_v135.mjs',P/'ritsu_browser_recover_v133.mjs'):
    r=subprocess.run(['node','--check',str(f)],capture_output=True,text=True,timeout=15)
    self.assertEqual(r.returncode,0,(f,r.stderr))
 def test_routes_never_post_chatgpt_or_rename_owners_chat(self):
  js=(P/'ritsu_browser_catalog_v135.mjs').read_text()
  self.assertNotIn('.click(',js)
  self.assertNotIn('POST',js)
  self.assertNotIn('search(',js)
  self.assertIn('local-chatgpt%3[Aa]',js)
  self.assertIn('page.url()!==url',js)
  route=(P/'server_catalog_routes.js').read_text()
  self.assertIn('RITSU_V135_CATALOG_ROUTES',route)
  self.assertIn("send(503",route)
  self.assertIn('invalid_exact_binding',route)
 def test_courier_packet_carries_all_browser_routes(self):
  with mock.patch.object(cauldron_courier,'invoke') as inv:
   inv.return_value=''
   with self.assertRaises(cauldron_courier.RemoteBlocked): cauldron_courier.apply(P,lambda x:None)
   # When only recovery is confirmed, catalog probe still happens.
   self.assertEqual(inv.call_args_list[0].args[0],'READ_ONLY_ENDPOINT_PROBE')
  s=(P/'cauldron_courier.py').read_text()
  self.assertIn('server_catalog_routes.js',s)
  self.assertIn('CATALOG_ROUTE_PROBE',s)
  self.assertIn('v1.3.5',s)
 def test_release_is_code25_and_downloads_only(self):
  o=(P/'onego.py').read_text()
  self.assertEqual(onego.VERSION,'1.3.5')
  self.assertIn('versionCode 25',o)
  self.assertIn('termux-media-scan',o)
  self.assertNotIn('command([\'termux-open',o)
  self.assertLess(o.index('publish(signed)'),o.index('cauldron_courier.apply(PACKET,say)'))
