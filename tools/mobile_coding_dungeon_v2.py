#!/data/data/com.termux/files/usr/bin/python
"""Typed, receipt-first Coding Dungeon ingress for Android/Termux.

Remote callers can select only bounded campaign fields and a registered workspace
identifier. Paths, commands, argv, environment, URLs, model names, manifests,
branch names, and publication destinations are resolved by this phone-local
coordinator. Every campaign owns a deterministic worktree and tmux session; the
authoritative queue/job record lives outside tmux.
"""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import re
import signal
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any

DUNGEON_RUN_SCHEMA = "home-center.dungeon-run.v2"
DUNGEON_STATUS_SCHEMA = "home-center.dungeon-status.v2"
INFERENCE_POLICY = "codex-local-low-deterministic-v1"
PUBLICATION_POLICY = "checkpoint-only"
WORKSPACE_REGISTRY_SCHEMA = "home-center.dungeon-workspaces.v2"
TOKEN_DROUGHT_SCHEMA = "home-center.fortress-token-drought.v1"
TOKEN_DROUGHT_KEYS = {"schema", "enabled", "reason", "updatedAtMs"}
RUN_KEYS = {
    "action", "schema", "requestId", "deviceId", "campaignId", "workspaceId",
    "objective", "acceptance", "constraints", "taskKind", "lane", "criticalReason",
    "budgetProfile", "verificationProfile", "inferencePolicy", "publicationPolicy",
}
STATUS_KEYS = {"action", "schema", "requestId", "deviceId", "jobId"}
LANES = {"critical", "standard", "background"}
BUDGETS = {
    "probe": {"wallSeconds": 15 * 60, "stageSeconds": 10 * 60},
    "standard": {"wallSeconds": 2 * 60 * 60, "stageSeconds": 90 * 60},
    "long": {"wallSeconds": 8 * 60 * 60, "stageSeconds": 6 * 60 * 60},
}
VERIFICATION_PROFILES = {"fast", "default", "full"}
TASK_KINDS = {"implement", "repair", "verify", "review", "research"}
TERMINAL_STATES = {"SUCCEEDED", "FAILED", "QUARANTINED"}
VISIBLE_STATES = {"ACCEPTED", "RUNNING", "CHECKPOINTED", *TERMINAL_STATES}
ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]*$")
JOB_RE = re.compile(r"^dng_[0-9a-f]{24}$")
REF_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]{0,199}$")
LOG_HEAD_BYTES = 80_000
LOG_TAIL_BYTES = 100_000


class DungeonError(RuntimeError):
    pass


class DungeonConflict(DungeonError):
    pass


def epoch_ms() -> int:
    return int(time.time() * 1000)


def default_state_root() -> Path:
    return Path(os.environ.get("HC_DUNGEON_V2_STATE", "~/.local/state/home-center/coding-dungeon-v2")).expanduser()


def default_registry_path() -> Path:
    return Path(os.environ.get("HC_DUNGEON_V2_WORKSPACES", "~/.config/home-center/dungeon-workspaces.v2.json")).expanduser()


def default_token_drought_path() -> Path:
    return Path(os.environ.get("HC_FORTRESS_TOKEN_DROUGHT", "~/.config/home-center/fortress-token-drought.v1.json")).expanduser()


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def input_hash(action: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json(action).encode("utf-8")).hexdigest()


