#!/usr/bin/env python3
from __future__ import annotations

import json
import importlib.util
import subprocess
import sys
import tempfile
import types
from concurrent.futures import ThreadPoolExecutor
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
assert len(dungeon.session_for(normalized["requestId"])) == 31
unicode_fixture = dungeon.normalize_run_action({
    "requestId": "fortress-unicode-fixture-0001", "campaignId": "fortress-online", "workspaceId": "home-center",
    "objective": "Map Ω \"star\" \\ path\nwithout shell.", "acceptance": ["Preserve 🌟 exactly."],
    "constraints": ["Keep tabs\tinside evidence."], "taskKind": "verify", "lane": "standard",
    "budgetProfile": "probe", "verificationProfile": "fast",
})
assert dungeon.input_hash(unicode_fixture) == "5a380184616f6e0abc66e8b6d358d5b4d0f3b5fab9231ba04bb97830c2e3651d"

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
codex_summary = dungeon.executor_receipt({
    "exit": 0, "timedOut": False, "outputBytes": 200, "outputTruncated": False,
    "outputTail": '{"type":"item.completed","item":{"type":"agent_message","text":"Exact checkpoint ready."}}\n'
})
assert codex_summary["summary"] == "Exact checkpoint ready."
assert dungeon.executor_receipt({"outputTail": "plain local result\x1b"})["summary"] == "plain local result"
adapter_source = (ROOT / "tools" / "dungeon_local_adam.py").read_text(encoding="utf-8")
for marker in ("disabled_run_command", "disabled_phone_intent", "confined_execute_tool", "ALLOWED_TOOLS", "worker.run_command =", "worker.phone_intent =", "worker.execute_tool ="):
    assert marker in adapter_source

worker_stub = types.ModuleType("adam_codex_phone")
worker_stub.run_command = lambda _workspace, _obj: {"ok": True, "unsafe": "shell"}
worker_stub.phone_intent = lambda _workspace, _obj: {"ok": True, "unsafe": "device"}
worker_stub.execute_tool = lambda _workspace, obj: (False, {"ok": True, "tool": obj.get("tool")})
reviewed_stub = types.ModuleType("adam_venice_reviewed")
reviewed_calls = []
reviewed_stub.run_task = lambda prompt, workspace: reviewed_calls.append((prompt, workspace)) or 0
prior_worker = sys.modules.get("adam_codex_phone")
prior_reviewed = sys.modules.get("adam_venice_reviewed")
try:
    sys.modules["adam_codex_phone"] = worker_stub
    sys.modules["adam_venice_reviewed"] = reviewed_stub
    adapter_spec = importlib.util.spec_from_file_location("dungeon_local_adam_contract", ROOT / "tools" / "dungeon_local_adam.py")
    assert adapter_spec and adapter_spec.loader
    adapter = importlib.util.module_from_spec(adapter_spec)
    adapter_spec.loader.exec_module(adapter)
    assert adapter.main(["bounded", "campaign"]) == 0
    assert worker_stub.run_command is adapter.disabled_run_command
    assert worker_stub.phone_intent is adapter.disabled_phone_intent
    assert worker_stub.execute_tool is adapter.confined_execute_tool
    assert worker_stub.run_command(Path.cwd(), {"command": "anything"})["ok"] is False
    assert worker_stub.phone_intent(Path.cwd(), {"intent": "anything"})["ok"] is False
    assert worker_stub.execute_tool(Path.cwd(), {"tool": "future_network_tool"})[1]["ok"] is False
    assert worker_stub.execute_tool(Path.cwd(), {"tool": "read_file"})[1] == {"ok": True, "tool": "read_file"}
    assert reviewed_calls and reviewed_calls[0][0] == "bounded campaign"
finally:
    if prior_worker is None:
        sys.modules.pop("adam_codex_phone", None)
    else:
        sys.modules["adam_codex_phone"] = prior_worker
    if prior_reviewed is None:
        sys.modules.pop("adam_venice_reviewed", None)
    else:
        sys.modules["adam_venice_reviewed"] = prior_reviewed

