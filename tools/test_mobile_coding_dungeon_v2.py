#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import mobile_coding_dungeon_v2 as dungeon


def request(**updates):
    value = {
        "action": "dungeon_run",
        "schema": dungeon.DUNGEON_RUN_SCHEMA,
        "requestId": "fortress-android67-0001",
        "deviceId": "primary-phone",
        "campaignId": "fortress-online",
        "workspaceId": "home-center",
        "objective": "Implement and verify the typed Coding Dungeon ingress.",
        "acceptance": ["Unknown fields fail closed.", "Each job owns one isolated tmux session."],
        "constraints": ["No raw shell, caller path, argv, URL, environment, or model field."],
        "taskKind": "implement",
        "lane": "critical",
        "criticalReason": "Restore the missing first-class Fortress execution aperture.",
        "budgetProfile": "probe",
        "verificationProfile": "fast",
        "inferencePolicy": dungeon.INFERENCE_POLICY,
        "publicationPolicy": dungeon.PUBLICATION_POLICY,
    }
    value.update(updates)
    return value


normalized = dungeon.normalize_run_action(request())
assert normalized["inferencePolicy"] == dungeon.INFERENCE_POLICY
assert normalized["publicationPolicy"] == "checkpoint-only"
assert dungeon.job_id_for(normalized["requestId"]) == dungeon.job_id_for(normalized["requestId"])
assert dungeon.session_for(normalized["requestId"]).startswith("hc-dng-")

for field, value in {
    "manifest": "/tmp/attack.json",
    "path": "/data/data/com.termux/files/home",
    "command": "rm -rf anything",
    "argv": ["bash", "-lc", "evil"],
    "url": "https://example.invalid",
    "env": {"TOKEN": "secret"},
    "model": "caller-selected",
}.items():
    try:
        dungeon.normalize_run_action(request(**{field: value}))
        raise AssertionError(f"{field} should be rejected")
    except dungeon.DungeonError as exc:
        assert "rejects unknown field" in str(exc)

try:
    dungeon.normalize_run_action(request(lane="standard"))
    raise AssertionError("criticalReason outside critical lane should fail")
except dungeon.DungeonError:
    pass

try:
    dungeon.normalize_run_action(request(objective="Valid prefix\x00invalid control"))
    raise AssertionError("control characters should fail")
except dungeon.DungeonError:
    pass

argv = dungeon.codex_argv("bounded objective")
assert argv == ["codex", "exec", "--sandbox", "workspace-write", "--ask-for-approval", "never", "--json", "bounded objective"]
assert all(part not in {"bash", "sh", "-lc"} for part in argv)

with tempfile.TemporaryDirectory() as td:
    base = Path(td)
    repo = base / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.email", "test@example.invalid"], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.name", "Dungeon Test"], check=True)
    (repo / "README.md").write_text("test\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(repo), "add", "README.md"], check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-qm", "initial"], check=True)
    registry = base / "workspaces.json"
    registry.write_text(json.dumps({
        "schema": dungeon.WORKSPACE_REGISTRY_SCHEMA,
        "workspaces": {"home-center": {"root": str(repo), "baseRef": "HEAD", "verification": {"fast": []}}},
    }), encoding="utf-8")
    state = base / "state"
    launches = []

    def fake_launcher(state_root, registry_path, job):
        launches.append((state_root, registry_path, job["jobId"]))
        return {"ok": True, "attached": False}

    first = dungeon.submit(request(), state, registry, fake_launcher)
    assert first["schema"] == "home-center.dungeon-submit-receipt.v2"
    assert first["state"] == "ACCEPTED" and first["attached"] is False
    second = dungeon.submit(request(), state, registry, fake_launcher)
    assert second["jobId"] == first["jobId"] and second["attached"] is True
    assert len(launches) == 2  # replay attaches/restarts only the same deterministic job
    try:
        dungeon.submit(request(objective="A different exact intent with the same request identity."), state, registry, fake_launcher)
        raise AssertionError("conflicting replay should fail")
    except dungeon.DungeonConflict:
        pass
    read = dungeon.status({
        "action": "dungeon_status", "schema": dungeon.DUNGEON_STATUS_SCHEMA,
        "requestId": "fortress-status-0001", "deviceId": "primary-phone", "jobId": first["jobId"],
    }, state)
    assert read["state"] == "ACCEPTED" and read["inputHash"] == first["inputHash"]
    job = dungeon.load_job(state, first["jobId"])
    workspace = dungeon.load_workspace(registry, "home-center")
    worktree, branch, baseline = dungeon.prepare_worktree(state, job, workspace)
    assert worktree.is_dir() and branch.startswith("fortress/fortress-online-")
    evidence = dungeon.mutation_evidence(worktree, baseline)
    assert evidence["changed"] is False
    (worktree / "new.txt").write_text("checkpoint\n", encoding="utf-8")
    evidence = dungeon.mutation_evidence(worktree, baseline)
    assert evidence["changed"] is True and evidence["dirty"] is True
    missing = dungeon.run_process(["definitely-not-a-real-dungeon-executable"], worktree, 1, state / "runs" / first["jobId"] / "missing.log")
    assert missing["exit"] == 127 and missing["timedOut"] is False

print("Mobile Coding Dungeon v2 contract: PASS")
