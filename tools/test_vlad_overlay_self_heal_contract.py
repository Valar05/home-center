#!/usr/bin/env python3
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
daemon=(ROOT/'tools/vlad_swarm_daemon.py').read_text(encoding='utf-8')
recovery=(ROOT/'tools/recover_adam_overlay_phone.sh').read_text(encoding='utf-8')
service=(ROOT/'android/operator-overlay/app/src/main/java/com/homecenter/operatoroverlay/OperatorOverlayService.java').read_text(encoding='utf-8')

for token in ['def ensure_operator_overlay(', 'recover_adam_overlay_phone.sh', 'operator.overlay.recovery', 'content query --uri']:
    assert token in daemon, f'missing self-heal token: {token}'

for token in ['com.homecenter.operatoroverlay.RESTORE', 'overlay_hidden=0', 'control_enabled=0', 'start_and_restore_overlay']:
    assert token in recovery, f'missing explicit visible-recovery token: {token}'

assert 'control_enabled=1' not in recovery, 'recovery must never remotely enable control'
assert 'ACTION_RESTORE' in service, 'recovery must inherit the canonical overlay RESTORE action'
assert 'setControlEnabled(this, false)' in service, 'RESTORE must fail closed with control disabled'

print('Vlad overlay self-heal contract: PASS')
