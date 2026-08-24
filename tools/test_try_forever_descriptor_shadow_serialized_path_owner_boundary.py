#!/usr/bin/env python3
"""RED / UNEXECUTED owner boundary for cross-host descriptor-shadow path display privacy."""

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


def main() -> int:
    # A Windows absolute path is foreign host topology when this serialized receipt is reviewed on
    # POSIX. Host-OS ``Path.is_absolute`` alone must not launder it into repository display text.
    windows_drive = project_shadow_receipt(
        ROOT,
        _result(r"C:\Users\alice\private\try-forever-a.patch"),
    )
    windows_unc = project_shadow_receipt(
        ROOT,
        _result(r"\\server\share\private\try-forever-a.patch"),
    )
    for receipt in (windows_drive, windows_unc):
        projected = receipt["portableArtifacts"][0]
        assert projected["pathScope"] == "EXTERNAL", projected
        assert projected["path"] == "<external-path>", projected
        assert "alice" not in str(receipt)
        assert "server" not in str(receipt)

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
