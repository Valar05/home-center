#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("ssh_axis", ROOT / "tools" / "ssh_axis.py")
assert SPEC and SPEC.loader
ssh_axis = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = ssh_axis
SPEC.loader.exec_module(ssh_axis)


class SshAxisTest(unittest.TestCase):
    def receipt(self, returncode: int, stdout: str, stderr: str = ""):
        completed = subprocess.CompletedProcess([], returncode, stdout, stderr)
        with patch.object(ssh_axis, "transport_probe", return_value=(True, "tcp:open")):
            with patch.object(ssh_axis.subprocess, "run", return_value=completed) as run:
                receipt = ssh_axis.ssh_probe("cauldron", "dclar@127.0.0.1", 1.0)
        return receipt, run.call_args.args[0]

    def test_windows_crlf_echo_probe_is_callable(self):
        receipt, command = self.receipt(0, "FORTRESS_SSH_AXIS_OK\r\n")
        self.assertEqual("echo FORTRESS_SSH_AXIS_OK", ssh_axis.PROBE)
        self.assertEqual(ssh_axis.PROBE, command[-1])
        self.assertNotIn("printf", command[-1])
        self.assertTrue(receipt.callable)
        self.assertEqual("callable", receipt.state)

    def test_nonzero_remote_command_stays_failed(self):
        receipt, _ = self.receipt(1, "", "remote command failed")
        self.assertFalse(receipt.callable)
        self.assertEqual("command_failed", receipt.state)

    def test_ssh_255_stays_authentication_failed(self):
        receipt, _ = self.receipt(255, "", "permission denied")
        self.assertFalse(receipt.callable)
        self.assertEqual("authentication_failed", receipt.state)


if __name__ == "__main__":
    unittest.main()
