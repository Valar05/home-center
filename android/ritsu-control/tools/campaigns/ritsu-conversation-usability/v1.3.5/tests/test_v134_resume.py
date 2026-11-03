import hashlib,io,sys,tempfile,unittest
from pathlib import Path
from unittest import mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import cauldron_courier as courier
import onego
P=Path(__file__).resolve().parents[1]

class ResumableWindowsRepair(unittest.TestCase):
 def run_fake(self,has_route_after_apply,has_route_before=False):
  calls=[]
  def fake(label,script,seconds=50):
   n=len(courier.ps_cmd(script));self.assertLessEqual(n,3400,(label,n));calls.append(label)
   if label=='READ_ONLY_ENDPOINT_PROBE':
    good=has_route_before or (has_route_after_apply and 'APPLY' in calls)
    return 'RITSU_RECOVERY_ROUTE=VERIFIED' if good else 'RECOVERY_PROBE=ERROR_WebException'
   if label=='CATALOG_ROUTE_PROBE':
    return 'CATALOG_PROBE_HTTP=200' if (has_route_before or (has_route_after_apply and 'APPLY' in calls)) else 'CATALOG_PROBE_HTTP=404'
   if label=='PREFLIGHT':return 'RITSU_CAULDRON_PREFLIGHT=PASS'
   if label.isdigit():return 'RITSU_CHUNK_'+label+'=PASS'
   if label=='EXTRACT':return 'RITSU_REMOTE_ZIP_EXTRACTED=PASS'
   if label.startswith('VERIFY_FILE_'):return 'RITSU_EXTRACTED_'+label.rsplit('_',1)[1]+'=PASS'
   if label=='READBACK_WINDOWS_PHASE':return 'RITSU_APPLY_LAUNCH=STARTED\nWINDOWS_PHASE=PRECHECK\nRITSU_WINDOWS_BLOCKED=ACTIVE_RITSU_SERVER_COUNT_0'
   if label=='APPLY':
    self.assertIn('[ScriptBlock]::Create',script)
    self.assertNotIn('ExecutionPolicy Bypass',script)
    return ''
   return ''
  with mock.patch.object(courier,'invoke',fake):
   try:result=courier.apply(P,lambda x:None)
   except courier.RemoteBlocked as e:result='BLOCKED:'+str(e)
  return result,calls
 def test_preexisting_operational_skips_transfer_and_restart(self):
  v,called=self.run_fake(False,True)
  self.assertEqual(v,'WINDOWS_RECOVERY_ENDPOINT_VERIFIED_EXISTING')
  self.assertEqual(called,['READ_ONLY_ENDPOINT_PROBE','CATALOG_ROUTE_PROBE'])
 def test_missing_apply_output_reconciled_by_endpoint(self):
  v,called=self.run_fake(True)
  self.assertEqual(v,'WINDOWS_RECOVERY_ENDPOINT_VERIFIED')
  self.assertEqual(called.count('APPLY'),1)
  self.assertEqual(called.count('READ_ONLY_ENDPOINT_PROBE'),2)
  self.assertEqual(called.count('CATALOG_ROUTE_PROBE'),1)
 def test_missing_live_endpoint_reports_exact_remote_phase(self):
  v,called=self.run_fake(False)
  self.assertIn('ACTIVE_RITSU_SERVER_COUNT_0',v)
  self.assertIn('BLOCKED:',v)
  self.assertEqual(called.count('APPLY'),1)
 def test_script_does_not_use_ps1_file_invocation(self):
  s=(P/'cauldron_courier.py').read_text()
  self.assertIn('[ScriptBlock]::Create',s)
  self.assertNotIn('exit $LASTEXITCODE',s)
  self.assertIn('READBACK_WINDOWS_PHASE',s)
  self.assertIn('READ_ONLY_ENDPOINT_PROBE',s)
 def test_exact_previous_code24_signature_is_pinned(self):
  self.assertEqual(onego.CODE24_SHA,'0b3c4adc67576f5390ddf6af2bcbfb16b17f8b118f2e21a5dfba203fb8eb802b')
  self.assertIn('reused_code24_sha256',Path(onego.__file__).read_text())
  self.assertNotIn('build_sign(staged,sign)\n        stage(',Path(onego.__file__).read_text())
 def test_failure_does_not_prevent_verified_file_publication(self):
  src=Path(onego.__file__).read_text()
  self.assertLess(src.index('publish(signed)'),src.index('cauldron_courier.apply(PACKET,say)'))
  self.assertIn('APK_PUBLISHED_BACKEND_NOT_VERIFIED',src)
  self.assertIn('termux-media-scan',src)
