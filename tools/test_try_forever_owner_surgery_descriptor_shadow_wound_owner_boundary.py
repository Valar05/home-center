#!/usr/bin/env python3
"""RED owner-boundary regression for descriptor-shadow wound comparison semantics.

SOURCE ONLY / UNEXECUTED. Current descriptor-shadow v3 reports false/false/false when held-directory
custody fails before comparison completes. This fixture requires the owner to report null comparison
fields instead: failure-to-compare is not measured divergence.
"""

from types import SimpleNamespace

import try_forever_owner_surgery_descriptor_shadow_audit as shadow
from try_forever_posix_directory_handle_custody import DescriptorArtifactCustodyError


PATH = "patches/try-forever-a.patch"
OWNER = "android/operator-overlay/app/src/main/java/com/homecenter/operatoroverlay/OperatorOverlayService.java"
BASE = "1" * 40
SHA = "a" * 64


def canonical() -> dict[str, object]:
    return {
        "schema": shadow.CANONICAL_SCHEMA,
        "artifactDirectoryEntriesObserved": 1,
        "artifactCandidatesObserved": 1,
        "surgeries": [
            {
                "path": PATH,
                "artifact_kind": "patch",
                "owner": OWNER,
                "base_blob": BASE,
                "state": "CORRECTED_PROPOSED_NOT_APPLIED",
                "promotion_candidate": True,
                "artifact_byte_count": 10,
                "artifact_sha256": SHA,
            }
        ],
        "artifactContentWitnesses": [
            {"path": PATH, "byteCount": 10, "sha256": SHA}
        ],
        "discoveryErrors": [],
        "evidenceComplete": True,
        "currentOwnerBlobs": {OWNER: BASE},
        "collisionSets": [],
        "staleBaseGroups": [],
        "unverifiedBaseGroups": [],
    }


class WoundedHeld:
    def __init__(self, root):
        self.root = root

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return None

    def candidate_inventory(self, *, is_candidate, max_entries, max_candidates):
        raise DescriptorArtifactCustodyError("candidate changed before comparison")


class PortableObserver:
    @staticmethod
    def observe(path, *, max_bytes):
        assert path.as_posix() == PATH
        assert max_bytes == shadow.MAX_ARTIFACT_BYTES
        return SimpleNamespace(size_bytes=10, sha256=SHA, utf8_text="artifact")


def main() -> int:
    old_classify = shadow.classify
    old_capability = shadow.current_directory_handle_binding_capability
    old_held = shadow.HeldDirectoryCustody
    old_observer = shadow.observe_generated_index_artifact
    shadow.classify = lambda *args, **kwargs: canonical()
    shadow.current_directory_handle_binding_capability = lambda: SimpleNamespace(
        status=shadow.SUPPORTED,
        boundary="supported",
    )
    shadow.HeldDirectoryCustody = WoundedHeld
    shadow.observe_generated_index_artifact = PortableObserver.observe
    try:
        result = shadow.audit_descriptor_shadow()
    finally:
        shadow.classify = old_classify
        shadow.current_directory_handle_binding_capability = old_capability
        shadow.HeldDirectoryCustody = old_held
        shadow.observe_generated_index_artifact = old_observer

    assert result["status"] == "DESCRIPTOR_WOUND"
    assert "candidate changed before comparison" in result["boundary"]
    assert result["artifactSetMatch"] is None
    assert result["metricsMatch"] is None
    assert result["contentIdentityMatch"] is None
    assert result["descriptorAuthorityAdmitted"] is False
    assert result["ownerMutation"] is False
    assert result["tested"] is False
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
