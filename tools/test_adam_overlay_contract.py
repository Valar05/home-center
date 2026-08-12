#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
service = (ROOT / "android/operator-overlay/app/src/main/java/com/homecenter/operatoroverlay/OperatorOverlayService.java").read_text(encoding="utf-8")
state = (ROOT / "android/operator-overlay/app/src/main/java/com/homecenter/operatoroverlay/OperatorState.java").read_text(encoding="utf-8")
provider = (ROOT / "android/operator-overlay/app/src/main/java/com/homecenter/operatoroverlay/OperatorStateProvider.java").read_text(encoding="utf-8")
daemon = (ROOT / "tools/vlad_swarm_daemon.py").read_text(encoding="utf-8")
router = (ROOT / "tools/adam.py").read_text(encoding="utf-8")
worker = (ROOT / "tools/adam_codex_phone.py").read_text(encoding="utf-8")
reviewed = (ROOT / "tools/adam_venice_reviewed.py").read_text(encoding="utf-8")

for token in [
    'adamModeButton("TERM", "terminal"',
    'adamModeButton("CHAT", "chat"',
    'adamModeButton("CONT", "continue"',
    'adamModeButton("VLAD", "vlad"',
    'submitAdamRequest()',
    'announceForAccessibility',
    'Latest Home Center or Adam message',
    'FLAG_NOT_TOUCH_MODAL',
]:
    assert token in service, f"overlay missing {token}"

for token in ["KEY_ADAM_REQUEST_ID", "KEY_ADAM_REQUEST_MODE", "KEY_ADAM_REQUEST_PAYLOAD_B64", "Base64.NO_WRAP"]:
    assert token in state, f"state missing {token}"
for token in ["adam_request_id", "adam_request_mode", "adam_request_payload_b64"]:
    assert token in provider, f"provider missing {token}"
for token in ["process_adam_overlay", "adam-last-request-id", "base64.b64decode", "operator_update", "ADAM_POLL_SECONDS"]:
    assert token in daemon, f"daemon missing {token}"

for token in [
    'ONE_SHOT_MODES = ("terminal", "chat", "continue", "vlad")',
    'WORKER = ROOT / "tools" / "adam_venice_reviewed.py"',
    'jarGoverned=True',
    'veniceReviewed=True',
    'daemonBackoff=True',
    'def run_worker(',
    'def run_mode(',
]:
    assert token in router, f"adam body router missing {token}"

assert '"shell"' not in service
assert 'if mode == "terminal"' in router
assert 'return run_worker(mode, text, cwd, timeout)' in router
assert 'ollama_generate' not in router
assert 'local_exec_plan' not in router

assert 'ACTIVE JUDGEMENT JARS (binding)' in worker
assert 'def active_jars(' in worker
assert 'Unstructured model prose is never shown' in worker
assert 'Venice reviews every stop' in reviewed
assert 'Daemon Persistence and Connector Backoff' in reviewed
print("Adam overlay transport / reviewed Codex-worker contract: PASS")
