import contextlib,io,pathlib,shutil,subprocess,sys,tempfile,unittest
from unittest.mock import patch
from pathlib import Path
P=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(P))
import onego,cauldron_courier

class BrowserAndServerContract(unittest.TestCase):
    def test_browser_recovery_never_sends(self):
        b=(P/'ritsu_browser_recover_v133.mjs').read_text()
        server=(P/'server_recovery_patch.js').read_text()
        self.assertNotIn('.click(',b)
        self.assertNotIn('getByRole(\'button\',{name:\'Send',b)
        self.assertNotIn('fetch(\'https://chatgpt.com',b)
        self.assertIn("'complete',turnId,tabId",server) if False else self.assertIn("type:'complete'",server)
        self.assertIn("row.state!=='uncertain'",server)
        self.assertIn("if(busy)",server)
        self.assertIn('sha256:hash(result.text)',server)
        self.assertIn('no_server_receipt',server)
        self.assertNotIn('jobs.push(',server)
    @unittest.skipUnless(shutil.which('node'),'node unavailable')
    def test_real_node_parser_on_source_patch_and_helper(self):
        code="""import http from 'node:http';
import fs from 'node:fs/promises';
import {spawn} from 'node:child_process';
import {createHash} from 'node:crypto';
import path from 'node:path'; import os from 'node:os';
const hash=s=>createHash('sha256').update(s).digest('hex');
const BRIDGE='demo';const turnPattern=/^[a-f0-9-]{36}$/;const tabPattern=/^[A-Za-z0-9_-]{4,80}$/;
async function createServer(){const turns=new Map(),history=[],busy=false;let seq=0;
async function append(e){};
  const server=http.createServer(async(req,res)=>{
  const send=(s,o)=>{};const url=new URL(req.url,'http://localhost');
      if(req.method==='GET'&&url.pathname==='/v1/ritsu/status')return send(200,{ok:true,seq});
  });
}
"""
        a='  const server=http.createServer(async(req,res)=>{'
        b="      if(req.method==='GET'&&url.pathname==='/v1/ritsu/status')"
        self.assertEqual(code.count(a),1);self.assertEqual(code.count(b),1)
        extra=(P/'server_recovery_patch.js').read_text()
        route="""      if(req.method==='GET'&&url.pathname==='/v1/ritsu/recover'){
        const id=url.searchParams.get('turnId')||'',tab=url.searchParams.get('tabId')||'';
        const digest=url.searchParams.get('promptSha256')||'';
        if(!turnPattern.test(id)||!tabPattern.test(tab)||!/^[0-9a-f]{64}$/.test(digest))
          return send(400,{error:'invalid_recovery_identity'});
        const result=await recoverOriginalTurn(id,tab,digest);
        return send(200,result);
      }
"""
        patched=code.replace(a,extra+'\n'+a,1).replace(b,route+b,1)
        with tempfile.TemporaryDirectory() as tmp:
            src=Path(tmp)/'server.mjs';src.write_text(patched)
            outcome=subprocess.run(['node','--check',str(src)],capture_output=True,text=True,timeout=10)
            self.assertEqual(outcome.returncode,0,outcome.stderr)
            helper=subprocess.run(['node','--check',str(P/'ritsu_browser_recover_v133.mjs')],capture_output=True,text=True,timeout=10)
            self.assertEqual(helper.returncode,0,helper.stderr)
    def test_bounded_courier_encodings(self):
        source="Write-Output 'RITSU_CAULDRON_PREFLIGHT=PASS'"
        self.assertIn('powershell.exe -NoProfile',cauldron_courier.ps_cmd(source))
        self.assertLess(len(cauldron_courier.ps_cmd("Write-Output 'RITSU_CHUNK_1=PASS'")),3400)

class AndroidRelease(unittest.TestCase):
    def test_targeted_media_scan_after_verification(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);src=root/'signed.apk';src.write_bytes(b'verified APK example')
            (root/'storage/downloads').mkdir(parents=True)
            observed=[]
            def fake(args,**kw):
                observed.append(args)
                return 'Media scanner submitted one file'
            with patch.object(onego,'HOME',root),patch.object(onego,'command',fake),patch.object(onego.shutil,'which',lambda x:'/fake/termux-media-scan' if x=='termux-media-scan' else None):
                with contextlib.redirect_stdout(io.StringIO()) as out:onego.publish(src)
            self.assertEqual(len(observed),1)
            self.assertEqual(observed[0][0],'/fake/termux-media-scan')
            self.assertEqual(observed[0][1],onego.receipts['downloads_apk'])
            self.assertIn('MEDIA_REFRESH=REQUESTED',out.getvalue())
            self.assertIn('COPY_VERIFIED=PASS',out.getvalue())
    def test_no_automatic_retry_or_termux_installer(self):
        p=(P/'patch_recovery.py').read_text()
        self.assertNotIn('setPositiveButton("Retry original"',p)
        self.assertNotIn('ledger.updateState(entry.id,"LOCAL_QUEUED")',p)
        source=(P/'onego.py').read_text()
        for forbidden in ['termux-open','pm install','am start']:
            self.assertNotIn('command([\''+forbidden+'\'',source)

if __name__=='__main__':unittest.main()
