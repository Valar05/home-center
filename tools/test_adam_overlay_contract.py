#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
service = (ROOT / "android/operator-overlay/app/src/main/java/com/homecenter/operatoroverlay/OperatorOverlayService.java").read_text(encoding="utf-8")
state = (ROOT / "android/operator-overlay/app/src/main/java/com/homecenter/operatoroverlay/OperatorState.java").read_text(encoding="utf-8")
provider = (ROOT / "android/operator-overlay/app/src/main/java/com/homecenter/operatoroverlay/OperatorStateProvider.java").read_text(encoding="utf-8")
daemon = (ROOT / "tools/vlad_swarm_daemon.py").read_text(encoding="utf-8")
adam = (ROOT / "tools/adam.py").read_text(encoding="utf-8")

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
    "cloudFallback=False",
    "HC_ADAM_CONTINUE_CMD",
    "qwen2.5-coder:1.5b",
    "def run_mode(",
]:
    assert token in adam, f"adam router missing {token}"

# The Android overlay still submits only the four original explicit modes.
assert '"shell"' not in service
# No automatic route selection: each model lane is entered only by its explicit mode.
assert 'run_chat(text' in adam and 'run_vlad(text' in adam and 'run_continue(text' in adam
assert 'cloudFallback=True' not in adam
print("Adam overlay explicit-mode/no-agent contract: PASS")
