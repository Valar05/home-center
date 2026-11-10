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
def test():
 test_phone_remote_gate()
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
