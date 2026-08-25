#!/usr/bin/env python3
"""Regression source for owner-surgery exact metadata admission.

SOURCE ONLY / UNEXECUTED. This file pins supporting policy behavior and does not call the canonical
custody owner SOURCE_WIRED until an authorized regression lane actually executes it.
"""

from try_forever_owner_surgery_metadata_exactness import (
    MAX_OWNER_IDENTITY_CODEPOINTS,
    OwnerSurgeryMetadataError,
    admit_owner_identity,
    admit_patch_metadata,
    source_receipt,
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


def test_owner_identity_rejects_string_subclass_before_callback():
    callback_touched = {"value": False}

    class HostileOwner(str):
        def strip(self, *args, **kwargs):
            callback_touched["value"] = True
            raise AssertionError("caller-owned strip callback executed")

    expect_rejected(
        lambda: admit_owner_identity(HostileOwner("tools/owner.py")),
        "exact built-in string",
    )
    assert callback_touched["value"] is False


def test_owner_identity_has_pre_group_resource_ceiling():
    assert admit_owner_identity("o" * MAX_OWNER_IDENTITY_CODEPOINTS) == (
        "o" * MAX_OWNER_IDENTITY_CODEPOINTS
    )
    expect_rejected(
        lambda: admit_owner_identity("o" * (MAX_OWNER_IDENTITY_CODEPOINTS + 1)),
        "source ceiling",
    )
    receipt = source_receipt()
    assert receipt["exactBuiltinOwnerStringAdmission"] is True
    assert receipt["boundedOwnerIdentityAdmission"] is True
    assert receipt["ownerIdentityCodepointCeiling"] == MAX_OWNER_IDENTITY_CODEPOINTS


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


def test_patch_metadata_rejects_string_subclass_before_regex_work():
    class HostilePatch(str):
        pass

    expect_rejected(
        lambda: admit_patch_metadata(HostilePatch(canonical_patch())),
        "exact built-in string",
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


def test_duplicate_cardinality_scan_stops_after_second_match_semantically():
    many_duplicate_states = "# STATUS: CORRECTED_PROPOSED_NOT_APPLIED\n" * 10_000
    expect_rejected(
        lambda: admit_patch_metadata(canonical_patch(many_duplicate_states)),
        "observed 2",
    )
    assert source_receipt()["headerCardinalityScanBounded"] is True


def test_malformed_duplicate_header_label_cannot_disappear_from_cardinality():
    expect_rejected(
        lambda: admit_patch_metadata(canonical_patch("# BASE OWNER BLOB: definitely-not-a-sha\n")),
        "observed 2",
    )
    expect_rejected(
        lambda: admit_patch_metadata(canonical_patch("# STATE: \n")),
        "observed 2",
    )
    expect_rejected(
        lambda: admit_patch_metadata(canonical_patch("# OWNER: owner with internal space\n")),
        "at most one explicit owner header",
    )


def test_header_recognition_is_line_local_not_cross_line_whitespace():
    text = (
        f"# BASE OWNER BLOB:\n{BASE}\n"
        "# STATUS: APPLIED_SOURCE\n"
    )
    expect_rejected(lambda: admit_patch_metadata(text), "base-owner blob")


def test_crlf_is_line_framing_not_part_of_authority_value():
    text = (
        f"# BASE OWNER BLOB: {BASE}\r\n"
        "# STATUS: APPLIED_SOURCE\r\n"
        "# OWNER: owner with internal space\r\n"
    )
    admitted = admit_patch_metadata(text)
    assert admitted.base_blob == BASE
    assert admitted.state == "APPLIED_SOURCE"
    assert admitted.explicit_owner == "owner with internal space"


def test_patch_without_explicit_owner_can_remain_source_for_existing_default_owner_fallback():
    text = f"# BASE OWNER BLOB: {BASE}\n# STATUS: APPLIED_SOURCE\n"
    admitted = admit_patch_metadata(text)
    assert admitted.explicit_owner is None
    assert admitted.state == "APPLIED_SOURCE"
    assert admitted.promotion_candidate is False
