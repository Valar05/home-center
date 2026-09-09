#!/usr/bin/env python3
"""Regression test: Home Center background relay must not depend on Shizuku/rish."""

from __future__ import annotations

import builtins
import importlib.util
import os
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RELAY = ROOT / "tools" / "android_phone_home_center_relay.py"
FORBIDDEN_BASELINE_IMPORTS = {
    "android_phone_hands_bridge",
    "android_operator_overlay",
}


def main() -> None:
    source = RELAY.read_text(encoding="utf-8")

    if "overlay_heartbeat" in source:
        raise AssertionError(
            "relay baseline loop must not invoke operator-overlay/Shizuku heartbeat"
        )
    if "background_termux_shizuku_independent" not in source:
        raise AssertionError("relay must advertise the Shizuku-independent background lane")
    if '"baselineTransport": "termux-no-shizuku"' not in source:
        raise AssertionError("relay heartbeat must record the Shizuku-independent baseline")

    bash = shutil.which("bash")
    if not bash:
        raise AssertionError("bash is required for phone_shell regression test")
    os.environ["PREFIX"] = str(Path(bash).resolve().parent.parent)

    imported_optional: list[str] = []
    real_import = builtins.__import__

    def guarded_import(name, globals=None, locals=None, fromlist=(), level=0):
        root = name.split(".", 1)[0]
        if root in FORBIDDEN_BASELINE_IMPORTS:
            imported_optional.append(root)
            raise RuntimeError(f"optional Shizuku module imported: {root}")
        return real_import(name, globals, locals, fromlist, level)

    builtins.__import__ = guarded_import
    try:
        spec = importlib.util.spec_from_file_location("relay_under_test", RELAY)
        if spec is None or spec.loader is None:
            raise AssertionError("could not load relay module")
        relay = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(relay)

        first = relay.execute_action(
            {
                "action": "phone_shell",
                "command": "printf SHIZUKU_FREE_BASELINE",
                "timeoutSeconds": 10,
            }
        )
        if not first.get("ok") or first.get("stdout") != "SHIZUKU_FREE_BASELINE":
            raise AssertionError(f"background phone_shell failed: {first!r}")
        if imported_optional:
            raise AssertionError(
                f"background phone_shell imported Shizuku modules: {imported_optional!r}"
            )

        # Optional UI failure must remain isolated from the background lane.
        try:
            relay.execute_action({"action": "operator_overlay_status"})
        except RuntimeError as exc:
            if "optional Shizuku module imported" not in str(exc):
                raise
        else:
            raise AssertionError("guarded optional overlay import unexpectedly succeeded")

        second = relay.execute_action(
            {
                "action": "phone_shell",
                "command": "printf STILL_ALIVE",
                "timeoutSeconds": 10,
            }
        )
        if not second.get("ok") or second.get("stdout") != "STILL_ALIVE":
            raise AssertionError(
                f"background lane did not survive optional UI failure: {second!r}"
            )
    finally:
        builtins.__import__ = real_import

    print("PHONE_RELAY_SHIZUKU_INDEPENDENCE_OK")


if __name__ == "__main__":
    main()
