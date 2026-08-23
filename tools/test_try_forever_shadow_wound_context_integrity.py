#!/usr/bin/env python3
"""Focused hostile source fixture for descriptor-shadow wound-context integrity.

SOURCE ONLY. This fixture has not been observed executing in an authorized regression lane.
"""

from pathlib import Path

from try_forever_owner_surgery_backend_policy import PORTABLE_UNAVAILABLE
from try_forever_owner_surgery_descriptor_shadow_audit import CANONICAL_SCHEMA, SCHEMA, SUPPORTED
from try_forever_owner_surgery_shadow_receipt_self_integrity import (
    project_shadow_receipt_with_self_integrity,
)

ROOT = Path("/repo")
CANONICAL_SHA = "1" * 64


def wound(status: str, **overrides):
    result = {
        "schema": SCHEMA,
        "status": status,
        "canonicalAuthorityBackend": "PORTABLE_PATHNAME_REVALIDATION",
        "canonicalAuthoritySchema": CANONICAL_SCHEMA,
        "canonicalResultSha256": CANONICAL_SHA,
        "canonicalEvidenceComplete": True,
        "canonicalArtifactDirectoryEntriesObserved": 0,
        "canonicalArtifactCandidatesObserved": 0,
        "descriptorCapabilityStatus": SUPPORTED,
        "descriptorAuthorityAdmitted": False,
        "ownerMutation": False,
        "boundary": "bounded wound",
        "portableShadowArtifacts": [],
        "descriptorArtifacts": [],
        "descriptorArtifactDirectoryEntriesObserved": None,
        "descriptorArtifactCandidatesObserved": None,
        "artifactSetMatch": None,
        "metricsMatch": None,
        "contentIdentityMatch": None,
    }
    result.update(overrides)
    return result


def rejected(result, needle: str):
    try:
        project_shadow_receipt_with_self_integrity(ROOT, result)
    except ValueError as exc:
        assert needle in str(exc), (needle, str(exc))
    else:
        raise AssertionError(f"counterfeit wound context escaped: {result!r}")


def main() -> int:
    rejected(
        wound("CANONICAL_SCHEMA_WOUND", canonicalAuthoritySchema=None, canonicalEvidenceComplete=None, descriptorCapabilityStatus=None),
        "explicit non-empty canonical schema identity",
    )
    rejected(
        wound("CANONICAL_SCHEMA_WOUND", canonicalAuthoritySchema=CANONICAL_SCHEMA, canonicalEvidenceComplete=None, descriptorCapabilityStatus=None),
        "requires a non-v10 canonical schema",
    )
    assert project_shadow_receipt_with_self_integrity(
        ROOT,
        wound("CANONICAL_SCHEMA_WOUND", canonicalAuthoritySchema="try-forever-owner-surgery-custody.v9", canonicalEvidenceComplete=None, descriptorCapabilityStatus=None),
    )["woundContextValidated"] is True

    rejected(
        wound("CANONICAL_WOUND", canonicalEvidenceComplete=True, descriptorCapabilityStatus=None),
        "evidenceComplete=false",
    )
    assert project_shadow_receipt_with_self_integrity(
        ROOT,
        wound("CANONICAL_WOUND", canonicalEvidenceComplete=False, descriptorCapabilityStatus=None),
    )["woundContextValidated"] is True

    rejected(
        wound("DESCRIPTOR_UNAVAILABLE", descriptorCapabilityStatus=SUPPORTED),
        "portable-unavailable descriptor capability",
    )
    assert project_shadow_receipt_with_self_integrity(
        ROOT,
        wound("DESCRIPTOR_UNAVAILABLE", descriptorCapabilityStatus=PORTABLE_UNAVAILABLE),
    )["woundContextValidated"] is True

    rejected(
        wound("PORTABLE_SHADOW_WOUND", descriptorCapabilityStatus=PORTABLE_UNAVAILABLE),
        "supported descriptor capability",
    )
    rejected(
        wound("CAPABILITY_WOUND", descriptorCapabilityStatus=SUPPORTED),
        "non-admitted descriptor capability state",
    )
    assert project_shadow_receipt_with_self_integrity(
        ROOT,
        wound("CAPABILITY_WOUND", descriptorCapabilityStatus="UNKNOWN_PLATFORM_STATE"),
    )["woundContextValidated"] is True

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
