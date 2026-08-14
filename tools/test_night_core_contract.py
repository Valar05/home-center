#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ops = (ROOT / "tools/fortress_phone_ops.sh").read_text(encoding="utf-8")
night = (ROOT / "tools/fortress_night_status.py").read_text(encoding="utf-8")
state = (ROOT / "android/operator-overlay/app/src/main/java/com/homecenter/operatoroverlay/OperatorState.java").read_text(encoding="utf-8")

for token in [
    'NIGHT_STATUS="$ROOT/tools/fortress_night_status.py"',
    'night_status()',
    'exec python3 "$NIGHT_STATUS"',
    'night-status|night|night-core',
]:
    assert token in ops, f"phone ops missing Night Core delegation: {token}"

night_body = ops[ops.index('night_status()'):ops.index('overlay_restart()', ops.index('night_status()'))]
for forbidden in ['dumpsys battery', 'android_chromium_control.py', 'screencap', 'ui_dump']:
    assert forbidden not in night_body, f"night-status wrapper regressed to expensive/unbounded edge: {forbidden}"

for token in [
    'fortress.night-core.status.v2',
    'termux-battery-status',
    '/sys/class/power_supply/battery',
    'rish-dumpsys',
    'subprocess.run(cmd, text=True, capture_output=True, timeout=timeout)',
    'CHARGE_RECOVERY',
    'POWERED_ACTIVE',
    'BATTERY_ACTIVE',
    'BATTERY_BALANCED',
    'BATTERY_CONSERVE',
    'recommendedPollSeconds',
    'heavyWorkAllowed',
    'no inference, Chromium screenshot, or UI dump',
]:
    assert token in night, f"Night Core implementation missing {token}"

assert 'return termux_battery() or sysfs_battery() or rish_battery()' in night
assert 'run([rish, "-c", "dumpsys battery"], 3)' in night
assert 'bash tools/fortress_phone_ops.sh night-status' in state
assert 'key.equals("night")' in state
print("Night Core bounded local battery policy contract: PASS")
