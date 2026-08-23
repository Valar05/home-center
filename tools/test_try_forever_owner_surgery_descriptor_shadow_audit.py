#!/usr/bin/env python3
"""Regression source for the non-authoritative owner-surgery descriptor shadow audit.

SOURCE ONLY. This file has not been observed executing in an authorized test lane.
"""

from types import SimpleNamespace

import try_forever_owner_surgery_descriptor_shadow_audit as shadow
from try_forever_generated_index_artifact_observation import (
    GeneratedIndexArtifactChangedError,
)
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
    sha256 = "a" * 64
    byte_count = 10

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
            byte_count=self.byte_count,
            sha256=self.sha256,
        )


class FakePortableObserver:
    sha256 = "a" * 64
    size_bytes = 10
    wound = None
    paths: list[str] = []

    @classmethod
    def observe(cls, path, *, max_bytes):
        cls.paths.append(path.as_posix())
        assert max_bytes == shadow.MAX_ARTIFACT_BYTES
        if cls.wound:
            raise cls.wound
        return SimpleNamespace(
            size_bytes=cls.size_bytes,
            sha256=cls.sha256,
            utf8_text="artifact",
        )


def with_fakes(
    *,
    portable,
    capability="SUPPORTED_POSIX_PRIMITIVES",
    held=FakeHeld,
    portable_observer=FakePortableObserver,
):
    old_classify = shadow.classify
    old_capability = shadow.current_directory_handle_binding_capability
    old_held = shadow.HeldDirectoryCustody
    old_observer = shadow.observe_generated_index_artifact
    shadow.classify = lambda *args, **kwargs: portable
    shadow.current_directory_handle_binding_capability = lambda: SimpleNamespace(
        status=capability,
        boundary="descriptor primitives unavailable",
    )
    shadow.HeldDirectoryCustody = held
    portable_observer.paths = []
    shadow.observe_generated_index_artifact = portable_observer.observe
    return old_classify, old_capability, old_held, old_observer


def restore(old):
    (
        shadow.classify,
        shadow.current_directory_handle_binding_capability,
        shadow.HeldDirectoryCustody,
        shadow.observe_generated_index_artifact,
    ) = old


def main() -> int:
    # Matching staging evidence now requires paths, work metrics, and exact byte/SHA identity.
    old = with_fakes(portable=portable_result())
    try:
        result = shadow.audit_descriptor_shadow()
    finally:
        restore(old)
    assert result["schema"] == "try-forever-owner-surgery-descriptor-shadow.v2"
    assert result["status"] == "SHADOW_MATCH"
    assert result["artifactSetMatch"] is True
    assert result["metricsMatch"] is True
    assert result["contentIdentityMatch"] is True
    assert result["portableShadowArtifacts"] == [
        {
            "path": "patches/try-forever-a.patch",
            "byteCount": 10,
            "sha256": "a" * 64,
        }
    ]
    assert result["descriptorArtifactDirectoryEntriesObserved"] == 4
    assert result["descriptorArtifactCandidatesObserved"] == 1
    assert result["descriptorAuthorityAdmitted"] is False
    assert result["ownerMutation"] is False
    assert result["regressionExecuted"] is False
    assert result["tested"] is False
    assert "collisionSets" not in result
    assert "ownerEvidenceAdmitted" not in result

    # A descriptor/canonical path-set disagreement remains visible and blocks a match.
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
    assert metric_drift["contentIdentityMatch"] is True

    # Exact content identity is an independent comparison surface.
    class ContentDriftHeld(FakeHeld):
        sha256 = "b" * 64

    old = with_fakes(portable=portable_result(), held=ContentDriftHeld)
    try:
        content_drift = shadow.audit_descriptor_shadow()
    finally:
        restore(old)
    assert content_drift["status"] == "SHADOW_DIVERGED"
    assert content_drift["artifactSetMatch"] is True
    assert content_drift["metricsMatch"] is True
    assert content_drift["contentIdentityMatch"] is False
    assert content_drift["descriptorAuthorityAdmitted"] is False

    # Portable exact-content staging wounds before descriptor comparison and cannot be normalized.
    class WoundedPortable(FakePortableObserver):
        wound = GeneratedIndexArtifactChangedError("portable artifact changed")

    old = with_fakes(portable=portable_result(), portable_observer=WoundedPortable)
    try:
        portable_wound = shadow.audit_descriptor_shadow()
    finally:
        restore(old)
    assert portable_wound["status"] == "PORTABLE_SHADOW_WOUND"
    assert "portable artifact changed" in portable_wound["boundary"]
    assert portable_wound["descriptorAuthorityAdmitted"] is False
    assert portable_wound["artifactSetMatch"] is None
    WoundedPortable.wound = None

    # Descriptor primitives unavailable means the portable owner simply remains authority; this is
    # not a selected-descriptor failure followed by a downgrade.
    old = with_fakes(
        portable=portable_result(),
        capability=shadow.PORTABLE_UNAVAILABLE,
    )
    try:
        unavailable = shadow.audit_descriptor_shadow()
    finally:
        restore(old)
    assert unavailable["status"] == "DESCRIPTOR_UNAVAILABLE"
    assert unavailable["descriptorAuthorityAdmitted"] is False
    assert unavailable["artifactSetMatch"] is None
    assert unavailable["contentIdentityMatch"] is None

    # Unknown/corrupt capability text must not be normalized into ordinary descriptor unavailability.
    for invalid_capability in ("", "SUPPORTED", "supported_posix_primitives", "UNKNOWN"):
        old = with_fakes(portable=portable_result(), capability=invalid_capability)
        try:
            capability_wound = shadow.audit_descriptor_shadow()
        finally:
            restore(old)
        assert capability_wound["status"] == "CAPABILITY_WOUND"
        assert repr(invalid_capability) in capability_wound["boundary"]
        assert capability_wound["descriptorAuthorityAdmitted"] is False
        assert capability_wound["artifactSetMatch"] is None

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

    # Canonical incompleteness stops shadow staging before any artifact read can decorate it as MATCH.
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
    assert incomplete_shadow["status"] == "CANONICAL_WOUND"
    assert incomplete_shadow["portableShadowArtifacts"] == []
    assert incomplete_shadow["descriptorArtifacts"] == []
    assert incomplete_shadow["artifactSetMatch"] is None
    assert incomplete_shadow["descriptorAuthorityAdmitted"] is False

    # The shadow may not truthiness-normalize malformed canonical evidence into a boolean claim.
    malformed = portable_result()
    malformed["evidenceComplete"] = "false"
    old = with_fakes(portable=malformed)
    try:
        try:
            shadow.audit_descriptor_shadow()
        except ValueError as exc:
            assert "canonical evidenceComplete must be one boolean" in str(exc)
        else:
            raise AssertionError("malformed canonical evidence earned a shadow result")
    finally:
        restore(old)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
