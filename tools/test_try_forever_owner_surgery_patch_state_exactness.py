#!/usr/bin/env python3
"""RED regression source for exact textual owner-surgery state evidence.

The owner-surgery state policy already rejects normalization-dependent state tokens. This fixture
pins the missing owner boundary: the textual patch header grammar itself must not erase leading or
trailing state whitespace before the policy sees the token.

Regression source only. It does not apply the prepared owner surgery or claim execution/TESTED.
"""

from pathlib import Path
from tempfile import TemporaryDirectory

import try_forever_owner_surgery_custody_probe as custody


OWNER = "android/operator-overlay/app/src/main/java/com/homecenter/operatoroverlay/OperatorOverlayService.java"
BASE = "c5de1411a6b68087ae17aff83c032af754587150"


def patch_with_status(raw_status_tail: str) -> str:
    return (
        f"# STATUS:{raw_status_tail}\n"
        f"# BASE OWNER BLOB: {BASE}\n"
        f"# OWNER: {OWNER}\n"
        "diff --git a/owner b/owner\n"
    )


def inspect(raw_status_tail: str):
    with TemporaryDirectory() as tmp:
        path = Path(tmp) / "try-forever-state.patch"
        path.write_text(patch_with_status(raw_status_tail), encoding="utf-8")
        return custody.inspect_patch(path)


def test_single_structural_space_plus_exact_token_is_admitted():
    surgery, error = inspect(" CORRECTED_PROPOSED_NOT_APPLIED")
    assert error is None
    assert surgery is not None
    assert surgery.state == "CORRECTED_PROPOSED_NOT_APPLIED"
    assert surgery.promotion_candidate is True


def test_extra_leading_state_space_cannot_be_normalized_into_authority():
    surgery, error = inspect("  CORRECTED_PROPOSED_NOT_APPLIED")
    assert surgery is None
    assert error is not None
    assert "state" in error.boundary.lower()


def test_trailing_state_space_cannot_be_normalized_into_authority():
    surgery, error = inspect(" CORRECTED_PROPOSED_NOT_APPLIED ")
    assert surgery is None
    assert error is not None
    assert "state" in error.boundary.lower()


def test_tab_separator_cannot_be_normalized_into_authority():
    surgery, error = inspect("\tCORRECTED_PROPOSED_NOT_APPLIED")
    assert surgery is None
    assert error is not None
    assert "state" in error.boundary.lower()
