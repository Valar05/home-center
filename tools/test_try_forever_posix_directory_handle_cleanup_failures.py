#!/usr/bin/env python3
"""Focused regression source for descriptor-custody cleanup-close containment.

Source existence is not regression execution, TESTED, runtime, deployment, phone delivery, or
acceptance evidence. These fixtures pin cleanup ownership separately from open/read/enumeration
custody: a close failure is typed when it is the primary failure, but cleanup must not replace a
more informative failure already propagating from the custody operation.
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
    DescriptorCustodyCleanupError,
    HeldDirectoryCustody,
)


def _require_posix_descriptor_surface() -> None:
    if current_directory_handle_binding_capability().status != "SUPPORTED_POSIX_PRIMITIVES":
        pytest.skip("held-directory descriptor primitives unavailable on this runtime")


class _EmptyEntries:
    def __enter__(self):
        return iter(())

    def __exit__(self, exc_type, exc, tb):
        return False


class _OneEntry:
    name = "unrelated.txt"


class _OneEntries:
    def __enter__(self):
        return iter((_OneEntry(),))

    def __exit__(self, exc_type, exc, tb):
        return False


def test_explicit_root_close_failure_is_typed_and_descriptor_is_retired(
    tmp_path: Path,
    monkeypatch,
):
    _require_posix_descriptor_surface()
    root = tmp_path / "patches"
    root.mkdir()
    held = HeldDirectoryCustody(root)
    target_fd = held.fd
    real_close = os.close

    def fail_target_close(fd: int):
        if fd == target_fd:
            raise OSError("synthetic root close failure")
        return real_close(fd)

    monkeypatch.setattr(os, "close", fail_target_close)
    try:
        with pytest.raises(
            DescriptorCustodyCleanupError,
            match="held directory descriptor close failed",
        ):
            held.close()
        assert held.fd == -1
    finally:
        real_close(target_fd)


def test_root_close_failure_does_not_mask_body_failure(tmp_path: Path, monkeypatch):
    _require_posix_descriptor_surface()
    root = tmp_path / "patches"
    root.mkdir()
    held = HeldDirectoryCustody(root)
    target_fd = held.fd
    real_close = os.close

    def fail_target_close(fd: int):
        if fd == target_fd:
            raise OSError("synthetic root close failure")
        return real_close(fd)

    monkeypatch.setattr(os, "close", fail_target_close)
    try:
        with pytest.raises(ValueError, match="primary body wound"):
            with held:
                raise ValueError("primary body wound")
        assert held.fd == -1
    finally:
        real_close(target_fd)


def test_scan_close_failure_is_typed_when_inventory_otherwise_succeeds(
    tmp_path: Path,
    monkeypatch,
):
    _require_posix_descriptor_surface()
    root = tmp_path / "patches"
    root.mkdir()
    real_open = os.open
    real_close = os.close
    scan_fd: dict[str, int] = {}

    with HeldDirectoryCustody(root) as held:
        def capture_scan_open(path, flags, *args, **kwargs):
            fd = real_open(path, flags, *args, **kwargs)
            if path == "." and kwargs.get("dir_fd") == held.fd:
                scan_fd["value"] = fd
            return fd

        def fail_scan_close(fd: int):
            if fd == scan_fd.get("value"):
                raise OSError("synthetic scan close failure")
            return real_close(fd)

        monkeypatch.setattr(os, "open", capture_scan_open)
        monkeypatch.setattr(os, "scandir", lambda _fd: _EmptyEntries())
        monkeypatch.setattr(os, "close", fail_scan_close)
        try:
            with pytest.raises(
                DescriptorCustodyCleanupError,
                match="held-directory scan handle close failed",
            ):
                held.candidate_inventory(
                    is_candidate=lambda _name: False,
                    max_entries=8,
                    max_candidates=8,
                )
        finally:
            real_close(scan_fd["value"])


def test_scan_close_failure_does_not_mask_primary_inventory_wound(
    tmp_path: Path,
    monkeypatch,
):
    _require_posix_descriptor_surface()
    root = tmp_path / "patches"
    root.mkdir()
    real_open = os.open
    real_close = os.close
    scan_fd: dict[str, int] = {}

    with HeldDirectoryCustody(root) as held:
        def capture_scan_open(path, flags, *args, **kwargs):
            fd = real_open(path, flags, *args, **kwargs)
            if path == "." and kwargs.get("dir_fd") == held.fd:
                scan_fd["value"] = fd
            return fd

        def fail_scan_close(fd: int):
            if fd == scan_fd.get("value"):
                raise OSError("synthetic scan close failure")
            return real_close(fd)

        monkeypatch.setattr(os, "open", capture_scan_open)
        monkeypatch.setattr(os, "scandir", lambda _fd: _OneEntries())
        monkeypatch.setattr(os, "close", fail_scan_close)
        try:
            with pytest.raises(
                DescriptorArtifactCustodyError,
                match="scan exceeds 0 entry budget",
            ):
                held.candidate_inventory(
                    is_candidate=lambda _name: False,
                    max_entries=0,
                    max_candidates=8,
                )
        finally:
            real_close(scan_fd["value"])


def test_artifact_close_failure_is_typed_when_observation_otherwise_succeeds(
    tmp_path: Path,
    monkeypatch,
):
    _require_posix_descriptor_surface()
    root = tmp_path / "patches"
    root.mkdir()
    name = "try-forever-a.patch"
    (root / name).write_text("hello", encoding="utf-8")
    real_open = os.open
    real_close = os.close
    artifact_fd: dict[str, int] = {}

    with HeldDirectoryCustody(root) as held:
        def capture_artifact_open(path, flags, *args, **kwargs):
            fd = real_open(path, flags, *args, **kwargs)
            if path == name and kwargs.get("dir_fd") == held.fd:
                artifact_fd["value"] = fd
            return fd

        def fail_artifact_close(fd: int):
            if fd == artifact_fd.get("value"):
                raise OSError("synthetic artifact close failure")
            return real_close(fd)

        monkeypatch.setattr(os, "open", capture_artifact_open)
        monkeypatch.setattr(os, "close", fail_artifact_close)
        try:
            with pytest.raises(
                DescriptorCustodyCleanupError,
                match="candidate descriptor close failed",
            ):
                held.observe_utf8_regular_file(name, max_bytes=32)
        finally:
            real_close(artifact_fd["value"])


def test_artifact_close_failure_does_not_mask_primary_artifact_wound(
    tmp_path: Path,
    monkeypatch,
):
    _require_posix_descriptor_surface()
    root = tmp_path / "patches"
    root.mkdir()
    name = "try-forever-a.patch"
    (root / name).write_text("x", encoding="utf-8")
    real_open = os.open
    real_close = os.close
    artifact_fd: dict[str, int] = {}

    with HeldDirectoryCustody(root) as held:
        def capture_artifact_open(path, flags, *args, **kwargs):
            fd = real_open(path, flags, *args, **kwargs)
            if path == name and kwargs.get("dir_fd") == held.fd:
                artifact_fd["value"] = fd
            return fd

        def fail_artifact_close(fd: int):
            if fd == artifact_fd.get("value"):
                raise OSError("synthetic artifact close failure")
            return real_close(fd)

        monkeypatch.setattr(os, "open", capture_artifact_open)
        monkeypatch.setattr(os, "close", fail_artifact_close)
        try:
            with pytest.raises(
                DescriptorArtifactCustodyError,
                match="candidate exceeds 0 byte custody budget",
            ):
                held.observe_utf8_regular_file(name, max_bytes=0)
        finally:
            real_close(artifact_fd["value"])
