#!/usr/bin/env python3
"""Focused hostile source fixture for canonical descriptor-shadow result identity.

SOURCE ONLY. This fixture has not been observed executing in an authorized regression lane.
The point is narrower than temporal equality: a malformed canonical result identity must not become
valid merely because every nested receipt repeats the same malformed value.
"""

from pathlib import Path

from try_forever_owner_surgery_descriptor_shadow_audit import (
    CANONICAL_SCHEMA,
    SCHEMA as SHADOW_SCHEMA,
    SUPPORTED,
)
from try_forever_owner_surgery_shadow_receipt_self_integrity import (
    TEMPORAL_BINDING_SCHEMA,
    TEMPORAL_RECEIPT_INTEGRITY_SCHEMA,
    project_shadow_receipt_with_self_integrity,
)


ROOT = Path("/repo")
VALID_SHA = "1" * 64
ARTIFACT_SHA = "a" * 64


def temporal(canonical_sha: object) -> dict[str, object]:
    return {
        "schema": TEMPORAL_BINDING_SCHEMA,
        "status": "TEMPORAL_CONTENT_BOUND",
        "canonicalResultSha256": canonical_sha,
        "shadowCanonicalResultSha256": canonical_sha,
        "temporalBindingProven": True,
        "authorityAdmitted": False,
        "ownerMutation": False,
        "regressionExecuted": False,
        "tested": False,
        "runtimeUi": False,
        "runtimeTalkBack": False,
        "phoneDelivered": False,
        "boundary": "bounded semantic result only",
        "receiptIntegritySchema": TEMPORAL_RECEIPT_INTEGRITY_SCHEMA,
        "shadowReceiptContextAdmitted": True,
    }


def raw_match(canonical_sha: object) -> dict[str, object]:
    artifact = {"path": "patches/a.patch", "byteCount": 10, "sha256": ARTIFACT_SHA}
    return {
        "schema": SHADOW_SCHEMA,
        "status": "SHADOW_MATCH",
        "canonicalAuthorityBackend": "PORTABLE_PATHNAME_REVALIDATION",
        "canonicalAuthoritySchema": CANONICAL_SCHEMA,
        "canonicalResultSha256": canonical_sha,
        "canonicalEvidenceComplete": True,
        "canonicalArtifactDirectoryEntriesObserved": 1,
        "canonicalArtifactCandidatesObserved": 1,
        "descriptorCapabilityStatus": SUPPORTED,
        "descriptorAuthorityAdmitted": False,
        "ownerMutation": False,
        "boundary": "exact comparison completed",
        "portableShadowArtifacts": [artifact],
        "descriptorArtifacts": [artifact],
        "descriptorArtifactDirectoryEntriesObserved": 1,
        "descriptorArtifactCandidatesObserved": 1,
        "artifactSetMatch": True,
        "metricsMatch": True,
        "contentIdentityMatch": True,
        "temporalContentBinding": temporal(canonical_sha),
        "temporalBindingProven": True,
    }


def rejected(canonical_sha: object) -> None:
    try:
        project_shadow_receipt_with_self_integrity(ROOT, raw_match(canonical_sha))
    except ValueError as exc:
        assert "canonicalResultSha256 must be 64 lowercase hexadecimal" in str(exc), str(exc)
    else:
        raise AssertionError(
            f"malformed canonical result identity escaped by repeating itself: {canonical_sha!r}"
        )


def main() -> int:
    receipt = project_shadow_receipt_with_self_integrity(ROOT, raw_match(VALID_SHA))
    assert receipt["status"] == "SHADOW_MATCH"
    assert receipt["temporalReceiptContextAdmitted"] is True

    rejected(None)
    rejected(123)
    rejected("1" * 63)
    rejected("1" * 65)
    rejected("A" * 64)
    rejected(" " + VALID_SHA)
    rejected(VALID_SHA + " ")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
