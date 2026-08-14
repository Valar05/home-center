#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

MODULE_PATH = Path(__file__).with_name("fortress_bootstrap.py")
SPEC = importlib.util.spec_from_file_location("fortress_bootstrap", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class PlatformDetectionTests(unittest.TestCase):
    def test_termux_marker_wins(self) -> None:
        self.assertEqual(
            MODULE.detect_platform(
                env={"TERMUX_VERSION": "0.118", "PREFIX": "/data/data/com.termux/files/usr"},
                os_name="posix",
                system_name="Linux",
                termux_prefix_exists=False,
            ),
            "android-termux",
        )

    def test_android_home_marker_is_termux(self) -> None:
        self.assertEqual(
            MODULE.detect_platform(
                env={
                    "ANDROID_ROOT": "/system",
                    "HOME": "/data/data/com.termux/files/home",
                    "PREFIX": "/data/data/com.termux/files/usr",
                },
                os_name="posix",
                system_name="Linux",
                termux_prefix_exists=False,
            ),
            "android-termux",
        )

    def test_windows(self) -> None:
        self.assertEqual(
            MODULE.detect_platform(
                env={},
                os_name="nt",
                system_name="Windows",
                termux_prefix_exists=False,
            ),
            "windows",
        )

    def test_unsupported_linux_is_not_silently_substituted(self) -> None:
        self.assertEqual(
            MODULE.detect_platform(
                env={},
                os_name="posix",
                system_name="Linux",
                termux_prefix_exists=False,
            ),
            "unsupported",
        )


class ContractTests(unittest.TestCase):
    def test_parser_accepts_same_actions_on_both_adapters(self) -> None:
        parser = MODULE.build_parser()
        for action in ("install", "repair", "status", "doctor", "local", "uninstall"):
            args = parser.parse_args([action])
            self.assertEqual(args.action, action)

    def test_secret_redaction_is_recursive(self) -> None:
        value = {
            "token": "alpha-secret",
            "nested": ["prefix alpha-secret suffix", {"x": "alpha-secret"}],
        }
        redacted = MODULE.redact_value(value, {"alpha-secret"})
        text = json.dumps(redacted)
        self.assertNotIn("alpha-secret", text)
        self.assertIn("<redacted>", text)

    def test_source_has_no_browser_automation_dependency(self) -> None:
        source = MODULE_PATH.read_text(encoding="utf-8").lower()
        forbidden = (
            "playwright",
            "selenium",
            "pyautogui",
            "chromedriver",
            "chatgpt.com",
            "openai.com/api",
        )
        for term in forbidden:
            self.assertNotIn(term, source)
        self.assertIn('"browserorchestration": false', source)

    def test_battery_governor_is_explicitly_deferred(self) -> None:
        parser = MODULE.build_parser()
        args = parser.parse_args(["status"])
        args.quiet = True
        with tempfile.TemporaryDirectory() as temp:
            ctx = MODULE.Context(args, "android-termux", Path(temp))
            try:
                receipt = MODULE.write_receipt(
                    ctx,
                    ok=True,
                    result={"ok": True},
                    error=None,
                )
            finally:
                ctx.close()
        governor = receipt["capabilityLedger"]["batteryGovernor"]
        self.assertEqual(governor["status"], "deferred_by_owner")
        self.assertIn("outpace charging", governor["requirement"])
        self.assertIn("underperform", governor["requirement"])

    def test_repo_identity_requires_existing_machine_bodies(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.assertFalse(MODULE.is_repo_root(root))
            for item in (
                root / "AGENTS.md",
                root / "tools" / "fortress_phone_campaign.sh",
                root / "computer-hands" / "windows" / "home-center-hands.ps1",
                root / ".continue" / "offline-config.yaml",
            ):
                item.parent.mkdir(parents=True, exist_ok=True)
                item.write_text("x", encoding="utf-8")
            self.assertTrue(MODULE.is_repo_root(root))

    def test_powercfg_parser(self) -> None:
        sample = "Current AC Power Setting Index: 0x00000002\r\n"
        self.assertEqual(MODULE.parse_powercfg_ac_index(sample), 2)
        self.assertIsNone(MODULE.parse_powercfg_ac_index("not present"))

    def test_powershell_interactive_mode_does_not_force_noninteractive(self) -> None:
        class FakeContext:
            def capture(self, name, command, **kwargs):
                self.command = command
                return SimpleNamespace(returncode=0, stdout="", stderr="")

        fake = FakeContext()
        MODULE.run_powershell(fake, "interactive", "Write-Output ok", interactive=True)
        lowered = [str(part).lower() for part in fake.command]
        self.assertNotIn("-noninteractive", lowered)
        MODULE.run_powershell(fake, "noninteractive", "Write-Output ok", interactive=False)
        lowered = [str(part).lower() for part in fake.command]
        self.assertIn("-noninteractive", lowered)

    def test_power_policy_requires_success_before_active_receipt(self) -> None:
        parser = MODULE.build_parser()
        args = parser.parse_args(["install"])
        args.quiet = True
        with tempfile.TemporaryDirectory() as temp:
            ctx = MODULE.Context(args, "windows", Path(temp))
            ctx.args.no_ac_awake = False
            try:
                with mock.patch.object(MODULE.shutil, "which", return_value="powercfg.exe"), mock.patch.object(
                    MODULE, "powercfg_query", side_effect=[(1, "lid"), (900, "sleep")]
                ), mock.patch.object(
                    ctx,
                    "capture",
                    side_effect=[
                        SimpleNamespace(returncode=0),
                        SimpleNamespace(returncode=5),
                        SimpleNamespace(returncode=0),
                    ],
                ):
                    with self.assertRaises(MODULE.BootstrapError):
                        MODULE.apply_windows_ac_awake_policy(ctx)
                self.assertFalse((ctx.state_dir / "power-policy-active.json").exists())
            finally:
                ctx.close()

    def test_power_policy_refuses_non_reversible_change(self) -> None:
        parser = MODULE.build_parser()
        args = parser.parse_args(["install"])
        args.quiet = True
        with tempfile.TemporaryDirectory() as temp:
            ctx = MODULE.Context(args, "windows", Path(temp))
            ctx.args.no_ac_awake = False
            try:
                with mock.patch.object(MODULE.shutil, "which", return_value="powercfg.exe"), mock.patch.object(
                    MODULE, "powercfg_query", side_effect=[(None, "missing"), (900, "sleep")]
                ), mock.patch.object(ctx, "capture") as capture:
                    with self.assertRaises(MODULE.BootstrapError):
                        MODULE.apply_windows_ac_awake_policy(ctx)
                    capture.assert_not_called()
            finally:
                ctx.close()


class LockTests(unittest.TestCase):
    def test_stale_lock_is_recovered(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            lock_path = Path(temp) / "bootstrap.lock"
            lock_path.write_text(
                json.dumps(
                    {
                        "pid": 99999999,
                        "action": "install",
                        "createdEpoch": 1,
                    }
                ),
                encoding="utf-8",
            )
            with MODULE.ProcessLock(lock_path, "status"):
                data = json.loads(lock_path.read_text(encoding="utf-8"))
                self.assertEqual(data["pid"], os.getpid())
            self.assertFalse(lock_path.exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
