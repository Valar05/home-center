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
chromium = (ROOT / "tools/android_chromium_control.py").read_text(encoding="utf-8")
recovery = (ROOT / "tools/recover_adam_overlay_phone.sh").read_text(encoding="utf-8")

# Dormant explicit-mode plumbing is deliberately preserved for minimum-risk surgery,
# but the visible Beard surface is one natural-language input with AUTO routing.
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
    assert token in service, f"overlay missing preserved contract {token}"
for token in [
    'private String adamMode = "auto";',
    'adamInput.setHint("Talk to Adam…");',
    'Button adamSendButton = button("Ask");',
    'quickRequestButton("Restart", "restart"',
    'quickRequestButton("Night", "night"',
    'quickRequestButton("Chrome", "chrome"',
    'quickRequestButton("Canary", "canary"',
    'OperatorState.submitAdamRequest(this, "auto", request, System.currentTimeMillis())',
    'private View touchGuard;',
    'private void syncTouchGuard(boolean active)',
    'OverlayUiPolicy.touchGuardActive(',
    'FLAG_NOT_TOUCH_MODAL',
]:
    assert token in service, f"one-input Beard overlay missing {token}"
for forbidden in [
    'details.addView(adamModeRow);',
    'root.addView(spotifyRow);',
]:
    assert forbidden not in service, f"one-input Beard overlay still exposes {forbidden}"

for token in ["KEY_ADAM_REQUEST_ID", "KEY_ADAM_REQUEST_MODE", "KEY_ADAM_REQUEST_PAYLOAD_B64", "Base64.NO_WRAP"]:
    assert token in state, f"state missing {token}"
for token in ["adam_request_id", "adam_request_mode", "adam_request_payload_b64"]:
    assert token in provider, f"provider missing {token}"

# Deterministic, no-inference quick ops available through the existing overlay request path.
for token in [
    'deterministicTerminalAlias',
    'bash tools/fortress_phone_ops.sh overlay-restart',
    'bash tools/fortress_phone_ops.sh status',
    'bash tools/fortress_phone_ops.sh chrome-open',
    'bash tools/fortress_phone_ops.sh chrome-reload',
    'bash tools/fortress_phone_ops.sh canary',
]:
    assert token in state, f"state missing deterministic quick op {token}"

# Phone-ops v2 delegates Chromium truth to the dedicated observed-state controller.
for token in [
    'fortress.phone-ops.v2',
    'android_chromium_control.py',
    'chrome_open()',
    'chrome_reload()',
    'chrome_back()',
    'overlay_restart()',
    'exec python3 "$CHROMIUM" canary',
]:
    assert token in phone_ops, f"phone ops missing {token}"
for token in [
    'fortress.android-chromium-control.v1',
    'fortress.android-chromium-canary.v1',
    'dumpsys activity activities',
    'browserWasForceStopped',
    'secondExplicitNavigationObserved',
    'finalChromiumStateObserved',
    'requested browser state was not independently observed',
]:
    assert token in chromium, f"chromium controller missing {token}"

# Night Core is a cheap, deterministic phone policy surface: battery + overlay + relay,
# with no inference and no Chromium screenshot/UI dump.
for token in [
    'night_status()',
    'dumpsys battery',
    'fortress.night-core.status.v1',
    'CHARGE_RECOVERY',
    'POWERED_ACTIVE',
    'BATTERY_ACTIVE',
    'BATTERY_BALANCED',
    'BATTERY_CONSERVE',
    'recommendedPollSeconds',
    'heavyWorkAllowed',
    'night-status|night|night-core',
]:
    assert token in phone_ops, f"Night Core phone policy missing {token}"
night_start = phone_ops.index('night_status()')
night_end = phone_ops.index('overlay_restart()', night_start)
night_body = phone_ops[night_start:night_end]
assert 'android_chromium_control.py' not in night_body
assert 'screencap' not in night_body
assert 'ui_dump' not in night_body

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
print("Adam one-input Beard / Chromium v2 / Night Core / durable-delivery contract: PASS")
