#!/usr/bin/env python3
"""Focused regression source for descriptor-shadow -> temporal-binding composition.

SOURCE ONLY. No authorized execution receipt exists for this file.
"""

from types import SimpleNamespace

import try_forever_owner_surgery_descriptor_shadow_audit as shadow
from try_forever_posix_directory_handle_custody import (
    DescriptorCandidate,
    DescriptorCandidateInventory,
    DescriptorIdentity,
)


OWNER = "android/operator-overlay/app/src/main/java/com/homecenter/operatoroverlay/OperatorOverlayService.java"
PATH = "patches/try-forever-a.patch"
SHA = "a" * 64


def canonical(*, include_witness: bool) -> dict[str, object]:
    surgery = {
        "path": PATH,
        "artifact_kind": "patch",
        "owner": OWNER,
        "base_blob": "1" * 40,
        "state": "CORRECTED_PROPOSED_NOT_APPLIED",
        "promotion_candidate": True,
        "artifact_byte_count": 10,
        "artifact_sha256": SHA,
    }
    result: dict[str, object] = {
        "schema": shadow.CANONICAL_SCHEMA,
        "artifactDirectoryEntriesObserved": 1,
        "artifactCandidatesObserved": 1,
        "surgeries": [surgery],
        "discoveryErrors": [],
        "evidenceComplete": True,
        "currentOwnerBlobs": {OWNER: "1" * 40},
        "collisionSets": [],
        "staleBaseGroups": [],
        "unverifiedBaseGroups": [],
    }
    if include_witness:
        result["artifactContentWitnesses"] = [
            {"path": PATH, "byteCount": 10, "sha256": SHA}
        ]
    return result


class FakePortableObserver:
    @staticmethod
    def observe(path, *, max_bytes):
        assert path.as_posix() == PATH
        assert max_bytes == shadow.MAX_ARTIFACT_BYTES
        return SimpleNamespace(size_bytes=10, sha256=SHA, utf8_text="artifact")


class FakeHeld:
    def __init__(self, root):
        self.root = root

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return None

    def candidate_inventory(self, *, is_candidate, max_entries, max_candidates):
        assert is_candidate("try-forever-a.patch") is True
        assert max_entries == shadow.MAX_CUSTODY_DIRECTORY_ENTRIES
        assert max_candidates == shadow.MAX_CUSTODY_ARTIFACTS
        return DescriptorCandidateInventory(
            candidates=(
                DescriptorCandidate(
                    name="try-forever-a.patch",
                    identity=DescriptorIdentity(device=1, inode=2, size=10, mtime_ns=3),
                    mode=0o100644,
                ),
            ),
            entries_observed=1,
        )

    def observe_utf8_regular_file(self, name, *, max_bytes, expected_candidate):
        assert name == "try-forever-a.patch"
        assert expected_candidate.name == name
        assert max_bytes == shadow.MAX_ARTIFACT_BYTES
        return SimpleNamespace(name=name, byte_count=10, sha256=SHA)


def run_with(canonical_result: dict[str, object]) -> dict[str, object]:
    old_classify = shadow.classify
    old_capability = shadow.current_directory_handle_binding_capability
    old_held = shadow.HeldDirectoryCustody
    old_observer = shadow.observe_generated_index_artifact
    try:
        shadow.classify = lambda *args, **kwargs: canonical_result
        shadow.current_directory_handle_binding_capability = lambda: SimpleNamespace(
            status=shadow.SUPPORTED,
            boundary="supported",
        )
        shadow.HeldDirectoryCustody = FakeHeld
        shadow.observe_generated_index_artifact = FakePortableObserver.observe
        return shadow.audit_descriptor_shadow()
    finally:
        shadow.classify = old_classify
        shadow.current_directory_handle_binding_capability = old_capability
        shadow.HeldDirectoryCustody = old_held
        shadow.observe_generated_index_artifact = old_observer


def main() -> int:
    # A shadow byte/path/metric match is not itself temporal proof when the canonical result lacks
    # same-observation content witnesses.
    legacy = run_with(canonical(include_witness=False))
    assert legacy["status"] == "SHADOW_MATCH"
    assert legacy["temporalBindingProven"] is False
    assert legacy["temporalContentBinding"]["status"] == "CANONICAL_CONTENT_WITNESS_MISSING"

    # With exact canonical same-observation witnesses, the actual shadow audit composes into the
    # temporal policy and proves the later portable/descriptor reads match those canonical bytes.
    bound = run_with(canonical(include_witness=True))
    assert bound["status"] == "SHADOW_MATCH"
    assert bound["artifactSetMatch"] is True
    assert bound["metricsMatch"] is True
    assert bound["contentIdentityMatch"] is True
    assert bound["temporalBindingProven"] is True
    assert bound["temporalContentBinding"]["status"] == "TEMPORAL_CONTENT_BOUND"
    assert bound["temporalContentBinding"]["authorityAdmitted"] is False
    assert bound["descriptorAuthorityAdmitted"] is False
    assert bound["ownerMutation"] is False
    assert bound["tested"] is False
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
