#!/usr/bin/env python3
"""Regression source for TRY FOREVER owner-surgery backend selection.

SOURCE ONLY. This file has not been observed executing in an authorized test lane.
"""

from try_forever_owner_surgery_backend_policy import (
    DESCRIPTOR_BACKEND,
    OWNER_AUTHORITY_FIELDS,
    PORTABLE_BACKEND,
    PORTABLE_UNAVAILABLE,
    REQUIRED_OWNER_EVIDENCE_FIELDS,
    SUPPORTED_POSIX,
    admit_selected_backend_result,
    classify_selected_backend_failure,
    select_owner_surgery_backend,
)


def complete_result(**overrides):
    result = {
        "backend": DESCRIPTOR_BACKEND,
        "artifactDirectoryEntriesObserved": 7,
        "artifactCandidatesObserved": 3,
        "evidenceComplete": True,
        "collisionSets": [],
        "staleBaseGroups": [],
        "unverifiedBaseGroups": [],
        "portableFallbackAttempted": False,
    }
    result.update(overrides)
    return result


def expect_rejected(descriptor, result, needle: str) -> None:
    try:
        admit_selected_backend_result(descriptor, result)
    except ValueError as exc:
        assert needle in str(exc), (needle, str(exc))
    else:
        raise AssertionError(f"unsafe backend result earned evidence authority: {result!r}")


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
    assert OWNER_AUTHORITY_FIELDS == (
        "collisionSets",
        "staleBaseGroups",
        "unverifiedBaseGroups",
    )

    admitted = admit_selected_backend_result(descriptor, complete_result())
    assert admitted == {
        "backend": DESCRIPTOR_BACKEND,
        "status": "EVIDENCE_ADMITTED",
        "artifactDirectoryEntriesObserved": 7,
        "artifactCandidatesObserved": 3,
        "evidenceComplete": True,
        "authorityGroupCounts": {
            "collisionSets": 0,
            "staleBaseGroups": 0,
            "unverifiedBaseGroups": 0,
        },
        "portableFallbackAttempted": False,
        "ownerEvidenceAdmitted": True,
    }

    incomplete = admit_selected_backend_result(
        descriptor,
        complete_result(evidenceComplete=False),
    )
    assert incomplete["ownerEvidenceAdmitted"] is False
    assert incomplete["evidenceComplete"] is False

    # Diagnostic surgeries may remain present after a wounded exhaustive scan; they are not promotion authority.
    incomplete_with_diagnostics = complete_result(evidenceComplete=False)
    incomplete_with_diagnostics["surgeries"] = [{"path": "diagnostic-only.patch"}]
    assert admit_selected_backend_result(
        descriptor,
        incomplete_with_diagnostics,
    )["ownerEvidenceAdmitted"] is False

    expect_rejected(
        descriptor,
        complete_result(collisionSets=[{"owner": "x"}], evidenceComplete=False),
        "partial promotion authority",
    )
    expect_rejected(
        descriptor,
        complete_result(artifactCandidatesObserved=8),
        "cannot exceed",
    )
    expect_rejected(
        descriptor,
        complete_result(artifactCandidatesObserved=True),
        "non-negative integer",
    )
    expect_rejected(
        descriptor,
        complete_result(artifactDirectoryEntriesObserved=-1),
        "non-negative integer",
    )
    expect_rejected(
        descriptor,
        complete_result(evidenceComplete="yes"),
        "evidenceComplete",
    )
    expect_rejected(
        descriptor,
        complete_result(staleBaseGroups=None),
        "staleBaseGroups",
    )
    expect_rejected(
        descriptor,
        complete_result(backend=PORTABLE_BACKEND),
        "identity",
    )
    expect_rejected(
        descriptor,
        complete_result(portableFallbackAttempted=True),
        "fallback",
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

    portable_result = complete_result(backend=PORTABLE_BACKEND)
    admitted_portable = admit_selected_backend_result(portable, portable_result)
    assert admitted_portable["backend"] == PORTABLE_BACKEND
    assert admitted_portable["ownerEvidenceAdmitted"] is True

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
