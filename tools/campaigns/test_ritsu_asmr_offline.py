#!/usr/bin/env python3
"""Offline, dependency-free contract tests. Never contact Pocket or relay."""
import hashlib, importlib.util, io, json, tempfile, wave
from pathlib import Path
MODULE=Path(__file__).with_name('ritsu_asmr_windows.py')
spec=importlib.util.spec_from_file_location('ritsu_as',MODULE)
r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)
def wav(text):
 buffer=io.BytesIO()
 with wave.open(buffer,'wb') as w:
  w.setnchannels(1);w.setsampwidth(2);w.setframerate(24000);w.writeframes(b'\0\0'*2400)
 return buffer.getvalue()
def test_phone_remote_gate():
 src=Path(__file__).with_name('ritsu_asmr_phone.py')
 spec=importlib.util.spec_from_file_location('ritsu_as_phone',src)
 phone=importlib.util.module_from_spec(spec);spec.loader.exec_module(phone)
 accepted=[
  'https://github.com/Valar05/home-center',
  'https://github.com/Valar05/home-center.git',
  'git@github.com:Valar05/home-center.git',
  'ssh://git@github.com/Valar05/home-center.git']
 rejected=[
  'https://github.com/Valar05/home-center-evil',
  'https://github.com/not-valar05/home-center.git',
  'https://evil.github.com/Valar05/home-center.git',
  'https://github.com/Valar05/home-center.git.evil',
  'https://user:token@github.com/Valar05/home-center.git']
 assert all(phone.is_canonical_origin(x) for x in accepted), 'Canonical GitHub remote falsely rejected'
 assert not any(phone.is_canonical_origin(x) for x in rejected), 'Spoofed GitHub remote accepted'
def test_remote_success_gate():
 src=Path(__file__).with_name('ritsu_asmr_phone.py')
 spec=importlib.util.spec_from_file_location('ritsu_as_phone_status',src)
 phone=importlib.util.module_from_spec(spec);spec.loader.exec_module(phone)
 from unittest.mock import patch
 from types import SimpleNamespace
 def fake(returncode,output):
  return SimpleNamespace(returncode=returncode,stdout=output)
 with patch.object(phone.subprocess,'run',return_value=fake(0,'RITSU_ASMR_REMOTE_OK=1\n')):
  assert 'RITSU_ASMR_REMOTE_OK=1' in phone.ps('Write-Output 1')
 for code,output in [(0,'{"phase": "blocked"}\n'),(255,'RITSU_ASMR_REMOTE_OK=1\n')]:
  with patch.object(phone.subprocess,'run',return_value=fake(code,output)):
   try:phone.ps('Write-Output 1')
   except RuntimeError:pass
   else:raise AssertionError('Invalid Windows operation response accepted')
def test_watchdog_guard():
 from unittest.mock import patch
 with patch.object(r,'inspect_watchdog',return_value={'taskPresent':False}):
  try:r.recover_watchdog()
  except RuntimeError as e:assert 'WATCHDOG_TASK_MISSING' in str(e)
  else:raise AssertionError('Missing watchdog should block recovery')
 with patch.object(r,'inspect_watchdog',return_value={'taskPresent':True,'listenerPids':[],'relatedProcesses':[{'pid':42}],'taskState':'Ready'}):
  try:r.recover_watchdog()
  except RuntimeError as e:assert 'PROCESS_ALREADY_PRESENT' in str(e)
  else:raise AssertionError('Existing Pocket process should block duplicate recovery')
