#!/usr/bin/env python3
"""RED source contract for finite Adam request work before trim/alias/encoding.

SOURCE ONLY / UNEXECUTED at creation. This fixture describes the existing-owner
boundary required by patches/try-forever-adam-request-source-work-throat.patch.
It must not be cited as TESTED until an authoritative execution receipt exists.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SERVICE_PATH = ROOT / "android/operator-overlay/app/src/main/java/com/homecenter/operatoroverlay/OperatorOverlayService.java"
STATE_PATH = ROOT / "android/operator-overlay/app/src/main/java/com/homecenter/operatoroverlay/OperatorState.java"
PATCH_PATH = ROOT / "patches/try-forever-adam-request-source-work-throat.patch"

service = SERVICE_PATH.read_text(encoding="utf-8")
state = STATE_PATH.read_text(encoding="utf-8")
patch = PATCH_PATH.read_text(encoding="utf-8")

service_start = service.index("    private void submitAdamRequest()")
service_end = service.index("    private void recomputeExpandedWidth()", service_start)
service_submit = service[service_start:service_end]

# Direct UI send must stop over-ceiling source before toString()/trim().
service_gate = service_submit.index(
    "AdamSendAvailabilityAccessibilityPolicy.sourceWithinWorkBudget(editable)")
service_materialize = service_submit.index("editable.toString().trim()")
assert service_gate < service_materialize

# The repeatable Adam action receipt remains deliberately preserved while its
# separate migration blocker is unresolved.
assert 'adamInput.announceForAccessibility("Sent to Adam " + adamMode)' in service_submit

state_start = state.index("    static void submitAdamRequest(")
state_end = state.index("    static void updateSpotifyReceipt(", state_start)
state_submit = state[state_start:state_end]

# Package/direct callers do not inherit the UI gate automatically.
assert "MAX_ADAM_REQUEST_SOURCE_CODE_UNITS" in state
assert "MAX_ADAM_MODE_SOURCE_CODE_UNITS" in state
mode_gate = state_submit.index("rawMode.length() > MAX_ADAM_MODE_SOURCE_CODE_UNITS")
mode_trim = state_submit.index("rawMode.trim().toLowerCase()")
assert mode_gate < mode_trim
request_gate = state_submit.index("exact.length() > MAX_ADAM_REQUEST_SOURCE_CODE_UNITS")
request_trim = state_submit.index("exact.trim().isEmpty()")
alias = state_submit.index("deterministicTerminalAlias(exact)")
encode = state_submit.index("exact.getBytes(StandardCharsets.UTF_8)")
assert request_gate < request_trim < alias < encode

# The staged surgery is exact-base-locked to the authenticated current owners
# and does not mutate routing destinations or P0 recovery machinery.
assert "Service base blob: 2935243f136359e3489a89108406e888b0ec2911" in patch
assert "State base blob: 94772cc4e9a3b42591832337420de4c416aa18e4" in patch
assert "P0/phone execution, routing aliases, queue/relay, recovery, and transport destinations are untouched." in patch

print("Adam request finite source-work owner boundary: PASS")
