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
    _, blocked = worker.execute_tool(ws, {"tool":"run_command","command":"rm -rf /"})
    assert blocked.get("ok") is False
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

print("Adam Codex-shaped phone worker contract: PASS")