def clean_text(value: Any, key: str, minimum: int = 1, maximum: int = 1200) -> str:
    if not isinstance(value, str):
        raise DungeonError(f"{key} must be a string")
    out = value.strip()
    if not minimum <= len(out) <= maximum:
        raise DungeonError(f"{key} must contain {minimum}-{maximum} characters")
    if re.search(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", out):
        raise DungeonError(f"{key} contains unsupported control characters")
    return out


def clean_id(value: Any, key: str, maximum: int = 120) -> str:
    out = clean_text(value, key, 3, maximum)
    if not ID_RE.fullmatch(out) or ".." in out:
        raise DungeonError(f"{key} contains unsupported characters")
    return out


def clean_list(value: Any, key: str, required: bool = False, maximum: int = 24) -> list[str]:
    if value is None and not required:
        return []
    if not isinstance(value, list) or (required and not value) or len(value) > maximum:
        raise DungeonError(f"{key} must contain {'1' if required else '0'}-{maximum} strings")
    out = [clean_text(item, f"{key}[{index}]", 1, 600) for index, item in enumerate(value)]
    if len(set(out)) != len(out):
        raise DungeonError(f"{key} contains a duplicate entry")
    return out


def normalize_run_action(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise DungeonError("dungeon action must be an object")
    unknown = sorted(set(value) - RUN_KEYS)
    if unknown:
        raise DungeonError(f"dungeon_run rejects unknown field: {unknown[0]}")
    if value.get("action", "dungeon_run") != "dungeon_run":
        raise DungeonError("dungeon_run action identity is invalid")
    if value.get("schema", DUNGEON_RUN_SCHEMA) != DUNGEON_RUN_SCHEMA:
        raise DungeonError(f"dungeon_run schema must be {DUNGEON_RUN_SCHEMA}")
    lane = clean_text(value.get("lane", "standard"), "lane", 1, 20)
    if lane not in LANES:
        raise DungeonError("lane must be critical, standard, or background")
    critical_reason = "" if value.get("criticalReason") is None else clean_text(value["criticalReason"], "criticalReason", 12, 800)
    if lane == "critical" and not critical_reason:
        raise DungeonError("critical lane requires criticalReason")
    if lane != "critical" and critical_reason:
        raise DungeonError("criticalReason is only allowed for the critical lane")
    budget = clean_text(value.get("budgetProfile", "standard"), "budgetProfile", 1, 20)
    if budget not in BUDGETS:
        raise DungeonError("budgetProfile must be probe, standard, or long")
    verification = clean_text(value.get("verificationProfile", "default"), "verificationProfile", 1, 20)
    if verification not in VERIFICATION_PROFILES:
        raise DungeonError("verificationProfile must be fast, default, or full")
    task_kind = clean_text(value.get("taskKind", "implement"), "taskKind", 1, 20)
    if task_kind not in TASK_KINDS:
        raise DungeonError("taskKind must be implement, repair, verify, review, or research")
    if value.get("inferencePolicy", INFERENCE_POLICY) != INFERENCE_POLICY:
        raise DungeonError(f"inferencePolicy must be {INFERENCE_POLICY}")
    if value.get("publicationPolicy", PUBLICATION_POLICY) != PUBLICATION_POLICY:
        raise DungeonError(f"publicationPolicy must be {PUBLICATION_POLICY}")
    normalized = {
        "action": "dungeon_run",
        "schema": DUNGEON_RUN_SCHEMA,
        "requestId": clean_id(value.get("requestId"), "requestId", 180),
        "deviceId": clean_id(value.get("deviceId", "primary-phone"), "deviceId", 120).lower(),
        "campaignId": clean_id(value.get("campaignId"), "campaignId", 100).lower(),
        "workspaceId": clean_id(value.get("workspaceId"), "workspaceId", 100).lower(),
        "objective": clean_text(value.get("objective"), "objective", 8, 8000),
        "acceptance": clean_list(value.get("acceptance"), "acceptance", required=True),
        "constraints": clean_list(value.get("constraints"), "constraints"),
        "taskKind": task_kind,
        "lane": lane,
        "budgetProfile": budget,
        "verificationProfile": verification,
        "inferencePolicy": INFERENCE_POLICY,
        "publicationPolicy": PUBLICATION_POLICY,
    }
    if critical_reason:
        normalized["criticalReason"] = critical_reason
    return normalized


def normalize_status_action(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise DungeonError("dungeon action must be an object")
    unknown = sorted(set(value) - STATUS_KEYS)
    if unknown:
        raise DungeonError(f"dungeon_status rejects unknown field: {unknown[0]}")
    if value.get("action", "dungeon_status") != "dungeon_status":
        raise DungeonError("dungeon_status action identity is invalid")
    if value.get("schema", DUNGEON_STATUS_SCHEMA) != DUNGEON_STATUS_SCHEMA:
        raise DungeonError(f"dungeon_status schema must be {DUNGEON_STATUS_SCHEMA}")
    job_id = clean_text(value.get("jobId"), "jobId", 20, 40)
    if not JOB_RE.fullmatch(job_id):
        raise DungeonError("jobId is invalid")
    return {
        "action": "dungeon_status",
        "schema": DUNGEON_STATUS_SCHEMA,
        "requestId": clean_id(value.get("requestId"), "requestId", 180),
        "deviceId": clean_id(value.get("deviceId", "primary-phone"), "deviceId", 120).lower(),
        "jobId": job_id,
    }


def job_id_for(request_id: str) -> str:
    return "dng_" + hashlib.sha256(request_id.encode("utf-8")).hexdigest()[:24]


def session_for(request_id: str) -> str:
    return "hc-dng-" + hashlib.sha256(request_id.encode("utf-8")).hexdigest()[:16]


def slug(value: str, fallback: str = "campaign") -> str:
    out = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return (out or fallback)[:40]


def atomic_write(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    with tmp.open("w", encoding="utf-8") as handle:
        handle.write(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp, path)
    directory = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def bounded_token_drought(value: Any) -> dict[str, Any]:
    body = value if isinstance(value, dict) else {}
    return {
        "schema": TOKEN_DROUGHT_SCHEMA,
        "active": bool(body.get("active", False)),
        "valid": bool(body.get("valid", True)),
        "source": str(body.get("source") or "unknown")[:80],
        "reason": str(body.get("reason") or "")[:600],
        "updatedAtMs": int(body.get("updatedAtMs") or 0),
    }


def token_drought_status(path: Path | None = None) -> dict[str, Any]:
    sentinel = (path or default_token_drought_path()).expanduser().resolve()
    if not sentinel.exists():
        return {
            "schema": TOKEN_DROUGHT_SCHEMA,
            "active": False,
            "valid": True,
            "source": "absent-default-off",
            "reason": "No local token-drought sentinel is present.",
            "updatedAtMs": 0,
            "path": str(sentinel),
        }
    try:
        value = json.loads(sentinel.read_text(encoding="utf-8"))
        if not isinstance(value, dict) or set(value) != TOKEN_DROUGHT_KEYS:
            raise ValueError("sentinel keys are invalid")
        if value.get("schema") != TOKEN_DROUGHT_SCHEMA:
            raise ValueError("sentinel schema is invalid")
        if not isinstance(value.get("enabled"), bool):
            raise ValueError("enabled must be boolean")
        if not isinstance(value.get("reason"), str) or not 1 <= len(value["reason"].strip()) <= 600:
            raise ValueError("reason is invalid")
        if not isinstance(value.get("updatedAtMs"), int) or value["updatedAtMs"] < 0:
            raise ValueError("updatedAtMs is invalid")
    except Exception as exc:
        return {
            "schema": TOKEN_DROUGHT_SCHEMA,
            "active": True,
            "valid": False,
            "source": "invalid-local-sentinel",
            "reason": f"Invalid token-drought sentinel fails closed: {type(exc).__name__}.",
            "updatedAtMs": 0,
            "path": str(sentinel),
        }
    return {
        "schema": TOKEN_DROUGHT_SCHEMA,
        "active": value["enabled"],
        "valid": True,
        "source": "local-sentinel",
        "reason": value["reason"].strip(),
        "updatedAtMs": value["updatedAtMs"],
        "path": str(sentinel),
    }


def set_token_drought(enabled: bool, reason: str, path: Path | None = None) -> dict[str, Any]:
    sentinel = (path or default_token_drought_path()).expanduser().resolve()
    payload = {
        "schema": TOKEN_DROUGHT_SCHEMA,
        "enabled": bool(enabled),
        "reason": clean_text(reason, "reason", 4, 600),
        "updatedAtMs": epoch_ms(),
    }
    atomic_write(sentinel, payload)
    os.chmod(sentinel, 0o600)
    return token_drought_status(sentinel)


def paid_inference_allowed(path: Path | None = None) -> bool:
    return not token_drought_status(path)["active"]


def append_event(state_root: Path, job_id: str, kind: str, **data: Any) -> None:
    ledger = state_root / "runs" / job_id / "ledger.jsonl"
    ledger.parent.mkdir(parents=True, exist_ok=True)
    event = {"atMs": epoch_ms(), "kind": kind, **data}
    with ledger.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False, separators=(",", ":")) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def job_path(state_root: Path, job_id: str) -> Path:
    if not JOB_RE.fullmatch(job_id):
        raise DungeonError("jobId is invalid")
    return state_root / "jobs" / f"{job_id}.json"


def load_job(state_root: Path, job_id: str) -> dict[str, Any]:
    path = job_path(state_root, job_id)
    if not path.is_file():
        raise DungeonError("dungeon job not found")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or value.get("jobId") != job_id:
        raise DungeonError("dungeon job record is invalid")
    return value


def transition(state_root: Path, job: dict[str, Any], state: str, stage: str, note: str, **updates: Any) -> dict[str, Any]:
    if state not in VISIBLE_STATES:
        raise DungeonError(f"unsupported dungeon state: {state}")
    if job.get("state") in TERMINAL_STATES and state != job.get("state"):
        raise DungeonError("terminal dungeon jobs cannot transition back into execution")
    now = epoch_ms()
    history = list(job.get("history") or [])[-199:]
    history.append({"atMs": now, "state": state, "stage": stage, "note": note[:1000]})
    next_job = {**job, **updates, "state": state, "stage": stage, "updatedAtMs": now, "history": history}
    atomic_write(job_path(state_root, job["jobId"]), next_job)
    append_event(state_root, job["jobId"], "transition", state=state, stage=stage, note=note[:1000])
    return next_job


def load_workspace(registry_path: Path, workspace_id: str) -> dict[str, Any]:
    if not registry_path.is_file():
        raise DungeonError(f"trusted workspace registry is missing: {registry_path}")
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    if registry.get("schema") != WORKSPACE_REGISTRY_SCHEMA or not isinstance(registry.get("workspaces"), dict):
        raise DungeonError("trusted workspace registry schema is invalid")
    entry = registry["workspaces"].get(workspace_id)
    if not isinstance(entry, dict):
        raise DungeonError(f"workspaceId is not registered locally: {workspace_id}")
    root_raw = entry.get("root")
    if not isinstance(root_raw, str) or not root_raw.strip():
        raise DungeonError("registered workspace root is invalid")
    root = Path(root_raw).expanduser().resolve()
    if not root.is_dir():
        raise DungeonError("registered workspace root is unavailable")
    base_ref = str(entry.get("baseRef") or "HEAD").strip()
    if not REF_RE.fullmatch(base_ref) or ".." in base_ref or base_ref.startswith("-") or "@{" in base_ref:
        raise DungeonError("registered baseRef is unsafe")
    verification = entry.get("verification") or {}
    if not isinstance(verification, dict):
        raise DungeonError("registered verification map is invalid")
    return {"root": root, "baseRef": base_ref, "verification": verification}


def run_process(argv: list[str], cwd: Path, timeout: int, output_path: Path) -> dict[str, Any]:
    if not argv or not all(isinstance(part, str) and part and "\x00" not in part for part in argv):
        raise DungeonError("internal argv is invalid")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    started = epoch_ms()
    timed_out = False
    tail = bytearray()
    total_read = 0
    head_written = 0
    drain_errors: list[str] = []
    with output_path.open("wb") as output_handle:
        try:
            process = subprocess.Popen(
                argv,
                cwd=cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                start_new_session=True,
                shell=False,
                bufsize=0,
            )
        except OSError as exc:
            message = f"executor unavailable: {exc}\n".encode("utf-8", "replace")
            output_handle.write(message)
            output_handle.flush()
            os.fsync(output_handle.fileno())
            return {"argv0": Path(argv[0]).name, "exit": 127, "timedOut": False, "startedAtMs": started, "endedAtMs": epoch_ms(), "outputBytes": len(message), "outputTruncated": False, "outputTail": f"executor unavailable: {exc}"}

        def drain_output() -> None:
            nonlocal total_read, head_written
            try:
                assert process.stdout is not None
                while True:
                    chunk = process.stdout.read(64 * 1024)
                    if not chunk:
                        break
                    total_read += len(chunk)
                    remaining_head = max(0, LOG_HEAD_BYTES - head_written)
                    if remaining_head:
                        prefix = chunk[:remaining_head]
                        output_handle.write(prefix)
                        output_handle.flush()
                        head_written += len(prefix)
                    tail.extend(chunk)
                    if len(tail) > LOG_TAIL_BYTES:
                        del tail[:-LOG_TAIL_BYTES]
            except Exception as exc:  # bounded evidence; coordinator still closes fail-safe
                drain_errors.append(str(exc)[:1000])

        drain_thread = threading.Thread(target=drain_output, name=f"dungeon-log-{Path(argv[0]).name}", daemon=True)
        drain_thread.start()
        try:
            exit_code = process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
            try:
                os.killpg(process.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                process.wait(timeout=5)
            exit_code = None
        drain_thread.join(timeout=10)
        if drain_thread.is_alive() and process.stdout is not None:
            process.stdout.close()
            drain_thread.join(timeout=2)
        if drain_thread.is_alive():
            drain_errors.append("output drain did not stop after executor exit")
        if total_read > head_written:
            tail_start = max(0, total_read - len(tail))
            nonoverlap = max(0, head_written - tail_start)
            suffix = bytes(tail[nonoverlap:])
            marker = f"\n...[output bounded; totalBytes={total_read}; preserved head and tail]...\n".encode("utf-8")
            output_handle.write(marker)
            output_handle.write(suffix)
        if drain_errors:
            output_handle.write(("\n...[output drain warning: " + "; ".join(drain_errors) + "]...\n").encode("utf-8", "replace"))
        output_handle.flush()
        os.fsync(output_handle.fileno())
    output = bytes(tail).decode("utf-8", "replace")
    return {"argv0": Path(argv[0]).name, "exit": exit_code, "timedOut": timed_out, "startedAtMs": started, "endedAtMs": epoch_ms(), "outputBytes": total_read, "outputTruncated": total_read > head_written, "outputTail": output[-12000:]}


def git(root: Path, *args: str, timeout: int = 120) -> str:
    completed = subprocess.run(
        ["git", "-C", str(root), *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=timeout,
        shell=False,
        check=False,
    )
    if completed.returncode != 0:
        raise DungeonError(f"git {' '.join(args[:2])} failed: {(completed.stdout or '')[-2000:]}")
    return (completed.stdout or "").strip()


def mutation_evidence(worktree: Path, baseline_head: str) -> dict[str, Any]:
    head = git(worktree, "rev-parse", "HEAD")
    status = git(worktree, "status", "--porcelain=v1")
    diff_stat = git(worktree, "diff", "--stat")
    return {"head": head, "headChanged": head != baseline_head, "dirty": bool(status), "status": status[-12000:], "diffStat": diff_stat[-12000:], "changed": bool(status) or head != baseline_head}


def prepare_worktree(state_root: Path, job: dict[str, Any], workspace: dict[str, Any]) -> tuple[Path, str, str]:
    source = workspace["root"]
    git(source, "rev-parse", "--is-inside-work-tree")
    stored_baseline = str(job.get("baselineHead") or "")
    baseline_head = stored_baseline if re.fullmatch(r"[0-9a-f]{40}", stored_baseline) else git(source, "rev-parse", workspace["baseRef"])
    branch = f"fortress/{slug(job['action']['campaignId'])}-{job['jobId'][-10:]}"
    worktree = (state_root / "worktrees" / job["jobId"]).resolve()
    if worktree.is_dir():
        git(worktree, "rev-parse", "--is-inside-work-tree")
        active_branch = git(worktree, "rev-parse", "--abbrev-ref", "HEAD")
        if active_branch != branch:
            raise DungeonError("deterministic worktree is attached to an unexpected branch")
        if not stored_baseline:
            baseline_head = git(worktree, "rev-parse", "HEAD")
        return worktree, branch, baseline_head
    worktree.parent.mkdir(parents=True, exist_ok=True)
    exists = subprocess.run(
        ["git", "-C", str(source), "show-ref", "--verify", "--quiet", f"refs/heads/{branch}"],
        shell=False,
        check=False,
    ).returncode == 0
    args = ["worktree", "add", str(worktree), branch] if exists else ["worktree", "add", "-b", branch, str(worktree), baseline_head]
    git(source, *args, timeout=300)
    return worktree, branch, baseline_head


def build_prompt(action: dict[str, Any]) -> str:
    acceptance = "\n".join(f"- {item}" for item in action["acceptance"])
    constraints = "\n".join(f"- {item}" for item in action["constraints"]) or "- No additional caller constraints."
    return f"""FORTRESS CODING DUNGEON CAMPAIGN
Campaign: {action['campaignId']}
Task kind: {action['taskKind']}
Objective: {action['objective']}

Acceptance:
{acceptance}

Binding constraints:
{constraints}

Execution law:
- Inspect repository evidence and all applicable AGENTS.md, MEMORIES.md, SKILLS.md, and project instructions before editing.
- Work only inside this isolated worktree. Do not push, deploy, merge, publish, alter remotes, or change another worktree.
- Make the smallest coherent change that earns every acceptance item.
- Run project-native verification available inside the sandbox; the deterministic coordinator will independently re-run its trusted verification profile.
- Do not claim runtime, device, deployment, or human acceptance without exact evidence.
- If blocked, preserve concrete evidence in the final response. Do not invent an adjacent mission.
""".strip()


def codex_argv(prompt: str) -> list[str]:
    return ["codex", "exec", "--sandbox", "workspace-write", "--ask-for-approval", "never", "--json", prompt]


def local_adam_argv(worktree: Path, prompt: str) -> list[str] | None:
    adapter = worktree / "tools" / "dungeon_local_adam.py"
    reviewed = worktree / "tools" / "adam_venice_reviewed.py"
    core = worktree / "tools" / "adam_codex_phone.py"
    return [sys.executable, str(adapter), prompt] if adapter.is_file() and reviewed.is_file() and core.is_file() else None


def clean_verification_commands(workspace: dict[str, Any], profile: str) -> list[list[str]]:
    raw = workspace["verification"].get(profile, [])
    if not isinstance(raw, list) or len(raw) > 20:
        raise DungeonError("registered verification profile is invalid")
    commands: list[list[str]] = [["git", "diff", "--check"]]
    for index, argv in enumerate(raw):
        if not isinstance(argv, list) or not 1 <= len(argv) <= 32:
            raise DungeonError(f"registered verification command {index} is invalid")
        cleaned = [clean_text(part, f"verification[{index}] argv", 1, 500) for part in argv]
        commands.append(cleaned)
    return commands


def remaining_seconds(deadline: float, cap: int) -> int:
    return max(0, min(cap, int(deadline - time.monotonic())))


def verify(worktree: Path, workspace: dict[str, Any], profile: str, state_root: Path, job_id: str, deadline: float) -> dict[str, Any]:
    results = []
    for index, argv in enumerate(clean_verification_commands(workspace, profile)):
        timeout = remaining_seconds(deadline, 30 * 60)
        if timeout <= 0:
            return {"ok": False, "budgetExhausted": True, "results": results}
        result = run_process(argv, worktree, timeout, state_root / "runs" / job_id / f"verify-{index}.log")
        results.append({"argv": argv, **result})
        if result["exit"] != 0:
            return {"ok": False, "results": results}
    return {"ok": True, "results": results}


def bounded_job(job: dict[str, Any]) -> dict[str, Any]:
    drought = bounded_token_drought(job.get("tokenDrought"))
    return {
        "jobId": job["jobId"],
        "campaignId": job["action"]["campaignId"],
        "workspaceId": job["action"]["workspaceId"],
        "taskKind": job["action"]["taskKind"],
        "lane": job["action"]["lane"],
        "state": job["state"],
        "stage": job.get("stage", ""),
        "acceptedAtMs": job["acceptedAtMs"],
        "updatedAtMs": job["updatedAtMs"],
        "branch": job.get("branch", ""),
        "executor": job.get("executor", ""),
        "reason": str(job.get("reason") or "")[:1000],
        "verificationOk": bool((job.get("verification") or {}).get("ok")),
        "tokenDrought": drought,
        "paidInferenceAllowed": not drought["active"],
    }


def submit(action_value: Any, state_root: Path | None = None, registry_path: Path | None = None, launcher=None) -> dict[str, Any]:
    action = normalize_run_action(action_value)
    root = (state_root or default_state_root()).expanduser().resolve()
    registry = (registry_path or default_registry_path()).expanduser().resolve()
    load_workspace(registry, action["workspaceId"])
    root.mkdir(parents=True, exist_ok=True)
    job_id = job_id_for(action["requestId"])
    digest = input_hash(action)
    admission_lock_path = root / "locks" / f"admit-{job_id}.lock"
    admission_lock_path.parent.mkdir(parents=True, exist_ok=True)
    with admission_lock_path.open("a+", encoding="utf-8") as admission_lock:
        fcntl.flock(admission_lock.fileno(), fcntl.LOCK_EX)
        path = job_path(root, job_id)
        attached = False
        if path.exists():
            job = load_job(root, job_id)
            if job.get("inputHash") != digest:
                raise DungeonConflict("requestId is already bound to a different dungeon intent")
            attached = True
        else:
            now = epoch_ms()
            job = {
                "schema": "home-center.dungeon-job.v2",
                "jobId": job_id,
                "requestId": action["requestId"],
                "inputHash": digest,
                "tmuxSession": session_for(action["requestId"]),
                "action": action,
                "state": "ACCEPTED",
                "stage": "admitted",
                "acceptedAtMs": now,
                "updatedAtMs": now,
                "history": [{"atMs": now, "state": "ACCEPTED", "stage": "admitted", "note": "Exact typed intent durably admitted."}],
            }
            atomic_write(path, job)
            append_event(root, job_id, "accepted", requestId=action["requestId"], inputHash=digest, lane=action["lane"])
        if job["state"] not in TERMINAL_STATES:
            start = launcher or launch_tmux
            launched = start(root, registry, job)
            if not launched.get("ok"):
                job = transition(root, job, "FAILED", "tmux_admission", str(launched.get("error") or "tmux admission failed"), reason=str(launched.get("error") or "tmux admission failed"))
            elif launched.get("attached"):
                attached = True
        return {
            "schema": "home-center.dungeon-submit-receipt.v2",
            "requestId": action["requestId"],
            "inputHash": digest,
            "jobId": job_id,
            "tmuxSession": job["tmuxSession"],
            "state": job["state"],
            "attached": attached,
            "statusRef": f"phone-state://coding-dungeon-v2/jobs/{job_id}",
        }


def tmux_argv(tmux: str, state_root: Path, registry_path: Path, job: dict[str, Any]) -> list[str]:
    return [
        tmux, "new-session", "-d", "-s", job["tmuxSession"], sys.executable,
        str(Path(__file__).resolve()), "run-job", "--job-id", job["jobId"],
        "--state-root", str(state_root), "--registry", str(registry_path),
    ]


def launch_tmux(state_root: Path, registry_path: Path, job: dict[str, Any]) -> dict[str, Any]:
    tmux = shutil.which("tmux")
    if not tmux:
        return {"ok": False, "error": "tmux is unavailable"}
    session = job["tmuxSession"]
    present = subprocess.run([tmux, "has-session", "-t", session], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=False, check=False).returncode == 0
    if present:
        return {"ok": True, "attached": True}
    argv = tmux_argv(tmux, state_root, registry_path, job)
    completed = subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, shell=False, check=False)
    return {"ok": completed.returncode == 0, "attached": False, "error": (completed.stdout or "")[-2000:]}


def status(action_value: Any, state_root: Path | None = None) -> dict[str, Any]:
    action = normalize_status_action(action_value)
    root = (state_root or default_state_root()).expanduser().resolve()
    job = load_job(root, action["jobId"])
    return {
        "schema": "home-center.dungeon-status-receipt.v2",
        "requestId": action["requestId"],
        "jobId": job["jobId"],
        "inputHash": job["inputHash"],
        "state": job["state"],
        "job": bounded_job(job),
        "statusRef": f"phone-state://coding-dungeon-v2/jobs/{job['jobId']}",
    }


def execute(action: dict[str, Any]) -> dict[str, Any]:
    kind = action.get("action") if isinstance(action, dict) else None
    if kind == "dungeon_run":
        return submit(action)
    if kind == "dungeon_status":
        return status(action)
    raise DungeonError("unsupported typed dungeon action")


def run_job(state_root: Path, registry_path: Path, job_id: str) -> int:
    root = state_root.expanduser().resolve()
    registry = registry_path.expanduser().resolve()
    lock_path = root / "locks" / f"{job_id}.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+", encoding="utf-8") as job_lock:
        try:
            fcntl.flock(job_lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return 0
        job = load_job(root, job_id)
        if job["state"] in TERMINAL_STATES:
            return 0
        action = normalize_run_action(job["action"])
        if input_hash(action) != job["inputHash"]:
            transition(root, job, "QUARANTINED", "identity", "Stored action hash mismatch.", reason="stored action hash mismatch")
            return 4
        lane_lock_name = "lane-critical.lock" if action["lane"] == "critical" else "lane-noncritical.lock"
        lane_lock_path = root / "locks" / lane_lock_name
        with lane_lock_path.open("a+", encoding="utf-8") as lane_lock:
            append_event(root, job_id, "lane_wait", lane=action["lane"], lock=lane_lock_name)
            fcntl.flock(lane_lock.fileno(), fcntl.LOCK_EX)
            deadline = time.monotonic() + BUDGETS[action["budgetProfile"]]["wallSeconds"]
            try:
                if action["lane"] == "standard":
                    os.nice(5)
                elif action["lane"] == "background":
                    os.nice(10)
                workspace = load_workspace(registry, action["workspaceId"])
                worktree, branch, baseline_head = prepare_worktree(root, job, workspace)
                job = transition(root, job, "RUNNING", "deterministic_preflight", "Isolated worktree and branch resolved.", branch=branch, baselineHead=baseline_head, worktreeRef=f"phone-state://coding-dungeon-v2/worktrees/{job_id}")
                prompt = build_prompt(action)
                stage_timeout = BUDGETS[action["budgetProfile"]]["stageSeconds"]
                executor = ""
                result: dict[str, Any] | None = None
                drought = token_drought_status()
                bounded_drought = bounded_token_drought(drought)
                job = transition(
                    root, job, "RUNNING", "inference_policy",
                    "Paid inference is disabled by the local token-drought sentinel." if drought["active"] else "Local inference policy permits the fixed Codex stage.",
                    tokenDrought=bounded_drought, paidInferenceAllowed=not drought["active"],
                )
                if drought["active"]:
                    append_event(root, job_id, "paid_inference_skipped", executor="codex_exec", reason=drought["reason"], valid=drought["valid"])
                codex = None if drought["active"] else shutil.which("codex")
                codex_timeout = remaining_seconds(deadline, stage_timeout)
                if codex and codex_timeout > 0:
                    argv = codex_argv(prompt)
                    argv[0] = codex
                    result = run_process(argv, worktree, codex_timeout, root / "runs" / job_id / "codex.jsonl")
                    append_event(root, job_id, "executor", executor="codex_exec", exit=result["exit"], timedOut=result["timedOut"])
                    evidence = mutation_evidence(worktree, baseline_head)
                    if result["exit"] == 0:
                        executor = "codex_exec"
                    elif evidence["changed"]:
                        transition(root, job, "QUARANTINED", "codex_exec", "Codex stopped ambiguously after mutating the isolated worktree.", executor="codex_exec", mutation=evidence, reason="ambiguous Codex outcome after mutation")
                        return 4
                if not executor:
                    local_argv = local_adam_argv(worktree, prompt)
                    local_timeout = remaining_seconds(deadline, stage_timeout)
                    if local_argv and local_timeout > 0:
                        result = run_process(local_argv, worktree, local_timeout, root / "runs" / job_id / "local-adam.log")
                        append_event(root, job_id, "executor", executor="local_adam", exit=result["exit"], timedOut=result["timedOut"])
                        evidence = mutation_evidence(worktree, baseline_head)
                        if result["exit"] == 0:
                            executor = "local_adam"
                        elif evidence["changed"]:
                            transition(root, job, "QUARANTINED", "local_adam", "Local inference stopped ambiguously after mutating the isolated worktree.", executor="local_adam", mutation=evidence, reason="ambiguous local-inference outcome after mutation")
                            return 4
                if not executor:
                    low = shutil.which("home-center-phone-ask")
                    low_timeout = remaining_seconds(deadline, 120)
                    if low and low_timeout > 0:
                        low_prompt = "Classify this failed coding campaign without proposing commands. Return JSON with decision HOLD or VERIFY and one reason. Objective: " + action["objective"][:1200]
                        low_result = run_process([low, low_prompt], worktree, low_timeout, root / "runs" / job_id / "low-local.log")
                        append_event(root, job_id, "low_local_judge", exit=low_result["exit"], timedOut=low_result["timedOut"])
                    evidence = mutation_evidence(worktree, baseline_head)
                    transition(root, job, "FAILED", "deterministic_closeout", "No mutating executor completed; low local inference was advisory only.", executor="deterministic_only", mutation=evidence, reason="no mutating executor completed")
                    return 2
                evidence = mutation_evidence(worktree, baseline_head)
                if action["taskKind"] in {"implement", "repair"} and not evidence["changed"]:
                    transition(root, job, "FAILED", "deterministic_closeout", "The executor returned success without a repository mutation for a mutating task.", executor=executor, mutation=evidence, reason="successful executor produced no mutation")
                    return 2
                job = transition(root, job, "CHECKPOINTED", "verification", "Executor stopped cleanly; deterministic verification began.", executor=executor, mutation=evidence)
                verification = verify(worktree, workspace, action["verificationProfile"], root, job_id, deadline)
                final_evidence = mutation_evidence(worktree, baseline_head)
                if not verification["ok"]:
                    transition(root, job, "FAILED", "verification", "Trusted verification failed; isolated worktree was preserved.", verification=verification, mutation=final_evidence, reason="trusted verification failed")
                    return 2
                transition(root, job, "SUCCEEDED", "checkpoint_only", "Trusted verification passed; the isolated worktree remains unpushed and unmerged for review.", verification=verification, mutation=final_evidence, reason="verified checkpoint ready")
                return 0
            except DungeonError as exc:
                fresh = load_job(root, job_id)
                transition(root, fresh, "FAILED", "coordinator", str(exc), reason=str(exc))
                return 2
            except Exception as exc:  # fail closed with a durable, bounded receipt
                fresh = load_job(root, job_id)
                transition(root, fresh, "QUARANTINED", "coordinator", f"Unexpected coordinator failure: {exc}", reason=f"unexpected coordinator failure: {exc}")
                return 4


def doctor(registry_path: Path | None = None) -> dict[str, Any]:
    registry = (registry_path or default_registry_path()).expanduser().resolve()
    checks = {name: bool(shutil.which(name)) for name in ("python", "git", "tmux", "codex")}
    checks["workspaceRegistry"] = registry.is_file()
    drought = token_drought_status()
    return {
        "schema": "home-center.dungeon-doctor.v2",
        "ok": checks["python"] and checks["git"] and checks["tmux"] and checks["workspaceRegistry"],
        "checks": checks,
        "registry": str(registry),
        "tokenDrought": bounded_token_drought(drought),
        "paidInferenceAllowed": not drought["active"],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Typed Home Center Mobile Coding Dungeon v2")
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run-job")
    run.add_argument("--job-id", required=True)
    run.add_argument("--state-root", required=True)
    run.add_argument("--registry", required=True)
    check = sub.add_parser("doctor")
    check.add_argument("--registry")
    drought = sub.add_parser("drought")
    drought_sub = drought.add_subparsers(dest="drought_command", required=True)
    drought_status = drought_sub.add_parser("status")
    drought_status.add_argument("--path")
    for name in ("on", "off"):
        command = drought_sub.add_parser(name)
        command.add_argument("--reason", required=True)
        command.add_argument("--path")
    args = parser.parse_args(argv)
    if args.command == "run-job":
        return run_job(Path(args.state_root), Path(args.registry), args.job_id)
    if args.command == "drought":
        drought_path = Path(args.path) if args.path else None
        if args.drought_command == "status":
            result = token_drought_status(drought_path)
        else:
            result = set_token_drought(args.drought_command == "on", args.reason, drought_path)
        print(json.dumps(result, indent=2))
        return 0
    print(json.dumps(doctor(Path(args.registry) if args.registry else None), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
