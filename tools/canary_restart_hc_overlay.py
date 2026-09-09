#!/usr/bin/env python3
from pathlib import Path
import sys

root = Path(__file__).resolve().parents[1]
svc = root / 'android/operator-overlay/app/src/main/java/com/homecenter/operatoroverlay/OperatorOverlayService.java'
text = svc.read_text(encoding='utf-8')

checks = {
    'dedicated_restart_label': ('RESTART HC' in text or 'TURN HC ON' in text),
    'offline_condition': ('!online' in text and 'enabled' in text),
    'not_control_toggle_only': ('handleHomeCenterRestart' in text or 'restartHomeCenter' in text or 'ACTION_HOME_CENTER_RESTART' in text),
    'accessible_restart': ('Restart Home Center' in text or 'Turn Home Center on' in text),
}
failed = [k for k,v in checks.items() if not v]
print({'checks': checks, 'failed': failed})
raise SystemExit(1 if failed else 0)
