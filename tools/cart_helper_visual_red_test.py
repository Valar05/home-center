#!/data/data/com.termux/files/usr/bin/python3
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "tools" / "visual_evidence" / "cart_helper_accessibility_restricted_20260620_161324.json"
failures = []

def require(condition, message):
    if not condition:
        failures.append(message)

artifact = json.loads(EVIDENCE.read_text())
shot = Path(artifact["capturePath"])
main = (ROOT / "app/src/main/java/com/dclar/homecenter/MainActivity.java").read_text()
regression = (ROOT / "tools/home_center_regression_tests.py").read_text()

require(shot.exists(), f"missing fresh screenshot evidence: {shot}")
require(artifact["assertions"].get("controlledByRestrictedSettingVisible") is True,
        "red evidence must record Controlled by Restricted Setting visible")
require("Controlled by Restricted Setting" in artifact["actualVisibleRead"],
        "red evidence must name the visible restricted-setting failure")
require("isCartHelperEnabled" in main, "MainActivity must detect whether cart helper is actually enabled")
require("Manual Add" in main, "Cart Review must expose a Manual Add fallback")
require("Android restricted settings may block cart automation" in main,
        "Attempt Add must explain restricted-setting fallback instead of pretending automation can be enabled")
require("cart_helper_visual_red_test.py" in regression,
        "main regression harness must include this visual red test")

if failures:
    print("Cart helper visual red test failed:", file=sys.stderr)
    for failure in failures:
        print(f"- {failure}", file=sys.stderr)
    sys.exit(1)

print("Cart helper visual red test: OK")
