#!/usr/bin/env python3
import importlib.util
import json
import subprocess
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "tools" / "fortress_cli.py"
spec = importlib.util.spec_from_file_location("fortress_cli", MODULE_PATH)
fortress_cli = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(fortress_cli)


class FortressCliTests(unittest.TestCase):
    def test_cauldron_delegates_to_ssh_axis(self):
        payload = {
            "ssh_axis": [{
                "target": "cauldron",
                "endpoint": "dclar@thecauldron:10022",
                "state": "callable",
                "callable": True,
                "transport_ok": True,
                "auth_ok": True,
                "command_ok": True,
                "observed": "ok",
                "elapsed_ms": 17,
            }]
        }
        proc = subprocess.CompletedProcess([], 0, stdout=json.dumps(payload), stderr="")
        runner = mock.Mock(return_value=proc)
        fake_axis = mock.Mock()
        fake_axis.is_file.return_value = True
        fake_axis.__str__ = mock.Mock(return_value="/repo/tools/ssh_axis.py")
        with mock.patch.object(fortress_cli, "SSH_AXIS", fake_axis):
            result = fortress_cli.cauldron_status(runner)
        self.assertTrue(result["ok"])
        self.assertEqual(result["endpoint"], "dclar@thecauldron:10022")
        command = runner.call_args.args[0]
        self.assertEqual(command[-4:], ["check", "--target", "cauldron", "--json"])

    def test_wiko_health_is_separate_and_read_only(self):
        def opener(url, timeout):
            self.assertIn("/brain/api/status", url)
            self.assertEqual(timeout, 8.0)
            return 200, {
                "home_center": True,
                "ollama": True,
                "model": "qwen3.5:2b",
                "index": {"phase": "ready", "entries": 33501},
            }
        result = fortress_cli.wiko_status(opener)
        self.assertTrue(result["ok"])
        self.assertEqual(result["state"], "callable")
        self.assertEqual(result["model"], "qwen3.5:2b")

    def test_degraded_wiko_does_not_change_cauldron_record(self):
        cauldron = {"surface": "cauldron", "ok": True, "state": "callable"}
        wiko = {"surface": "wiko", "ok": False, "state": "unreachable"}
        with mock.patch.object(fortress_cli, "cauldron_status", return_value=cauldron),              mock.patch.object(fortress_cli, "wiko_status", return_value=wiko),              mock.patch.object(fortress_cli, "source_sha256", return_value="abc"):
            result = fortress_cli.aggregate()
        self.assertTrue(result["cauldron"]["ok"])
        self.assertFalse(result["wiko"]["ok"])
        self.assertFalse(result["ok"])

    def test_status_observes_degraded_state_without_failure(self):
        degraded = {
            "schema": fortress_cli.SCHEMA,
            "source_sha256": "abc",
            "cauldron": {"surface": "cauldron", "ok": True, "state": "callable"},
            "wiko": {"surface": "wiko", "ok": False, "state": "unreachable"},
            "ok": False,
        }
        with mock.patch.object(fortress_cli, "aggregate", return_value=degraded),              mock.patch.object(fortress_cli, "emit"):
            self.assertEqual(fortress_cli.main(["status"]), 0)

    def test_doctor_fails_closed_on_degraded_required_surface(self):
        degraded = {
            "schema": fortress_cli.SCHEMA,
            "source_sha256": "abc",
            "cauldron": {"surface": "cauldron", "ok": True, "state": "callable"},
            "wiko": {"surface": "wiko", "ok": False, "state": "unreachable"},
            "ok": False,
        }
        with mock.patch.object(fortress_cli, "aggregate", return_value=degraded),              mock.patch.object(fortress_cli, "emit"):
            self.assertEqual(fortress_cli.main(["doctor"]), 2)


if __name__ == "__main__":
    unittest.main()
