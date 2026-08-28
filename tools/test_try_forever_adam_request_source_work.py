#!/usr/bin/env python3
"""Split source contract for finite Adam request work before trim/alias/encoding.

SOURCE ONLY / UNEXECUTED. OperatorState request custody is now SOURCE_WIRED;
OperatorOverlayService pre-materialization custody remains the deliberate RED boundary.
This fixture must not be cited as TESTED until an authoritative execution receipt exists.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SERVICE_PATH = ROOT / "android/operator-overlay/app/src/main/java/com/homecenter/operatoroverlay/OperatorOverlayService.java"
STATE_PATH = ROOT / "android/operator-overlay/app/src/main/java/com/homecenter/operatoroverlay/OperatorState.java"
PATCH_PATH = ROOT / "patches/try-forever-adam-request-source-work-throat.patch"

service = SERVICE_PATH.read_text(encoding="utf-8")
state = STATE_PATH.read_text(encoding="utf-8")
patch = PATCH_PATH.read_text(encoding="utf-8")

state_start = state.index("    static void submitAdamRequest(")
state_end = state.index("    static void updateSpotifyReceipt(", state_start)
state_submit = state[state_start:state_end]

# Package/direct callers own a finite request throat before trim/alias/encoding.
assert "MAX_ADAM_REQUEST_SOURCE_CODE_UNITS" in state
request_gate = state_submit.index("exact.length() > MAX_ADAM_REQUEST_SOURCE_CODE_UNITS")
request_trim = state_submit.index("exact.trim().isEmpty()")
alias = state_submit.index("deterministicTerminalAlias(exact)")
encode = state_submit.index("exact.getBytes(StandardCharsets.UTF_8)")
assert request_gate < request_trim < alias < encode

# Mode authority is delegated to the exact canonical mode policy instead of
# independently normalizing whitespace/case inside the request persistence owner.
mode_admission = state_submit.index("AdamModeSelectionAccessibilityPolicy.requireMode(")
request_source = state_submit.index('String exact = text == null ? "" : text;')
assert mode_admission < request_source
assert ".trim().toLowerCase" not in state_submit

# The durable surgery artifact records partial application rather than pretending
# the service and state owners share one capability state.
assert "State: PARTIAL_APPLIED_SOURCE__SERVICE_PROPOSED_NOT_APPLIED" in patch
assert "Service current/base blob: 2935243f136359e3489a89108406e888b0ec2911" in patch
assert "OperatorState current/result blob: 3870272863878cd7eaef69d24b31a6c8de1bbef9" in patch
assert "Direct state owner is SOURCE_WIRED" in patch
assert "P0/phone execution" in patch and "untouched" in patch

# The staged service surgery must consume the same bounded material-request
# classification before materializing/trimming admitted source.
patch_gate = patch.index("AdamSendAvailabilityAccessibilityPolicy.hasMaterialRequest(editable)")
patch_materialize = patch.index("editable.toString().trim()")
assert patch_gate < patch_materialize

service_start = service.index("    private void submitAdamRequest()")
service_end = service.index("    private void recomputeExpandedWidth()", service_start)
service_submit = service[service_start:service_end]

# The repeatable Adam action receipt remains deliberately preserved while its
# separate migration blocker is unresolved.
assert 'adamInput.announceForAccessibility("Sent to Adam " + adamMode)' in service_submit

# Remaining RED owner boundary: authenticated native source must itself consume
# the bounded availability predicate before toString()/trim(). Keep the failure
# precise and compile-valid instead of relying on an accidental substring error.
assert "AdamSendAvailabilityAccessibilityPolicy.hasMaterialRequest(editable)" in service_submit, (
    "RED: OperatorOverlayService.submitAdamRequest still materializes editable source "
    "before the bounded Adam availability gate"
)
service_gate = service_submit.index(
    "AdamSendAvailabilityAccessibilityPolicy.hasMaterialRequest(editable)")
service_materialize = service_submit.index("editable.toString().trim()")
assert service_gate < service_materialize

print("Adam request finite source-work owner boundary: PASS")
