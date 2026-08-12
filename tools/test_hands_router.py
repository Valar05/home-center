#!/usr/bin/env python3
import importlib.util, json, os, tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parent
SPEC=importlib.util.spec_from_file_location('hands_router',ROOT/'hands_router.py'); hr=importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(hr)

def reset(tmp):
 hr.STATE=Path(tmp)/'state'; hr.KEY=Path(tmp)/'key'; hr.TOGGLE=hr.STATE/'enabled'; hr.QUEUE=hr.STATE/'queue'; hr.DONE=hr.STATE/'done'; hr.RECEIPTS=hr.STATE/'receipts.jsonl'

def main():
 with tempfile.TemporaryDirectory() as t:
  reset(t)
  j=hr.enqueue('vlad','primary-phone','observe',payload='{}'); assert hr.verify(j)
  assert not hr.objectively_harmful(j)
  bad=dict(j); bad['payload']='tampered'; assert not hr.verify(bad)
  deadly=hr.enqueue('venice','THECAULDRON','shell.exec',command='rm -rf /'); assert hr.objectively_harmful(deadly)
  r=hr.dispatch(deadly); assert r['status']=='blocked'
  hr.set_enabled(False); safe=hr.enqueue('venice','primary-phone','home'); assert hr.dispatch(safe)['status']=='paused'
  hr.set_enabled(True)
  os.environ['HC_HANDS_SSH_DISPATCH']='false'; os.environ['HC_HANDS_WLAN_DISPATCH']='true'; os.environ['HC_HANDS_COMPUTER_DISPATCH']='false'
  routed=hr.enqueue('vlad','THECAULDRON','status'); rr=hr.dispatch(routed); assert rr['status']=='completed' and rr['transport']=='wlan'
  print(json.dumps({'ok':True,'tests':['signed spool','tamper rejection','objective harm block','toggle pause','ssh-to-wlan fallback']}))
 return 0
if __name__=='__main__': raise SystemExit(main())
