#!/usr/bin/env python3
import contextlib
import importlib.util
import io
import json
import os
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("adam", ROOT / "tools" / "adam.py")
assert spec and spec.loader
adam = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adam)


def run(mode, text, request_id):
    os.environ["HC_COMMAND_ID"] = request_id
    stream = io.StringIO()
    with contextlib.redirect_stdout(stream):
        rc = adam.run_mode(mode, text, str(ROOT), 20)
    value = json.loads(stream.getvalue().strip().splitlines()[-1])
    return rc, value


with tempfile.TemporaryDirectory() as directory:
    os.environ["HC_INNER_FORTRESS_STATE"] = str(Path(directory) / "state.json")
    assert adam.inner_should_intercept("Pills taken") is True
    assert adam.inner_should_intercept("I need a shower") is False

    rc, opened = run("chat", "  Inner Fortress\n", "adam-invoke-1")
    assert rc == 0
    assert opened["mode"] == "inner-fortress"
    assert opened["response"]["state"] == "ACTIVE_REHEARSAL"
    assert opened["response"]["raw"] == "  Inner Fortress\n"
    session_id = opened["response"]["sessionId"]

    rc, story = run("chat", "Story.", "adam-story-1")
    assert rc == 0
    assert story["response"]["route"] == "STORY_CONTINUE"
    assert story["response"]["sessionId"] == session_id
    assert story["response"]["cognitionEnvelope"]["performanceLabel"] == "CHATGPT_REHEARSAL_OF_SHE_RA"

print("Adam CHAT -> Inner Fortress durable rehearsal integration: PASS")
