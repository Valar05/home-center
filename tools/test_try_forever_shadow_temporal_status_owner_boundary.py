#!/usr/bin/env python3
"""RED owner-boundary regression for descriptor-shadow temporal status exactness.

SOURCE ONLY. The exact status policy exists, but the existing receipt self-integrity owner has not yet
been observed consuming it. This fixture must stay RED until authenticated owner source rejects an
unknown temporal status before bounded operator projection.
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


def completed_result_with_unknown_temporal_status() -> dict[str, object]:
    artifact = {"path": "patches/a.patch", "byteCount": 10, "sha256": ARTIFACT_SHA}
    temporal = {
        "schema": TEMPORAL_BINDING_SCHEMA,
        "status": "TEMPORAL_CONTENT_FOG",
        "canonicalResultSha256": CANONICAL_SHA,
        "shadowCanonicalResultSha256": CANONICAL_SHA,
        "temporalBindingProven": False,
        "authorityAdmitted": False,
        "ownerMutation": False,
        "regressionExecuted": False,
        "tested": False,
        "runtimeUi": False,
        "runtimeTalkBack": False,
        "phoneDelivered": False,
        "boundary": "counterfeit unknown temporal state",
        "receiptIntegritySchema": TEMPORAL_RECEIPT_INTEGRITY_SCHEMA,
        "shadowReceiptContextAdmitted": True,
    }
    return {
        "schema": SHADOW_SCHEMA,
        "status": "SHADOW_MATCH",
        "canonicalAuthorityBackend": "PORTABLE_PATHNAME_REVALIDATION",
        "canonicalAuthoritySchema": CANONICAL_SCHEMA,
        "canonicalResultSha256": CANONICAL_SHA,
        "canonicalEvidenceComplete": True,
        "canonicalArtifactDirectoryEntriesObserved": 1,
        "canonicalArtifactCandidatesObserved": 1,
        "descriptorCapabilityStatus": SUPPORTED,
        "descriptorAuthorityAdmitted": False,
        "ownerMutation": False,
        "regressionExecuted": False,
        "tested": False,
        "runtimeUi": False,
        "runtimeTalkBack": False,
        "phoneDelivered": False,
        "boundary": "temporal status owner boundary",
        "portableShadowArtifacts": [artifact],
        "descriptorArtifacts": [artifact],
        "descriptorArtifactDirectoryEntriesObserved": 1,
        "descriptorArtifactCandidatesObserved": 1,
        "artifactSetMatch": True,
        "metricsMatch": True,
        "contentIdentityMatch": True,
        "temporalContentBinding": temporal,
        "temporalBindingProven": False,
    }


def main() -> int:
    try:
        project_shadow_receipt_with_self_integrity(
            ROOT,
            completed_result_with_unknown_temporal_status(),
        )
    except ValueError as exc:
        assert "temporal status" in str(exc).lower(), str(exc)
    else:
        raise AssertionError("unknown temporal status crossed self-integrity owner boundary")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
