#!/usr/bin/env python3
from __future__ import annotations
import json, os, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'tools/home_center_ssh.py'

with tempfile.TemporaryDirectory() as td:
    td = Path(td)
    cfg = td / 'ssh-targets.json'
    cfg.write_text(json.dumps({
        'schema':'home-center-ssh-targets-v1',
        'targets':{
            'box':{
                'host':'10.0.0.7',
                'user':'drew',
                'port':2222,
                'identityFile':'~/.ssh/test_key',
                'connectTimeoutSeconds':7,
                'commandTimeoutSeconds':30,
                'options':['IdentitiesOnly=yes']
            }
        }
    }), encoding='utf-8')
    env = dict(os.environ, HC_SSH_CONFIG=str(cfg), HC_SSH_STATE=str(td/'state'))
    p = subprocess.run([sys.executable, str(SCRIPT), 'argv', 'box', 'printf ok'], env=env, text=True, capture_output=True)
    assert p.returncode == 0, p.stderr
    out = p.stdout.strip()
    for needle in ['ssh ', '-p 2222', 'BatchMode=yes', 'ConnectTimeout=7', 'IdentitiesOnly=yes', 'drew@10.0.0.7', "'printf ok'"]:
        assert needle in out, (needle, out)
    p = subprocess.run([sys.executable, str(SCRIPT), 'targets'], env=env, text=True, capture_output=True)
    assert p.returncode == 0
    assert json.loads(p.stdout) == ['box']
print('PASS home-center-ssh contract')
