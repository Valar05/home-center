#!/data/data/com.termux/files/usr/bin/python
"""VANGUARD // OVERLAY RESURRECTION operator campaign.

One stable command drives one durable campaign:

  free Chromium Throne worker -> deterministic source contract -> Android build ->
  Shizuku install -> visible user microphone arm -> live phone evidence.

The campaign preserves the operator checkout, stores resumable state, retries transient
failures, feeds repairable build/runtime evidence back to the exact free-tab lane, and
keeps requested/implemented/tested/deployed/callable/delivered/accepted states distinct.

It never starts ambient microphone capture from BOOT_COMPLETED or a background shell.
The only shell-launched Android surface is visible MainActivity; Android's required
user interaction owns ARM LISTENING.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shlex
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

BRANCH = "campaign/vanguard-overlay-resurrection"
REPO_FULL = "Valar05/home-center"
PACKAGE = "com.homecenter.operatoroverlay"
STATE = Path(os.environ.get("HC_VANGUARD_OVERLAY_STATE", "~/.local/state/home-center/vanguard-overlay-resurrection")).expanduser()
HISTORY = STATE / "history.jsonl"
LATEST = STATE / "latest.json"
WORKER_META = STATE / "worker.json"
LOG = STATE / "campaign.log"
STOP_FILE = STATE / "STOP"
MANAGED_WORKTREE = STATE / "worktree"
RELAY_STATE = STATE / "relay-command.json"
ATTEMPTS = STATE / "attempts.json"
PHONE_STATE = STATE / "phone-state.txt"
BUILD_STATE = STATE / "build.json"
DEPLOY_STATE = STATE / "deploy.json"
BODY_PROBE_DIR = STATE / "body-probe"

SCRIPT = Path(__file__).resolve()
ROOT = Path(os.environ.get("HC_REPO_ROOT", str(SCRIPT.parents[1]))).expanduser().resolve()
COMMISSION_REL = Path("campaigns/vanguard-overlay-resurrection/WORKER_COMMISSION.md")
CONTRACT_REL = Path("tools/vanguard_overlay_contract_test.py")
PROJECT_REL = Path("android/operator-overlay")

EXIT_WAITING_RELAY = 20
EXIT_WAITING_USER = 21
EXIT_SOURCE_FAILED = 22
EXIT_BUILD_FAILED = 23
EXIT_PHONE_FAILED = 24
EXIT_STOPPED = 25
EXIT_BODY_BLOCKED = 26

MAX_SOURCE_REPAIR_ROUNDS = int(os.environ.get("HC_VANGUARD_OVERLAY_SOURCE_ROUNDS", "4"))
MAX_STAGE_REPAIR_ROUNDS = int(os.environ.get("HC_VANGUARD_OVERLAY_STAGE_ROUNDS", "3"))
MAX_END_TO_END_PASSES = int(os.environ.get("HC_VANGUARD_OVERLAY_E2E_PASSES", "4"))
REPAIR_ROUND_SECONDS = int(os.environ.get("HC_VANGUARD_OVERLAY_REPAIR_ROUND_SECONDS", "2700"))
USER_ARM_SECONDS = int(os.environ.get("HC_VANGUARD_OVERLAY_USER_ARM_SECONDS", "600"))


def now_ms() -> int:
    return int(time.time() * 1000)


def mkdirs() -> None:
    STATE.mkdir(parents=True, exist_ok=True)


def load_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return default


def atomic_json(path: Path, obj: dict) -> None:
    mkdirs()
    tmp = path.with_suffix(path.suffix + ".part")
    tmp.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def emit(phase: str, status: str, detail: str, **extra) -> dict:
    mkdirs()
    row = {
        "schema": "vanguard-overlay-campaign-v3",
        "campaign": "VANGUARD // OVERLAY RESURRECTION",
        "phase": phase,
        "status": status,
        "detail": detail,
        "atMs": now_ms(),
        "branch": BRANCH,
        "requested": True,
        "implemented": bool(extra.pop("implemented", False)),
        "tested": bool(extra.pop("tested", False)),
        "deployed": bool(extra.pop("deployed", False)),
        "callable": bool(extra.pop("callable", False)),
        "delivered": bool(extra.pop("delivered", False)),
        "accepted": bool(extra.pop("accepted", False)),
        **extra,
    }
    with HISTORY.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, sort_keys=True) + "\n")
    atomic_json(LATEST, row)
    print(json.dumps(row, sort_keys=True), flush=True)
    return row


def run(cmd: list[str], cwd: Path | None = None, timeout: int = 900, env: dict | None = None) -> dict:
    try:
        process = subprocess.run(
            cmd,
            cwd=str(cwd or ROOT),
            text=True,
            capture_output=True,
            timeout=timeout,
            env=env,
        )
        return {"rc": process.returncode, "stdout": process.stdout[-30000:], "stderr": process.stderr[-20000:]}
    except subprocess.TimeoutExpired as exc:
        return {
            "rc": 124,
            "stdout": exc.stdout[-30000:] if isinstance(exc.stdout, str) else "",
            "stderr": (exc.stderr[-20000:] if isinstance(exc.stderr, str) else "") + f"\nTIMEOUT after {timeout}s",
        }


def command_exists(name: str) -> bool:
    return run(["sh", "-lc", f"command -v {shlex.quote(name)}"], timeout=15)["rc"] == 0


def stop_requested() -> bool:
    return STOP_FILE.exists()


def clear_stop() -> None:
    try:
        STOP_FILE.unlink()
    except FileNotFoundError:
        pass


def short_text(value, limit: int = 12000) -> str:
    text = value if isinstance(value, str) else json.dumps(value, sort_keys=True, default=str)
    return text[-limit:]


def repo_ok(root: Path) -> tuple[bool, str]:
    if not (root / ".git").exists():
        return False, f"not a git worktree: {root}"
    remote = run(["git", "remote", "get-url", "origin"], cwd=root, timeout=20)
    if remote["rc"] != 0:
        return False, "origin remote missing"
    url = remote["stdout"].strip()
    if "Valar05/home-center" not in url:
        return False, f"wrong origin: {url}"
    return True, url


def discover_source_repo() -> Path:
    explicit = os.environ.get("HC_REPO_ROOT", "").strip()
    candidates: list[Path] = []
    if explicit:
        candidates.append(Path(explicit).expanduser())
    candidates.extend([
        ROOT,
        Path.cwd(),
        Path.home() / "home-center",
        Path.home() / "src" / "home-center",
        Path.home() / "projects" / "home-center",
        Path.home() / "git" / "home-center",
        Path("/storage/emulated/0/Documents/home-center"),
        Path("/storage/emulated/0/Documents/GitHub/home-center"),
    ])
    seen: set[str] = set()
    for candidate in candidates:
        try:
            resolved = candidate.resolve()
        except OSError:
            continue
        for probe in [resolved, *resolved.parents]:
            key = str(probe)
            if key in seen:
                continue
            seen.add(key)
            ok, _ = repo_ok(probe)
            if ok:
                return probe
    raise RuntimeError("HOME_CENTER_REPO_NOT_FOUND: set HC_REPO_ROOT to an authenticated Valar05/home-center checkout")


def git_fetch_branch(source_repo: Path) -> str:
    fetched = run(["git", "fetch", "--prune", "origin", BRANCH], cwd=source_repo, timeout=180)
    if fetched["rc"] != 0:
        raise RuntimeError("git fetch failed: " + short_text(fetched["stderr"] or fetched["stdout"], 4000))
    head = run(["git", "rev-parse", f"origin/{BRANCH}"], cwd=source_repo, timeout=30)
    if head["rc"] != 0:
        raise RuntimeError("remote campaign branch missing after fetch")
    return head["stdout"].strip()


def remote_branch_head(source_repo: Path) -> str:
    result = run(["git", "ls-remote", "origin", f"refs/heads/{BRANCH}"], cwd=source_repo, timeout=60)
    if result["rc"] != 0 or not result["stdout"].strip():
        return ""
    return result["stdout"].split()[0]


def ensure_worktree() -> tuple[Path, str]:
    mkdirs()
    source_repo = discover_source_repo()
    head = git_fetch_branch(source_repo)
    if not MANAGED_WORKTREE.exists():
        result = run(["git", "worktree", "add", "--detach", str(MANAGED_WORKTREE), f"origin/{BRANCH}"], cwd=source_repo, timeout=180)
        if result["rc"] != 0:
            raise RuntimeError("managed worktree creation failed: " + short_text(result["stderr"] or result["stdout"], 4000))
    else:
        ok, detail = repo_ok(MANAGED_WORKTREE)
        if not ok:
            raise RuntimeError("campaign-owned worktree is unhealthy; refusing destructive recreation: " + detail)
        reset = run(["git", "reset", "--hard", f"origin/{BRANCH}"], cwd=MANAGED_WORKTREE, timeout=120)
        if reset["rc"] != 0:
            raise RuntimeError("managed worktree reset failed: " + short_text(reset["stderr"] or reset["stdout"], 4000))
        # Deliberately preserve untracked Gradle build caches in this campaign-owned
        # worktree. Remote workers mutate GitHub, not this worktree, so reset is the
        # source-of-truth operation and incremental builds survive resume.
    return MANAGED_WORKTREE, head


def source_contract(worktree: Path) -> dict:
    path = worktree / CONTRACT_REL
    if not path.exists():
        return {"ok": False, "rc": 2, "parsed": None, "stderr": f"missing {CONTRACT_REL}"}
    result = run([sys.executable, str(path)], cwd=worktree, timeout=120)
    parsed = None
    try:
        parsed = json.loads(result["stdout"])
    except Exception:
        pass
    return {"ok": result["rc"] == 0, "rc": result["rc"], "parsed": parsed, "stdout": result["stdout"], "stderr": result["stderr"]}


def failed_source_checks(contract: dict) -> list[str]:
    return list((contract.get("parsed") or {}).get("failed", []))


def sync_and_check() -> tuple[Path, str, dict]:
    worktree, head = ensure_worktree()
    return worktree, head, source_contract(worktree)


def next_attempt(stage: str) -> int:
    values = load_json(ATTEMPTS, {})
    attempt = int(values.get(stage, 0)) + 1
    values[stage] = attempt
    atomic_json(ATTEMPTS, values)
    return attempt


def read_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists() or not path.is_file():
        return values
    try:
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key, value = stripped.split("=", 1)
            values[key.strip()] = value.strip().strip("'\"")
    except OSError:
        pass
    return values


def discover_relay() -> dict:
    values = dict(os.environ)
    candidates = [
        Path("~/.config/home-center/chromium-throne.env").expanduser(),
        Path("~/.home-center/chromium-throne/relay.env").expanduser(),
        Path("~/.local/state/home-center/chromium-throne/relay.env").expanduser(),
        Path("~/.local/state/home-center/browser-porch/relay.env").expanduser(),
        Path("~/.local/state/home-center/browser-porch/throne.env").expanduser(),
    ]
    for path in candidates:
        for key, value in read_env_file(path).items():
            values.setdefault(key, value)
    base = (
        values.get("HC_THRONE_RELAY_URL")
        or values.get("HOME_CENTER_CHROMIUM_THRONE_RELAY_URL")
        or values.get("HOME_CENTER_BROWSER_PORCH_RELAY_URL")
        or ""
    ).strip().rstrip("/")
    capability = (
        values.get("HC_THRONE_CAPABILITY")
        or values.get("HOME_CENTER_CHROMIUM_THRONE_CAPABILITY")
        or ""
    ).strip()
    if base and not base.endswith("/v1/throne"):
        base += "/v1/throne"
    return {
        "ok": bool(base and len(capability) >= 32),
        "baseUrl": base or None,
        "capabilityPresent": len(capability) >= 32,
        "capability": capability,
        "searched": [str(path) for path in candidates],
    }


def relay_public(relay: dict) -> dict:
    return {key: value for key, value in relay.items() if key != "capability"}


def wait_for_relay_config(max_seconds: int = 75) -> dict:
    started = time.time()
    delay = 2
    relay = discover_relay()
    while time.time() - started < max_seconds and not stop_requested():
        relay = discover_relay()
        if relay["ok"]:
            return relay
        emit("relay-discovery", "retrying", "Chromium Throne relay authority is not discoverable yet; preserving the requested free-tab lane and retrying.", relay=relay_public(relay))
        time.sleep(delay)
        delay = min(20, delay * 2)
    return relay


def http_json(url: str, method: str, capability: str, payload: dict | None = None, timeout: int = 30) -> tuple[int, dict | None, str]:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        headers={
            "authorization": f"Bearer {capability}",
            "content-type": "application/json",
            "cache-control": "no-store",
        },
        method=method,
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8", errors="replace")
            return response.status, (json.loads(raw) if raw.strip() else None), raw
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            body = json.loads(raw)
        except Exception:
            body = None
        return exc.code, body, raw
    except urllib.error.URLError as exc:
        return 0, None, str(exc)


def commission_text(worktree: Path) -> tuple[str, str]:
    body = (worktree / COMMISSION_REL).read_text(encoding="utf-8")
    return hashlib.sha256(body.encode("utf-8")).hexdigest(), body


def relay_command_state(command_id: str) -> dict:
    relay = discover_relay()
    if not relay["ok"]:
        return {"ok": False, "state": "relay-missing"}
    status, body, raw = http_json(relay["baseUrl"] + "/status", "GET", relay["capability"], None, timeout=20)
    if status != 200 or not isinstance(body, dict):
        return {"ok": False, "state": "status-unreadable", "httpStatus": status, "detail": raw[-1000:]}
    command = next((item for item in (body.get("commands") or []) if item.get("commandId") == command_id), None)
    return {"ok": command is not None, "state": (command or {}).get("state", "unknown"), "command": command, "snapshot": body.get("snapshot")}


def active_dispatch(stage: str, source_head: str) -> dict | None:
    record = load_json(RELAY_STATE, {})
    if record.get("stage") != stage or record.get("sourceHeadAtDispatch") != source_head or not record.get("commandId"):
        return None
    state = relay_command_state(record["commandId"])
    if state.get("state") in ("queued", "leased"):
        return {**record, "resumed": True, "relayState": state.get("state")}
    return None


def dispatch_free_tab(worktree: Path, source_head: str, stage: str, issues: list[str]) -> dict:
    active = active_dispatch(stage, source_head)
    if active:
        return {"ok": True, **active}
    relay = wait_for_relay_config()
    if not relay["ok"]:
        return {
            "ok": False,
            "waiting": True,
            "error": "THRONE_RELAY_NOT_CONFIGURED",
            "detail": "The requested Chromium Throne free-tab lane exists in source but its live relay URL/capability is not discoverable on this body. No substitute worker lane was selected.",
            "relay": relay_public(relay),
        }
    digest, base_commission = commission_text(worktree)
    attempt = next_attempt(stage)
    command_id = f"vanguard-overlay-{stage}-{attempt}-{digest[:8]}-{source_head[:8]}"
    issue_text = "\n".join(f"- {short_text(item, 2500)}" for item in issues[:12]) or "- Continue the commissioned implementation from current evidence."
    appendix = f"""

