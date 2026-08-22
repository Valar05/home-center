#!/usr/bin/env python3
"""Regression source for TRY FOREVER owner-surgery backend selection.

SOURCE ONLY. This file has not been observed executing in an authorized test lane.
"""

from try_forever_owner_surgery_backend_policy import (
    DESCRIPTOR_BACKEND,
    PORTABLE_BACKEND,
    PORTABLE_UNAVAILABLE,
    REQUIRED_OWNER_EVIDENCE_FIELDS,
    SUPPORTED_POSIX,
    classify_selected_backend_failure,
    select_owner_surgery_backend,
)


def main() -> int:
    descriptor = select_owner_surgery_backend(SUPPORTED_POSIX)
    assert descriptor.backend == DESCRIPTOR_BACKEND
    assert descriptor.descriptor_selected is True
    assert descriptor.portable_is_primary is False
    assert descriptor.fallback_after_backend_failure is False
    assert descriptor.required_owner_evidence_fields == REQUIRED_OWNER_EVIDENCE_FIELDS
    assert descriptor.required_owner_evidence_fields == (
        "artifactDirectoryEntriesObserved",
        "artifactCandidatesObserved",
    )

    wound = classify_selected_backend_failure(
        descriptor,
        "candidate identity changed after held-root enumeration",
    )
    assert wound == {
        "backend": DESCRIPTOR_BACKEND,
        "status": "FAIL_CLOSED",
        "boundary": "candidate identity changed after held-root enumeration",
        "portableFallbackAttempted": False,
        "ownerEvidenceAdmitted": False,
    }

    portable = select_owner_surgery_backend(PORTABLE_UNAVAILABLE)
    assert portable.backend == PORTABLE_BACKEND
    assert portable.descriptor_selected is False
    assert portable.portable_is_primary is True
    assert portable.fallback_after_backend_failure is False
    assert portable.required_owner_evidence_fields == REQUIRED_OWNER_EVIDENCE_FIELDS

    for unsupported in ("", "SUPPORTED", "UNKNOWN", "supported_posix_primitives"):
        try:
            select_owner_surgery_backend(unsupported)
        except ValueError as exc:
            assert "unsupported directory-handle capability status" in str(exc)
        else:
            raise AssertionError(f"unknown capability status earned backend authority: {unsupported!r}")

    try:
        classify_selected_backend_failure(descriptor, "")
    except ValueError as exc:
        assert "failure boundary" in str(exc)
    else:
        raise AssertionError("empty descriptor failure boundary earned authority")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
