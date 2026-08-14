#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "tools" / "android_chromium_control.py"
SHELL = ROOT / "tools" / "fortress_phone_ops.sh"
STATE = ROOT / "android/operator-overlay/app/src/main/java/com/homecenter/operatoroverlay/OperatorState.java"

fake_bridge = types.ModuleType("android_phone_hands_bridge")
fake_bridge.run_rish = lambda command, timeout=20: ""
fake_bridge.ui_dump = lambda: ""
sys.modules["android_phone_hands_bridge"] = fake_bridge

spec = importlib.util.spec_from_file_location("android_chromium_control", SOURCE)
assert spec and spec.loader
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

# Pure input contract.
assert mod.validate_url("https://example.com/path?q=1") == "https://example.com/path?q=1"
for bad in ["", "example.com", "file:///tmp/x", "javascript:alert(1)", "chrome://flags"]:
    try:
        mod.validate_url(bad)
    except ValueError:
        pass
    else:
        raise AssertionError(f"unsafe/non-http URL accepted: {bad!r}")

# Package selection is bounded to known Chromium-family packages.
seen = []
mod.package_present = lambda package: seen.append(package) is None and package == "com.chrome.beta"
assert mod.resolve_package() == "com.chrome.beta"
assert seen == ["com.android.chrome", "com.chrome.beta"]

# URL launch is shell-quoted and success requires observed browser state, not am-start alone.
commands = []
mod.resolve_package = lambda: "com.android.chrome"
mod.rish = lambda command, timeout=20: commands.append(command) or "Status: ok"
mod.snapshot = lambda package, expected_url=None: {
    "packageForeground": True,
    "stateObserved": True,
    "screenSha256": "a" * 64,
    "uiSha256": "b" * 64,
}
mod.persist = lambda value, path=mod.LAST_RECEIPT: None
attack_url = "https://example.com/a'b?x=1"
opened = mod.open_url(attack_url)
assert opened["ok"] is True
assert opened["requestedUrl"] == attack_url
launch_command = next(command for command in commands if command.startswith("am start -W"))
assert "-p com.android.chrome" in launch_command
assert "'\"'\"'" in launch_command, "apostrophe was not shell-escaped"

# A launch with no independent observed browser state must fail closed.
mod.snapshot = lambda package, expected_url=None: {"packageForeground": True, "stateObserved": False}
failed = mod.open_url("https://example.com/")
assert failed["ok"] is False

# Canary contract must include browser-death recovery and two explicit transitions.
mod.force_stop = lambda: {"ok": True, "operation": "force-stop"}
mod.open_url = lambda url, operation="open": {
    "ok": True,
    "operation": operation,
    "package": "com.android.chrome",
    "requestedUrl": url,
    "observation": {"screenSha256": "1" * 64},
}
mod.navigate = lambda url: {
    "ok": True,
    "operation": "navigate",
    "package": "com.android.chrome",
    "requestedUrl": url,
    "observation": {"screenSha256": "2" * 64},
}
mod.snapshot = lambda package, expected_url=None: {"stateObserved": True, "packageForeground": True}
canary = mod.canary()
assert canary["ok"] is True
assert canary["acceptance"] == {
    "browserWasForceStopped": True,
    "reopenedAfterDeath": True,
    "secondExplicitNavigationObserved": True,
    "finalChromiumStateObserved": True,
}
assert canary["screenHashChangedAcrossTransitions"] is True
assert canary["firstTransition"]["requestedUrl"] != canary["secondTransition"]["requestedUrl"]

shell = SHELL.read_text(encoding="utf-8")
state = STATE.read_text(encoding="utf-8")
for token in [
    "android_chromium_control.py",
    "chrome-open-b64",
    "chrome-navigate-b64",
    "chrome-back",
    "exec python3 \"$CHROMIUM\" canary",
]:
    assert token in shell, f"phone ops missing {token}"
for token in [
    "encodedUrlCommand",
    "Base64.NO_WRAP",
    '"chrome-open"',
    '"chrome-navigate"',
    'key.equals("back")',
    'key.equals("chrome canary")',
]:
    assert token in state, f"overlay alias compiler missing {token}"

print("Android Chromium deterministic control contract: PASS")
