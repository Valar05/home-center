#!/data/data/com.termux/files/usr/bin/python
"""Durable operator campaign for VANGUARD // OVERLAY RESURRECTION.

This is intentionally a campaign, not an install snippet. The stable command owns
state/history, a managed worktree, process isolation, free-tab worker dispatch,
source-contract verification, phone build/install, liveness, STOP, and receipts.

Truth boundary: repository/source/build receipts are never rounded up to physical
phone acceptance. Microphone capture is never armed from boot or by this shell.
The visible Android app owns the required user-initiated ARM action.
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
        "schema": "vanguard-overlay-campaign-v1",
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
            "stdout": (exc.stdout or "")[-30000:] if isinstance(exc.stdout, str) else "",
            "stderr": ((exc.stderr or "")[-20000:] if isinstance(exc.stderr, str) else "") + f"\nTIMEOUT after {timeout}s",
        }


def command_exists(name: str) -> bool:
    return run(["sh", "-lc", f"command -v {shlex.quote(name)}"], timeout=15)["rc"] == 0


def repo_ok(root: Path = ROOT) -> tuple[bool, str]:
    if not (root / ".git").exists() and not (root / ".git").is_file():
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
    candidates = []
    if explicit:
        candidates.append(Path(explicit).expanduser())
    candidates.extend([
        ROOT,
        Path.home() / "home-center",
        Path.home() / "src" / "home-center",
        Path.home() / "projects" / "home-center",
        Path("/storage/emulated/0/Documents/home-center"),
    ])
    seen = set()
    for candidate in candidates:
        try:
            resolved = candidate.resolve()
        except OSError:
            continue
        if str(resolved) in seen:
            continue
        seen.add(str(resolved))
        ok, _ = repo_ok(resolved)
        if ok:
            return resolved
    raise RuntimeError("HOME_CENTER_REPO_NOT_FOUND: set HC_REPO_ROOT to an authenticated Valar05/home-center checkout")


def git_fetch_branch(source_repo: Path) -> str:
    result = run(["git", "fetch", "--prune", "origin", BRANCH], cwd=source_repo, timeout=180)
    if result["rc"] != 0:
        raise RuntimeError("git fetch failed: " + (result["stderr"] or result["stdout"])[-4000:])
    head = run(["git", "rev-parse", f"origin/{BRANCH}"], cwd=source_repo, timeout=30)
    if head["rc"] != 0:
        raise RuntimeError("remote campaign branch missing after fetch")
    return head["stdout"].strip()


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
            raise RuntimeError("managed worktree is not healthy: " + detail)
        reset = run(["git", "reset", "--hard", f"origin/{BRANCH}"], cwd=MANAGED_WORKTREE, timeout=120)
        if reset["rc"] != 0:
            raise RuntimeError("managed worktree reset failed: " + (reset["stderr"] or reset["stdout"])[-4000:])
        clean = run(["git", "clean", "-fd", "--", "android/operator-overlay", "tools/vanguard_overlay_contract_test.py", "campaigns/vanguard-overlay-resurrection"], cwd=MANAGED_WORKTREE, timeout=60)
        if clean["rc"] != 0:
            raise RuntimeError("managed worktree clean failed: " + clean["stderr"][-2000:])
    return MANAGED_WORKTREE, head


def source_contract(worktree: Path) -> dict:
    path = worktree / CONTRACT_REL
    if not path.exists():
        return {"ok": False, "rc": 2, "stdout": "", "stderr": f"missing {CONTRACT_REL}"}
    result = run([sys.executable, str(path)], cwd=worktree, timeout=120)
    parsed = None
    try:
        parsed = json.loads(result["stdout"])
    except Exception:
        pass
    return {"ok": result["rc"] == 0, "rc": result["rc"], "parsed": parsed, "stdout": result["stdout"], "stderr": result["stderr"]}


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
    for path in (
        Path("~/.config/home-center/chromium-throne.env").expanduser(),
        Path("~/.home-center/chromium-throne/relay.env").expanduser(),
        Path("~/.local/state/home-center/chromium-throne/relay.env").expanduser(),
        Path("~/.local/state/home-center/browser-porch/relay.env").expanduser(),
    ):
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
        base = base + "/v1/throne"
    return {
        "ok": bool(base and len(capability) >= 32),
        "baseUrl": base or None,
        "capabilityPresent": len(capability) >= 32,
        "capability": capability,
    }


def http_json(url: str, method: str, capability: str, payload: dict | None = None, timeout: int = 30) -> tuple[int, dict | None, str]:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {
        "authorization": f"Bearer {capability}",
        "content-type": "application/json",
        "cache-control": "no-store",
    }
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
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


def commission_hash(worktree: Path) -> tuple[str, str]:
    path = worktree / COMMISSION_REL
    body = path.read_text(encoding="utf-8")
    return hashlib.sha256(body.encode("utf-8")).hexdigest(), body


def dispatch_free_tab(worktree: Path, source_head: str) -> dict:
    relay = discover_relay()
    if not relay["ok"]:
        return {
            "ok": False,
            "waiting": True,
            "error": "THRONE_RELAY_NOT_CONFIGURED",
            "detail": "Need HC_THRONE_RELAY_URL (or Home Center equivalent) plus a >=32-character Chromium Throne capability. Campaign remains resumable; do not paste the commission into a shell.",
            "relay": {k: v for k, v in relay.items() if k != "capability"},
        }
    digest, commission = commission_hash(worktree)
    command_id = f"vanguard-overlay-{digest[:12]}-{source_head[:10]}"
    context = (
        "VANGUARD // OVERLAY RESURRECTION. Continue the exact bounded repository commission. "
        "Work in the existing campaign/vanguard-overlay-resurrection branch. Read the persisted PLAN_ALLOWED receipt first. "
        "The phone campaign, not the browser worker, owns physical deployment/acceptance."
    )
    payload = {
        "commandId": command_id,
        "action": "swarm.enqueue",
        "source": "vanguard-overlay-campaign",
        "createdAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "jobs": [{
            "jobId": f"vanguard-overlay-implementation-{digest[:12]}",
            "commission": commission,
            "context": context,
        }],
    }
    status, body, raw = http_json(relay["baseUrl"] + "/command", "POST", relay["capability"], payload, timeout=30)
    record = {
        "commandId": command_id,
        "commissionSha256": digest,
        "sourceHeadAtDispatch": source_head,
        "relayBaseUrl": relay["baseUrl"],
        "httpStatus": status,
        "response": body,
        "atMs": now_ms(),
    }
    atomic_json(RELAY_STATE, record)
    if status not in (200, 202):
        return {"ok": False, "waiting": False, "error": "THRONE_DISPATCH_FAILED", "detail": raw[-3000:], **record}
    return {"ok": True, **record}


def remote_branch_head(source_repo: Path) -> str:
    result = run(["git", "ls-remote", "origin", f"refs/heads/{BRANCH}"], cwd=source_repo, timeout=60)
    if result["rc"] != 0 or not result["stdout"].strip():
        return ""
    return result["stdout"].split()[0]


def wait_for_worker_commit(worktree: Path, baseline_head: str, timeout_seconds: int = 7200) -> tuple[bool, str]:
    source_repo = discover_source_repo()
    relay = discover_relay()
    started = time.time()
    last_status_ms = 0
    while time.time() - started < timeout_seconds:
        if stop_requested():
            return False, "STOP_REQUESTED"
        head = remote_branch_head(source_repo)
        if head and head != baseline_head:
            return True, head
        if relay["ok"] and RELAY_STATE.exists() and now_ms() - last_status_ms > 30000:
            last_status_ms = now_ms()
            status, body, raw = http_json(relay["baseUrl"] + "/status", "GET", relay["capability"], None, timeout=20)
            emit(
                "free-tab",
                "waiting",
                "Waiting for Chromium Throne worker to push the implementation branch.",
                relayHttpStatus=status,
                relaySnapshot=body if status == 200 else raw[-1000:],
                implemented=False,
            )
        time.sleep(10)
    return False, "FREE_TAB_TIMEOUT"


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
    digest = hashlib.sha256(apk.read_bytes()).hexdigest()
    record = {
        "schema": "vanguard-overlay-build-v1",
        "ok": True,
        "apk": str(apk),
        "bytes": apk.stat().st_size,
        "sha256": digest,
        "sourceHead": run(["git", "rev-parse", "HEAD"], cwd=worktree, timeout=20)["stdout"].strip(),
        "testAndBuildRc": result["rc"],
        "atMs": now_ms(),
        "truthBoundary": "Build/test success is repository/build-body evidence, not phone deployment or acceptance.",
    }
    atomic_json(BUILD_STATE, record)
    return {**record, "resultTail": (result["stdout"] + "\n" + result["stderr"])[-6000:]}


def find_rish() -> str:
    explicit = os.environ.get("RISH", "").strip()
    candidates = [explicit, str(Path.home() / "bin" / "rish")]
    if command_exists("rish"):
        which = run(["sh", "-lc", "command -v rish"], timeout=15)["stdout"].strip()
        candidates.insert(0, which)
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
    q_apk = shlex.quote(str(apk))
    q_staged = shlex.quote(staged)
    stage = rish(f"set -e; cp {q_apk} {q_staged}; chmod 644 {q_staged}; sha256sum {q_staged}", timeout=180)
    staged_sha = ""
    for token in (stage["stdout"] + " " + stage["stderr"]).split():
        if len(token) == 64 and all(ch in "0123456789abcdef" for ch in token.lower()):
            staged_sha = token.lower()
    if stage["rc"] != 0 or staged_sha != expected:
        return {"ok": False, "error": "APK_STAGE_HASH_MISMATCH", "expected": expected, "actual": staged_sha, "stage": stage}
    install = rish(f"pm install -r {q_staged}", timeout=300)
    rish(f"rm -f {q_staged}", timeout=30)
    if install["rc"] != 0 or "Success" not in install["stdout"]:
        return {"ok": False, "error": "PM_INSTALL_FAILED", "install": install}
    grants = []
    for command in (
        f"pm enable --user 0 {PACKAGE}",
        f"appops set {PACKAGE} SYSTEM_ALERT_WINDOW allow",
        f"pm grant {PACKAGE} android.permission.POST_NOTIFICATIONS",
        f"pm grant {PACKAGE} android.permission.RECORD_AUDIO",
    ):
        grants.append({"command": command.split()[0:3], "result": rish(command, timeout=60)})
    launch = rish(f"am start -n {PACKAGE}/.MainActivity", timeout=60)
    return {"ok": launch["rc"] == 0, "install": install, "launch": launch, "grants": grants, "sha256": expected}


def query_phone_state() -> dict:
    command = (
        f"pm list packages {PACKAGE}; "
        f"appops get {PACKAGE} SYSTEM_ALERT_WINDOW 2>/dev/null || true; "
        f"pm check-permission {PACKAGE} android.permission.RECORD_AUDIO 2>/dev/null || true; "
        f"pm check-permission {PACKAGE} android.permission.POST_NOTIFICATIONS 2>/dev/null || true; "
        f"content query --uri content://com.homecenter.operatoroverlay.state/state 2>/dev/null || true"
    )
    result = rish(command, timeout=90)
    mkdirs()
    PHONE_STATE.write_text(result["stdout"] + result["stderr"], encoding="utf-8")
    raw = result["stdout"] + "\n" + result["stderr"]
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
    return {
        "ok": result["rc"] == 0,
        "packageInstalled": f"package:{PACKAGE}" in raw,
        "overlayAllowed": "SYSTEM_ALERT_WINDOW: allow" in raw or "SYSTEM_ALERT_WINDOW: allow;" in raw,
        "recordAudioGranted": "granted" in raw.lower() or "android.permission.RECORD_AUDIO: granted" in raw,
        "raw": raw[-12000:],
        "fields": fields,
    }


def integer_field(state: dict, key: str) -> int:
    try:
        return int(str(state.get("fields", {}).get(key, "0")).strip())
    except ValueError:
        return 0


def notify_user_arm() -> None:
    if command_exists("termux-notification"):
        run([
            "termux-notification",
            "--id", "vanguard-overlay-arm",
            "--title", "Vanguard overlay needs one deliberate tap",
            "--content", "Home Center is installed. Open the visible overlay and ARM LISTENING; Android requires a user-initiated microphone start.",
        ], timeout=30)


def phone_canary(wait_user_seconds: int = 600) -> dict:
    state = query_phone_state()
    if not state["packageInstalled"] or not state["overlayAllowed"]:
        return {"ok": False, "waitingUser": False, "error": "PHONE_BASELINE_FAILED", "state": state}
    fields = state["fields"]
    required = {"overlay_mode", "listening_state", "mic_active", "ring_write_bytes", "ring_capacity_bytes", "transcript_segment_count", "last_transcript_at_ms", "keep_count"}
    missing = sorted(required - set(fields))
    if missing:
        return {"ok": False, "waitingUser": False, "error": "STATE_PROVIDER_FIELDS_MISSING", "missing": missing, "state": state}
    if fields.get("mic_active") not in ("1", "true", "TRUE"):
        notify_user_arm()
        emit(
            "phone-arm",
            "waiting-user",
            "APK is installed and visible. Android requires one deliberate visible ARM LISTENING action before microphone capture may continue in background.",
            deployed=True,
            callable=False,
            waitingFor="visible-user-arm",
            state=fields,
        )
        deadline = time.time() + wait_user_seconds
        while time.time() < deadline and not stop_requested():
            time.sleep(3)
            state = query_phone_state()
            if state["fields"].get("mic_active") in ("1", "true", "TRUE"):
                fields = state["fields"]
                break
        else:
            return {"ok": False, "waitingUser": True, "error": "WAITING_USER_ARM", "state": state}
    before = integer_field(state, "ring_write_bytes")
    capacity = integer_field(state, "ring_capacity_bytes")
    if capacity <= 0:
        return {"ok": False, "waitingUser": False, "error": "RING_CAPACITY_INVALID", "state": state}
    time.sleep(5)
    after_state = query_phone_state()
    after = integer_field(after_state, "ring_write_bytes")
    if after <= before:
        return {"ok": False, "waitingUser": False, "error": "RING_NOT_ADVANCING", "before": before, "after": after, "state": after_state}
    return {
        "ok": True,
        "waitingUser": False,
        "beforeRingWriteBytes": before,
        "afterRingWriteBytes": after,
        "ringCapacityBytes": capacity,
        "state": after_state,
        "truthBoundary": "This proves an initial live microphone/ring canary only. Full/bubble/hidden restore, transcript speech canary, KEEP, stop-release, bounded overwrite, reboot-disarm, battery behavior, and human acceptance remain open.",
    }


def stop_requested() -> bool:
    return (STATE / "STOP").exists()


def clear_stop() -> None:
    try:
        (STATE / "STOP").unlink()
    except FileNotFoundError:
        pass


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
        emit("launcher", "already-running", "Campaign worker is already alive.", worker=meta)
        return 0
    clear_stop()
    log_handle = LOG.open("a", encoding="utf-8")
    env = dict(os.environ)
    env["PYTHONUNBUFFERED"] = "1"
    p = subprocess.Popen(
        [sys.executable, str(SCRIPT), "__worker"],
        cwd=str(ROOT),
        stdout=log_handle,
        stderr=subprocess.STDOUT,
        stdin=subprocess.DEVNULL,
        start_new_session=True,
        env=env,
    )
    meta = {
        "schema": "vanguard-overlay-worker-v1",
        "pid": p.pid,
        "pgid": p.pid,
        "startedAtMs": now_ms(),
        "log": str(LOG),
        "state": str(STATE),
    }
    atomic_json(WORKER_META, meta)
    emit(
        "launcher",
        "running",
        "Campaign worker started in an isolated process group; operator shell is free.",
        worker=meta,
        controls=["vanguard-overlay status", "vanguard-overlay follow", "vanguard-overlay stop", "vanguard-overlay resume", "vanguard-overlay receipts"],
    )
    return 0


def stop_worker() -> int:
    mkdirs()
    (STATE / "STOP").write_text(str(now_ms()) + "\n", encoding="utf-8")
    alive, meta = worker_alive()
    if not alive:
        emit("stop", "stopped", "No live worker process exists; STOP intent is persisted.")
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
            emit("stop", "stopped", "Campaign process group stopped with TERM.", worker=meta)
            return 0
        time.sleep(0.2)
    try:
        os.killpg(pgid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    time.sleep(0.2)
    alive, _ = worker_alive()
    emit("stop", "stopped" if not alive else "failed", "Campaign process group escalated to KILL.", worker=meta)
    return 0 if not alive else 2


def doctor() -> int:
    mkdirs()
    checks = []
    try:
        source = discover_source_repo()
        ok, remote = repo_ok(source)
        head = remote_branch_head(source) if ok else ""
        checks.append({"check": "home-center-repo", "ok": ok, "detail": remote, "path": str(source)})
        checks.append({"check": "campaign-branch", "ok": bool(head), "detail": head or "remote branch not reachable"})
    except Exception as exc:
        checks.append({"check": "home-center-repo", "ok": False, "detail": str(exc)})
    relay = discover_relay()
    checks.append({"check": "chromium-throne-relay", "ok": relay["ok"], "detail": {k: v for k, v in relay.items() if k != "capability"}})
    rb = find_rish()
    checks.append({"check": "rish-shizuku", "ok": bool(rb), "detail": rb or "missing"})
    checks.append({"check": "java", "ok": command_exists("java"), "detail": "required for phone-local Android build"})
    checks.append({"check": "gradle", "ok": bool(find_gradle(MANAGED_WORKTREE if MANAGED_WORKTREE.exists() else ROOT)), "detail": "wrapper/GRADLE_BIN/known Termux gradle/system gradle"})
    alive, meta = worker_alive()
    result = {
        "schema": "vanguard-overlay-doctor-v1",
        "okForRepositoryCampaign": all(row["ok"] for row in checks[:2]),
        "okForAutomaticFreeTabDispatch": relay["ok"],
        "okForPhoneDeploy": bool(rb) and command_exists("java"),
        "workerAlive": alive,
        "worker": meta,
        "checks": checks,
        "stateDir": str(STATE),
        "truthBoundary": "Doctor reports available lanes; missing optional lanes do not erase the commission or justify a substitute architecture.",
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["okForRepositoryCampaign"] else 2


def status() -> int:
    mkdirs()
    latest = json.loads(LATEST.read_text(encoding="utf-8")) if LATEST.exists() else {
        "schema": "vanguard-overlay-campaign-v1",
        "phase": "never-run",
        "status": "idle",
    }
    alive, meta = worker_alive()
    elapsed = None
    if alive and meta.get("startedAtMs"):
        elapsed = max(0, now_ms() - int(meta["startedAtMs"]))
    output = {
        "latest": latest,
        "workerAlive": alive,
        "worker": meta or None,
        "elapsedMs": elapsed,
        "heartbeatAgeMs": max(0, now_ms() - int(latest.get("atMs", now_ms()))) if latest.get("atMs") else None,
        "paths": {"state": str(STATE), "log": str(LOG), "history": str(HISTORY), "latest": str(LATEST), "managedWorktree": str(MANAGED_WORKTREE)},
    }
    print(json.dumps(output, indent=2, sort_keys=True))
    return 0


def receipts(limit: int = 30) -> int:
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
        with LOG.open("r", encoding="utf-8", errors="replace") as fh:
            fh.seek(0, os.SEEK_END)
            while True:
                line = fh.readline()
                if line:
                    print(line, end="", flush=True)
                    continue
                alive, _ = worker_alive()
                if not alive:
                    # Drain once after worker death.
                    rest = fh.read()
                    if rest:
                        print(rest, end="", flush=True)
                    return 0
                time.sleep(0.4)
    except KeyboardInterrupt:
        print("\nFOLLOW DETACHED — campaign worker was not stopped.", file=sys.stderr)
        return 130


def canary_transport() -> int:
    mkdirs()
    payload = "quotes ' \" / Unicode Ritsu 雪 / dollar $HOME / literal $(touch SHOULD_NOT_EXIST) / multiline\nsecond line\n"
    payload_path = STATE / "transport-canary.txt"
    payload_path.write_text(payload, encoding="utf-8")
    before = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    result = run([sys.executable, str(SCRIPT), "__canary_transport", str(payload_path), before], timeout=30)
    transport_ok = result["rc"] == 0 and "TRANSPORT_OK" in result["stdout"] and not (STATE / "SHOULD_NOT_EXIST").exists()

    child = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(300)"],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    pgid = child.pid
    os.killpg(pgid, signal.SIGTERM)
    try:
        child.wait(timeout=3)
    except subprocess.TimeoutExpired:
        os.killpg(pgid, signal.SIGKILL)
        child.wait(timeout=3)
    isolation_ok = child.returncode is not None
    row = emit(
        "campaign-canary",
        "passed" if transport_ok and isolation_ok else "failed",
        "Prompt/data transport remained inert and an isolated process group was stoppable out-of-band." if transport_ok and isolation_ok else "Campaign canary failed.",
        transportSafe=transport_ok,
        processIsolationStop=isololation if False else isolation_ok,
        transportSha256=before,
        implemented=True,
        tested=transport_ok and isolation_ok,
    )
    return 0 if row["status"] == "passed" else 3


def canary_transport_child(path: str, expected: str) -> int:
    data = Path(path).read_bytes()
    actual = hashlib.sha256(data).hexdigest()
    if actual != expected:
        print("TRANSPORT_HASH_MISMATCH")
        return 2
    print("TRANSPORT_OK")
    return 0


def install_command() -> int:
    mkdirs()
    worktree, head = ensure_worktree()
    bin_dir = Path(os.environ.get("PREFIX", str(Path.home() / ".local"))).expanduser() / "bin"
    # Termux normally already has ~/bin in PATH; prefer that stable operator location when it exists/is writable.
    termux_bin = Path.home() / "bin"
    try:
        termux_bin.mkdir(parents=True, exist_ok=True)
        if os.access(termux_bin, os.W_OK):
            bin_dir = termux_bin
    except OSError:
        bin_dir.mkdir(parents=True, exist_ok=True)
    bin_dir.mkdir(parents=True, exist_ok=True)
    wrapper = bin_dir / "vanguard-overlay"
    script_path = worktree / "tools" / "vanguard_overlay_campaign.py"
    wrapper.write_text(
        "#!/data/data/com.termux/files/usr/bin/bash\n"
        "set -euo pipefail\n"
        f"export HC_VANGUARD_OVERLAY_STATE={shlex.quote(str(STATE))}\n"
        f"exec {shlex.quote(sys.executable)} {shlex.quote(str(script_path))} \"$@\"\n",
        encoding="utf-8",
    )
    wrapper.chmod(0o755)
    emit(
        "install-command",
        "ready",
        "Stable vanguard-overlay command installed against the managed campaign worktree.",
        command=str(wrapper),
        sourceHead=head,
        implemented=True,
        callable=True,
    )
    print(str(wrapper))
    return 0


def worker_main() -> int:
    try:
        emit("worker", "running", "Advancing the same Vanguard overlay resurrection campaign.")
        worktree, head = ensure_worktree()
        emit("source-sync", "healthy", "Managed worktree synchronized without touching operator edits.", sourceHead=head, worktree=str(worktree))
        contract = source_contract(worktree)
        if not contract["ok"]:
            failed = (contract.get("parsed") or {}).get("failed", [])
            emit(
                "source-contract",
                "needs-implementation",
                "Retired overlay does not yet satisfy the resurrection contract; dispatching the bounded implementation commission to a free Chromium Throne tab.",
                sourceHead=head,
                failedChecks=failed,
                implemented=False,
            )
            dispatch = dispatch_free_tab(worktree, head)
            if not dispatch["ok"]:
                emit(
                    "free-tab",
                    "waiting-relay" if dispatch.get("waiting") else "failed",
                    dispatch.get("detail", dispatch.get("error", "dispatch failed")),
                    dispatch={k: v for k, v in dispatch.items() if k not in ("capability",)},
                )
                return EXIT_WAITING_RELAY if dispatch.get("waiting") else EXIT_SOURCE_FAILED
            emit("free-tab", "dispatched", "Bounded implementation commission queued to Chromium Throne.", commandId=dispatch["commandId"], commissionSha256=dispatch["commissionSha256"])
            changed, outcome = wait_for_worker_commit(worktree, head)
            if not changed:
                emit("free-tab", "blocked", f"Free-tab implementation did not produce a new branch head: {outcome}", commandId=dispatch["commandId"])
                return EXIT_SOURCE_FAILED
            worktree, head = ensure_worktree()
            contract = source_contract(worktree)
        if not contract["ok"]:
            emit(
                "source-contract",
                "failed",
                "New branch head still fails the deterministic resurrection source contract; campaign will not build or touch the phone.",
                sourceHead=head,
                failedChecks=(contract.get("parsed") or {}).get("failed", []),
                implemented=True,
                tested=False,
            )
            return EXIT_SOURCE_FAILED
        emit(
            "source-contract",
            "passed",
            "Repository source satisfies the bounded resurrection architecture contract. This is not phone proof.",
            sourceHead=head,
            implemented=True,
            tested=True,
        )
        if stop_requested():
            emit("worker", "stopped", "STOP requested before build/deploy.", implemented=True, tested=True)
            return 0
        build = build_apk(worktree)
        if not build.get("ok"):
            emit("build", "blocked", build.get("detail", build.get("error", "build failed")), evidence=build, implemented=True, tested=False)
            return EXIT_BUILD_FAILED
        emit(
            "build",
            "passed",
            "Android tests/build produced a hashed APK on the authorized campaign body. Phone deployment is still false.",
            apk=build["apk"], sha256=build["sha256"], sourceHead=build["sourceHead"],
            implemented=True, tested=True,
        )
        if stop_requested():
            emit("worker", "stopped", "STOP requested before phone mutation.", implemented=True, tested=True)
            return 0
        install = install_apk(build)
        if not install.get("ok"):
            emit("phone-install", "blocked", install.get("error", "phone install failed"), evidence=install, implemented=True, tested=True, deployed=False)
            return EXIT_PHONE_FAILED
        emit(
            "phone-install",
            "installed",
            "APK installed through Shizuku and MainActivity launched visibly. The campaign did not arm microphone capture from background.",
            sha256=build["sha256"], implemented=True, tested=True, deployed=True, callable=False,
        )
        canary = phone_canary()
        if not canary.get("ok"):
            if canary.get("waitingUser"):
                emit("phone-canary", "waiting-user", "Phone is waiting for the required visible ARM LISTENING action; resume remains safe and idempotent.", evidence=canary, implemented=True, tested=True, deployed=True)
                return EXIT_WAITING_USER
            emit("phone-canary", "failed", canary.get("error", "phone canary failed"), evidence=canary, implemented=True, tested=True, deployed=True)
            return EXIT_PHONE_FAILED
        emit(
            "phone-canary",
            "passed-initial",
            "Live phone proved installed package, overlay authority, explicit user-armed microphone activity, bounded ring capacity, and advancing ring write state. Full product acceptance remains open.",
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
                "KEEP-LAST-60s-exactly-one-durable-bundle",
                "rolling-data-remains-bounded-through-wrap",
                "reboot-listening-disarmed",
                "Adam-absent-live-runtime",
                "Ritsu-intelligence-failure-does-not-break-capture",
                "battery/thermal-observation",
                "Drew-acceptance",
            ],
        )
        return 0
    except Exception as exc:
        emit("worker", "failed", f"{type(exc).__name__}: {exc}")
        return 70


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(prog="vanguard-overlay", description="Vanguard Home Center overlay resurrection campaign")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("run", "resume", "status", "follow", "stop", "doctor", "canary", "install", "source", "phone", "dispatch", "__worker"):
        sub.add_parser(name)
    r = sub.add_parser("receipts")
    r.add_argument("--limit", type=int, default=30)
    c = sub.add_parser("__canary_transport")
    c.add_argument("path")
    c.add_argument("sha256")
    return ap.parse_args()


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
        return canary_transport()
    if args.cmd == "install":
        return install_command()
    if args.cmd == "receipts":
        return receipts(args.limit)
    if args.cmd == "__worker":
        return worker_main()
    if args.cmd == "__canary_transport":
        return canary_transport_child(args.path, args.sha256)
    if args.cmd == "source":
        worktree, head = ensure_worktree()
        result = source_contract(worktree)
        emit("source-contract", "passed" if result["ok"] else "failed", "Manual source contract probe.", sourceHead=head, failedChecks=(result.get("parsed") or {}).get("failed", []), implemented=result["ok"], tested=result["ok"])
        return 0 if result["ok"] else 1
    if args.cmd == "phone":
        state = query_phone_state()
        print(json.dumps(state, indent=2, sort_keys=True))
        return 0 if state["packageInstalled"] else 1
    if args.cmd == "dispatch":
        worktree, head = ensure_worktree()
        result = dispatch_free_tab(worktree, head)
        print(json.dumps({k: v for k, v in result.items() if k != "capability"}, indent=2, sort_keys=True))
        return 0 if result.get("ok") else 1
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
