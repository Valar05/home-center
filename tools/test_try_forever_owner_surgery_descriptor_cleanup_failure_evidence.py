#!/usr/bin/env python3
"""SOURCE / UNEXECUTED canonical regression for descriptor cleanup failure evidence.

A selected descriptor backend can finish bounded inventory and artifact observation and then fail while
closing the held root. Canonical v10 must still fail promotion authority closed, must not retry through
the portable backend, and must retain only the bounded inventory work that was already observed before
the cleanup wound. No artifact is named as *the* failing artifact because cleanup is a backend-level
wound rather than an identified artifact-custody failure.
"""

from pathlib import Path

import pytest

from try_forever_directory_handle_binding_capability import (
    current_directory_handle_binding_capability,
)
from try_forever_owner_surgery_backend_policy import DESCRIPTOR_BACKEND
from try_forever_owner_surgery_custody_probe import classify
from try_forever_posix_directory_handle_custody import (
    DescriptorCustodyCleanupError,
    HeldDirectoryCustody,
)


OWNER = "android/operator-overlay/app/src/main/java/com/homecenter/operatoroverlay/OperatorOverlayService.java"
BASE = "c5de1411a6b68087ae17aff83c032af754587150"


def _require_descriptor_backend() -> None:
    if current_directory_handle_binding_capability().status != "SUPPORTED_POSIX_PRIMITIVES":
        pytest.skip("descriptor backend primitives unavailable on this runtime")


def _patch() -> str:
    return (
        "# STATUS: CORRECTED_PROPOSED_NOT_APPLIED\n"
        f"# BASE OWNER BLOB: {BASE}\n"
        f"# OWNER: {OWNER}\n"
        "diff --git a/owner b/owner\n"
    )


def test_root_cleanup_wound_preserves_observed_counts_without_partial_authority(
    tmp_path: Path,
    monkeypatch,
):
    _require_descriptor_backend()
    root = tmp_path / "patches"
    root.mkdir()
    (root / "try-forever-a.patch").write_text(_patch(), encoding="utf-8")

    real_close = HeldDirectoryCustody._close

    def close_then_fail(self, *, preserve_primary_failure: bool):
        real_close(self, preserve_primary_failure=preserve_primary_failure)
        if not preserve_primary_failure:
            raise DescriptorCustodyCleanupError("synthetic held-root cleanup failure")

    monkeypatch.setattr(HeldDirectoryCustody, "_close", close_then_fail)
    result = classify(root, {OWNER: BASE})

    assert result["backend"] == DESCRIPTOR_BACKEND
    assert result["portableFallbackAttempted"] is False
    assert result["artifactDirectoryEntriesObserved"] == 1
    assert result["artifactCandidatesObserved"] == 1
    assert result["surgeries"] == []
    assert result["collisionSets"] == []
    assert result["staleBaseGroups"] == []
    assert result["unverifiedBaseGroups"] == []
    assert result["evidenceComplete"] is False

    assert len(result["discoveryErrors"]) == 1
    error = result["discoveryErrors"][0]
    assert error["artifact_kind"] == "descriptor_backend"
    assert Path(error["path"]).name == root.name
    assert "cleanup" in error["boundary"]


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__]))
