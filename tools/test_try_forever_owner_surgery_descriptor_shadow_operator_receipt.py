#!/usr/bin/env python3
"""Hostile source fixture for the descriptor-shadow operator receipt command.

SOURCE ONLY. This file has not been observed executing in an authorized regression lane.
"""

import hashlib
import json
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


def artifact(path="patches/a.patch", sha256=ARTIFACT_SHA):
    return {"path": path, "byteCount": 10, "sha256": sha256}


def temporal():
    return {
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


def raw_match():
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
        "boundary": "raw machine boundary must not become routine operator prose",
        "portableShadowArtifacts": [artifact()],
        "descriptorArtifacts": [artifact()],
        "descriptorArtifactDirectoryEntriesObserved": 2,
        "descriptorArtifactCandidatesObserved": 1,
        "artifactSetMatch": True,
        "metricsMatch": True,
        "contentIdentityMatch": True,
        "temporalContentBinding": temporal(),
        "temporalBindingProven": True,
    }


def recompute_operator_receipt_sha256(receipt: dict[str, object]) -> str:
    payload = dict(receipt)
    payload.pop("operatorReceiptSha256")
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def main() -> int:
    original = owner.audit_descriptor_shadow
    try:
        raw = raw_match()
        owner.audit_descriptor_shadow = lambda **kwargs: raw
        receipt = owner.build_descriptor_shadow_operator_receipt(ROOT)
        assert receipt["operatorReceiptSchema"] == owner.SCHEMA
        assert receipt["receiptSelfIntegritySchema"].endswith(".v1")
        assert receipt["comparisonEvidenceRecomputed"] is True
        assert receipt["temporalReceiptContextAdmitted"] is True
        assert receipt["rawMachineEvidenceRemainsSeparate"] is True
        assert receipt["rawMachineEvidenceIncluded"] is False
        assert receipt["secondReceiptProjectorCreated"] is False
        assert receipt["secondDescriptorAuthorityCreated"] is False
        assert receipt["phoneP0MutationAuthority"] is False
        assert raw["boundary"] not in str(receipt)
        assert receipt["authorityAdmitted"] is False
        assert receipt["tested"] is False

        # ``metricsMatch`` is operator-auditable only if the exact bounded compared work is visible.
        assert receipt["comparisonWork"] == {
            "canonical": {
                "directoryEntriesObserved": 2,
                "candidatesObserved": 1,
            },
            "descriptor": {
                "directoryEntriesObserved": 2,
                "candidatesObserved": 1,
            },
        }

        # The bounded receipt gets a deterministic identity that is not authority/test/runtime proof.
        fingerprint = receipt["operatorReceiptSha256"]
        assert isinstance(fingerprint, str)
        assert len(fingerprint) == 64
        assert all(ch in "0123456789abcdef" for ch in fingerprint)
        assert fingerprint == recompute_operator_receipt_sha256(receipt)
        second = owner.build_descriptor_shadow_operator_receipt(ROOT)
        assert second["operatorReceiptSha256"] == fingerprint

        # Materially different but still-valid compared work changes the bounded receipt identity.
        different_work = raw_match()
        different_work["canonicalArtifactDirectoryEntriesObserved"] = 3
        different_work["descriptorArtifactDirectoryEntriesObserved"] = 3
        owner.audit_descriptor_shadow = lambda **kwargs: different_work
        different_receipt = owner.build_descriptor_shadow_operator_receipt(ROOT)
        assert different_receipt["metricsMatch"] is True
        assert different_receipt["comparisonWork"]["canonical"]["directoryEntriesObserved"] == 3
        assert different_receipt["operatorReceiptSha256"] != fingerprint

        # A lying metrics boolean cannot coexist with visibly contradictory work counters.
        lying_metrics = raw_match()
        lying_metrics["descriptorArtifactDirectoryEntriesObserved"] = 3
        owner.audit_descriptor_shadow = lambda **kwargs: lying_metrics
        try:
            owner.build_descriptor_shadow_operator_receipt(ROOT)
        except ValueError as exc:
            assert "comparison booleans contradict" in str(exc) or "metricsMatch contradicts" in str(exc)
        else:
            raise AssertionError("operator receipt displayed contradictory work-metric evidence")

        # A lying raw content comparison must be rejected before display projection.
        lying = raw_match()
        lying["descriptorArtifacts"] = [artifact(sha256="b" * 64)]
        owner.audit_descriptor_shadow = lambda **kwargs: lying
        try:
            owner.build_descriptor_shadow_operator_receipt(ROOT)
        except ValueError as exc:
            assert "comparison booleans contradict" in str(exc)
        else:
            raise AssertionError("operator receipt command displayed contradictory raw evidence")

        # A legitimate wound has no completed comparison-work receipt and no temporal proof.
        wound_without_stale_proof = raw_match()
        wound_without_stale_proof.update({
            "status": "DESCRIPTOR_WOUND",
            "descriptorArtifacts": [],
            "descriptorArtifactDirectoryEntriesObserved": None,
            "descriptorArtifactCandidatesObserved": None,
            "artifactSetMatch": None,
            "metricsMatch": None,
            "contentIdentityMatch": None,
        })
        wound_without_stale_proof.pop("temporalContentBinding")
        wound_without_stale_proof.pop("temporalBindingProven")
        owner.audit_descriptor_shadow = lambda **kwargs: wound_without_stale_proof
        wound_receipt = owner.build_descriptor_shadow_operator_receipt(ROOT)
        assert wound_receipt["comparisonWork"] is None
        assert wound_receipt["temporalReceiptContextAdmitted"] is False

        # No stale temporal proof may survive a wound/unavailable raw result.
        wounded = raw_match()
        wounded.update({
            "status": "DESCRIPTOR_WOUND",
            "descriptorArtifacts": [],
            "descriptorArtifactDirectoryEntriesObserved": None,
            "descriptorArtifactCandidatesObserved": None,
            "artifactSetMatch": None,
            "metricsMatch": None,
            "contentIdentityMatch": None,
        })
        owner.audit_descriptor_shadow = lambda **kwargs: wounded
        try:
            owner.build_descriptor_shadow_operator_receipt(ROOT)
        except ValueError as exc:
            assert "must not carry temporal binding evidence" in str(exc)
        else:
            raise AssertionError("operator receipt command retained stale temporal proof on a wound")
    finally:
        owner.audit_descriptor_shadow = original

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
