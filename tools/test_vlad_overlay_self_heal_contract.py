#!/usr/bin/env python3
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
text=(ROOT/'tools/vlad_swarm_daemon.py').read_text(encoding='utf-8')
required=['def ensure_operator_overlay(', 'recover_adam_overlay_phone.sh', 'operator.overlay.recovery', 'content query --uri']
for token in required:
    assert token in text, f'missing self-heal token: {token}'
print('Vlad overlay self-heal contract: PASS')
