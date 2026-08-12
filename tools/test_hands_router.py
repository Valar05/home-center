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
  steps=[{'op':'phone.observe','args':{}},{'op':'phone.home','args':{},'expect':{'rc':0}}]
  j=hr.enqueue('vlad','primary-phone',steps,max_runtime=30); assert hr.verify(j) and hr.validate(j) is None
  bad=dict(j); bad['steps']=[{'op':'agent.look_and_decide','args':{}}]; assert hr.validate(bad).startswith('invalid_step')
  tampered=dict(j); tampered['target']='other'; assert not hr.verify(tampered)
  deadly=hr.enqueue('venice','THECAULDRON',[{'op':'shell.exec','args':{'command':'rm -rf /'}}]); assert hr.dispatch(deadly)['status']=='blocked'
  hr.set_enabled(False); safe=hr.enqueue('venice','primary-phone',[{'op':'phone.home','args':{}}]); assert hr.dispatch(safe)['status']=='paused'
  hr.set_enabled(True)
  os.environ['HC_HANDS_SSH_DISPATCH']='false'; os.environ['HC_HANDS_WLAN_DISPATCH']='true'; os.environ['HC_HANDS_COMPUTER_DISPATCH']='false'
  routed=hr.enqueue('vlad','THECAULDRON',[{'op':'system.status','args':{}}]); rr=hr.dispatch(routed); assert rr['status']=='completed' and rr['transport']=='wlan'
  try: hr.enqueue('vlad','THECAULDRON',[{'op':'system.status','args':{}}]*(hr.MAX_STEPS+1)); raise AssertionError('unbounded job accepted')
  except ValueError as e: assert 'too_many_steps' in str(e)
  print(json.dumps({'ok':True,'tests':['finite operation vocabulary','agent loop rejected','signed spool','tamper rejection','objective harm block','toggle pause','ssh-to-wlan fallback','step bound']}))
 return 0
if __name__=='__main__': raise SystemExit(main())