## CAMPAIGN REPAIR APPENDIX — {stage} attempt {attempt}
This is continuation of the same commission, not a new mission. The campaign observed these current failures/evidence:
{issue_text}

Read the current remote branch before changing anything. Repair the failure class without regressing earlier constraints. Run the deterministic resurrection source contract, focused tests, Regnet QA, and Venice completion review; then push the SAME `campaign/vanguard-overlay-resurrection` branch. Repository/build evidence is not phone acceptance.
"""
    payload = {
        "commandId": command_id,
        "action": "swarm.enqueue",
        "source": "vanguard-overlay-campaign",
        "createdAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "jobs": [{
            "jobId": f"vanguard-overlay-{stage}-{attempt}-{digest[:8]}",
            "commission": (base_commission + appendix)[:31900],
            "context": (
                "VANGUARD // OVERLAY RESURRECTION. Preserve owner, requested Home Center overlay lineage, Chromium Throne free-tab lane, Adam exclusion, retention law, and evidence boundaries. "
                "Work only in campaign/vanguard-overlay-resurrection. The phone campaign owns physical build/install/acceptance."
            ),
        }],
    }
    pending = {
        "schema": "vanguard-overlay-relay-dispatch-v2",
        "stage": stage,
        "attempt": attempt,
        "commandId": command_id,
        "commissionSha256": digest,
        "sourceHeadAtDispatch": source_head,
        "relayBaseUrl": relay["baseUrl"],
        "status": "submitting",
        "issues": issues[:12],
        "atMs": now_ms(),
    }
    # Persist command identity before network submission so a campaign crash cannot
    # casually generate a second worker for an already accepted command.
    atomic_json(RELAY_STATE, pending)
    status, body, raw = http_json(relay["baseUrl"] + "/command", "POST", relay["capability"], payload, timeout=30)
    record = {**pending, "httpStatus": status, "response": body, "status": "submitted" if status in (200, 202) else "submit-failed"}
    atomic_json(RELAY_STATE, record)
    if status not in (200, 202):
        return {"ok": False, "waiting": status == 0, "error": "THRONE_DISPATCH_FAILED", "detail": raw[-3000:], **record}
    return {"ok": True, **record}


def wait_for_repair(command_id: str, baseline_head: str, timeout_seconds: int = REPAIR_ROUND_SECONDS) -> tuple[bool, str, str, dict]:
    source_repo = discover_source_repo()
    started = time.time()
    last_head = baseline_head
    last_contract: dict = {"ok": False, "parsed": None}
    terminal_seen_at: float | None = None
    next_heartbeat = 0.0
    while time.time() - started < timeout_seconds:
        if stop_requested():
            return False, "STOP_REQUESTED", last_head, last_contract
        head = remote_branch_head(source_repo)
        if head and head != last_head:
            last_head = head
            _, synced_head, last_contract = sync_and_check()
            emit(
                "free-tab-readback",
                "passed" if last_contract["ok"] else "contract-red",
                "A new remote worker commit was observed and read back through the deterministic source contract.",
                commandId=command_id,
                sourceHead=synced_head,
                failedChecks=failed_source_checks(last_contract),
                implemented=last_contract["ok"],
                tested=last_contract["ok"],
            )
            if last_contract["ok"]:
                return True, "NEW_GREEN_HEAD", synced_head, last_contract
        relay_state = relay_command_state(command_id)
        state = relay_state.get("state")
        if state in ("completed", "failed", "cancelled") and terminal_seen_at is None:
            terminal_seen_at = time.time()
        if terminal_seen_at is not None and time.time() - terminal_seen_at >= 30:
            if not last_contract.get("parsed"):
                _, synced_head, last_contract = sync_and_check()
                last_head = synced_head
                if synced_head != baseline_head and last_contract["ok"]:
                    return True, "TERMINAL_GREEN_HEAD", synced_head, last_contract
            return False, f"THRONE_{str(state).upper()}_NO_GREEN_REPAIR", last_head, last_contract
        if time.time() >= next_heartbeat:
            next_heartbeat = time.time() + 30
            emit(
                "free-tab",
                "waiting",
                "Chromium Throne repair is live; waiting for remote evidence rather than narrating completion.",
                commandId=command_id,
                sourceHead=last_head,
                relayState=state,
                elapsedSeconds=int(time.time() - started),
            )
        time.sleep(10)
    return False, "REPAIR_ROUND_TIMEOUT", last_head, last_contract


def repair_branch(stage: str, worktree: Path, head: str, issues: list[str], rounds: int = MAX_STAGE_REPAIR_ROUNDS) -> tuple[bool, Path, str, dict]:
    contract = source_contract(worktree)
    current_issues = list(issues)
    for round_no in range(1, rounds + 1):
        if stop_requested():
            return False, worktree, head, contract
        dispatch = dispatch_free_tab(worktree, head, stage, current_issues)
        if not dispatch["ok"]:
            if dispatch.get("waiting"):
                emit("free-tab", "waiting-relay", dispatch.get("detail", "Relay unavailable."), stage=stage, round=round_no, relay=dispatch.get("relay"))
                return False, worktree, head, contract
            emit("free-tab", "dispatch-failed", dispatch.get("detail", dispatch.get("error", "dispatch failed")), stage=stage, round=round_no)
            time.sleep(min(30, 2 ** round_no))
            continue
        emit("free-tab", "dispatched", "Bounded repair commission queued to the exact free-tab lane.", stage=stage, round=round_no, commandId=dispatch["commandId"], attempt=dispatch.get("attempt"), resumed=dispatch.get("resumed", False))
        repaired, outcome, observed_head, observed_contract = wait_for_repair(dispatch["commandId"], head)
        worktree, head, contract = sync_and_check()
        if repaired and head != dispatch["sourceHeadAtDispatch"] and contract["ok"]:
            return True, worktree, head, contract
        current_issues = [
            f"Previous {stage} repair outcome: {outcome}",
            *[f"source-contract: {item}" for item in failed_source_checks(contract)],
            *issues[:8],
        ]
        emit("repair", "continuing", "Repair round did not produce a new green branch head; carrying current evidence into another bounded attempt.", stage=stage, round=round_no, outcome=outcome, observedHead=observed_head, currentHead=head, failedChecks=failed_source_checks(contract))
        time.sleep(min(30, 2 ** round_no))
    return False, worktree, head, contract


def drive_source_to_green() -> tuple[Path, str, dict]:
    worktree, head, contract = sync_and_check()
    if contract["ok"]:
        return worktree, head, contract
    issues = [f"source-contract: {item}" for item in failed_source_checks(contract)]
    emit("source-contract", "needs-implementation", "Current overlay source is below the commissioned resurrection contract; opening bounded free-tab repair rounds.", sourceHead=head, failedChecks=failed_source_checks(contract))
    repaired, worktree, head, contract = repair_branch("source", worktree, head, issues, MAX_SOURCE_REPAIR_ROUNDS)
    if not repaired or not contract["ok"]:
        relay = discover_relay()
        if not relay["ok"]:
            raise RuntimeError("THRONE_RELAY_NOT_CONFIGURED")
        raise RuntimeError("SOURCE_REPAIR_ROUNDS_EXHAUSTED: " + ",".join(failed_source_checks(contract)))
    return worktree, head, contract


def current_head(worktree: Path) -> str:
    result = run(["git", "rev-parse", "HEAD"], cwd=worktree, timeout=20)
    return result["stdout"].strip() if result["rc"] == 0 else ""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def find_gradle(worktree: Path) -> list[str] | None:
    wrapper = worktree / PROJECT_REL / "gradlew"
    if wrapper.exists():
        return [str(wrapper)]
    explicit = os.environ.get("GRADLE_BIN", "").strip()
    if explicit and Path(explicit).exists():
        return [explicit]
    known = Path("/data/data/com.termux/files/usr/tmp/gradle-8.14.3/gradle-8.14.3/bin/gradle")
    if known.exists():
        return [str(known)]
    if command_exists("gradle"):
        return ["gradle"]
    return None


def body_probe(worktree: Path) -> dict:
    probe = worktree / "tools" / "home_center_shizuku_setup_probe.sh"
    if not probe.exists():
        return {"ok": False, "error": "CANONICAL_BODY_PROBE_MISSING"}
    BODY_PROBE_DIR.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ)
    env["HOME_CENTER_SHIZUKU_REPORT_DIR"] = str(BODY_PROBE_DIR)
    result = run(["sh", str(probe), "--report-only", "--no-network-install"], cwd=worktree, timeout=180, env=env)
    report = BODY_PROBE_DIR / "home_center_shizuku_readiness.json"
    parsed = load_json(report, {})
    return {"ok": result["rc"] == 0, "report": parsed, "stdout": result["stdout"], "stderr": result["stderr"], "path": str(report)}


def build_apk(worktree: Path) -> dict:
    project = worktree / PROJECT_REL
    head = current_head(worktree)
    cached = load_json(BUILD_STATE, {})
    cached_apk = Path(cached.get("apk", "")) if cached.get("apk") else None
    if cached.get("ok") and cached.get("sourceHead") == head and cached_apk and cached_apk.exists() and cached_apk.stat().st_size > 10000:
        actual = sha256_file(cached_apk)
        if actual == cached.get("sha256"):
            return {**cached, "reused": True, "truthBoundary": "Cached build hash was reverified on this body; deployment state remains separate."}

    gradle = find_gradle(worktree)
    if not gradle:
        return {"ok": False, "error": "GRADLE_MISSING", "detail": "No Gradle wrapper, GRADLE_BIN, known Termux Gradle, or gradle executable found.", "bodyProbe": body_probe(worktree)}
    if not command_exists("java"):
        return {"ok": False, "error": "JAVA_MISSING", "detail": "Java is required for the Android build.", "bodyProbe": body_probe(worktree)}

    args = gradle + [":app:testDebugUnitTest", ":app:assembleDebug", "--no-daemon"]
    aapt = Path("/data/data/com.termux/files/usr/bin/aapt2")
    if aapt.exists():
        args.append(f"-Pandroid.aapt2FromMavenOverride={aapt}")
    result = run(args, cwd=project, timeout=2400)
    apk = project / "app" / "build" / "outputs" / "apk" / "debug" / "app-debug.apk"
    if result["rc"] != 0 or not apk.exists() or apk.stat().st_size < 10000:
        return {"ok": False, "error": "ANDROID_BUILD_FAILED", "result": result, "apk": str(apk), "sourceHead": head}
    sha = sha256_file(apk)
    record = {
        "schema": "vanguard-overlay-build-v2",
        "ok": True,
        "apk": str(apk),
        "bytes": apk.stat().st_size,
        "sha256": sha,
        "sourceHead": head,
        "testAndBuildRc": result["rc"],
        "atMs": now_ms(),
        "reused": False,
        "truthBoundary": "Build/test success is build-body evidence, not phone deployment or acceptance.",
    }
    atomic_json(BUILD_STATE, record)
    return record


def build_with_retry(worktree: Path) -> dict:
    first = build_apk(worktree)
    if first.get("ok") or first.get("error") in ("GRADLE_MISSING", "JAVA_MISSING"):
        return first
    emit("build", "retrying", "Android build failed once; retrying the same deterministic build before spending a free-tab repair round.", error=first.get("error"), evidence=short_text(first, 5000), implemented=True)
    time.sleep(5)
    return build_apk(worktree)


def find_rish() -> str:
    explicit = os.environ.get("RISH", "").strip()
    candidates = [
        explicit,
        str(Path.home() / "rish"),
        str(Path.home() / "bin" / "rish"),
        str(Path.home() / ".local" / "bin" / "rish"),
        "/storage/emulated/0/Android/data/moe.shizuku.privileged.api/files/rish",
        "/storage/emulated/0/Documents/rish",
        "/storage/emulated/0/Download/rish",
    ]
    if command_exists("rish"):
        candidates.insert(0, run(["sh", "-lc", "command -v rish"], timeout=15)["stdout"].strip())
    for candidate in candidates:
        if not candidate:
            continue
        path = Path(candidate)
        if not path.exists() or not path.is_file():
            continue
        try:
            path.chmod(path.stat().st_mode | 0o100)
        except OSError:
            pass
        if os.access(path, os.X_OK):
            return str(path)
    return ""


def rish(command: str, timeout: int = 120) -> dict:
    binary = find_rish()
    if not binary:
        return {"rc": 127, "stdout": "", "stderr": "RISH_MISSING"}
    return run([binary, "-c", command], timeout=timeout)


def installed_apk_sha() -> dict:
    result = rish(
        f"set -e; p=$(pm path {PACKAGE} 2>/dev/null | sed -n 's/^package://p' | head -1); "
        "[ -n \"$p\" ]; sha256sum \"$p\"",
        timeout=90,
    )
    sha = ""
    for token in (result["stdout"] + " " + result["stderr"]).split():
        if len(token) == 64 and all(ch in "0123456789abcdef" for ch in token.lower()):
            sha = token.lower()
            break
    return {"ok": result["rc"] == 0 and bool(sha), "sha256": sha, "result": result}


def query_phone_state() -> dict:
    command = (
        f"echo __package__; pm list packages {PACKAGE}; "
        f"echo __overlay__; appops get {PACKAGE} SYSTEM_ALERT_WINDOW 2>/dev/null || true; "
        f"echo __record_audio__; pm check-permission {PACKAGE} android.permission.RECORD_AUDIO 2>/dev/null || true; "
        f"echo __notifications__; pm check-permission {PACKAGE} android.permission.POST_NOTIFICATIONS 2>/dev/null || true; "
        f"echo __state__; content query --uri content://com.homecenter.operatoroverlay.state/state 2>/dev/null || true"
    )
    result = rish(command, timeout=90)
    mkdirs()
    raw = result["stdout"] + "\n" + result["stderr"]
    PHONE_STATE.write_text(raw, encoding="utf-8")
    fields: dict[str, str] = {}
    for key in (
        "overlay_mode",
        "listening_state",
        "mic_active",
        "ring_write_bytes",
        "ring_capacity_bytes",
        "transcript_segment_count",
        "last_transcript_at_ms",
        "keep_count",
        "actual_sample_rate_hz",
        "latest_error",
    ):
        marker = key + "="
        if marker in raw:
            tail = raw.split(marker, 1)[1]
            fields[key] = tail.split(",", 1)[0].split()[0].strip()
    record_audio = raw.split("__record_audio__", 1)[1].split("__notifications__", 1)[0] if "__record_audio__" in raw and "__notifications__" in raw else ""
    notifications = raw.split("__notifications__", 1)[1].split("__state__", 1)[0] if "__notifications__" in raw and "__state__" in raw else ""
    return {
        "ok": result["rc"] == 0,
        "rishMissing": result["rc"] == 127,
        "packageInstalled": f"package:{PACKAGE}" in raw,
        "overlayAllowed": "SYSTEM_ALERT_WINDOW: allow" in raw or "SYSTEM_ALERT_WINDOW: allow;" in raw,
        "recordAudioGranted": "granted" in record_audio.lower(),
        "notificationsGranted": "granted" in notifications.lower(),
        "fields": fields,
        "raw": raw[-12000:],
    }


def int_field(state: dict, key: str) -> int:
    try:
        return int(str(state.get("fields", {}).get(key, "0")).strip())
    except ValueError:
        return 0


def grant_phone_authority() -> dict:
    results = []
    for command in (
        f"pm enable --user 0 {PACKAGE}",
        f"appops set {PACKAGE} SYSTEM_ALERT_WINDOW allow",
        f"pm grant {PACKAGE} android.permission.POST_NOTIFICATIONS",
        f"pm grant {PACKAGE} android.permission.RECORD_AUDIO",
    ):
        result = rish(command, timeout=60)
        results.append({"operation": command.split()[0:3], "rc": result["rc"], "stdout": result["stdout"][-1000:], "stderr": result["stderr"][-1000:]})
    return {"ok": all(row["rc"] == 0 for row in results[:2]), "results": results}


def install_apk(build: dict, worktree: Path) -> dict:
    if not find_rish():
        return {"ok": False, "error": "RISH_MISSING", "bodyProbe": body_probe(worktree)}
    expected = build["sha256"]
    installed = installed_apk_sha()
    state = query_phone_state()
    if installed.get("ok") and installed.get("sha256") == expected and state.get("packageInstalled"):
        grants = grant_phone_authority()
        # Preserve a successful existing user arm. Only bring MainActivity forward if
        # listening is not active and a visible ARM action may still be required.
        launch = None
        if state.get("fields", {}).get("mic_active") not in ("1", "true", "TRUE"):
            launch = rish(f"am start -n {PACKAGE}/.MainActivity", timeout=60)
        record = {
            "schema": "vanguard-overlay-deploy-v2",
            "ok": True,
            "status": "already-current",
            "sha256": expected,
            "sourceHead": build.get("sourceHead"),
            "installedSha256": installed.get("sha256"),
            "grants": grants,
            "launch": launch,
            "atMs": now_ms(),
            "truthBoundary": "Matching installed APK hash proves this build is deployed; live behavior still needs canaries.",
        }
        atomic_json(DEPLOY_STATE, record)
        return record

    apk = Path(build["apk"]).resolve()
    staged = "/data/local/tmp/vanguard-overlay.apk"
    stage = rish(f"set -e; cp {shlex.quote(str(apk))} {shlex.quote(staged)}; chmod 644 {shlex.quote(staged)}; sha256sum {shlex.quote(staged)}", timeout=180)
    staged_sha = ""
    for token in (stage["stdout"] + " " + stage["stderr"]).split():
        if len(token) == 64 and all(ch in "0123456789abcdef" for ch in token.lower()):
            staged_sha = token.lower()
    if stage["rc"] != 0 or staged_sha != expected:
        return {"ok": False, "error": "APK_STAGE_HASH_MISMATCH", "expected": expected, "actual": staged_sha, "stage": stage}
    install = rish(f"pm install -r {shlex.quote(staged)}", timeout=300)
    rish(f"rm -f {shlex.quote(staged)}", timeout=30)
    if install["rc"] != 0 or "Success" not in install["stdout"]:
        return {"ok": False, "error": "PM_INSTALL_FAILED", "install": install}
    grants = grant_phone_authority()
    launch = rish(f"am start -n {PACKAGE}/.MainActivity", timeout=60)
    observed = installed_apk_sha()
    if not observed.get("ok") or observed.get("sha256") != expected:
        return {"ok": False, "error": "INSTALLED_APK_HASH_MISMATCH", "expected": expected, "observed": observed, "install": install}
    record = {
        "schema": "vanguard-overlay-deploy-v2",
        "ok": launch["rc"] == 0,
        "status": "installed",
        "sha256": expected,
        "sourceHead": build.get("sourceHead"),
        "installedSha256": observed.get("sha256"),
        "install": install,
        "grants": grants,
        "launch": launch,
        "atMs": now_ms(),
        "truthBoundary": "APK install/hash verification proves deployment identity; it does not prove microphone, transcript, KEEP, or UX acceptance.",
    }
    atomic_json(DEPLOY_STATE, record)
    return record


def install_with_retry(build: dict, worktree: Path) -> dict:
    first = install_apk(build, worktree)
    if first.get("ok") or first.get("error") == "RISH_MISSING":
        return first
    emit("phone-install", "retrying", "Phone install/deploy verification failed once; refreshing grants/state and retrying before spending a source repair round.", error=first.get("error"), evidence=short_text(first, 5000), implemented=True, tested=True)
    grant_phone_authority()
    time.sleep(3)
    return install_apk(build, worktree)


def notify(title: str, content: str, notification_id: str) -> None:
    if command_exists("termux-notification"):
        run(["termux-notification", "--id", notification_id, "--title", title, "--content", content], timeout=30)


def phone_canary(wait_user_seconds: int = USER_ARM_SECONDS) -> dict:
    state = query_phone_state()
    if state.get("rishMissing"):
        return {"ok": False, "waitingUser": False, "error": "RISH_MISSING", "state": state}
    if not state["packageInstalled"] or not state["overlayAllowed"]:
        return {"ok": False, "waitingUser": False, "error": "PHONE_BASELINE_FAILED", "state": state}
    required = {"overlay_mode", "listening_state", "mic_active", "ring_write_bytes", "ring_capacity_bytes", "transcript_segment_count", "last_transcript_at_ms", "keep_count"}
    missing = sorted(required - set(state["fields"]))
    if missing:
        return {"ok": False, "waitingUser": False, "error": "STATE_PROVIDER_FIELDS_MISSING", "missing": missing, "state": state}
    if state["fields"].get("mic_active") not in ("1", "true", "TRUE"):
        notify(
            "Vanguard overlay: one deliberate tap required",
            "Open Home Center and ARM LISTENING. Android requires a visible user-initiated microphone start; the campaign will continue automatically afterward.",
            "vanguard-overlay-arm",
        )
        emit("phone-arm", "waiting-user", "APK is deployed and visible. Waiting only for Android's required deliberate ARM LISTENING action; no reinstall will occur on resume when the deployed hash still matches.", deployed=True, waitingFor="visible-user-arm", state=state["fields"])
        deadline = time.time() + wait_user_seconds
        while time.time() < deadline:
            if stop_requested():
                return {"ok": False, "waitingUser": False, "error": "STOP_REQUESTED", "state": state}
            time.sleep(3)
            state = query_phone_state()
            if state["fields"].get("mic_active") in ("1", "true", "TRUE"):
                break
        else:
            return {"ok": False, "waitingUser": True, "error": "WAITING_USER_ARM", "state": state}
    before = int_field(state, "ring_write_bytes")
    capacity = int_field(state, "ring_capacity_bytes")
    if capacity <= 0:
        return {"ok": False, "waitingUser": False, "error": "RING_CAPACITY_INVALID", "state": state}
    time.sleep(5)
    after_state = query_phone_state()
    after = int_field(after_state, "ring_write_bytes")
    if after <= before:
        return {"ok": False, "waitingUser": False, "error": "RING_NOT_ADVANCING", "before": before, "after": after, "state": after_state}
    return {
        "ok": True,
        "waitingUser": False,
        "beforeRingWriteBytes": before,
        "afterRingWriteBytes": after,
        "ringCapacityBytes": capacity,
        "state": after_state,
        "truthBoundary": "Initial live canary only: package + overlay authority + visible-user-armed microphone + bounded ring capacity + advancing write position. Remaining acceptance stays explicit.",
    }


def repairable_phone_error(error: str) -> bool:
    return error in {
        "STATE_PROVIDER_FIELDS_MISSING",
        "RING_CAPACITY_INVALID",
        "RING_NOT_ADVANCING",
        "PHONE_BASELINE_FAILED",
        "PM_INSTALL_FAILED",
        "INSTALLED_APK_HASH_MISMATCH",
    }


def worker_alive() -> tuple[bool, dict]:
    if not WORKER_META.exists():
        return False, {}
    try:
        meta = json.loads(WORKER_META.read_text(encoding="utf-8"))
        pid = int(meta.get("pid", 0))
        if pid <= 1:
            return False, meta
        os.kill(pid, 0)
        return True, meta
    except (OSError, ValueError, json.JSONDecodeError):
        return False, {}


def spawn_worker() -> int:
    mkdirs()
    alive, meta = worker_alive()
    if alive:
        emit("launcher", "already-running", "Campaign worker is already alive; no duplicate process was started.", worker=meta)
        return 0
    clear_stop()
    log_handle = LOG.open("a", encoding="utf-8")
    env = dict(os.environ)
    env["PYTHONUNBUFFERED"] = "1"
    process = subprocess.Popen(
        [sys.executable, str(SCRIPT), "__worker"],
        cwd=str(ROOT),
        stdout=log_handle,
        stderr=subprocess.STDOUT,
        stdin=subprocess.DEVNULL,
        start_new_session=True,
        env=env,
    )
    meta = {
        "schema": "vanguard-overlay-worker-v3",
        "pid": process.pid,
        "pgid": process.pid,
        "startedAtMs": now_ms(),
        "log": str(LOG),
        "state": str(STATE),
    }
    atomic_json(WORKER_META, meta)
    emit(
        "launcher",
        "running",
        "Campaign worker started in an isolated process group; the operator shell is free.",
        worker=meta,
        controls=["vanguard-overlay status", "vanguard-overlay follow", "vanguard-overlay stop", "vanguard-overlay resume", "vanguard-overlay receipts"],
    )
    return 0


def stop_worker() -> int:
    mkdirs()
    STOP_FILE.write_text(str(now_ms()) + "\n", encoding="utf-8")
    alive, meta = worker_alive()
    if not alive:
        emit("stop", "stopped", "No live campaign process exists; STOP intent is persisted for stale/restarted workers.")
        return 0
    pgid = int(meta.get("pgid") or meta.get("pid"))
    try:
        os.killpg(pgid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    deadline = time.time() + 5
    while time.time() < deadline:
        alive, _ = worker_alive()
        if not alive:
            emit("stop", "stopped", "Entire campaign process group stopped with TERM.", worker=meta)
            return 0
        time.sleep(0.2)
    try:
        os.killpg(pgid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    time.sleep(0.3)
    alive, _ = worker_alive()
    emit("stop", "stopped" if not alive else "failed", "Campaign process group required bounded KILL escalation.", worker=meta)
    return 0 if not alive else 2


def status() -> int:
    mkdirs()
    latest = load_json(LATEST, {"schema": "vanguard-overlay-campaign-v3", "phase": "never-run", "status": "idle"})
    alive, meta = worker_alive()
    elapsed = max(0, now_ms() - int(meta.get("startedAtMs", now_ms()))) if alive else None
    output = {
        "latest": latest,
        "workerAlive": alive,
        "worker": meta or None,
        "elapsedMs": elapsed,
        "heartbeatAgeMs": max(0, now_ms() - int(latest.get("atMs", now_ms()))) if latest.get("atMs") else None,
        "paths": {
            "state": str(STATE),
            "log": str(LOG),
            "history": str(HISTORY),
            "latest": str(LATEST),
            "managedWorktree": str(MANAGED_WORKTREE),
            "relay": str(RELAY_STATE),
            "build": str(BUILD_STATE),
            "deploy": str(DEPLOY_STATE),
        },
    }
    print(json.dumps(output, indent=2, sort_keys=True))
    return 0


def receipts(limit: int) -> int:
    if not HISTORY.exists():
        print("[]")
        return 0
    rows = HISTORY.read_text(encoding="utf-8", errors="replace").splitlines()[-max(1, limit):]
    print("[\n" + ",\n".join(rows) + "\n]")
    return 0


def follow() -> int:
    mkdirs()
    LOG.touch(exist_ok=True)
    try:
        with LOG.open("r", encoding="utf-8", errors="replace") as handle:
            handle.seek(0, os.SEEK_END)
            while True:
                line = handle.readline()
                if line:
                    print(line, end="", flush=True)
                    continue
                alive, _ = worker_alive()
                if not alive:
                    rest = handle.read()
                    if rest:
                        print(rest, end="", flush=True)
                    return 0
                time.sleep(0.4)
    except KeyboardInterrupt:
        print("\nFOLLOW DETACHED — the campaign worker was NOT stopped.", file=sys.stderr)
        return 130


def canary_transport_child(path: str, expected: str) -> int:
    data = Path(path).read_bytes()
    if hashlib.sha256(data).hexdigest() != expected:
        print("TRANSPORT_HASH_MISMATCH")
        return 2
    print("TRANSPORT_OK")
    return 0


def canary_tree_child(pid_file: str) -> int:
    child = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(300)"],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    Path(pid_file).write_text(str(child.pid) + "\n", encoding="utf-8")

    def reap_and_exit(_signum, _frame):
        try:
            child.wait(timeout=2)
        except subprocess.TimeoutExpired:
            try:
                child.terminate()
                child.wait(timeout=1)
            except Exception:
                try:
                    child.kill()
                    child.wait(timeout=1)
                except Exception:
                    pass
        raise SystemExit(0)

    signal.signal(signal.SIGTERM, reap_and_exit)
    signal.signal(signal.SIGINT, reap_and_exit)
    try:
        child.wait(timeout=300)
    except subprocess.TimeoutExpired:
        reap_and_exit(signal.SIGTERM, None)
    return 0


def pid_exists(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def campaign_canary() -> int:
    mkdirs()
    inert_marker = STATE / "SHOULD_NOT_EXIST"
    try:
        inert_marker.unlink()
    except FileNotFoundError:
        pass
    payload = "quotes ' \" / Unicode Ritsu 雪 / dollar $HOME / literal $(touch SHOULD_NOT_EXIST) / multiline\nsecond line\n"
    payload_path = STATE / "transport-canary.txt"
    payload_path.write_text(payload, encoding="utf-8")
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    transported = run([sys.executable, str(SCRIPT), "__canary_transport", str(payload_path), digest], timeout=30)
    transport_ok = transported["rc"] == 0 and "TRANSPORT_OK" in transported["stdout"] and not inert_marker.exists()

    pid_file = STATE / "tree-canary-child.pid"
    try:
        pid_file.unlink()
    except FileNotFoundError:
        pass
    tree = subprocess.Popen(
        [sys.executable, str(SCRIPT), "__canary_tree", str(pid_file)],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    deadline = time.time() + 5
    while time.time() < deadline and not pid_file.exists():
        time.sleep(0.05)
    grandchild_pid = int(pid_file.read_text().strip()) if pid_file.exists() else 0
    try:
        os.killpg(tree.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    try:
        tree.wait(timeout=4)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(tree.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        tree.wait(timeout=3)
    time.sleep(0.2)
    process_tree_stop_ok = tree.returncode is not None and (grandchild_pid <= 0 or not pid_exists(grandchild_pid))

    row = emit(
        "campaign-canary",
        "passed" if transport_ok and process_tree_stop_ok else "failed",
        "Inert prompt transport and whole-process-group STOP canaries passed." if transport_ok and process_tree_stop_ok else "Campaign transport/process-isolation canary failed.",
        transportSafe=transport_ok,
        processTreeStop=process_tree_stop_ok,
        transportSha256=digest,
        implemented=True,
        tested=transport_ok and process_tree_stop_ok,
    )
    return 0 if row["status"] == "passed" else 3


def install_command() -> int:
    mkdirs()
    worktree, head = ensure_worktree()
    prefix = os.environ.get("PREFIX", "").strip()
    preferred = Path(prefix) / "bin" if prefix else Path.home() / "bin"
    preferred.mkdir(parents=True, exist_ok=True)
    if not os.access(preferred, os.W_OK):
        preferred = Path.home() / "bin"
        preferred.mkdir(parents=True, exist_ok=True)
    wrapper = preferred / "vanguard-overlay"
    campaign_script = worktree / "tools" / "vanguard_overlay_campaign.py"
    wrapper.write_text(
        "#!/data/data/com.termux/files/usr/bin/bash\n"
        "set -euo pipefail\n"
        f"export HC_VANGUARD_OVERLAY_STATE={shlex.quote(str(STATE))}\n"
        f"exec {shlex.quote(sys.executable)} {shlex.quote(str(campaign_script))} \"$@\"\n",
        encoding="utf-8",
    )
    wrapper.chmod(0o755)
    emit("install-command", "ready", "Stable vanguard-overlay entrypoint installed against the campaign-owned worktree.", command=str(wrapper), sourceHead=head, implemented=True, callable=True)
    print(str(wrapper))
    return 0


def doctor() -> int:
    mkdirs()
    checks: list[dict] = []
    source = None
    try:
        source = discover_source_repo()
        ok, remote = repo_ok(source)
        head = remote_branch_head(source) if ok else ""
        checks.append({"check": "home-center-repo", "ok": ok, "detail": remote, "path": str(source)})
        checks.append({"check": "campaign-branch", "ok": bool(head), "detail": head or "remote branch not reachable"})
    except Exception as exc:
        checks.append({"check": "home-center-repo", "ok": False, "detail": str(exc)})
        checks.append({"check": "campaign-branch", "ok": False, "detail": "repo unavailable"})
    relay = discover_relay()
    checks.append({"check": "chromium-throne-relay", "ok": relay["ok"], "detail": relay_public(relay)})
    rish_bin = find_rish()
    checks.append({"check": "rish-shizuku", "ok": bool(rish_bin), "detail": rish_bin or "missing"})
    java_ok = command_exists("java")
    checks.append({"check": "java", "ok": java_ok, "detail": "required for phone-local Android build"})
    probe_worktree = MANAGED_WORKTREE if MANAGED_WORKTREE.exists() else (source or ROOT)
    gradle_ok = bool(find_gradle(probe_worktree))
    checks.append({"check": "gradle", "ok": gradle_ok, "detail": "wrapper / GRADLE_BIN / known Termux Gradle / system Gradle"})
    body = body_probe(probe_worktree) if (probe_worktree / "tools" / "home_center_shizuku_setup_probe.sh").exists() else None
    alive, meta = worker_alive()
    result = {
        "schema": "vanguard-overlay-doctor-v3",
        "okForRepositoryCampaign": bool(checks[0]["ok"] and checks[1]["ok"]),
        "okForAutomaticFreeTabDispatch": relay["ok"],
        "okForPhoneDeploy": bool(rish_bin and java_ok and gradle_ok),
        "workerAlive": alive,
        "worker": meta or None,
        "checks": checks,
        "canonicalBodyProbe": body,
        "stateDir": str(STATE),
        "truthBoundary": "Doctor reports actual lanes. A missing lane is a precise boundary and never authority for an adjacent substitute.",
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["okForRepositoryCampaign"] else 2


def build_failure_issues(build: dict) -> list[str]:
    return [
        f"Android build failure: {build.get('error', 'unknown')}",
        short_text(build.get("result", {}).get("stdout", ""), 5000),
        short_text(build.get("result", {}).get("stderr", ""), 5000),
    ]


def phone_failure_issues(stage: str, evidence: dict) -> list[str]:
    return [
        f"{stage} failure: {evidence.get('error', evidence.get('status', 'unknown'))}",
        short_text(evidence, 9000),
    ]


def worker_main() -> int:
    try:
        emit("worker", "running", "Advancing the same Vanguard overlay resurrection campaign.")
        worktree, head, contract = drive_source_to_green()
        if stop_requested():
            emit("worker", "stopped", "STOP requested after source repair and before build/deploy.", implemented=contract["ok"], tested=contract["ok"])
            return EXIT_STOPPED

        for pass_no in range(1, MAX_END_TO_END_PASSES + 1):
            worktree, head, contract = sync_and_check()
            if not contract["ok"]:
                repaired, worktree, head, contract = repair_branch("source-regression", worktree, head, [f"source-contract: {item}" for item in failed_source_checks(contract)])
                if not repaired:
                    raise RuntimeError("SOURCE_REPAIR_ROUNDS_EXHAUSTED: " + ",".join(failed_source_checks(contract)))
            emit("source-contract", "passed", "Repository source satisfies the resurrection architecture contract. Source truth remains below phone truth.", passNo=pass_no, sourceHead=head, implemented=True, tested=True)

            build = build_with_retry(worktree)
            if not build.get("ok"):
                if build.get("error") in ("GRADLE_MISSING", "JAVA_MISSING"):
                    emit("build", "body-blocked", build.get("detail", build.get("error")), passNo=pass_no, evidence=build, implemented=True, tested=False)
                    return EXIT_BODY_BLOCKED
                emit("build", "repairing", "Persistent Android build failure is feeding back into the exact free-tab repair lane.", passNo=pass_no, error=build.get("error"), evidence=short_text(build, 7000), implemented=True, tested=False)
                repaired, worktree, head, contract = repair_branch("build", worktree, head, build_failure_issues(build))
                if repaired:
                    continue
                emit("build", "blocked", "Build repair rounds exhausted without a new green branch head.", passNo=pass_no, evidence=build, implemented=True, tested=False)
                return EXIT_BUILD_FAILED
            emit("build", "passed", "Android test/build produced or revalidated a hashed APK; deployment is still a separate state.", passNo=pass_no, apk=build["apk"], sha256=build["sha256"], sourceHead=build["sourceHead"], reused=build.get("reused", False), implemented=True, tested=True)
            if stop_requested():
                emit("worker", "stopped", "STOP requested before phone mutation.", implemented=True, tested=True)
                return EXIT_STOPPED

            deploy = install_with_retry(build, worktree)
            if not deploy.get("ok"):
                if deploy.get("error") == "RISH_MISSING":
                    emit("phone-install", "body-blocked", "Shizuku/rish authority is genuinely unavailable after canonical discovery/probe. No adjacent deployment lane was selected.", evidence=deploy, implemented=True, tested=True, deployed=False)
                    return EXIT_BODY_BLOCKED
                if repairable_phone_error(str(deploy.get("error"))):
                    emit("phone-install", "repairing", "Persistent deployment failure is feeding exact phone evidence back to the free-tab repair lane.", passNo=pass_no, error=deploy.get("error"), evidence=short_text(deploy, 7000), implemented=True, tested=True, deployed=False)
                    repaired, worktree, head, contract = repair_branch("phone-install", worktree, head, phone_failure_issues("phone-install", deploy))
                    if repaired:
                        continue
                emit("phone-install", "blocked", deploy.get("error", "Phone install failed"), passNo=pass_no, evidence=deploy, implemented=True, tested=True, deployed=False)
                return EXIT_PHONE_FAILED
            emit("phone-install", "deployed", "Phone APK identity is verified. Matching deployed builds are not reinstalled on resume, preserving any successful user arm.", passNo=pass_no, status=deploy.get("status"), sha256=deploy.get("sha256"), sourceHead=deploy.get("sourceHead"), implemented=True, tested=True, deployed=True)

            canary = phone_canary()
            if not canary.get("ok"):
                if canary.get("waitingUser"):
                    emit("phone-canary", "waiting-user", "Deployment remains intact; waiting on Android's required visible ARM LISTENING action. Resume will hash-check and skip reinstall when this APK still matches.", passNo=pass_no, evidence=canary, implemented=True, tested=True, deployed=True)
                    return EXIT_WAITING_USER
                if canary.get("error") == "RISH_MISSING":
                    emit("phone-canary", "body-blocked", "Shizuku/rish disappeared during live verification; canonical phone authority must be restored before evidence can continue.", passNo=pass_no, evidence=canary, implemented=True, tested=True, deployed=True)
                    return EXIT_BODY_BLOCKED
                if repairable_phone_error(str(canary.get("error"))):
                    emit("phone-canary", "repairing", "Deterministic live phone canary failed; feeding the actual phone evidence back into a bounded free-tab repair round.", passNo=pass_no, error=canary.get("error"), evidence=short_text(canary, 8000), implemented=True, tested=True, deployed=True)
                    repaired, worktree, head, contract = repair_branch("phone-canary", worktree, head, phone_failure_issues("phone-canary", canary))
                    if repaired:
                        continue
                emit("phone-canary", "failed", canary.get("error", "Phone canary failed"), passNo=pass_no, evidence=canary, implemented=True, tested=True, deployed=True)
                return EXIT_PHONE_FAILED

            emit(
                "phone-canary",
                "passed-initial",
                "Live phone proved installed package, overlay authority, visible-user-armed microphone activity, bounded ring capacity, and advancing ring state. Full product acceptance remains intentionally open.",
                passNo=pass_no,
                evidence=canary,
                implemented=True,
                tested=True,
                deployed=True,
                callable=True,
                delivered=True,
                accepted=False,
                remainingAcceptance=[
                    "full-bubble-hidden-notification-restore",
                    "stop-releases-microphone-and-ring-stops",
                    "speech-produces-sample-mapped-transcript",
                    "KEEP-LAST-60s-produces-exactly-one-durable-audio-text-bundle",
                    "rolling-raw-and-text-remain-bounded-through-wrap",
                    "reboot-leaves-listening-disarmed",
                    "Adam-absent-from-live-runtime",
                    "Ritsu-opinion-layer-failure-does-not-break-capture-control",
                    "battery-thermal-observation",
                    "Drew-acceptance",
                ],
            )
            return 0

        emit("worker", "blocked", "End-to-end repair pass budget exhausted before the initial live phone canary passed.", implemented=True)
        return EXIT_PHONE_FAILED
    except RuntimeError as exc:
        message = str(exc)
        if message == "STOP_REQUESTED":
            emit("worker", "stopped", "STOP requested; campaign state is preserved.")
            return EXIT_STOPPED
        if "THRONE_RELAY_NOT_CONFIGURED" in message:
            emit("worker", "waiting-relay", "Exact blocker preserved: the requested Chromium Throne free-tab relay authority is not discoverable. No adjacent worker lane was substituted.")
            return EXIT_WAITING_RELAY
        if "SOURCE_REPAIR_ROUNDS_EXHAUSTED" in message:
            emit("worker", "source-blocked", message)
            return EXIT_SOURCE_FAILED
        emit("worker", "failed", f"RuntimeError: {message}")
        return 70
    except Exception as exc:
        emit("worker", "failed", f"{type(exc).__name__}: {exc}")
        return 70


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="vanguard-overlay", description="Vanguard Home Center overlay resurrection campaign")
    subs = parser.add_subparsers(dest="cmd", required=True)
    for name in ("run", "resume", "status", "follow", "stop", "doctor", "canary", "install", "source", "phone", "dispatch", "__worker"):
        subs.add_parser(name)
    receipt_parser = subs.add_parser("receipts")
    receipt_parser.add_argument("--limit", type=int, default=30)
    transport = subs.add_parser("__canary_transport")
    transport.add_argument("path")
    transport.add_argument("sha256")
    tree = subs.add_parser("__canary_tree")
    tree.add_argument("pid_file")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.cmd in ("run", "resume"):
        return spawn_worker()
    if args.cmd == "status":
        return status()
    if args.cmd == "follow":
        return follow()
    if args.cmd == "stop":
        return stop_worker()
    if args.cmd == "doctor":
        return doctor()
    if args.cmd == "canary":
        return campaign_canary()
    if args.cmd == "install":
        return install_command()
    if args.cmd == "receipts":
        return receipts(args.limit)
    if args.cmd == "__worker":
        return worker_main()
    if args.cmd == "__canary_transport":
        return canary_transport_child(args.path, args.sha256)
    if args.cmd == "__canary_tree":
        return canary_tree_child(args.pid_file)
    if args.cmd == "source":
        worktree, head, contract = sync_and_check()
        emit("source-contract", "passed" if contract["ok"] else "failed", "Manual source-contract probe.", sourceHead=head, failedChecks=failed_source_checks(contract), implemented=contract["ok"], tested=contract["ok"])
        return 0 if contract["ok"] else 1
    if args.cmd == "phone":
        state = query_phone_state()
        print(json.dumps(state, indent=2, sort_keys=True))
        return 0 if state["packageInstalled"] else 1
    if args.cmd == "dispatch":
        worktree, head, contract = sync_and_check()
        result = dispatch_free_tab(worktree, head, "manual-source", [f"source-contract: {item}" for item in failed_source_checks(contract)])
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result.get("ok") else 1
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
