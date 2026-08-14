#!/usr/bin/env python3
import json, os, subprocess, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOOL = ROOT / "tools" / "demotivational_poster_os.py"

with tempfile.TemporaryDirectory() as td:
    state = Path(td) / "poster.sqlite3"
    env = dict(os.environ, HC_POSTER_OS_STATE=str(state), HC_POSTER_SURFACE_COOLDOWN_SECONDS="0")
    def run(*args):
        return subprocess.run(["python3", str(TOOL), *args], env=env, text=True, capture_output=True, check=True).stdout

    run("ingest", "Home Center still has no button after architecture work", "--importance", "9", "--tags", "button,failure,adam")
    first = json.loads(run("surface", "--force"))
    assert first["truth"] == "PROMPT_AUTHORED", first
    assert first["render_state"] == "PROMPT_AUTHORED", first
    assert first["title"], first
    assert first["prompt"], first
    sid = first["id"]

    # Repeat is legal. It may or may not be the same specimen, but no specimen is globally banned by prior surfacing.
    second = json.loads(run("surface", "--force"))
    assert second and second["id"], second

    run("feedback", sid, "KEEP")
    status = json.loads(run("status"))
    assert status["specimens"] >= 3, status
    assert status["rendered"] == 0, status
    assert status["renderer_configured"] is False, status

print("poster-os canary: PASS")
