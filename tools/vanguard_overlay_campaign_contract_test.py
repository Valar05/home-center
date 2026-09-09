#!/usr/bin/env python3
"""Static regression contract for VANGUARD // OVERLAY RESURRECTION campaign.

PASS is source-shape evidence only. The bootstrap separately runs dynamic inert-prompt
and process-tree STOP canaries on the actual operator body.
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

    def ordered(*needles: str) -> bool:
        if not worker:
            return False
        positions = [worker.find(needle) for needle in needles]
        return all(pos >= 0 for pos in positions) and positions == sorted(positions)

    add("campaign_exists", bool(body), "Campaign source is readable.")
    add("python_syntax", syntax_ok, syntax_detail)
    add("stable_branch", 'BRANCH = "campaign/vanguard-overlay-resurrection"' in body, "Campaign is pinned to the commissioned remote branch.")
    add("durable_history", 'HISTORY = STATE / "history.jsonl"' in body and 'LATEST = STATE / "latest.json"' in body, "Append-only history and compact latest state survive process exit.")
    add("durable_attempts", 'ATTEMPTS = STATE / "attempts.json"' in body and "def next_attempt(stage" in body, "Repair generations survive campaign restart and prevent terminal relay ID collision.")
    add("managed_worktree", '["git", "worktree", "add"' in body and "MANAGED_WORKTREE" in body and '["git", "reset", "--hard", f"origin/{BRANCH}"]' in body, "Campaign-owned detached worktree preserves operator checkout state.")
    add("incremental_build_cache_preserved", "preserve untracked Gradle build caches" in body and 'cached.get("sourceHead") == head' in body, "Resume can reuse a hash-verified build for the same source head.")
    add("free_tab_exact_lane", '"action": "swarm.enqueue"' in body and '"source": "vanguard-overlay-campaign"' in body and "/v1/throne" in body, "Chromium Throne relay is the implementation/repair worker lane.")
    add("no_adjacent_worker_fallback", "No substitute worker lane was selected" in body and "No adjacent worker lane was substituted" in body, "Missing relay authority checkpoints instead of silently substituting a worker lane.")
    add("relay_backoff", "wait_for_relay_config" in body and "delay = min(20, delay * 2)" in body, "Relay discovery retries with bounded backoff.")
    add("relay_crash_checkpoint", '"status": "submitting"' in body and "atomic_json(RELAY_STATE, pending)" in body and "active_dispatch" in body, "Command identity is persisted before network submission and an actually-active command is resumed.")
    add("bounded_source_repair", "MAX_SOURCE_REPAIR_ROUNDS" in body and 'repair_branch("source"' in body, "Source-contract failure has bounded free-tab repair rounds.")
    add("bounded_build_repair", 'repair_branch("build"' in body and "Persistent Android build failure is feeding back" in body, "Persistent compile/build failures become a free-tab recovery path.")
    add("bounded_phone_repair", 'repair_branch("phone-canary"' in body and "Deterministic live phone canary failed" in body, "Repairable live-phone failures become a free-tab recovery path.")
    add("pipeline_order", ordered("drive_source_to_green()", "build_with_retry(worktree)", "install_with_retry(build, worktree)", "phone_canary()"), "worker_main preserves source -> build -> deploy -> live-canary ordering.")
    add("visible_activity_only_install", 'am start -n {PACKAGE}/.MainActivity' in body and "am start-foreground-service" not in body, "Shell install launches only visible MainActivity and never background-arms the microphone service.")
    add("user_arm_wait", "visible-user-arm" in body and "USER_ARM_SECONDS" in body and "mic_active" in body, "Campaign explicitly waits for Android's required visible microphone arm action.")
    add("resume_preserves_user_arm", "installed_apk_sha" in body and '"status": "already-current"' in body and "Matching deployed builds are not reinstalled on resume" in body, "A matching installed APK is hash-verified and not reinstalled, preserving a successful arm.")
    add(
        "canonical_rish_discovery",
        all(token in body for token in (
            'Path.home() / "rish"',
            'Path.home() / "bin" / "rish"',
            'Path.home() / ".local" / "bin" / "rish"',
            "/storage/emulated/0/Android/data/moe.shizuku.privileged.api/files/rish",
            "/storage/emulated/0/Documents/rish",
            "/storage/emulated/0/Download/rish",
        )),
        "Campaign matches the repository's canonical Shizuku/rish discovery locations in addition to env/PATH.",
    )
    add("canonical_body_probe", "home_center_shizuku_setup_probe.sh" in body and "--report-only" in body and "--no-network-install" in body, "Before body blockers are final, campaign can persist canonical Shizuku readiness diagnostics.")
    add("source_truth_boundary", "Source truth remains below phone truth" in body, "Source PASS is not rounded up to deployment.")
    add("build_truth_boundary", "Build/test success is build-body evidence, not phone deployment or acceptance" in body, "Build PASS is not rounded up to deployment.")
    add("deploy_truth_boundary", "APK install/hash verification proves deployment identity" in body, "Deployment identity is not rounded up to live behavior.")
    add("acceptance_remains_open", "remainingAcceptance" in body and "accepted=False" in body, "Initial live canary cannot self-accept the product.")
    add("process_isolation", body.count("start_new_session=True") >= 2, "Worker and destructive canary each use their own process group/session.")
    add("whole_tree_stop", "os.killpg(pgid, signal.SIGTERM)" in body and "os.killpg(pgid, signal.SIGKILL)" in body, "STOP targets the worker process group and escalates TERM to KILL.")
    add("canary_child_reaped", "def reap_and_exit" in body and "child.wait(timeout=2)" in body, "Process-tree canary reaps its child instead of mistaking a zombie PID for a live leak.")
    add("follow_detaches", "FOLLOW DETACHED" in body and "campaign worker was NOT stopped" in body, "Ctrl-C from follow detaches the viewer without killing the campaign.")
    add("inert_transport_canary", "TRANSPORT_OK" in body and "$(touch SHOULD_NOT_EXIST)" in body and "transportSha256" in body, "Prompt/data transport canary covers shell-looking text without eval.")
    add("resume_idempotent_worker", "already-running" in body and "no duplicate process was started" in body, "Repeated run/resume cannot duplicate a live campaign worker.")
    add("phone_state_evidence", all(token in body for token in ("overlay_mode", "listening_state", "mic_active", "ring_write_bytes", "ring_capacity_bytes", "transcript_segment_count", "keep_count")), "Phone state query exposes commissioned acceptance instrumentation.")
    add("legacy_recovery_not_called", "recover_adam_overlay_phone.sh" not in body and "deploy_adam_overlay_phone.sh" not in body and "HC_ENABLE_LEGACY_OPERATOR_OVERLAY" not in body, "New campaign never invokes the retired legacy recovery path.")
    add("no_github_actions_acceptance", "workflow_dispatch" not in body and "actions/" not in body, "GitHub Actions are not used as runtime/acceptance evidence.")
    add("operator_controls", all(f'"{name}"' in body for name in ("run", "resume", "status", "follow", "stop", "doctor", "canary", "receipts")), "Stable operator controls remain available after bootstrap.")

    failed = [row["check"] for row in checks if not row["ok"]]
    result = {
        "schema": "vanguard-overlay-campaign-source-contract-v4",
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
