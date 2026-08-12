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
  steps=[{'op':'phone.observe','args':{}},{'op':'phone.home','args':{}}]
  j=hr.enqueue('vlad','primary-phone',steps,max_runtime=30); assert hr.verify(j) and hr.validate(j) is None
  bad=dict(j); bad['steps']=[{'op':'agent.look_and_decide','args':{}}]; assert hr.validate(bad).startswith('invalid_step')
  tampered=dict(j); tampered['target']='other'; assert not hr.verify(tampered)
  deadly=hr.enqueue('venice','THECAULDRON',[{'op':'shell.exec','args':{'command':'rm -rf /'}}]); assert hr.objectively_harmful(deadly)
  hr.set_enabled(False); safe=hr.enqueue('venice','primary-phone',[{'op':'phone.home','args':{}}]); assert hr.dispatch(safe)['status']=='paused'
  hr.set_enabled(True)

  # Fallback is allowed only when a transport explicitly proves nothing started.
  os.environ['HC_HANDS_SSH_DISPATCH']="printf '%s\\n' '{\"safeToFallback\":true,\"status\":\"unavailable\"}'; exit 78"
  os.environ['HC_HANDS_WLAN_DISPATCH']="printf '%s\\n' '{\"safeToFallback\":false,\"status\":\"completed\"}'"
  os.environ['HC_HANDS_COMPUTER_DISPATCH']='false'
  routed=hr.enqueue('vlad','THECAULDRON',[{'op':'system.status','args':{}}]); rr=hr.dispatch(routed)
  assert rr['status']=='completed' and rr['transport']=='wlan', rr

  # Once a transport may have executed anything, router must stop and never cascade.
  os.environ['HC_HANDS_SSH_DISPATCH']="printf '%s\\n' '{\"safeToFallback\":false,\"status\":\"failed\"}'; exit 9"
  os.environ['HC_HANDS_WLAN_DISPATCH']="printf '%s\\n' '{\"safeToFallback\":false,\"status\":\"completed\"}'"
  no_dupe=hr.enqueue('vlad','THECAULDRON',[{'op':'system.status','args':{}}]); nd=hr.dispatch(no_dupe)
  assert nd['status']=='failed' and nd['transport']=='ssh' and len(nd['attempts'])==1, nd

  try: hr.enqueue('vlad','THECAULDRON',[{'op':'system.status','args':{}}]*(hr.MAX_STEPS+1)); raise AssertionError('unbounded job accepted')
  except ValueError as e: assert 'too_many_steps' in str(e)
  print(json.dumps({'ok':True,'tests':['finite operation vocabulary','agent loop rejected','signed spool','tamper rejection','objective harm detection','toggle pause','explicit safe fallback','no fallback after possible execution','step bound']}))
 return 0
if __name__=='__main__': raise SystemExit(main())
