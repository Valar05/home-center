#!/usr/bin/env python3
"""Regression source for the non-authoritative owner-surgery descriptor shadow audit.

SOURCE ONLY. This file has not been observed executing in an authorized test lane.
"""

from types import SimpleNamespace

import try_forever_owner_surgery_descriptor_shadow_audit as shadow
from try_forever_posix_directory_handle_custody import (
    DescriptorArtifactCustodyError,
    DescriptorCandidate,
    DescriptorCandidateInventory,
    DescriptorIdentity,
)


ROOT = shadow.PATCH_ROOT
OWNER = "android/operator-overlay/app/src/main/java/com/homecenter/operatoroverlay/OperatorOverlayService.java"
BASE = "1111111111111111111111111111111111111111"


def portable_result(*, paths=("patches/try-forever-a.patch",), entries=4, candidates=1):
    return {
        "schema": "try-forever-owner-surgery-custody.v10",
        "artifactDirectoryEntriesObserved": entries,
        "artifactCandidatesObserved": candidates,
        "surgeries": [
            {
                "path": path,
                "artifact_kind": "patch",
                "owner": OWNER,
                "base_blob": BASE,
                "state": "CORRECTED_PROPOSED_NOT_APPLIED",
                "promotion_candidate": True,
            }
            for path in paths
        ],
        "discoveryErrors": [],
        "evidenceComplete": True,
        "currentOwnerBlobs": {OWNER: BASE},
        "collisionSets": [],
        "staleBaseGroups": [],
        "unverifiedBaseGroups": [],
    }


class FakeHeld:
    inventory = DescriptorCandidateInventory(
        candidates=(
            DescriptorCandidate(
                name="try-forever-a.patch",
                identity=DescriptorIdentity(device=1, inode=2, size=10, mtime_ns=3),
                mode=0o100644,
            ),
        ),
        entries_observed=4,
    )
    wound = None

    def __init__(self, root):
        self.root = root

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return None

    def candidate_inventory(self, *, is_candidate, max_entries, max_candidates):
        if self.wound:
            raise self.wound
        assert max_entries == shadow.MAX_CUSTODY_DIRECTORY_ENTRIES
        assert max_candidates == shadow.MAX_CUSTODY_ARTIFACTS
        assert is_candidate("try-forever-a.patch") is True
        assert is_candidate("README.md") is False
        return self.inventory

    def observe_utf8_regular_file(self, name, *, max_bytes, expected_candidate):
        assert name == expected_candidate.name
        assert max_bytes == shadow.MAX_ARTIFACT_BYTES
        return SimpleNamespace(
            name=name,
            byte_count=10,
            sha256="a" * 64,
        )


def with_fakes(*, portable, capability="SUPPORTED_POSIX_PRIMITIVES", held=FakeHeld):
    old_classify = shadow.classify
    old_capability = shadow.current_directory_handle_binding_capability
    old_held = shadow.HeldDirectoryCustody
    shadow.classify = lambda *args, **kwargs: portable
    shadow.current_directory_handle_binding_capability = lambda: SimpleNamespace(
        status=capability,
        boundary="descriptor primitives unavailable",
    )
    shadow.HeldDirectoryCustody = held
    return old_classify, old_capability, old_held


def restore(old):
    shadow.classify, shadow.current_directory_handle_binding_capability, shadow.HeldDirectoryCustody = old


def main() -> int:
    # Matching descriptor evidence is useful staging evidence but never promotion authority.
    old = with_fakes(portable=portable_result())
    try:
        result = shadow.audit_descriptor_shadow()
    finally:
        restore(old)
    assert result["status"] == "SHADOW_MATCH"
    assert result["artifactSetMatch"] is True
    assert result["metricsMatch"] is True
    assert result["descriptorArtifactDirectoryEntriesObserved"] == 4
    assert result["descriptorArtifactCandidatesObserved"] == 1
    assert result["descriptorAuthorityAdmitted"] is False
    assert result["ownerMutation"] is False
    assert result["regressionExecuted"] is False
    assert result["tested"] is False
    assert "collisionSets" not in result
    assert "ownerEvidenceAdmitted" not in result

    # A descriptor/canonical path-set disagreement must remain visible and block promotion claims.
    old = with_fakes(portable=portable_result(paths=("patches/try-forever-other.patch",)))
    try:
        diverged = shadow.audit_descriptor_shadow()
    finally:
        restore(old)
    assert diverged["status"] == "SHADOW_DIVERGED"
    assert diverged["artifactSetMatch"] is False
    assert diverged["descriptorAuthorityAdmitted"] is False

    # Metrics disagree independently from path identity.
    old = with_fakes(portable=portable_result(entries=5, candidates=1))
    try:
        metric_drift = shadow.audit_descriptor_shadow()
    finally:
        restore(old)
    assert metric_drift["status"] == "SHADOW_DIVERGED"
    assert metric_drift["artifactSetMatch"] is True
    assert metric_drift["metricsMatch"] is False

    # Descriptor primitives unavailable means the portable owner simply remains authority; this is
    # not a selected-descriptor failure followed by a downgrade.
    old = with_fakes(
        portable=portable_result(),
        capability="PORTABLE_ATOMIC_BINDING_UNAVAILABLE",
    )
    try:
        unavailable = shadow.audit_descriptor_shadow()
    finally:
        restore(old)
    assert unavailable["status"] == "DESCRIPTOR_UNAVAILABLE"
    assert unavailable["descriptorAuthorityAdmitted"] is False
    assert unavailable["artifactSetMatch"] is None

    # A descriptor wound remains a shadow wound and cannot change canonical authority semantics.
    class WoundedHeld(FakeHeld):
        wound = DescriptorArtifactCustodyError("candidate changed")

    old = with_fakes(portable=portable_result(), held=WoundedHeld)
    try:
        wounded = shadow.audit_descriptor_shadow()
    finally:
        restore(old)
    assert wounded["status"] == "DESCRIPTOR_WOUND"
    assert "candidate changed" in wounded["boundary"]
    assert wounded["descriptorAuthorityAdmitted"] is False
    assert wounded["ownerMutation"] is False

    # Canonical incompleteness remains canonical evidence truth even if descriptor evidence matches.
    incomplete = portable_result()
    incomplete["evidenceComplete"] = False
    incomplete["discoveryErrors"] = [{
        "path": "patches/try-forever-a.patch",
        "artifact_kind": "patch",
        "boundary": "canonical artifact wounded",
    }]
    incomplete["surgeries"] = []
    old = with_fakes(portable=incomplete)
    try:
        incomplete_shadow = shadow.audit_descriptor_shadow()
    finally:
        restore(old)
    assert incomplete_shadow["canonicalEvidenceComplete"] is False
    assert incomplete_shadow["descriptorAuthorityAdmitted"] is False

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
