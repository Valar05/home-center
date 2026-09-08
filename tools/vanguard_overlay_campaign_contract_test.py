#!/usr/bin/env python3
"""Static contract test for the Vanguard overlay campaign machinery.

This test proves committed source shape only. The bootstrap separately runs dynamic
transport/process-tree canaries on the actual operator body.
"""
from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--campaign", default=str(Path(__file__).with_name("vanguard_overlay_campaign.py")))
    args = parser.parse_args()
    path = Path(args.campaign)
    body = path.read_text(encoding="utf-8") if path.exists() else ""

    checks: list[dict] = []

    def add(name: str, ok: bool, detail: str) -> None:
        checks.append({"check": name, "ok": bool(ok), "detail": detail})

    syntax_ok = False
    syntax_detail = "campaign source missing"
    if body:
        try:
            ast.parse(body, filename=str(path))
            syntax_ok = True
            syntax_detail = "Python AST parse passed."
        except SyntaxError as exc:
            syntax_detail = f"SyntaxError line {exc.lineno}: {exc.msg}"

    worker = ""
    if "def worker_main()" in body:
        worker = body.split("def worker_main()", 1)[1].split("def parse_args()", 1)[0]

    add("campaign_exists", bool(body), "Campaign source is readable.")
    add("python_syntax", syntax_ok, syntax_detail)
    add("stable_branch", 'BRANCH = "campaign/vanguard-overlay-resurrection"' in body, "Campaign is pinned to the commissioned remote branch.")
    add("durable_history", 'HISTORY = STATE / "history.jsonl"' in body and 'LATEST = STATE / "latest.json"' in body, "Append-only history and compact latest state survive process exit.")
    add(
        "managed_worktree",
        '["git", "worktree", "add"' in body and "MANAGED_WORKTREE" in body and '["git", "reset", "--hard", f"origin/{BRANCH}"]' in body,
        "Campaign-owned detached worktree preserves operator checkout state.",
    )
    add("free_tab_exact_lane", '"action": "swarm.enqueue"' in body and '"source": "vanguard-overlay-campaign"' in body and "/v1/throne" in body, "Chromium Throne relay is the implementation-worker lane.")
    add("no_adjacent_worker_fallback", "No substitute worker lane was selected" in body and "No adjacent worker lane was substituted" in body, "Missing relay authority checkpoints rather than silently substituting a worker lane.")
    add("bounded_repair_rounds", "MAX_SOURCE_REPAIR_ROUNDS" in body and "drive_source_to_green" in body and "failedChecks" in body, "Multiple repair commits/rounds are allowed until the deterministic source contract passes.")
    add("relay_backoff", "wait_for_relay_config" in body and "delay = min(20, delay * 2)" in body, "Relay discovery retries with bounded backoff.")
    add(
        "source_before_build",
        bool(worker) and 0 <= worker.find("drive_source_to_green()") < worker.find("build_apk(worktree)"),
        "worker_main source contract/repair stage gates Android build.",
    )
    add(
        "build_before_install",
        bool(worker) and 0 <= worker.find("build_apk(worktree)") < worker.find("install_apk(build)"),
        "worker_main hashed Android build gates phone install.",
    )
    add("visible_activity_only_install", 'am start -n {PACKAGE}/.MainActivity' in body and "am start-foreground-service" not in body, "Shell install launches only visible MainActivity and never background-arms the microphone FGS.")
    add("user_arm_wait", "visible-user-arm" in body and "USER_ARM_SECONDS" in body and "mic_active" in body, "Campaign explicitly waits for the required visible microphone arm action.")
    add("source_truth_boundary", "This proves source shape only" in body, "Source PASS is not rounded up to deployment.")
    add("build_truth_boundary", "Build/test success is build-body evidence, not phone deployment or acceptance" in body, "Build PASS is not rounded up to deployment.")
    add("acceptance_remains_open", "remainingAcceptance" in body and "accepted=False" in body, "Initial phone canary cannot self-accept the product.")
    add("process_isolation", body.count("start_new_session=True") >= 2, "Worker and destructive canary each use their own process group/session.")
    add("whole_tree_stop", "os.killpg(pgid, signal.SIGTERM)" in body and "os.killpg(pgid, signal.SIGKILL)" in body, "STOP targets the worker process group and escalates TERM to KILL.")
    add("follow_detaches", "FOLLOW DETACHED" in body and "campaign worker was NOT stopped" in body, "Ctrl-C from follow detaches the viewer without killing the campaign.")
    add("inert_transport_canary", "TRANSPORT_OK" in body and "$(touch SHOULD_NOT_EXIST)" in body and "transportSha256" in body, "Prompt/data transport canary covers shell-looking text without eval.")
    add("resume_idempotent", "already-running" in body and "no duplicate process was started" in body, "Repeated run/resume converges instead of duplicating the campaign worker.")
    add("phone_state_evidence", all(token in body for token in ("overlay_mode", "listening_state", "mic_active", "ring_write_bytes", "ring_capacity_bytes", "transcript_segment_count", "keep_count")), "Phone state query exposes commissioned acceptance instrumentation.")
    add("legacy_recovery_not_called", "recover_adam_overlay_phone.sh" not in body and "deploy_adam_overlay_phone.sh" not in body and "HC_ENABLE_LEGACY_OPERATOR_OVERLAY" not in body, "New campaign never invokes the retired legacy recovery path.")
    add("no_github_actions_acceptance", "workflow_dispatch" not in body and "actions/" not in body, "GitHub Actions are not used as runtime/acceptance evidence.")
    add("operator_controls", all(f'"{name}"' in body for name in ("run", "resume", "status", "follow", "stop", "doctor", "canary", "receipts")), "Stable operator controls remain available after bootstrap.")

    failed = [row["check"] for row in checks if not row["ok"]]
    result = {
        "schema": "vanguard-overlay-campaign-source-contract-v2",
        "ok": not failed,
        "campaign": str(path),
        "checks": checks,
        "failed": failed,
        "truthBoundary": "PASS proves committed campaign source shape only. Dynamic bootstrap canaries, Chromium Throne execution, Android build, phone deployment, and human acceptance require their own evidence.",
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
