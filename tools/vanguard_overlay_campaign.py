#!/data/data/com.termux/files/usr/bin/python
"""VANGUARD // OVERLAY RESURRECTION operator campaign.

The campaign owns orchestration, not microphone policy. It preserves an operator-owned
checkout, creates a private managed worktree, drives the exact Chromium Throne free-tab
lane until the source contract is green, builds on the authorized phone body when
possible, installs through Shizuku/rish, and collects phone evidence.

It NEVER arms the microphone from boot/background shell. Android must receive the
visible user action required for microphone foreground-service creation. Repository,
build, deployment, callable, delivered, and accepted states remain distinct.
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
PHONE_STATE = STATE / "phone-state.txt"
BUILD_STATE = STATE / "build.json"

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

MAX_SOURCE_REPAIR_ROUNDS = int(os.environ.get("HC_VANGUARD_OVERLAY_SOURCE_ROUNDS", "4"))
SOURCE_ROUND_SECONDS = int(os.environ.get("HC_VANGUARD_OVERLAY_SOURCE_ROUND_SECONDS", "2700"))
USER_ARM_SECONDS = int(os.environ.get("HC_VANGUARD_OVERLAY_USER_ARM_SECONDS", "600"))


def now_ms() -> int:
    return int(time.time() * 1000)


def mkdirs() -> None:
    STATE.mkdir(parents=True, exist_ok=True)


def atomic_json(path: Path, obj: dict) -> None:
    mkdirs()
    tmp = path.with_suffix(path.suffix + ".part")
    tmp.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def emit(phase: str, status: str, detail: str, **extra) -> dict:
    mkdirs()
    row = {
        "schema": "vanguard-overlay-campaign-v2",
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
    with HISTORY.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, sort_keys=True) + "\n")
    atomic_json(LATEST, row)
    print(json.dumps(row, sort_keys=True), flush=True)
    return row


def run(cmd: list[str], cwd: Path | None = None, timeout: int = 900, env: dict | None = None) -> dict:
    try:
        p = subprocess.run(
            cmd,
            cwd=str(cwd or ROOT),
            text=True,
            capture_output=True,
            timeout=timeout,
            env=env,
        )
        return {"rc": p.returncode, "stdout": p.stdout[-30000:], "stderr": p.stderr[-20000:]}
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


def repo_ok(root: Path) -> tuple[bool, str]:
    git_marker = root / ".git"
    if not git_marker.exists():
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
    raise RuntimeError("HOME_CENTER_REPO_NOT_FOUND: no authenticated Valar05/home-center checkout was found; set HC_REPO_ROOT to the real checkout")


def git_fetch_branch(source_repo: Path) -> str:
    fetched = run(["git", "fetch", "--prune", "origin", BRANCH], cwd=source_repo, timeout=180)
    if fetched["rc"] != 0:
        raise RuntimeError("git fetch failed: " + (fetched["stderr"] or fetched["stdout"])[-4000:])
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
            raise RuntimeError("managed worktree creation failed: " + (result["stderr"] or result["stdout"])[-4000:])
    else:
        ok, detail = repo_ok(MANAGED_WORKTREE)
        if not ok:
            raise RuntimeError("campaign-owned worktree is unhealthy; refusing to delete/recreate it automatically: " + detail)
        reset = run(["git", "reset", "--hard", f"origin/{BRANCH}"], cwd=MANAGED_WORKTREE, timeout=120)
        if reset["rc"] != 0:
            raise RuntimeError("managed worktree reset failed: " + (reset["stderr"] or reset["stdout"])[-4000:])
        clean = run(
            ["git", "clean", "-fd", "--", "android/operator-overlay", "tools/vanguard_overlay_contract_test.py", "tools/vanguard_overlay_campaign.py", "campaigns/vanguard-overlay-resurrection"],
            cwd=MANAGED_WORKTREE,
            timeout=60,
        )
        if clean["rc"] != 0:
            raise RuntimeError("managed worktree clean failed: " + clean["stderr"][-2000:])
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
    return {
        "ok": result["rc"] == 0,
        "rc": result["rc"],
        "parsed": parsed,
        "stdout": result["stdout"],
        "stderr": result["stderr"],
    }


def failed_source_checks(contract: dict) -> list[str]:
    return list((contract.get("parsed") or {}).get("failed", []))


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
        "searched": [str(p) for p in candidates],
    }


def relay_public(relay: dict) -> dict:
    return {k: v for k, v in relay.items() if k != "capability"}


def wait_for_relay_config(max_seconds: int = 75) -> dict:
    started = time.time()
    delay = 2
    last = discover_relay()
    while time.time() - started < max_seconds and not stop_requested():
        last = discover_relay()
        if last["ok"]:
            return last
        emit("relay-discovery", "retrying", "Chromium Throne relay authority is not discoverable yet; preserving the requested free-tab lane and retrying.", relay=relay_public(last))
        time.sleep(delay)
        delay = min(20, delay * 2)
    return last


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


def dispatch_free_tab(worktree: Path, source_head: str, round_no: int, failures: list[str]) -> dict:
    relay = wait_for_relay_config()
    if not relay["ok"]:
        return {
            "ok": False,
            "waiting": True,
            "error": "THRONE_RELAY_NOT_CONFIGURED",
            "detail": "The requested Chromium Throne free-tab lane exists in source but its live relay URL/capability is not discoverable on this body. Campaign state is durable; no substitute worker lane was selected.",
            "relay": relay_public(relay),
        }
    digest, base_commission = commission_text(worktree)
    command_id = f"vanguard-overlay-r{round_no}-{digest[:10]}-{source_head[:10]}"
    repair_appendix = ""
    if round_no > 1:
        repair_appendix = (
            "\n\n## CAMPAIGN REPAIR APPENDIX\n"
            "This is continuation, not a new mission. The previous branch head still failed these deterministic source-contract checks:\n"
            + "\n".join(f"- {item}" for item in failures)
            + "\nRead current branch state, repair the failures without regressing earlier constraints, rerun the contract, Regnet QA, Venice, then push the same branch.\n"
        )
    payload = {
        "commandId": command_id,
        "action": "swarm.enqueue",
        "source": "vanguard-overlay-campaign",
        "createdAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "jobs": [{
            "jobId": f"vanguard-overlay-implementation-r{round_no}-{digest[:10]}",
            "commission": base_commission + repair_appendix,
            "context": (
                "VANGUARD // OVERLAY RESURRECTION. Preserve the exact owner/tool/lane/exclusions/evidence contract. "
                "Work only in campaign/vanguard-overlay-resurrection. Read the persisted PLAN_ALLOWED receipt first. "
                "This is a free ChatGPT tab repository worker; the phone campaign owns build/install/physical acceptance."
            ),
        }],
    }
    status, body, raw = http_json(relay["baseUrl"] + "/command", "POST", relay["capability"], payload, timeout=30)
    record = {
        "schema": "vanguard-overlay-relay-dispatch-v1",
        "commandId": command_id,
        "round": round_no,
        "commissionSha256": digest,
        "sourceHeadAtDispatch": source_head,
        "relayBaseUrl": relay["baseUrl"],
        "httpStatus": status,
        "response": body,
        "failedChecksAtDispatch": failures,
        "atMs": now_ms(),
    }
    atomic_json(RELAY_STATE, record)
    if status not in (200, 202):
        return {"ok": False, "waiting": status == 0, "error": "THRONE_DISPATCH_FAILED", "detail": raw[-3000:], **record}
    return {"ok": True, **record}


def relay_command_state(command_id: str) -> dict:
    relay = discover_relay()
    if not relay["ok"]:
        return {"ok": False, "state": "relay-missing"}
    status, body, raw = http_json(relay["baseUrl"] + "/status", "GET", relay["capability"], None, timeout=20)
    if status != 200 or not isinstance(body, dict):
        return {"ok": False, "state": "status-unreadable", "httpStatus": status, "detail": raw[-1000:]}
    commands = body.get("commands") or []
    row = next((item for item in commands if item.get("commandId") == command_id), None)
    return {"ok": row is not None, "state": (row or {}).get("state", "unknown"), "command": row, "snapshot": body.get("snapshot")}


def sync_and_check() -> tuple[Path, str, dict]:
    worktree, head = ensure_worktree()
    return worktree, head, source_contract(worktree)


def wait_round_for_green(command_id: str, baseline_head: str, round_seconds: int) -> tuple[bool, str, dict]:
    source_repo = discover_source_repo()
    started = time.time()
    last_head = baseline_head
    last_contract: dict = {"ok": False, "parsed": None}
    terminal_seen_at: float | None = None
    next_heartbeat = 0.0
    while time.time() - started < round_seconds:
        if stop_requested():
            return False, "STOP_REQUESTED", last_contract
        head = remote_branch_head(source_repo)
        if head and head != last_head:
            last_head = head
            _, synced_head, last_contract = sync_and_check()
            emit(
                "source-review",
                "passed" if last_contract["ok"] else "repairing",
                "Chromium Throne pushed a new branch head; deterministic source contract re-evaluated.",
                commandId=command_id,
                sourceHead=synced_head,
                failedChecks=failed_source_checks(last_contract),
                implemented=last_contract["ok"],
                tested=last_contract["ok"],
            )
            if last_contract["ok"]:
                return True, synced_head, last_contract
        relay_state = relay_command_state(command_id)
        state = relay_state.get("state")
        if state in ("completed", "failed", "cancelled") and terminal_seen_at is None:
            terminal_seen_at = time.time()
        # Give a terminal browser response a short push/readback grace period; if
        # the contract is still red afterward, the next round carries exact failures.
        if terminal_seen_at is not None and time.time() - terminal_seen_at >= 30:
            if not last_contract.get("parsed"):
                _, synced_head, last_contract = sync_and_check()
                last_head = synced_head
                if last_contract["ok"]:
                    return True, synced_head, last_contract
            return False, f"THRONE_{str(state).upper()}_CONTRACT_RED", last_contract
        if time.time() >= next_heartbeat:
            next_heartbeat = time.time() + 30
            emit(
                "free-tab",
                "waiting",
                "Chromium Throne implementation round is live; waiting for evidence, not narrating completion.",
                commandId=command_id,
                sourceHead=last_head,
                relayState=state,
                elapsedSeconds=int(time.time() - started),
                failedChecks=failed_source_checks(last_contract),
            )
        time.sleep(10)
    return False, "SOURCE_ROUND_TIMEOUT", last_contract


def drive_source_to_green() -> tuple[Path, str, dict]:
    worktree, head, contract = sync_and_check()
    if contract["ok"]:
        return worktree, head, contract
    failures = failed_source_checks(contract)
    emit("source-contract", "needs-implementation", "Current retired overlay fails the commissioned resurrection contract; beginning governed free-tab repair rounds.", sourceHead=head, failedChecks=failures)
    for round_no in range(1, MAX_SOURCE_REPAIR_ROUNDS + 1):
        if stop_requested():
            raise RuntimeError("STOP_REQUESTED")
        dispatch = dispatch_free_tab(worktree, head, round_no, failures)
        if not dispatch["ok"]:
            if dispatch.get("waiting"):
                emit("free-tab", "waiting-relay", dispatch["detail"], round=round_no, relay=dispatch.get("relay"))
                raise RuntimeError("THRONE_RELAY_NOT_CONFIGURED")
            emit("free-tab", "dispatch-failed", dispatch.get("detail", dispatch.get("error", "dispatch failed")), round=round_no)
            time.sleep(min(60, 2 ** round_no))
            continue
        emit("free-tab", "dispatched", "Bounded implementation/repair commission queued to the requested free-tab lane.", commandId=dispatch["commandId"], round=round_no, commissionSha256=dispatch["commissionSha256"])
        green, outcome, observed = wait_round_for_green(dispatch["commandId"], head, SOURCE_ROUND_SECONDS)
        worktree, head, contract = sync_and_check()
        if green or contract["ok"]:
            return worktree, head, contract
        failures = failed_source_checks(contract) or failed_source_checks(observed)
        emit("source-repair", "continuing", "Source contract is still red; carrying exact failures into the next bounded free-tab repair round.", round=round_no, outcome=outcome, sourceHead=head, failedChecks=failures)
        time.sleep(min(60, 2 ** round_no))
    raise RuntimeError("SOURCE_REPAIR_ROUNDS_EXHAUSTED: " + ",".join(failures))


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


def build_apk(worktree: Path) -> dict:
    project = worktree / PROJECT_REL
    gradle = find_gradle(worktree)
    if not gradle:
        return {"ok": False, "error": "GRADLE_MISSING", "detail": "No Gradle wrapper, GRADLE_BIN, known Termux Gradle, or gradle executable found."}
    if not command_exists("java"):
        return {"ok": False, "error": "JAVA_MISSING", "detail": "Java is required for the Android build."}
    args = gradle + [":app:testDebugUnitTest", ":app:assembleDebug", "--no-daemon"]
    aapt = Path("/data/data/com.termux/files/usr/bin/aapt2")
    if aapt.exists():
        args.append(f"-Pandroid.aapt2FromMavenOverride={aapt}")
    result = run(args, cwd=project, timeout=2400)
    apk = project / "app" / "build" / "outputs" / "apk" / "debug" / "app-debug.apk"
    if result["rc"] != 0 or not apk.exists() or apk.stat().st_size < 10000:
        return {"ok": False, "error": "ANDROID_BUILD_FAILED", "result": result, "apk": str(apk)}
    sha = hashlib.sha256(apk.read_bytes()).hexdigest()
    record = {
        "schema": "vanguard-overlay-build-v1",
        "ok": True,
        "apk": str(apk),
        "bytes": apk.stat().st_size,
        "sha256": sha,
        "sourceHead": run(["git", "rev-parse", "HEAD"], cwd=worktree, timeout=20)["stdout"].strip(),
        "testAndBuildRc": result["rc"],
        "atMs": now_ms(),
        "truthBoundary": "Build/test success is build-body evidence, not phone deployment or acceptance.",
    }
    atomic_json(BUILD_STATE, record)
    return {**record, "resultTail": (result["stdout"] + "\n" + result["stderr"])[-6000:]}


def find_rish() -> str:
    explicit = os.environ.get("RISH", "").strip()
    candidates = [explicit]
    if command_exists("rish"):
        candidates.append(run(["sh", "-lc", "command -v rish"], timeout=15)["stdout"].strip())
    candidates.append(str(Path.home() / "bin" / "rish"))
    for candidate in candidates:
        if candidate and Path(candidate).exists() and os.access(candidate, os.X_OK):
            return candidate
    return ""


def rish(command: str, timeout: int = 120) -> dict:
    binary = find_rish()
    if not binary:
        return {"rc": 127, "stdout": "", "stderr": "RISH_MISSING"}
    return run([binary, "-c", command], timeout=timeout)


def install_apk(build: dict) -> dict:
    apk = Path(build["apk"]).resolve()
    expected = build["sha256"]
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
    grants = []
    for command in (
        f"pm enable --user 0 {PACKAGE}",
        f"appops set {PACKAGE} SYSTEM_ALERT_WINDOW allow",
        f"pm grant {PACKAGE} android.permission.POST_NOTIFICATIONS",
        f"pm grant {PACKAGE} android.permission.RECORD_AUDIO",
    ):
        result = rish(command, timeout=60)
        grants.append({"operation": command.split()[0:3], "rc": result["rc"], "stdout": result["stdout"][-1000:], "stderr": result["stderr"][-1000:]})
    # Launch only the visible activity. Do not start the microphone service here.
    launch = rish(f"am start -n {PACKAGE}/.MainActivity", timeout=60)
    return {"ok": launch["rc"] == 0, "install": install, "launch": launch, "grants": grants, "sha256": expected}


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


def notify(title: str, content: str, notification_id: str) -> None:
    if command_exists("termux-notification"):
        run(["termux-notification", "--id", notification_id, "--title", title, "--content", content], timeout=30)


def phone_canary(wait_user_seconds: int = USER_ARM_SECONDS) -> dict:
    state = query_phone_state()
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
        emit("phone-arm", "waiting-user", "APK is installed and visible. Waiting only for Android's required deliberate ARM LISTENING action; campaign remains alive and resumable.", deployed=True, waitingFor="visible-user-arm", state=state["fields"])
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
        "truthBoundary": "Initial live canary only: installed package + overlay authority + visible-user-armed microphone + bounded-capacity ring + advancing write position. Remaining physical acceptance is explicit in the receipt.",
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
        "schema": "vanguard-overlay-worker-v2",
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
        emit("stop", "stopped", "No live campaign process exists; STOP intent is persisted for any stale worker.")
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
    latest = json.loads(LATEST.read_text(encoding="utf-8")) if LATEST.exists() else {"schema": "vanguard-overlay-campaign-v2", "phase": "never-run", "status": "idle"}
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
    child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(300)"], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    Path(pid_file).write_text(str(child.pid) + "\n", encoding="utf-8")
    time.sleep(300)
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
        tree.wait(timeout=3)
    except subprocess.TimeoutExpired:
        os.killpg(tree.pid, signal.SIGKILL)
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
    if not preferred.exists():
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
    gradle_ok = bool(find_gradle(MANAGED_WORKTREE if MANAGED_WORKTREE.exists() else ROOT))
    checks.append({"check": "gradle", "ok": gradle_ok, "detail": "wrapper / GRADLE_BIN / known Termux Gradle / system Gradle"})
    alive, meta = worker_alive()
    result = {
        "schema": "vanguard-overlay-doctor-v2",
        "okForRepositoryCampaign": bool(checks[0]["ok"] and checks[1]["ok"]),
        "okForAutomaticFreeTabDispatch": relay["ok"],
        "okForPhoneDeploy": bool(rish_bin and java_ok and gradle_ok),
        "workerAlive": alive,
        "worker": meta or None,
        "checks": checks,
        "stateDir": str(STATE),
        "truthBoundary": "Doctor reports actual lanes. A missing lane is preserved as a precise boundary and never authorizes an adjacent substitute.",
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["okForRepositoryCampaign"] else 2


def worker_main() -> int:
    try:
        emit("worker", "running", "Advancing the same Vanguard overlay resurrection campaign.")
        worktree, head, contract = drive_source_to_green()
        if stop_requested():
            emit("worker", "stopped", "STOP requested after source work and before build/deploy.", implemented=contract["ok"], tested=contract["ok"])
            return EXIT_STOPPED
        emit("source-contract", "passed", "Repository source satisfies the resurrection architecture contract. This proves source shape only.", sourceHead=head, implemented=True, tested=True)

        build = build_apk(worktree)
        if not build.get("ok"):
            emit("build", "blocked", build.get("detail", build.get("error", "Android build failed")), evidence=build, implemented=True, tested=False)
            return EXIT_BUILD_FAILED
        emit("build", "passed", "Android unit-test/build lane produced a hashed APK. Deployment remains false.", apk=build["apk"], sha256=build["sha256"], sourceHead=build["sourceHead"], implemented=True, tested=True)
        if stop_requested():
            emit("worker", "stopped", "STOP requested before phone mutation.", implemented=True, tested=True)
            return EXIT_STOPPED

        install = install_apk(build)
        if not install.get("ok"):
            emit("phone-install", "blocked", install.get("error", "Phone install failed"), evidence=install, implemented=True, tested=True, deployed=False)
            return EXIT_PHONE_FAILED
        emit("phone-install", "installed", "APK installed through Shizuku and visible MainActivity launched. The shell did not arm microphone capture.", sha256=build["sha256"], implemented=True, tested=True, deployed=True)

        canary = phone_canary()
        if not canary.get("ok"):
            if canary.get("waitingUser"):
                emit("phone-canary", "waiting-user", "Installation is durable; only Android's required visible ARM LISTENING action remains before the initial live canary can continue. Run/resume is idempotent.", evidence=canary, implemented=True, tested=True, deployed=True)
                return EXIT_WAITING_USER
            emit("phone-canary", "failed", canary.get("error", "Phone canary failed"), evidence=canary, implemented=True, tested=True, deployed=True)
            return EXIT_PHONE_FAILED

        emit(
            "phone-canary",
            "passed-initial",
            "Live phone proved installed package, overlay authority, visible-user-armed microphone activity, bounded ring capacity, and advancing ring state. Product acceptance remains intentionally open.",
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
    receipts_parser = subs.add_parser("receipts")
    receipts_parser.add_argument("--limit", type=int, default=30)
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
        result = dispatch_free_tab(worktree, head, 1, failed_source_checks(contract))
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result.get("ok") else 1
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
