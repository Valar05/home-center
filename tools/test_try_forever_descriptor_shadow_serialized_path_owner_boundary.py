#!/usr/bin/env python3
"""SOURCE-WIRED / UNEXECUTED boundary for cross-host descriptor-shadow path display privacy."""

from pathlib import Path

from try_forever_owner_surgery_shadow_receipt_projection import (
    SHADOW_SCHEMA,
    project_shadow_receipt,
)


ROOT = Path("/srv/home-center")
CANONICAL_SHA = "1" * 64
ARTIFACT_SHA = "a" * 64


def _artifact(path: str) -> dict[str, object]:
    return {"path": path, "byteCount": 7, "sha256": ARTIFACT_SHA}


def _result(path: str) -> dict[str, object]:
    return {
        "schema": SHADOW_SCHEMA,
        "status": "SHADOW_MATCH",
        "canonicalResultSha256": CANONICAL_SHA,
        "boundary": "completed comparison",
        "portableShadowArtifacts": [_artifact(path)],
        "descriptorArtifacts": [_artifact(path)],
        "canonicalArtifactDirectoryEntriesObserved": 1,
        "canonicalArtifactCandidatesObserved": 1,
        "descriptorArtifactDirectoryEntriesObserved": 1,
        "descriptorArtifactCandidatesObserved": 1,
        "artifactSetMatch": True,
        "metricsMatch": True,
        "contentIdentityMatch": True,
        "descriptorAuthorityAdmitted": False,
        "ownerMutation": False,
    }


def _assert_external(path: str, *forbidden: str) -> None:
    receipt = project_shadow_receipt(ROOT, _result(path))
    projected = receipt["portableArtifacts"][0]
    assert projected["pathScope"] == "EXTERNAL", projected
    assert projected["path"] == "<external-path>", projected
    for text in forbidden:
        assert text not in str(receipt), (text, receipt)


def main() -> int:
    # Serialized host context must be judged cross-platform rather than by the reviewer host's
    # Path.is_absolute() semantics alone.
    _assert_external(r"C:\Users\alice\private\try-forever-a.patch", "alice")
    _assert_external(r"\\server\share\private\try-forever-a.patch", "server")
    _assert_external(r"C:private\try-forever-a.patch", "private")
    _assert_external(r"\rooted\private\try-forever-a.patch", "private")
    _assert_external("/tmp/private/try-forever-a.patch", "private")

    # A canonical repository-relative identity may contain Windows-looking characters after a real
    # repository prefix. It remains repository evidence and keeps collision-safe backslash display.
    repository = project_shadow_receipt(
        ROOT,
        _result(r"patches/C:\literal-name.patch"),
    )
    projected = repository["portableArtifacts"][0]
    assert projected["pathScope"] == "REPOSITORY", projected
    assert projected["path"] == r"patches/C:\\literal-name.patch", projected

    # This source fixture is not an execution receipt.
    assert repository["authorityAdmitted"] is False
    assert repository["tested"] is False
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
