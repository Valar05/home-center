#!/usr/bin/env python3
import importlib.util
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
SPEC=importlib.util.spec_from_file_location('hands_overlay',ROOT/'hands_overlay.py')
mod=importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(mod)

def main():
 target,steps=mod.compile_command('hands phone home'); assert target=='primary-phone' and steps==[{'op':'phone.home','args':{}}]
 target,steps=mod.compile_command('hands phone uri https://example.com com.example.app'); assert target=='primary-phone' and steps[0]['op']=='phone.open_uri' and steps[0]['args']['package']=='com.example.app'
 target,steps=mod.compile_command('hands pc status'); assert target=='THECAULDRON' and steps[0]['op']=='system.status'
 try: mod.compile_command('hands phone wander around until you find it'); raise AssertionError('unbounded intent compiled')
 except ValueError: pass
 print(json.dumps({'ok':True,'tests':['phone alias','open URI primitive','computer alias','unbounded intent rejection']}))
 return 0
if __name__=='__main__': raise SystemExit(main())