def test_scheduler_and_frames():
 import base64
 from unittest.mock import patch
 from types import SimpleNamespace
 with patch.object(r.subprocess,'run',return_value=SimpleNamespace(returncode=0,stdout='{"taskState":"Running","workerPids":[123]}',stderr='')) as call:
  active,row=r.worker_active('CANARY')
  assert active and row['workerPids']==[123]
  command=call.call_args.args[0][-1]
  assert 'TASK_IDENTITY_MISMATCH' in command and 'Get-CimInstance' in command
 with patch.object(r,'task_command',return_value={'taskState':'Missing','workerPids':[]}):
  with tempfile.TemporaryDirectory() as td,patch.object(r,'RUNS',Path(td)):
   f=r.folder_for('CANARY');f.mkdir();r.state(f,phase='launched',pid=21552)
   assert r.status_report('CANARY')['phase']=='abandoned'
 src=Path(__file__).with_name('ritsu_asmr_phone.py')
 spec=importlib.util.spec_from_file_location('ritsu_as_phone_frame',src)
 phone=importlib.util.module_from_spec(spec);spec.loader.exec_module(phone)
 obj={'phase':'rendered_not_delivered','wavPath':r'C:\Users\dclar\some.wav','durationSeconds':15.2}
 payload=json.dumps(obj).encode()
 encoded=base64.b64encode(payload).decode()
 digest=hashlib.sha256(payload).hexdigest().upper()
 lines=['JSTART:'+str(len(encoded))]
 lines+=['J:%05d:%s'%(i//16,encoded[i:i+16]) for i in range(0,len(encoded),16)]
 lines+=['H:%d:%s'%(i//16,digest[i:i+16]) for i in range(0,64,16)]
 output='\r\n'.join('\x1b[0m'+line+'  ' for line in lines)
 assert phone.extract_result(output+'\r\nRITSU_ASMR_REMOTE_OK=1\r\n')==obj
 for bad in (lines[:2]+lines[3:], lines+[lines[1]],lines[:-1]+['H:3:'+'0'*16]):
  try:phone.extract_result('\n'.join(bad))
  except RuntimeError:pass
  else:raise AssertionError('Corrupt/incomplete/duplicate frame accepted')

def test_fetch_resume():
 import base64
 from unittest.mock import patch
 src=Path(__file__).with_name('ritsu_asmr_phone.py')
 spec=importlib.util.spec_from_file_location('ritsu_as_phone_fetch',src)
 phone=importlib.util.module_from_spec(spec);spec.loader.exec_module(phone)
 audio=wav('sample');digest=phone.sha(audio)
 def frames(obj):
  data=json.dumps(obj).encode();coded=base64.b64encode(data).decode();h=phone.sha(data)
  return '\r\n'.join(['JSTART:'+str(len(coded))]+['J:%05d:%s'%(i//16,coded[i:i+16]) for i in range(0,len(coded),16)]+['H:%d:%s'%(i//16,h[i:i+16]) for i in range(0,64,16)]+['RITSU_ASMR_REMOTE_OK=1'])
 with tempfile.TemporaryDirectory() as td:
  home=Path(td);state=home/'state';state.mkdir()
  folder=home/'storage/downloads/RitsuASMR';folder.mkdir(parents=True)
  partial=folder/('CANARY.'+digest+'.partial')
  final=folder/'CANARY.wav'
  partial.write_bytes(audio[:1000])
  receipt={'phase':'rendered_not_delivered','episodeId':'CANARY','wavSha256':digest,'bytes':len(audio),'voiceSha256':r.VOICE_SHA}
  calls=[]
  def read(ep,size,offset,count,prefix=False):
   calls.append((offset,count,prefix))
   return phone.sha(audio[offset:offset+count]) if prefix else audio[offset:offset+count]
  with patch.object(phone,'STATE',state),patch.object(phone.Path,'home',return_value=home),patch.object(phone,'remote_run',return_value=frames(receipt)),patch.object(phone,'wav_read',side_effect=read):
   partial.write_bytes(b'X'*1000)
   try:phone.fetch_wav('commit','hash','CANARY')
   except RuntimeError as e:assert 'prefix does not match' in str(e)
   else:raise AssertionError('Corrupt partial accepted')
   assert partial.read_bytes()==b'X'*1000 and not final.exists()
   partial.write_bytes(audio[:1000]);calls.clear()
   result=phone.fetch_wav('commit','hash','CANARY')
   assert calls==[(0,1000,True),(1000,len(audio)-1000,False)]
   assert result['phase']=='delivered_to_phone_not_heard' and final.read_bytes()==audio and not partial.exists()
   calls.clear();phone.fetch_wav('commit','hash','CANARY');assert calls==[]
  data=audio[:500]
  with patch.object(phone,'STATE',state),patch.object(phone,'ps',return_value=frames({'offset':0,'count':500,'data':base64.b64encode(data).decode()})):
   assert phone.wav_read('CANARY',len(audio),0,500)==data
def test_taildrop():
 from unittest.mock import patch
 src=Path(__file__).with_name('ritsu_asmr_phone.py')
 spec=importlib.util.spec_from_file_location('ritsu_as_phone_taildrop',src)
 phone=importlib.util.module_from_spec(spec);spec.loader.exec_module(phone)
 audio=wav('canary');digest=phone.sha(audio)
 remote={'phase':'rendered_not_delivered','episodeId':'CANARY','wavSha256':digest,'bytes':len(audio),'voiceSha256':r.VOICE_SHA}
 sent={'phase':'taildrop_sent_not_verified','episodeId':'CANARY','device':phone.TAILDROP_DEVICE,'wavSha256':digest,'bytes':len(audio)}
 with tempfile.TemporaryDirectory() as td:
  home=Path(td);state=home/'state';state.mkdir()
  downloads=home/'storage/downloads';downloads.mkdir(parents=True)
  target=downloads/'CANARY.wav'
  with patch.object(phone,'STATE',state),patch.object(phone.Path,'home',return_value=home),patch.object(phone,'rendered_identity',return_value=(remote,digest,len(audio))),patch.object(phone,'ps',return_value='framed') as send,patch.object(phone,'extract_result',return_value=sent):
   result=phone.drop_wav('commit','hash','CANARY')
   assert result==sent and result['phase']!='delivered_to_phone_not_heard'
   script=send.call_args.args[0]
   assert 'file cp' in script and phone.TAILDROP_IP+':' in script and phone.TAILDROP_DEVICE in script
   assert 'Get-FileHash' in script and 'taildrop_dispatch_uncertain' in script
   assert 'Peer.PSObject.Properties.Value' in script and 'TailscaleIPs' in script
   assert 'if((Test-Path -LiteralPath $ledger) -and !$false)' in script
   try:phone.verify_wav('commit','hash','CANARY')
   except RuntimeError:pass
   else:raise AssertionError('Missing received audio accepted')
   target.write_bytes(b'x'*len(audio))
   try:phone.verify_wav('commit','hash','CANARY')
   except RuntimeError:pass
   else:raise AssertionError('Corrupt received audio accepted')
   target.write_bytes(audio)
   assert phone.verify_wav('commit','hash','CANARY')['phase']=='delivered_to_phone_not_heard'
   assert phone.verify_wav('commit','hash','CANARY',target)['path']==str(target)
def test():
 test_taildrop()
 test_fetch_resume()
 test_scheduler_and_frames()
 test_watchdog_guard()
 test_phone_remote_gate()
 test_remote_success_gate()
 expected=[('speech','Hello there.'),('pause',1500),('speech','Good rest.')]
 assert r.parse('Hello there.\n\n[Pause:1500]\n\nGood rest.')==expected
 for value in ('x'*451,'[Explosive thunder]','[Pause:31000]'):
  try:r.parse(value)
  except ValueError:pass
  else:raise AssertionError('Invalid transcript accepted: '+value[:20])
 with tempfile.TemporaryDirectory() as d:
  r.RUNS=Path(d)
  r.check_api=lambda:{'engine':'pocket-tts','model':'loaded'}
  calls=[]
  def fake(text):calls.append(text);return wav(text)
  r.synth=fake
  f=r.folder_for('CANARY');f.mkdir()
  data='Hello there.\n\n[Pause:1000]\n\nGood rest.'.encode()
  (f/'transcript.txt').write_bytes(data)
  r.atomic(f/'request.json',{'textSha256':r.sha(data)})
  r.render('CANARY')
  receipt=json.loads((f/'receipt.json').read_text())
  assert calls==['Hello there.','Good rest.']
  assert receipt['durationSeconds']==1.2
  assert receipt['voiceSha256']==r.VOICE_SHA
  assert r.sha((f/'CANARY.wav').read_bytes())==receipt['wavSha256']
  assert not (f/'STOP').exists()
 print('RITSU_ASMR_TEST=PASS parse/reject/voice-identity/cache/PCM-duration/receipt')
if __name__=='__main__':test()
