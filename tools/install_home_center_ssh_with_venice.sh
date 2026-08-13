#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
ROOT="${HC_REPO_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}"
cd "$ROOT"
python3 tools/test_home_center_ssh.py
python3 - <<'PY'
from pathlib import Path
from tools import adam_planned_venice as v

task = '''
Review this exact commissioned change before installation.

Build only a simple reusable Home Center SSH transport layer.
Allowed capability:
- config-backed SSH targets;
- existing SSH keys;
- target liveness/status probe;
- execute one bounded remote command;
- bounded connect/runtime timeout;
- receipt with target, command, stdout, stderr, exit code, duration, and timestamp.

Hard exclusions:
- no VM provisioning;
- no Gemini worker or cloud compute redesign;
- no new control plane;
- no GCP requirement;
- no IPv4/IPv6/Tailscale/public-address requirement;
- no orchestration system;
- no changing Drew's active worktree.

SSH is transport only, generic enough for Phone Hands, Computer Hands, Venice, Vlad, and future campaigns.
Inspect the already implemented files tools/home_center_ssh.py, tools/setup_home_center_ssh.sh, tools/test_home_center_ssh.py, and config/ssh-targets.example.json.
Apply the Judgment Jars. Do not impersonate Venice. Return real Venice PLAN_ALLOWED only if this implementation respects the commission.
'''
gate = v.preflight(task, Path.cwd(), stop_after_steps=20)
review = gate['review']
print('VENICE:', review.get('directive'), review.get('receipt'), flush=True)
if review.get('directive') != 'PLAN_ALLOWED' or review.get('planPermissionGranted') is not True:
    raise SystemExit(73)
PY
HC_REPO_ROOT="$ROOT" bash tools/setup_home_center_ssh.sh
home-center-ssh status
