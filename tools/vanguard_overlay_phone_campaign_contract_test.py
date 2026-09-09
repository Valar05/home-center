#!/usr/bin/env python3
"""Static contract for the cross-body primary-phone Vanguard runner."""
from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
args = parser.parse_args()
ROOT = Path(args.root).expanduser().resolve()
PHONE = ROOT / "tools" / "vanguard_overlay_phone_campaign.py"
CORE = ROOT / "tools" / "vanguard_overlay_campaign.py"
DESKTOP = ROOT / "tools" / "vanguard_overlay_throne_campaign.ps1"
PROTOCOL = ROOT / "campaigns" / "vanguard-overlay-resurrection" / "PHONE_CANARY_PROTOCOL.md"

checks: list[dict] = []


def add(name: str, ok: bool, detail: str) -> None:
    checks.append({"check": name, "ok": bool(ok), "detail": detail})


phone = PHONE.read_text(encoding="utf-8") if PHONE.exists() else ""
core = CORE.read_text(encoding="utf-8") if CORE.exists() else ""
desktop = DESKTOP.read_text(encoding="utf-8") if DESKTOP.exists() else ""
protocol = PROTOCOL.read_text(encoding="utf-8") if PROTOCOL.exists() else ""

syntax_ok = False
syntax_detail = "missing"
try:
    ast.parse(phone, filename=str(PHONE))
    syntax_ok = bool(phone)
    syntax_detail = "Python AST parse passed."
except SyntaxError as exc:
    syntax_detail = f"line {exc.lineno}: {exc.msg}"

add("phone_wrapper_exists", bool(phone), "Primary-phone cross-body wrapper exists.")
add("python_syntax", syntax_ok, syntax_detail)
add("loads_durable_core", "vanguard_overlay_campaign.py" in phone and "spec_from_file_location" in phone, "Wrapper reuses rather than duplicates the durable phone campaign engine.")
add("child_reenters_wrapper", "core.SCRIPT = Path(__file__).resolve()" in phone, "Detached worker re-enters the cross-body wrapper instead of silently losing its transport patch.")
add("mailbox_markers_match", "VANGUARD_THRONE_REQUEST" in phone and "VANGUARD_THRONE_RECEIPT" in phone and "VANGUARD_THRONE_REQUEST" in desktop and "VANGUARD_THRONE_RECEIPT" in desktop, "Phone and desktop runners share one durable mailbox protocol.")
add("mailbox_is_remote", "repos/{REPO}/issues/{PR_NUMBER}/comments" in phone and "gh api" in desktop, "Cross-body transport is persisted to GitHub PR comments rather than local-only state.")
add("phone_localhost_not_desktop", "and os.name != \"nt\"" in phone and "127.0.0.1" in phone, "Phone wrapper refuses to infer THECAULDRON from non-Windows localhost.")
add("no_adjacent_worker", "No adjacent worker lane was substituted" in phone, "Missing mailbox/auth does not authorize another worker lane.")
add("request_truth_boundary", "not evidence that the desktop relay or a free tab accepted" in phone, "Mailbox request is not rounded up to execution proof.")
add("desktop_exact_relay", "http://127.0.0.1:9234/v1/throne" in desktop and "relay-capability.txt" in desktop, "THECAULDRON runner targets the canonical Chromium Throne localhost relay/capability.")
add("desktop_swarm_only", "swarm.enqueue" in desktop and "Browser Nerve" not in desktop and "Computer Hands" not in desktop, "Desktop runner does not silently substitute adjacent browser bodies.")
add("desktop_remote_receipts", "Post-Receipt" in desktop and "sourceHeadObserved" in desktop and "truthBoundary" in desktop, "Free-tab relay states are persisted remotely with branch readback and explicit truth boundary.")
add("desktop_retry", "idempotent" in desktop and "backoff" in desktop and "retrying" in desktop, "Desktop runner is restartable and retries transient relay/mailbox failures.")
add("protocol_exists", bool(protocol), "Physical phone canary protocol exists.")
add("machine_arm_forbidden", "There is **no** `vanguard_action=ARM_LISTENING`" in protocol, "Shell/campaign cannot manufacture the Android while-in-use microphone arm.")
add("notification_tap_human_proof", "tap the Home Center heartbeat notification" in protocol, "Notification restore requires actual user tap evidence, not machine RESTORE laundering.")
add("core_truth_separation", "accepted=False" in core and "remainingAcceptance" in core, "Base phone engine does not self-accept after its initial canary.")

failed = [row["check"] for row in checks if not row["ok"]]
print(json.dumps({
    "schema": "vanguard-overlay-phone-campaign-contract-v2",
    "ok": not failed,
    "root": str(ROOT),
    "checks": checks,
    "failed": failed,
    "truthBoundary": "PASS proves committed cross-body campaign source shape only; desktop PowerShell parse/runtime, real Throne actuation, phone execution and physical acceptance remain separate evidence gates."
}, indent=2, sort_keys=True))
raise SystemExit(0 if not failed else 1)