with tempfile.TemporaryDirectory() as td:
    base = Path(td)
    repo = base / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "main", str(repo)], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.email", "test@example.invalid"], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.name", "Dungeon Test"], check=True)
    (repo / "README.md").write_text("test\n", encoding="utf-8")
    (repo / "tools").mkdir()
    for worker_name in ("dungeon_local_adam.py", "adam_venice_reviewed.py", "adam_codex_phone.py"):
        (repo / "tools" / worker_name).write_text("# test fixture\n", encoding="utf-8")
    (repo / ".continue" / "rules").mkdir(parents=True)
    (repo / ".continue" / "rules" / "70-judgement-jar-test.md").write_text(
        "Venice Completion and Code Review Gate\nDaemon Persistence and Connector Backoff\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-qm", "initial"], check=True)
    source_commit = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], check=True, text=True, capture_output=True).stdout.strip()
    registry = base / "workspaces.json"
    registry_value = {
        "schema": dungeon.WORKSPACE_REGISTRY_SCHEMA,
        "workspaces": {"home-center": {"root": str(repo), "baseRef": source_commit, "sourceCommit": source_commit, "sourceBranch": "main", "verification": {"fast": []}}},
    }
    registry.write_text(json.dumps(registry_value), encoding="utf-8")
    assert dungeon.registry_health(registry) == {"ok": True, "workspaceCount": 1, "error": ""}
    (repo / "README.md").write_text("tracked drift\n", encoding="utf-8")
    assert dungeon.registry_health(registry)["ok"] is False
    (repo / "README.md").write_text("test\n", encoding="utf-8")
    assert dungeon.registry_health(registry)["ok"] is True
    subprocess.run(["git", "-C", str(repo), "switch", "-q", "-c", "drift-branch"], check=True)
    assert dungeon.registry_health(registry)["ok"] is False
    subprocess.run(["git", "-C", str(repo), "switch", "-q", "main"], check=True)
    assert dungeon.registry_health(registry)["ok"] is True
    floating_registry = base / "floating-workspaces.json"
    floating_registry.write_text(json.dumps({
        "schema": dungeon.WORKSPACE_REGISTRY_SCHEMA,
        "workspaces": {"home-center": {"root": str(repo), "baseRef": "HEAD", "verification": {"fast": []}}},
    }), encoding="utf-8")
    assert dungeon.registry_health(floating_registry)["ok"] is False
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
    race_action = request(requestId="fortress-concurrent-admission-0001")
    with ThreadPoolExecutor(max_workers=8) as pool:
        raced = list(pool.map(lambda _index: dungeon.submit(race_action, state, registry, fake_launcher), range(8)))
    assert len({item["jobId"] for item in raced}) == 1
    assert sum(item["attached"] is False for item in raced) == 1
    assert sum(item["attached"] is True for item in raced) == 7
    assert dungeon.load_job(state, raced[0]["jobId"])["inputHash"] == raced[0]["inputHash"]
    binding_state = base / "state-binding-drift"
    binding_receipt = dungeon.submit(request(requestId="fortress-binding-drift-0001"), binding_state, registry, fake_launcher)
    drifted_registry = json.loads(json.dumps(registry_value))
    drifted_registry["workspaces"]["home-center"]["verification"]["fast"] = [["git", "status", "--short"]]
    registry.write_text(json.dumps(drifted_registry), encoding="utf-8")
    assert dungeon.run_job(binding_state, registry, binding_receipt["jobId"]) == 4
    binding_job = dungeon.load_job(binding_state, binding_receipt["jobId"])
    assert binding_job["state"] == "QUARANTINED" and binding_job["stage"] == "workspace_identity"
    registry.write_text(json.dumps(registry_value), encoding="utf-8")
    admitted_job = dungeon.load_job(state, first["jobId"])
    tmux_argv = dungeon.tmux_argv("/usr/bin/tmux", state, registry, admitted_job)
    assert tmux_argv[:5] == ["/usr/bin/tmux", "new-session", "-d", "-s", first["tmuxSession"]]
    assert "--" not in tmux_argv and "sh" not in tmux_argv and "-lc" not in tmux_argv
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
    assert worktree.is_dir() and branch == f"fortress/fortress-online-{first['jobId'][4:]}"
    evidence = dungeon.mutation_evidence(worktree, baseline)
    assert evidence["changed"] is False
    (worktree / "new.txt").write_text("checkpoint\n", encoding="utf-8")
    evidence = dungeon.mutation_evidence(worktree, baseline)
    assert evidence["changed"] is True and evidence["dirty"] is True
    missing = dungeon.run_process(["definitely-not-a-real-dungeon-executable"], worktree, 1, state / "runs" / first["jobId"] / "missing.log")
    assert missing["exit"] == 127 and missing["timedOut"] is False
    flood_log = state / "runs" / first["jobId"] / "bounded.log"
    flood = dungeon.run_process([sys.executable, "-c", "import sys; sys.stdout.write('x' * 350000)"], worktree, 10, flood_log)
    assert flood["exit"] == 0 and flood["outputBytes"] == 350000 and flood["outputTruncated"] is True
    assert flood_log.stat().st_size <= dungeon.LOG_HEAD_BYTES + dungeon.LOG_TAIL_BYTES + 2000
    assert flood["outputTail"].endswith("x" * 100)

    original_which = dungeon.shutil.which
    original_run_process = dungeon.run_process
    original_local_argv = dungeon.local_adam_argv
    mode = {"value": "dirty_codex"}
    executor_calls = []

    def fake_which(name):
        if name == "codex":
            return "/trusted/fake-codex"
        if name == "home-center-phone-ask":
            return "/trusted/fake-low" if mode["value"] in {"low_dirty", "low_clean"} else None
        return original_which(name)

    def fake_local_argv(_worktree, prompt):
        return ["/trusted/fake-local", prompt]

    def fake_process(argv, cwd, _timeout, _output_path):
        executable = argv[0]
        executor_calls.append(Path(executable).name)
        exit_code = 0
        output_tail = ""
        if executable == "/trusted/fake-codex":
            exit_code = 1
            output_tail = "codex stopped"
            if mode["value"] == "dirty_codex":
                (cwd / "codex-ambiguous.txt").write_text("dirty failure\n", encoding="utf-8")
        elif executable == "/trusted/fake-local":
            if mode["value"] == "local_success":
                (cwd / "local-checkpoint.txt").write_text("bounded success\n", encoding="utf-8")
                output_tail = "bounded local checkpoint"
            elif mode["value"] == "local_dirty_failure":
                (cwd / "local-ambiguous.txt").write_text("dirty failure\n", encoding="utf-8")
                exit_code = 1
                output_tail = "local stopped"
            else:
                exit_code = 1
        elif executable == "/trusted/fake-low":
            output_tail = '{"decision":"HOLD","reason":"No mutating executor completed."}'
            if mode["value"] == "low_dirty":
                (cwd / "low-local-violation.txt").write_text("forbidden mutation\n", encoding="utf-8")
        return {"argv0": Path(executable).name, "exit": exit_code, "timedOut": False,
                "startedAtMs": dungeon.epoch_ms(), "endedAtMs": dungeon.epoch_ms(),
                "outputBytes": len(output_tail.encode("utf-8")), "outputTruncated": False, "outputTail": output_tail}

    dungeon.shutil.which = fake_which
    dungeon.run_process = fake_process
    dungeon.local_adam_argv = fake_local_argv
    try:
        dirty_state = base / "state-dirty-codex"
        dirty_receipt = dungeon.submit(request(requestId="fortress-dirty-codex-0001"), dirty_state, registry, fake_launcher)
        assert dungeon.run_job(dirty_state, registry, dirty_receipt["jobId"]) == 4
        dirty_job = dungeon.load_job(dirty_state, dirty_receipt["jobId"])
        assert dirty_job["state"] == "QUARANTINED" and dirty_job["executor"] == "codex_exec"
        assert executor_calls == ["fake-codex"]

        mode["value"] = "local_dirty_failure"
        executor_calls.clear()
        local_dirty_state = base / "state-dirty-local"
        local_dirty_receipt = dungeon.submit(request(requestId="fortress-dirty-local-0001"), local_dirty_state, registry, fake_launcher)
        assert dungeon.run_job(local_dirty_state, registry, local_dirty_receipt["jobId"]) == 4
        local_dirty_job = dungeon.load_job(local_dirty_state, local_dirty_receipt["jobId"])
        assert local_dirty_job["state"] == "QUARANTINED" and local_dirty_job["executor"] == "local_adam"
        assert executor_calls == ["fake-codex", "fake-local"]

        mode["value"] = "low_dirty"
        executor_calls.clear()
        low_dirty_state = base / "state-dirty-low"
        low_dirty_receipt = dungeon.submit(request(requestId="fortress-dirty-low-0001"), low_dirty_state, registry, fake_launcher)
        assert dungeon.run_job(low_dirty_state, registry, low_dirty_receipt["jobId"]) == 4
        low_dirty_job = dungeon.load_job(low_dirty_state, low_dirty_receipt["jobId"])
        assert low_dirty_job["state"] == "QUARANTINED" and low_dirty_job["executor"] == "low_local_judge"
        assert executor_calls == ["fake-codex", "fake-local", "fake-low"]

        mode["value"] = "low_clean"
        executor_calls.clear()
        low_state = base / "state-clean-low"
        low_receipt = dungeon.submit(request(requestId="fortress-clean-low-0001"), low_state, registry, fake_launcher)
        assert dungeon.run_job(low_state, registry, low_receipt["jobId"]) == 2
        low_job = dungeon.load_job(low_state, low_receipt["jobId"])
        assert low_job["state"] == "FAILED" and low_job["executor"] == "low_local_judge"
        assert dungeon.bounded_job(low_job)["executorLogRef"].endswith("/low-local.log")
        assert executor_calls == ["fake-codex", "fake-local", "fake-low"]

        mode["value"] = "local_success"
        executor_calls.clear()
        local_state = base / "state-local-success"
        local_receipt = dungeon.submit(request(requestId="fortress-local-success-0001"), local_state, registry, fake_launcher)
        assert dungeon.run_job(local_state, registry, local_receipt["jobId"]) == 0
        local_job = dungeon.load_job(local_state, local_receipt["jobId"])
        assert local_job["state"] == "SUCCEEDED" and local_job["executor"] == "local_adam"
        assert local_job["verification"]["ok"] is True
        assert dungeon.bounded_job(local_job)["executorSummary"] == "bounded local checkpoint"
        assert executor_calls == ["fake-codex", "fake-local", "git"]
    finally:
        dungeon.shutil.which = original_which
        dungeon.run_process = original_run_process
        dungeon.local_adam_argv = original_local_argv

print("Mobile Coding Dungeon v2 contract: PASS")
