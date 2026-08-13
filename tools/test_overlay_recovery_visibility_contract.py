#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
recovery = (ROOT / "tools" / "recover_adam_overlay_phone.sh").read_text(encoding="utf-8")
service = (ROOT / "android" / "operator-overlay" / "app" / "src" / "main" / "java" / "com" / "homecenter" / "operatoroverlay" / "OperatorOverlayService.java").read_text(encoding="utf-8")
menu = (ROOT / "tools" / "home_center_status_menu.sh").read_text(encoding="utf-8")

assert "com.homecenter.operatoroverlay.RESTORE" in recovery
assert "overlay_hidden=0" in recovery
assert "control_enabled=0" in recovery
assert "start_and_restore_overlay" in recovery
assert "control_enabled=1" not in recovery

assert "ACTION_RESTORE" in service
assert "setControlEnabled(this, false)" in service
assert "setOverlayHidden(this" in service

assert "b2='Overlay on'" in menu
assert "fortress-campaign overlay" in menu

print("OVERLAY_RECOVERY_VISIBILITY_CONTRACT=passed")
