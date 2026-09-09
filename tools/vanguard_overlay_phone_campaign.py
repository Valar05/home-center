#!/data/data/com.termux/files/usr/bin/python
"""Primary-phone runner for VANGUARD // OVERLAY RESURRECTION.

This wrapper preserves the durable phone campaign in vanguard_overlay_campaign.py but
fixes the physical topology: Chromium Throne's relay is localhost on THECAULDRON, not
localhost on the phone. When no real local Throne relay is present, implementation and
repair commands are written as structured PR #351 mailbox requests. The desktop runner
reads those requests and is the only component allowed to submit them to Chromium
Throne's local relay.

GitHub is transport/evidence only. A mailbox request is never reported as a free-tab
execution, and a free-tab receipt is never rounded up to phone deployment.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import shlex
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
CORE_PATH = HERE / "vanguard_overlay_campaign.py"
PR_NUMBER = 351
REPO = "Valar05/home-center"
REQUEST_MARKER = "<!-- VANGUARD_THRONE_REQUEST -->"
RECEIPT_MARKER = "<!-- VANGUARD_THRONE_RECEIPT -->"
MAILBOX_STATE_NAME = "mailbox.json"

spec = importlib.util.spec_from_file_location("vanguard_overlay_campaign_core", CORE_PATH)
if spec is None or spec.loader is None:
    raise SystemExit(f"Cannot load campaign core: {CORE_PATH}")
core = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = core
spec.loader.exec_module(core)

# Critical: when core spawns its detached worker, it must re-enter this wrapper so the
# cross-body transport patch remains active in the child process.
core.SCRIPT = Path(__file__).resolve()
MAILBOX_STATE = core.STATE / MAILBOX_STATE_NAME


def gh_available() -> bool:
    return core.command_exists("gh") and core.run(["gh", "auth", "status"], timeout=30)["rc"] == 0


def gh_api(args: list[str], timeout: int = 90) -> dict:
    return core.run(["gh", "api", *args], timeout=timeout)


def comments() -> list[dict]:
    result = gh_api([f"repos/{REPO}/issues/{PR_NUMBER}/comments?per_page=100"], timeout=90)
    if result["rc"] != 0:
        return []
    try:
        value = json.loads(result["stdout"])
        return value if isinstance(value, list) else []
    except json.JSONDecodeError:
        return []


def marker_json(body: str, marker: str) -> dict | None:
    if marker not in body:
        return None
    tail = body.split(marker, 1)[1].strip()
    if tail.startswith("```json"):
        tail = tail[len("```json"):]
        if "```" in tail:
            tail = tail.split("```", 1)[0]
    elif tail.startswith("```"):
        tail = tail[3:]
        if "```" in tail:
            tail = tail.split("```", 1)[0]
    try:
        parsed = json.loads(tail.strip())
        return parsed if isinstance(parsed, dict) else None
    except json.JSONDecodeError:
        return None


def mailbox_snapshot() -> dict:
    rows = comments()
    requests: dict[str, dict] = {}
    receipts: dict[str, dict] = {}
    for row in rows:
        body = str(row.get("body") or "")
        request = marker_json(body, REQUEST_MARKER)
        if request and request.get("commandId"):
            requests[str(request["commandId"])] = {**request, "commentId": row.get("id"), "commentUrl": row.get("html_url")}
        receipt = marker_json(body, RECEIPT_MARKER)
        if receipt and receipt.get("commandId"):
            key = str(receipt["commandId"])
            current = receipts.get(key)
            if current is None or int(row.get("id") or 0) > int(current.get("commentId") or 0):
                receipts[key] = {**receipt, "commentId": row.get("id"), "commentUrl": row.get("html_url")}
    return {"requests": requests, "receipts": receipts, "commentCount": len(rows)}


def add_comment(body: str) -> dict:
    # Use the issue-comments API instead of `gh pr comment` so payload bytes are not
    # reinterpreted by a shell and the exact JSON envelope is preserved.
    result = gh_api([
        "--method", "POST",
        f"repos/{REPO}/issues/{PR_NUMBER}/comments",
        "-f", f"body={body}",
    ], timeout=90)
    parsed = None
    try:
        parsed = json.loads(result["stdout"]) if result["stdout"].strip() else None
    except json.JSONDecodeError:
        pass
    return {"ok": result["rc"] == 0, "result": parsed, "stdout": result["stdout"][-4000:], "stderr": result["stderr"][-4000:]}


def direct_relay_available() -> bool:
    relay = core.discover_relay()
    if not relay.get("ok"):
        return False
    base = str(relay.get("baseUrl") or "")
    # A caller may deliberately configure a reachable remote relay URL, but never
    # infer THECAULDRON from phone localhost. localhost/127.0.0.1 is accepted only
    # when this runner is explicitly running on Windows, which it normally is not.
    if ("127.0.0.1" in base or "localhost" in base) and os.name != "nt":
        return False
    status, _, _ = core.http_json(base + "/status", "GET", relay["capability"], None, timeout=5)
    return status == 200


def request_payload(worktree: Path, source_head: str, stage: str, issues: list[str]) -> tuple[str, dict]:
    digest, base_commission = core.commission_text(worktree)
    attempt = core.next_attempt("mailbox-" + stage)
    command_id = f"vanguard-overlay-{stage}-mailbox-{attempt}-{digest[:8]}-{source_head[:8]}"
    issue_text = "\n".join(f"- {core.short_text(item, 2500)}" for item in issues[:12]) or "- Continue the commissioned implementation from current evidence."
    appendix = f"""

