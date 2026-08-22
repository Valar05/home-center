#!/usr/bin/env python3
"""Focused regression source for descriptor-custody root/inventory I/O containment.

Source existence is not regression execution, TESTED, runtime, deployment, phone delivery, or
acceptance evidence. These fixtures target the authority-facing I/O boundaries that precede the
already-covered candidate artifact read path.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from try_forever_directory_handle_binding_capability import (
    current_directory_handle_binding_capability,
)
from try_forever_posix_directory_handle_custody import (
    DescriptorArtifactCustodyError,
    HeldDirectoryCustody,
    PosixDirectoryHandleCustodyUnavailable,
)


def _require_posix_descriptor_surface() -> None:
    if current_directory_handle_binding_capability().status != "SUPPORTED_POSIX_PRIMITIVES":
        pytest.skip("held-directory descriptor primitives unavailable on this runtime")


def _candidate_filter(name: str) -> bool:
    return name.startswith("try-forever-") and name.endswith(".patch")


def test_missing_root_is_typed_custody_unavailable(tmp_path: Path):
    _require_posix_descriptor_surface()
    with pytest.raises(
        PosixDirectoryHandleCustodyUnavailable,
        match="held directory open failed",
    ):
        HeldDirectoryCustody(tmp_path / "missing-patches")


def test_root_fstat_failure_is_typed_custody_unavailable(tmp_path: Path, monkeypatch):
    _require_posix_descriptor_surface()
    root = tmp_path / "patches"
    root.mkdir()

    def fail_fstat(_fd: int):
        raise OSError("synthetic fstat failure")

    monkeypatch.setattr(os, "fstat", fail_fstat)
    with pytest.raises(
        PosixDirectoryHandleCustodyUnavailable,
        match="descriptor identity read failed",
    ):
        HeldDirectoryCustody(root)


def test_scan_handle_open_failure_is_typed_inventory_rejection(tmp_path: Path, monkeypatch):
    _require_posix_descriptor_surface()
    root = tmp_path / "patches"
    root.mkdir()
    (root / "try-forever-a.patch").write_text("a", encoding="utf-8")

    with HeldDirectoryCustody(root) as held:
        real_open = os.open

        def fail_fresh_scan(path, flags, *args, **kwargs):
            if path == "." and kwargs.get("dir_fd") == held.fd:
                raise OSError("synthetic scan open failure")
            return real_open(path, flags, *args, **kwargs)

        monkeypatch.setattr(os, "open", fail_fresh_scan)
        with pytest.raises(
            DescriptorArtifactCustodyError,
            match="scan handle open failed",
        ):
            held.candidate_inventory(
                is_candidate=_candidate_filter,
                max_entries=32,
                max_candidates=8,
            )


def test_scandir_failure_is_typed_inventory_rejection(tmp_path: Path, monkeypatch):
    _require_posix_descriptor_surface()
    root = tmp_path / "patches"
    root.mkdir()
    (root / "try-forever-a.patch").write_text("a", encoding="utf-8")

    with HeldDirectoryCustody(root) as held:
        def fail_scandir(_fd: int):
            raise OSError("synthetic scandir failure")

        monkeypatch.setattr(os, "scandir", fail_scandir)
        with pytest.raises(
            DescriptorArtifactCustodyError,
            match="enumeration I/O failed",
        ):
            held.candidate_inventory(
                is_candidate=_candidate_filter,
                max_entries=32,
                max_candidates=8,
            )


def test_candidate_stat_failure_is_typed_inventory_rejection(tmp_path: Path, monkeypatch):
    _require_posix_descriptor_surface()
    root = tmp_path / "patches"
    root.mkdir()
    (root / "try-forever-a.patch").write_text("a", encoding="utf-8")

    class FailingEntry:
        name = "try-forever-a.patch"

        def stat(self, *, follow_symlinks: bool):
            assert follow_symlinks is False
            raise OSError("synthetic candidate stat failure")

    class FakeEntries:
        def __enter__(self):
            return iter((FailingEntry(),))

        def __exit__(self, exc_type, exc, tb):
            return False

    with HeldDirectoryCustody(root) as held:
        monkeypatch.setattr(os, "scandir", lambda _fd: FakeEntries())
        with pytest.raises(
            DescriptorArtifactCustodyError,
            match="candidate identity stat failed",
        ):
            held.candidate_inventory(
                is_candidate=_candidate_filter,
                max_entries=32,
                max_candidates=8,
            )


def test_candidate_policy_oserror_is_not_laundered_into_io_custody_error(tmp_path: Path):
    _require_posix_descriptor_surface()
    root = tmp_path / "patches"
    root.mkdir()
    (root / "try-forever-a.patch").write_text("a", encoding="utf-8")

    def fail_policy(_name: str) -> bool:
        raise OSError("caller policy failed")

    with HeldDirectoryCustody(root) as held:
        with pytest.raises(OSError, match="caller policy failed"):
            held.candidate_inventory(
                is_candidate=fail_policy,
                max_entries=32,
                max_candidates=8,
            )
