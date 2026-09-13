#!/usr/bin/env python3
"""Commit-bound mechanical proof runner for the terminal DMC vertical slice."""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA = "terminal-dmc-proof.v1"
ROOT = Path(__file__).resolve().parents[1]
DEMO_SCRIPT = "w" * 12 + "j" + "." * 6 + "j" + "." * 7 + "k" + "." * 4 + "j" + "." * 5 + "l"


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run(command, cwd=ROOT, env=env, text=True, capture_output=True, check=False)


def git(*args: str) -> str:
    result = run(["git", "-C", str(ROOT), *args])
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip())
    return result.stdout.strip()


def sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def last_json(stdout: str) -> dict[str, Any]:
    for line in reversed(stdout.splitlines()):
        line = line.strip()
        if not line:
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value
    return {}


def main() -> int:
    try:
        head = git("rev-parse", "HEAD")
        branch = git("branch", "--show-current") or "DETACHED"
        dirty_before = git("status", "--porcelain=v1", "--untracked-files=normal")

        test_cmd = [sys.executable, "-B", "tools/test_terminal_dmc.py"]
        test = run(test_cmd)
        test_report = last_json(test.stdout)

        demo_cmd = [
            sys.executable,
            "-B",
            "tools/terminal_dmc.py",
            "--script",
            DEMO_SCRIPT,
            "--render-final",
        ]
        demo = run(demo_cmd)
        demo_state = last_json(demo.stdout)

        dirty_after = git("status", "--porcelain=v1", "--untracked-files=normal")

        blockers: list[str] = []
        if dirty_before:
            blockers.append("WORKTREE_DIRTY_BEFORE_PROOF")
        if dirty_after:
            blockers.append("WORKTREE_DIRTY_AFTER_PROOF")
        if test.returncode != 0 or test_report.get("ok") is not True:
            blockers.append("REGRESSION_CONTRACT_FAILED")
        if demo.returncode != 0:
            blockers.append("SCRIPTED_DEMO_FAILED")
        if demo_state.get("last_move") != "BURIAL":
            blockers.append("GROUND_LAUNCH_JUGGLE_SPIKE_NOT_OBSERVED")
        if float(demo_state.get("style") or 0) < 200:
            blockers.append("STYLE_DID_NOT_REWARD_COMBO")
        if int(demo_state.get("combo") or 0) < 5:
            blockers.append("COMBO_CHAIN_TOO_SHORT")
        if "DMC TERMINAL // SHOVEL PROOF" not in demo.stdout:
            blockers.append("RENDER_SURFACE_MISSING")
        if "TARGET " not in demo.stdout or "STYLE " not in demo.stdout:
            blockers.append("HUD_SURFACE_MISSING")

        receipt = {
            "schema": SCHEMA,
            "status": "PASS" if not blockers else "FAIL",
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "repository": {
                "head_sha": head,
                "branch": branch,
                "clean_before": not bool(dirty_before),
                "clean_after": not bool(dirty_after),
            },
            "checks": {
                "regression": {
                    "command": test_cmd,
                    "exit_code": test.returncode,
                    "stdout_sha256": sha(test.stdout),
                    "stderr_sha256": sha(test.stderr),
                    "reported": test_report,
                },
                "scripted_demo": {
                    "command": demo_cmd,
                    "exit_code": demo.returncode,
                    "stdout_sha256": sha(demo.stdout),
                    "stderr_sha256": sha(demo.stderr),
                    "state": demo_state,
                    "frame_contains_title": "DMC TERMINAL // SHOVEL PROOF" in demo.stdout,
                    "frame_contains_target": "TARGET " in demo.stdout,
                    "frame_contains_style": "STYLE " in demo.stdout,
                },
            },
            "blockers": blockers,
            "evidence_boundary": {
                "proves": [
                    "deterministic combat core executes ground-launch-juggle-spike grammar",
                    "style/variety, dodge, shovel-parry and render regressions pass",
                    "scripted renderer exposes target/style/first-person shovel surface",
                    "result is bound to one clean Git commit",
                ],
                "does_not_prove": [
                    "raw-key interactive feel on Drew's actual terminal",
                    "human taste acceptance",
                    "merged or deployed state",
                ],
            },
        }
        print(json.dumps(receipt, indent=2, sort_keys=True))
        return 0 if not blockers else 1
    except Exception as exc:
        print(json.dumps({
            "schema": SCHEMA,
            "status": "FAIL",
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "blockers": ["PROOF_RUNNER_ERROR"],
            "error": str(exc),
        }, indent=2, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
