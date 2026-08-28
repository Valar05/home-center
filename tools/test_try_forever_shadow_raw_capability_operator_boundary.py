#!/usr/bin/env python3
"""Operator-command regression source for raw descriptor-shadow capability overclaims.

SOURCE ONLY. The actual bounded operator receipt command must reject every contradictory raw
capability field through the existing self-integrity owner before returning a bounded receipt. This
fixture is self-contained so regression ordering/import-path behavior cannot become evidence. It has
not been observed executing in an authorized test lane.
"""

from pathlib import Path

import try_forever_owner_surgery_descriptor_shadow_operator_receipt as owner
from try_forever_owner_surgery_descriptor_shadow_audit import (
    CANONICAL_SCHEMA,
    SCHEMA as SHADOW_SCHEMA,
    SUPPORTED,
)
from try_forever_owner_surgery_shadow_receipt_self_integrity import (
    TEMPORAL_BINDING_SCHEMA,
    TEMPORAL_RECEIPT_INTEGRITY_SCHEMA,
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
        "boundary": "raw capability membrane operator boundary",
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


def main() -> int:
    original = owner.audit_descriptor_shadow
    try:
        # Exercise every denied top-level raw capability through the real bounded command surface.
        # Authority/mutation matter here just as much as TESTED/runtime/phone claims; a projector
        # emitting conservative false values must not sanitize any of them.
        for field in (
            "descriptorAuthorityAdmitted",
            "ownerMutation",
            "regressionExecuted",
            "tested",
            "runtimeUi",
            "runtimeTalkBack",
            "phoneDelivered",
        ):
            raw = raw_match()
            raw[field] = True
            owner.audit_descriptor_shadow = lambda **kwargs: raw
            try:
                owner.build_descriptor_shadow_operator_receipt(ROOT)
            except ValueError as exc:
                assert f"{field}=false" in str(exc), str(exc)
            else:
                raise AssertionError(
                    f"operator receipt sanitized contradictory raw capability {field}=true"
                )
    finally:
        owner.audit_descriptor_shadow = original

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
