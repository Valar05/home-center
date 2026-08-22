#!/usr/bin/env python3
"""RED owner boundary for exact surgery-state admission plus v10 final-root custody.

This source is intentionally red against canonical probe v7 until the corrected v10 surgery is
actually applied and authenticated. v9 is rejected because current textual STATE_RE normalization
can erase whitespace before exact state admission. Source existence is not owner wiring or TESTED.
"""

from pathlib import Path


OWNER = Path("tools/try_forever_owner_surgery_custody_probe.py")


def _owner_source() -> str:
    return OWNER.read_text(encoding="utf-8")


def test_owner_uses_exact_state_admission_not_proposed_substring():
    source = _owner_source()
    assert "from try_forever_owner_surgery_state_policy import admit_owner_surgery_state" in source
    assert "admit_owner_surgery_state(state.group(1))" in source
    assert "_consistent_delta_string(payload, DELTA_STATE_KEYS, \"state/status\")" in source
    assert "return \"PROPOSED\" in upper" not in source


def test_owner_textual_state_header_does_not_normalize_state_token():
    source = _owner_source()
    assert 'STATE_RE = re.compile(r"^#\\s*(?:STATUS|State)\\s*: ([^\\r\\n]*)$", re.I | re.M)' in source
    assert 'STATE_RE = re.compile(r"^#\\s*(?:STATUS|State)\\s*:\\s*([^\\n]+?)\\s*$", re.I | re.M)' not in source


def test_owner_v10_brackets_artifact_authority_with_final_root_gate():
    source = _owner_source()
    assert '"schema": "try-forever-owner-surgery-custody.v10"' in source
    assert '"artifactRootFinalRevalidation": True' in source
    assert '"exactOwnerSurgeryStateAdmission": True' in source
    assert '"nonNormalizingPatchStateHeader": True' in source
    assert '"substringPromotionAuthority": False' in source