## CROSS-BODY CAMPAIGN REPAIR APPENDIX — {stage} attempt {attempt}
This is continuation of the SAME Vanguard commission. The primary-phone campaign observed:
{issue_text}

Read the current remote branch first. Repair the failure class without regressing any prior constraint. Run the deterministic resurrection source contract where executable, focused tests, Regnet QA and Venice review; push the SAME `campaign/vanguard-overlay-resurrection` branch. Do not claim phone deployment from a free tab.
"""
    command = {
        "commandId": command_id,
        "action": "swarm.enqueue",
        "source": "vanguard-overlay-phone-mailbox",
        "createdAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "jobs": [{
            "jobId": f"vanguard-overlay-{stage}-{attempt}-{digest[:8]}",
            "commission": (base_commission + appendix)[:31900],
            "context": (
                "VANGUARD // OVERLAY RESURRECTION. This request came from the physical phone campaign through the durable GitHub mailbox. "
                "Chromium Throne on THECAULDRON is the exact worker lane. Preserve the Home Center overlay lineage, one-service architecture, bounded retention, Ritsu default, Adam exclusion, and capability-state truth boundaries."
            ),
        }],
    }
    envelope = {
        "schema": "vanguard-throne-request-v1",
        "campaign": "VANGUARD // OVERLAY RESURRECTION",
        "transport": "github-pr-mailbox",
        "repo": REPO,
        "pr": PR_NUMBER,
        "branch": core.BRANCH,
        "stage": stage,
        "attempt": attempt,
        "commandId": command_id,
        "sourceHeadAtRequest": source_head,
        "commissionSha256": digest,
        "issues": issues[:12],
        "command": command,
        "requestedAtMs": core.now_ms(),
        "truthBoundary": "This remote comment requests exact Chromium Throne execution. It is not evidence that the desktop relay or a free tab accepted, executed, completed, tested, or pushed anything."
    }
    return command_id, envelope


def mailbox_dispatch(worktree: Path, source_head: str, stage: str, issues: list[str]) -> dict:
    if not gh_available():
        return {
            "ok": False,
            "waiting": True,
            "error": "GITHUB_MAILBOX_AUTH_UNAVAILABLE",
            "detail": "Phone cannot reach THECAULDRON localhost and authenticated gh is unavailable for the durable PR mailbox. No adjacent worker lane was substituted."
        }

    # Reuse only a still-unanswered request for the same stage/head. A terminal
    # receipt never traps future repair attempts because core.next_attempt is durable.
    snapshot = mailbox_snapshot()
    for command_id, request in snapshot["requests"].items():
        if request.get("stage") != stage or request.get("sourceHeadAtRequest") != source_head:
            continue
        receipt = snapshot["receipts"].get(command_id)
        if receipt is None or str(receipt.get("state")) in ("queued", "leased", "submitted", "dispatching"):
            record = {
                "schema": "vanguard-overlay-mailbox-dispatch-v1",
                "transport": "github-pr-mailbox",
                "stage": stage,
                "commandId": command_id,
                "sourceHeadAtDispatch": source_head,
                "status": "reused-pending-request",
                "requestCommentId": request.get("commentId"),
                "atMs": core.now_ms(),
            }
            core.atomic_json(core.RELAY_STATE, record)
            core.atomic_json(MAILBOX_STATE, record)
            return {"ok": True, "resumed": True, **record}

    command_id, envelope = request_payload(worktree, source_head, stage, issues)
    body = REQUEST_MARKER + "\n```json\n" + json.dumps(envelope, indent=2, sort_keys=True) + "\n```"
    posted = add_comment(body)
    if not posted["ok"]:
        return {"ok": False, "waiting": True, "error": "GITHUB_MAILBOX_WRITE_FAILED", "detail": posted["stderr"] or posted["stdout"]}
    record = {
        "schema": "vanguard-overlay-mailbox-dispatch-v1",
        "transport": "github-pr-mailbox",
        "stage": stage,
        "attempt": envelope["attempt"],
        "commandId": command_id,
        "commissionSha256": envelope["commissionSha256"],
        "sourceHeadAtDispatch": source_head,
        "status": "requested",
        "requestCommentId": (posted.get("result") or {}).get("id"),
        "requestCommentUrl": (posted.get("result") or {}).get("html_url"),
        "atMs": core.now_ms(),
    }
    core.atomic_json(core.RELAY_STATE, record)
    core.atomic_json(MAILBOX_STATE, record)
    return {"ok": True, **record}


def dispatch_free_tab(worktree: Path, source_head: str, stage: str, issues: list[str]) -> dict:
    if direct_relay_available():
        return core._direct_dispatch_free_tab(worktree, source_head, stage, issues)  # type: ignore[attr-defined]
    return mailbox_dispatch(worktree, source_head, stage, issues)


def mailbox_command_state(command_id: str) -> dict:
    if not gh_available():
        return {"ok": False, "state": "mailbox-auth-missing"}
    snapshot = mailbox_snapshot()
    request = snapshot["requests"].get(command_id)
    receipt = snapshot["receipts"].get(command_id)
    if receipt:
        return {
            "ok": True,
            "state": str(receipt.get("state") or "unknown"),
            "command": receipt,
            "snapshot": {"transport": "github-pr-mailbox", "request": request, "receipt": receipt},
        }
    if request:
        return {
            "ok": True,
            "state": "queued",
            "command": request,
            "snapshot": {"transport": "github-pr-mailbox", "request": request, "receipt": None},
        }
    return {"ok": False, "state": "mailbox-request-missing"}


def relay_command_state(command_id: str) -> dict:
    if direct_relay_available():
        return core._direct_relay_command_state(command_id)  # type: ignore[attr-defined]
    return mailbox_command_state(command_id)


def install_wrapper_command() -> int:
    core.mkdirs()
    worktree, head = core.ensure_worktree()
    prefix = os.environ.get("PREFIX", "").strip()
    preferred = Path(prefix) / "bin" if prefix else Path.home() / "bin"
    preferred.mkdir(parents=True, exist_ok=True)
    if not os.access(preferred, os.W_OK):
        preferred = Path.home() / "bin"
        preferred.mkdir(parents=True, exist_ok=True)
    wrapper = preferred / "vanguard-overlay"
    runner = worktree / "tools" / "vanguard_overlay_phone_campaign.py"
    wrapper.write_text(
        "#!/data/data/com.termux/files/usr/bin/bash\n"
        "set -euo pipefail\n"
        f"export HC_VANGUARD_OVERLAY_STATE={shlex.quote(str(core.STATE))}\n"
        f"exec {shlex.quote(sys.executable)} {shlex.quote(str(runner))} \"$@\"\n",
        encoding="utf-8",
    )
    wrapper.chmod(0o755)
    core.emit(
        "install-command",
        "ready",
        "Stable vanguard-overlay phone runner installed. Cross-body repair transport is GitHub PR mailbox -> THECAULDRON Throne runner, never phone localhost masquerading as desktop.",
        command=str(wrapper),
        sourceHead=head,
        implemented=True,
        callable=True,
    )
    print(str(wrapper))
    return 0


# Save the original direct functions before monkey-patching so an explicitly configured
# reachable relay remains usable without recursion.
core._direct_dispatch_free_tab = core.dispatch_free_tab
core._direct_relay_command_state = core.relay_command_state
core.dispatch_free_tab = dispatch_free_tab
core.relay_command_state = relay_command_state
core.install_command = install_wrapper_command

if __name__ == "__main__":
    raise SystemExit(core.main())
