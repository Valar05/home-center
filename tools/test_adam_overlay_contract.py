#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
service = (ROOT / "android/operator-overlay/app/src/main/java/com/homecenter/operatoroverlay/OperatorOverlayService.java").read_text(encoding="utf-8")
state = (ROOT / "android/operator-overlay/app/src/main/java/com/homecenter/operatoroverlay/OperatorState.java").read_text(encoding="utf-8")
provider = (ROOT / "android/operator-overlay/app/src/main/java/com/homecenter/operatoroverlay/OperatorStateProvider.java").read_text(encoding="utf-8")
daemon = (ROOT / "tools/vlad_swarm_daemon.py").read_text(encoding="utf-8")
router = (ROOT / "tools/adam.py").read_text(encoding="utf-8")
core = (ROOT / "tools/adam_codex_phone.py").read_text(encoding="utf-8")
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

for token in [
    "process_adam_overlay",
    "adam-last-request-id",
    "base64.b64decode",
    "operator_update",
    "ADAM_POLL_SECONDS",
    "timeout=None",
    "_save_pending_response",
    "_deliver_pending_responses",
    "_delivery_halt_path",
    "adam-overlay-pending-response-v1",
    "nextAttemptEpoch",
    "backoffSeconds",
    '"daemonWait":True',
]:
    assert token in daemon, f"daemon missing {token}"

run_idx = daemon.index('result=run(["python3",str(Path(repo_root)/"tools"/"adam.py")')
pending_idx = daemon.index('pending_path=_save_pending_response(pending)', run_idx)
assert pending_idx > run_idx
assert daemon.find('_set_last_adam_request_id(request_id)', run_idx) == -1
success_idx = daemon.index('if update["rc"]==0:')
ack_idx = daemon.index('_set_last_adam_request_id(request_id)', success_idx)
assert ack_idx > success_idx
assert 'payload=_operator_field(raw,"adam_request_payload_b64","");_set_last_adam_request_id(request_id)' not in daemon

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

# Core primitives load Jars but cannot run an unreviewed agent loop.
assert 'def active_jars(' in core
assert 'def run_task(' not in core
assert 'internal core; use bare `adam`' in core

# The only stop-capable worker loads Codex steering and canonical Venice.
assert 'CODEX LOCAL STEERING DOCUMENTS (binding)' in reviewed
assert 'canonical_venice_review(' in reviewed
assert 'Daemon Persistence and Connector Backoff' in reviewed
print("Adam overlay transport / reviewed-only durable-delivery contract: PASS")
