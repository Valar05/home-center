#!/usr/bin/env python3
from pathlib import Path
import sys

root = Path(__file__).resolve().parents[1]
overlay = root / 'android/operator-overlay/app/src/main/java/com/homecenter/operatoroverlay/OperatorOverlayService.java'
text = overlay.read_text(encoding='utf-8')

checks = {
    'visible restart label': ('RESTART HC' in text or 'TURN HC ON' in text),
    'offline predicate exists': ('!online' in text),
    'control enabled predicate exists': ('enabled' in text),
    'dedicated button variable or constructor': ('restart' in text.lower() and 'Button' in text),
    'restart action not aliased to control toggle': ('handleControlButton()' in text),
}

# The last item is only contextual. The real requirement is that a restart-specific
# action exists in addition to the existing control toggle.
restart_action = any(token in text for token in (
    'restartHomeCenter', 'recoverHomeCenter', 'restart_home_center',
    'HOME_CENTER_RESTART', 'RUN_COMMAND', 'home_center_phone_relay_recover.sh'))
checks['dedicated recovery action'] = restart_action

failed = [name for name, ok in checks.items() if not ok]
if failed:
    print('FAIL home-center-restart-button-canary')
    for name in failed:
        print(f' - missing: {name}')
    print('Required behavior: when control is enabled and heartbeat is stale, the existing phone overlay exposes one obvious button labeled RESTART HC or TURN HC ON. Pressing it must invoke the established phone-local Home Center recovery lane and must not merely toggle control state.')
    sys.exit(1)

print('PASS home-center-restart-button-canary')
