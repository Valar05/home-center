#!/usr/bin/env python3
"""Regression source for owner-surgery exact metadata admission.

SOURCE ONLY / UNEXECUTED. This file pins supporting policy behavior and does not call the canonical
custody owner SOURCE_WIRED until an authorized regression lane actually executes it.
"""

from try_forever_owner_surgery_metadata_exactness import (
    OwnerSurgeryMetadataError,
    admit_owner_identity,
    admit_patch_metadata,
)


BASE = "a" * 40


def expect_rejected(call, needle: str) -> None:
    try:
        call()
    except OwnerSurgeryMetadataError as exc:
        assert needle in str(exc), (needle, str(exc))
    else:
        raise AssertionError("ambiguous metadata earned supporting-source admission")


def test_owner_identity_is_exact_not_trim_repaired():
    owner = "android/operator-overlay/app/src/main/java/com/homecenter/operatoroverlay/OperatorOverlayService.java"
    assert admit_owner_identity(owner) == owner
    assert admit_owner_identity("owner with internal space") == "owner with internal space"
    expect_rejected(lambda: admit_owner_identity(" " + owner), "leading/trailing")
    expect_rejected(lambda: admit_owner_identity(owner + "\t"), "leading/trailing")
    expect_rejected(lambda: admit_owner_identity(""), "non-empty")


def canonical_patch(extra: str = "") -> str:
    return (
        f"# BASE OWNER BLOB: {BASE}\n"
        "# STATUS: CORRECTED_PROPOSED_NOT_APPLIED\n"
        "# OWNER: android/operator-overlay/app/src/main/java/com/homecenter/operatoroverlay/OperatorOverlayService.java\n"
        f"{extra}"
    )


def test_patch_metadata_requires_one_base_one_state_and_at_most_one_owner():
    admitted = admit_patch_metadata(canonical_patch())
    assert admitted.base_blob == BASE
    assert admitted.state == "CORRECTED_PROPOSED_NOT_APPLIED"
    assert admitted.promotion_candidate is True
    assert admitted.explicit_owner.endswith("OperatorOverlayService.java")

    expect_rejected(
        lambda: admit_patch_metadata(canonical_patch(f"# Base blob: {BASE}\n")),
        "exactly one base-owner blob header",
    )
    expect_rejected(
        lambda: admit_patch_metadata(canonical_patch("# State: CORRECTED_PROPOSED_NOT_APPLIED\n")),
        "exactly one state/status header",
    )
    expect_rejected(
        lambda: admit_patch_metadata(canonical_patch("# Target: tools/other-owner.py\n")),
        "at most one explicit owner header",
    )


def test_identical_duplicate_headers_are_still_ambiguous():
    expect_rejected(
        lambda: admit_patch_metadata(canonical_patch(f"# BASE OWNER BLOB: {BASE}\n")),
        "observed 2",
    )
    expect_rejected(
        lambda: admit_patch_metadata(canonical_patch("# STATUS: CORRECTED_PROPOSED_NOT_APPLIED\n")),
        "observed 2",
    )


def test_patch_without_explicit_owner_can_remain_source_for_existing_default_owner_fallback():
    text = f"# BASE OWNER BLOB: {BASE}\n# STATUS: APPLIED_SOURCE\n"
    admitted = admit_patch_metadata(text)
    assert admitted.explicit_owner is None
    assert admitted.state == "APPLIED_SOURCE"
    assert admitted.promotion_candidate is False
