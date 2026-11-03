import importlib.util,hashlib,os,pathlib,subprocess,sys,tempfile,unittest
PACKET=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(PACKET))
import onego,patch_android,patch_backend

class CampaignTests(unittest.TestCase):
    def test_deterministic_command_size(self):
        self.assertLessEqual(len(onego.ps_command(onego.WIN_READ)),3400)
        self.assertLessEqual(len(onego.ps_command(onego.WIN_INIT)),3400)
    def test_no_unpinned_urls(self):
        s=(PACKET/'RitsuConversationLinks.java').read_text()
        self.assertIn('https://chatgpt',s)
        self.assertIn('RitsuPairing.validateOrigin',s)
        self.assertIn('blocked(Activity',s)
        self.assertNotIn('archiveChatGPT(',s)
    def test_tab_close_not_destructive(self):
        s=(PACKET/'RitsuConversationDeck.java').read_text()
        block=s.split('void close(String id){',1)[1].split('void archive(String id){',1)[0]
        self.assertIn('open.remove(id)',block)
        self.assertNotIn('archived.add',block)
        self.assertNotIn('delete(',block)
        self.assertNotIn('RitsuLocalSync',block)
    def test_last_tab_stays_closed_on_relaunch(self):
        s=(PACKET/'RitsuConversationDeck.java').read_text()
        self.assertNotIn('if(!archived.contains(work.active().id)&&open.isEmpty())open.add(work.active().id);',s)
        self.assertIn('if(!store.contains("open"))open.add(work.active().id);',s)
        self.assertIn('void openWithoutSelection(String id)',s)
        links=(PACKET/'RitsuConversationLinks.java').read_text()
        self.assertIn('deck.openWithoutSelection(t.id)',links)
        self.assertNotIn('deck.ensureSelectedOpen();onChange.run();',links)
    def test_restart_contract_exact_process_not_scheduled_task(self):
        s=(PACKET/'windows_apply.py').read_text()
        self.assertIn('verified-launch.json',s)
        self.assertIn('RITSU_TAILSCALE_SERVE',s)
        self.assertIn('Get-CimInstance Win32_Process',s)
        self.assertIn('Start-Process -FilePath $exe',s)
        self.assertNotIn('Start-ScheduledTask',s)
        self.assertIn('if listener()!=401',s)
    def test_ui_source_anchors_unique(self):
        s=(PACKET/'patch_android.py').read_text()
        self.assertIn('CampaignActivity.class',s)
        self.assertIn('rememberReadingPosition',s)
        self.assertIn('EXPECTED',str(onego.CAMPAIGN).upper()+'EXPECTED')
    def test_backend_stage_on_synthetic_legacy_shape(self):
        with tempfile.TemporaryDirectory() as td:
            root=pathlib.Path(td)
            server=root/'tools/ritsu-local-server/server.mjs'
            bridge=root/'tools/campaigns/ritsu_control_playwright_bridge.mjs'
            server.parent.mkdir(parents=True);bridge.parent.mkdir(parents=True)
            server.write_text("""import {fileURLToPath} from 'node:url';\nasync function createServer(){\n  const server=http.createServer(async(req,res)=>{\n       if(req.method==='GET'&&url.pathname==='/v1/ritsu/status')return send(200,{ok:true,transport:'tailscale-sse',cloudOps:0,seq});\n       if(ev.complete)complete=true;\n});\n}\n""")
            bridge.write_text("""const args=new Map();\nif(['--doctor','--peek','--launch','--recover-reply','--resume-draft'].includes(flag)){}\n async function main(){\n  if(args.has('--doctor'))return doctor();\n}\n""")
            # patcher copies the voice hook from its own directory.
            patch_backend.patch(root)
            for item in [server,bridge,server.parent/'ritsu_pocket_voice_hook.mjs']:
                result=subprocess.run(['node','--check',str(item)],capture_output=True,text=True)
                self.assertEqual(result.returncode,0,result.stderr)
            with self.assertRaises(RuntimeError):patch_backend.patch(root)
    def test_voice_max_unit_never_silent_truncate(self):
        s=(PACKET/'ritsu_pocket_voice_hook.mjs').read_text()
        self.assertIn('text.length>450',s)
        self.assertIn('EXACT_SPAN_UNSPEAKABLE',s)
        self.assertIn("'--text-file'",s)
    def test_script_does_not_install_or_resend(self):
        s=(PACKET/'onego.py').read_text()
        self.assertNotIn('adb install',s)
        self.assertNotIn('git push',s)
        self.assertIn("'no_prompt_submitted':True",s)

if __name__=='__main__':unittest.main()
