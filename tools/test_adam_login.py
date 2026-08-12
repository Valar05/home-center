#!/usr/bin/env python3
import importlib.util
import json
import tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parent
HSPEC=importlib.util.spec_from_file_location('hands_router',ROOT/'hands_router.py')
hr=importlib.util.module_from_spec(HSPEC); HSPEC.loader.exec_module(hr)
LSPEC=importlib.util.spec_from_file_location('adam_login',ROOT/'adam_login.py')
login=importlib.util.module_from_spec(LSPEC); LSPEC.loader.exec_module(login)

def reset(tmp):
 hr.STATE=Path(tmp)/'state'; hr.KEY=Path(tmp)/'key'; hr.TOGGLE=hr.STATE/'enabled'; hr.QUEUE=hr.STATE/'queue'; hr.DONE=hr.STATE/'done'; hr.RECEIPTS=hr.STATE/'receipts.jsonl'
 login.hands=hr

def main():
 with tempfile.TemporaryDirectory() as t:
  reset(t)
  result=login.compile_login('https://example.com/login',ttl_seconds=90,max_attempts=1)
  job=result['job']
  assert result['ok'] is True and result['origin']=='https://example.com'
  assert job['producer']=='drew' and job['target']=='THECAULDRON' and hr.verify(job)
  assert len(job['steps'])==1 and job['steps'][0]['op']=='shell.exec'
  command=job['steps'][0]['args']['command']
  assert 'adam-autofill-login.ps1' in command
  assert 'password' not in command.lower() and 'cookie' not in command.lower()
  assert job['steps'][0]['expect']=={'ok':True}
  try:
   login.compile_login('http://example.com/login')
   raise AssertionError('insecure remote login URL accepted')
  except ValueError as exc:
   assert 'https' in str(exc).lower()
  print(json.dumps({'ok':True,'tests':['origin-bound login lease','explicit drew producer','bounded single Hands job','stable installed autofill executor','no plaintext credential in job','https requirement']}))
 return 0
if __name__=='__main__': raise SystemExit(main())
