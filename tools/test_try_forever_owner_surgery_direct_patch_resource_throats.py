#!/usr/bin/env python3
"""SOURCE-ONLY regression for direct patch-evidence resource throats.

This fixture pins two existing public helper boundaries that canonical v10 already calls through a
bounded artifact observation. Direct callers must be finite too: exact built-in patch text must fail
before regex traversal when over ceiling, and fallback-owner identity must fail before expected-header
formatting/equality when over ceiling. Presence of this file is not execution evidence.
"""

from try_forever_owner_surgery_default_owner_binding import (
    DEFAULT_OWNER,
    MAX_DEFAULT_OWNER_IDENTITY_CODEPOINTS,
    MAX_DEFAULT_OWNER_PATCH_CODEPOINTS,
    DefaultOwnerBindingError,
    admit_default_owner_from_patch,
    source_receipt as default_owner_receipt,
)
from try_forever_owner_surgery_metadata_exactness import (
    MAX_PATCH_METADATA_CODEPOINTS,
    OwnerSurgeryMetadataError,
    admit_patch_metadata,
    source_receipt as metadata_receipt,
)


BASE = "a" * 40


def _must_metadata_reject(text: str, needle: str) -> None:
    try:
        admit_patch_metadata(text)
    except OwnerSurgeryMetadataError as exc:
        assert needle in str(exc), (needle, str(exc))
    else:
        raise AssertionError("over-budget direct metadata evidence must fail closed")


def _must_default_owner_reject(*, text: str, default_owner: str, needle: str) -> None:
    try:
        admit_default_owner_from_patch(text, default_owner=default_owner)
    except DefaultOwnerBindingError as exc:
        assert needle in str(exc), (needle, str(exc))
    else:
        raise AssertionError("over-budget direct fallback-owner evidence must fail closed")


def main() -> int:
    metadata = metadata_receipt()
    assert metadata["boundedPatchTextAdmission"] is True
    assert metadata["patchTextCodepointCeiling"] == MAX_PATCH_METADATA_CODEPOINTS
    assert metadata["regressionExecuted"] is False
    assert metadata["tested"] is False

    default = default_owner_receipt()
    assert default["boundedPatchTextAdmission"] is True
    assert default["patchTextCodepointCeiling"] == MAX_DEFAULT_OWNER_PATCH_CODEPOINTS
    assert default["boundedDefaultOwnerAdmission"] is True
    assert default["defaultOwnerCodepointCeiling"] == MAX_DEFAULT_OWNER_IDENTITY_CODEPOINTS
    assert default["regressionExecuted"] is False
    assert default["tested"] is False

    canonical_patch = (
        f"# BASE OWNER BLOB: {BASE}\n"
        "# STATUS: APPLIED_SOURCE\n"
        f"diff --git a/{DEFAULT_OWNER} b/{DEFAULT_OWNER}\n"
    )
    admitted = admit_patch_metadata(canonical_patch)
    assert admitted.base_blob == BASE
    assert admitted.state == "APPLIED_SOURCE"
    fallback = admit_default_owner_from_patch(canonical_patch)
    assert fallback.owner == DEFAULT_OWNER

    _must_metadata_reject(
        "x" * (MAX_PATCH_METADATA_CODEPOINTS + 1),
        "patch text exceeds metadata source ceiling",
    )
    _must_default_owner_reject(
        text="x" * (MAX_DEFAULT_OWNER_PATCH_CODEPOINTS + 1),
        default_owner=DEFAULT_OWNER,
        needle="patch text exceeds fallback-owner source ceiling",
    )
    _must_default_owner_reject(
        text=canonical_patch,
        default_owner="o" * (MAX_DEFAULT_OWNER_IDENTITY_CODEPOINTS + 1),
        needle="default owner exceeds fallback-owner source ceiling",
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
