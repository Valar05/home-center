#!/usr/bin/env python3
from pathlib import Path
import tempfile
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import adam_codex_phone as worker

jars = worker.active_jars()
assert "Adam Personality Gate" in jars
assert "Repository Truth and Evidence" in jars
assert "Mission Boundary" in jars

assert worker.parse_action("generic prose that must never leak") is None
embedded = worker.parse_action('noise {"tool":"respond","text":"Hey Drew."} tail')
assert embedded and embedded["tool"] == "respond"

with tempfile.TemporaryDirectory() as td:
    ws = Path(td).resolve()
    # Dangerous and ordinary mutating shell are both denied to model inference.
    for command in (
        "rm -rf /",
        "rm a.txt",
        "git reset --hard HEAD~1",
        "git clean -fd",
        "git add .",
        "printf hacked > a.txt",
        "touch new.txt",
        "mv a b",
    ):
        _, blocked = worker.execute_tool(ws, {"tool":"run_command","command":command})
        assert blocked.get("ok") is False, (command, blocked)

    # Inspection/validation shell remains usable.
    _, inspected = worker.execute_tool(ws, {"tool":"run_command","command":"printf inspect-only"})
    assert inspected.get("ok") is True and "inspect-only" in inspected.get("stdout", "")

    _, wrote = worker.execute_tool(ws, {"tool":"write_file","path":"a.txt","content":"alpha\nbeta\n"})
    assert wrote.get("ok") is True
    _, read = worker.execute_tool(ws, {"tool":"read_file","path":"a.txt","start":1,"lines":5})
    assert read.get("ok") is True and "alpha" in read.get("content", "")
    _, found = worker.execute_tool(ws, {"tool":"search_files","query":"beta","path":"."})
    assert found.get("ok") is True and found.get("hits")
    try:
        worker.workspace_path(ws, "../escape")
        raise AssertionError("workspace escape should fail")
    except RuntimeError:
        pass
    terminal, response = worker.execute_tool(ws, {"tool":"respond","text":"Hey Drew."})
    assert terminal is True and response.get("text") == "Hey Drew."

print("Adam deterministic core / inferred-shell boundary contract: PASS")
