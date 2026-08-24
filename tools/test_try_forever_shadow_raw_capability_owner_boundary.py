#!/usr/bin/env python3
"""Owner-boundary regression source for raw descriptor-shadow capability integrity.

SOURCE ONLY. The existing self-integrity owner is now source-wired to
``require_raw_shadow_capability_membrane`` before bounded projection. This fixture pins that source
contract; it has not been observed executing in an authorized test lane.
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
CANONICAL_SHA = "1" * 64
ARTIFACT_SHA = "a" * 64


def raw_match() -> dict[str, object]:
    temporal = {
        "schema": TEMPORAL_BINDING_SCHEMA,
        "status": "TEMPORAL_CONTENT_BOUND",
        "canonicalResultSha256": CANONICAL_SHA,
        "shadowCanonicalResultSha256": CANONICAL_SHA,
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
    artifact = {"path": "patches/a.patch", "byteCount": 10, "sha256": ARTIFACT_SHA}
    return {
        "schema": SHADOW_SCHEMA,
        "status": "SHADOW_MATCH",
        "canonicalAuthorityBackend": "PORTABLE_PATHNAME_REVALIDATION",
        "canonicalAuthoritySchema": CANONICAL_SCHEMA,
        "canonicalResultSha256": CANONICAL_SHA,
        "canonicalEvidenceComplete": True,
        "canonicalArtifactDirectoryEntriesObserved": 2,
        "canonicalArtifactCandidatesObserved": 1,
        "descriptorCapabilityStatus": SUPPORTED,
        "descriptorAuthorityAdmitted": False,
        "ownerMutation": False,
        "regressionExecuted": False,
        "tested": False,
        "runtimeUi": False,
        "runtimeTalkBack": False,
        "phoneDelivered": False,
        "boundary": "raw capability membrane owner boundary",
        "portableShadowArtifacts": [artifact],
        "descriptorArtifacts": [artifact],
        "descriptorArtifactDirectoryEntriesObserved": 2,
        "descriptorArtifactCandidatesObserved": 1,
        "artifactSetMatch": True,
        "metricsMatch": True,
        "contentIdentityMatch": True,
        "temporalContentBinding": temporal,
        "temporalBindingProven": True,
    }


def expect_owner_rejected(field: str) -> None:
    raw = raw_match()
    raw[field] = True
    try:
        project_shadow_receipt_with_self_integrity(ROOT, raw)
    except ValueError as exc:
        assert f"{field}=false" in str(exc), str(exc)
    else:
        raise AssertionError(
            f"self-integrity owner sanitized contradictory raw capability {field}=true"
        )


def main() -> int:
    receipt = project_shadow_receipt_with_self_integrity(ROOT, raw_match())
    assert receipt["tested"] is False
    assert receipt["runtimeTalkBack"] is False

    for field in (
        "descriptorAuthorityAdmitted",
        "ownerMutation",
        "regressionExecuted",
        "tested",
        "runtimeUi",
        "runtimeTalkBack",
        "phoneDelivered",
    ):
        expect_owner_rejected(field)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
