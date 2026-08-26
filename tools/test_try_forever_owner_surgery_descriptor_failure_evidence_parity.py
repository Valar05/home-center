#!/usr/bin/env python3
"""RED SOURCE-ONLY boundary for descriptor-backend failure-evidence parity.

Canonical v10 already fails descriptor custody wounds closed with zero promotion authority. This
fixture requires the stronger evidence contract still missing from the descriptor path: work already
observed before failure must remain visible in the receipt, and a custody failure for one identified
artifact must retain that artifact's path/kind instead of collapsing to an anonymous backend error.

The fixture is intentionally SOURCE / UNEXECUTED and must not be reported as TESTED evidence.
"""

from pathlib import Path

import pytest

from try_forever_directory_handle_binding_capability import (
    current_directory_handle_binding_capability,
)
from try_forever_owner_surgery_backend_policy import DESCRIPTOR_BACKEND
from try_forever_owner_surgery_custody_probe import MAX_ARTIFACT_BYTES, classify


OWNER = "android/operator-overlay/app/src/main/java/com/homecenter/operatoroverlay/OperatorOverlayService.java"
BASE = "c5de1411a6b68087ae17aff83c032af754587150"


def _require_descriptor_backend() -> None:
    if current_directory_handle_binding_capability().status != "SUPPORTED_POSIX_PRIMITIVES":
        pytest.skip("descriptor backend primitives unavailable on this runtime")


def _patch(name: str) -> str:
    return (
        "# STATUS: CORRECTED_PROPOSED_NOT_APPLIED\n"
        f"# BASE OWNER BLOB: {BASE}\n"
        f"# OWNER: {OWNER}\n"
        f"# fixture: {name}\n"
        "diff --git a/owner b/owner\n"
    )


def _assert_zero_partial_authority(result: dict[str, object]) -> None:
    assert result["backend"] == DESCRIPTOR_BACKEND
    assert result["portableFallbackAttempted"] is False
    assert result["surgeries"] == []
    assert result["collisionSets"] == []
    assert result["staleBaseGroups"] == []
    assert result["unverifiedBaseGroups"] == []
    assert result["evidenceComplete"] is False


def test_descriptor_candidate_overflow_preserves_observed_work_counts(tmp_path: Path):
    _require_descriptor_backend()
    root = tmp_path / "patches"
    root.mkdir()
    (root / "try-forever-a.patch").write_text(_patch("a"), encoding="utf-8")
    (root / "try-forever-b.patch").write_text(_patch("b"), encoding="utf-8")

    result = classify(root, {OWNER: BASE}, max_candidates=1)
    _assert_zero_partial_authority(result)

    # RED on current source: descriptor inventory overflow collapses these observations to zero.
    assert result["artifactDirectoryEntriesObserved"] == 2
    assert result["artifactCandidatesObserved"] == 2
    assert len(result["discoveryErrors"]) == 1
    error = result["discoveryErrors"][0]
    assert error["artifact_kind"] == "artifact_inventory"
    assert "candidate set exceeds 1" in error["boundary"]


def test_descriptor_artifact_failure_retains_inventory_and_artifact_identity(tmp_path: Path):
    _require_descriptor_backend()
    root = tmp_path / "patches"
    root.mkdir()
    target = root / "try-forever-bad-utf8.patch"
    target.write_bytes(
        b"# STATUS: CORRECTED_PROPOSED_NOT_APPLIED\n# BASE OWNER BLOB: "
        + BASE.encode("ascii")
        + b"\n# OWNER: "
        + OWNER.encode("ascii")
        + b"\n\xff\n"
    )

    result = classify(root, {OWNER: BASE})
    _assert_zero_partial_authority(result)

    # RED on current source: a descriptor artifact-custody wound is collapsed to descriptor_backend
    # with zero observed counts even though held-root inventory already identified this exact file.
    assert result["artifactDirectoryEntriesObserved"] == 1
    assert result["artifactCandidatesObserved"] == 1
    assert len(result["discoveryErrors"]) == 1
    error = result["discoveryErrors"][0]
    assert Path(error["path"]).name == target.name
    assert error["artifact_kind"] == "patch"
    assert "UTF-8" in error["boundary"]


def test_descriptor_oversize_failure_retains_identified_artifact_without_prefix_authority(tmp_path: Path):
    _require_descriptor_backend()
    root = tmp_path / "patches"
    root.mkdir()
    target = root / "try-forever-oversized.patch"
    target.write_bytes(b"x" * (MAX_ARTIFACT_BYTES + 1))

    result = classify(root, {OWNER: BASE})
    _assert_zero_partial_authority(result)

    assert result["artifactDirectoryEntriesObserved"] == 1
    assert result["artifactCandidatesObserved"] == 1
    assert len(result["discoveryErrors"]) == 1
    error = result["discoveryErrors"][0]
    assert Path(error["path"]).name == target.name
    assert error["artifact_kind"] == "patch"
    assert "exceeds" in error["boundary"]


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__]))
