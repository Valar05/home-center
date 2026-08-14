#!/usr/bin/env python3
import json, os, subprocess, sys, tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
KERNEL=ROOT/'tools/fortress_phone_kernel.py'

def run(home,*args):
    env=dict(os.environ,HOME=str(home),FORTRESS_HOME_CENTER=str(ROOT))
    return subprocess.run([sys.executable,str(KERNEL),*args],env=env,text=True,capture_output=True,check=False)

with tempfile.TemporaryDirectory() as td:
    home=Path(td)
    p=run(home,'status'); assert p.returncode==0,p.stderr
    s=json.loads(p.stdout); assert s['offlineFirst'] is True
    assert s['ollama']['enabled'] is False
    p=run(home,'enqueue','local','fortress-prompt',json.dumps({'prompt':'fortress status'})); assert p.returncode==0,p.stderr
    jid=json.loads(p.stdout)['id']; assert jid
    p=run(home,'tick'); assert p.returncode==0,p.stderr
    s=json.loads(run(home,'status').stdout); assert s['counts'].get('done')==1,s
    p=run(home,'enqueue','ollama','anything','{}'); assert p.returncode!=0
print('fortress phone kernel tests: ok')
