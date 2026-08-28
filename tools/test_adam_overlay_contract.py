#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
service = (ROOT / "android/operator-overlay/app/src/main/java/com/homecenter/operatoroverlay/OperatorOverlayService.java").read_text(encoding="utf-8")
state = (ROOT / "android/operator-overlay/app/src/main/java/com/homecenter/operatoroverlay/OperatorState.java").read_text(encoding="utf-8")
provider = (ROOT / "android/operator-overlay/app/src/main/java/com/homecenter/operatoroverlay/OperatorStateProvider.java").read_text(encoding="utf-8")
daemon = (ROOT / "tools/vlad_swarm_daemon.py").read_text(encoding="utf-8")
router = (ROOT / "tools/adam.py").read_text(encoding="utf-8")
core = (ROOT / "tools/adam_codex_phone.py").read_text(encoding="utf-8")
planned = (ROOT / "tools/adam_planned_venice.py").read_text(encoding="utf-8")
reviewed = (ROOT / "tools/adam_venice_reviewed.py").read_text(encoding="utf-8")
phone_ops = (ROOT / "tools/fortress_phone_ops.sh").read_text(encoding="utf-8")
recovery = (ROOT / "tools/recover_adam_overlay_phone.sh").read_text(encoding="utf-8")

for token in [
    'adamModeButton("TERM", "terminal"',
    'adamModeButton("CHAT", "chat"',
    'adamModeButton("CONT", "continue"',
    'adamModeButton("VLAD", "vlad"',
    'submitAdamRequest()',
    'adamInput.setContentDescription("Adam input. Current mode terminal.")',
    'adamSendButton.setContentDescription("Send request to Adam using the selected explicit mode")',
    'Latest Home Center or Adam message',
    'FLAG_NOT_TOUCH_MODAL',
]:
    assert token in service, f"overlay missing {token}"
# Accessibility contract is semantic, not mechanism-specific: deprecated global
# announcement APIs are not required merely to prove the Adam input/send surface exists.
for token in ["KEY_ADAM_REQUEST_ID", "KEY_ADAM_REQUEST_MODE", "KEY_ADAM_REQUEST_PAYLOAD_B64", "Base64.NO_WRAP"]:
    assert token in state, f"state missing {token}"
for token in ["adam_request_id", "adam_request_mode", "adam_request_payload_b64"]:
    assert token in provider, f"provider missing {token}"

# Deterministic, no-inference quick ops available through the existing TERM input.
for token in [
    'deterministicTerminalAlias',
    'bash tools/fortress_phone_ops.sh overlay-restart',
    'bash tools/fortress_phone_ops.sh status',
    'bash tools/fortress_phone_ops.sh chrome-open',
    'bash tools/fortress_phone_ops.sh chrome-reload',
    'bash tools/fortress_phone_ops.sh canary',
]:
    assert token in state, f"state missing deterministic quick op {token}"
for token in [
    'fortress.phone-ops.v1',
    'chrome_open()',
    'chrome_reload()',
    'overlay_restart()',
    'dumpsys activity activities',
    'accept_adam_cli_phone.sh',
]:
    assert token in phone_ops, f"phone ops missing {token}"
# Overlay recovery must never destroy a working install to force a signer migration.
assert 'existing package preserved' in recovery
assert 'pm uninstall $PACKAGE' not in recovery

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
    'WORKER = ROOT / "tools" / "adam_planned_venice.py"',
    'jarGoverned=True',
    'preExecutionPlanReview=True',
    'veniceReviewed=True',
    'daemonBackoff=True',
    'def run_worker(',
    'def run_mode(',
]:
    assert token in router, f"adam body router missing {token}"
for mode in ['"terminal"', '"chat"', '"continue"', '"vlad"', '"radio"']:
    assert mode in router, f"adam router missing mode {mode}"

assert '"shell"' not in service
assert 'if mode == "terminal"' in router
assert 'return run_worker(mode, text, cwd, timeout)' in router
assert 'ollama_generate' not in router
assert 'local_exec_plan' not in router

assert 'def active_jars(' in core
assert 'def run_task(' not in core
assert 'internal core; use bare `adam`' in core

for token in [
    'def preflight(',
    'PLAN_ALLOWED',
    'REPLAN_REQUIRED',
    'selectedJars',
    'antagonism',
    'review_plan_phone(',
]:
    assert token in planned, f"planned worker missing {token}"

assert 'CODEX LOCAL STEERING DOCUMENTS (binding)' in reviewed
assert 'canonical_venice_review(' in reviewed
assert 'Daemon Persistence and Connector Backoff' in reviewed
print("Adam overlay transport / deterministic quick ops / planned + Venice-reviewed durable-delivery contract: PASS")
