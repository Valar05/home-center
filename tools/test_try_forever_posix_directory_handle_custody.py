#!/usr/bin/env python3
"""Regression source for held-directory-descriptor owner-surgery custody.

These tests require a POSIX runtime exposing the capability gate's full primitive set. Their source
existence is not execution, TESTED, runtime, deployment, phone delivery, or acceptance evidence.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from try_forever_directory_handle_binding_capability import (
    current_directory_handle_binding_capability,
)
from try_forever_posix_directory_handle_custody import (
    DescriptorArtifactCustodyError,
    HeldDirectoryCustody,
)


def _require_posix_descriptor_surface() -> None:
    if current_directory_handle_binding_capability().status != "SUPPORTED_POSIX_PRIMITIVES":
        pytest.skip("held-directory descriptor primitives unavailable on this runtime")


def _candidate_filter(name: str) -> bool:
    return name.startswith("try-forever-") and name.endswith(".patch")


def test_held_root_descriptor_survives_named_root_replacement(tmp_path: Path):
    _require_posix_descriptor_surface()
    root = tmp_path / "patches"
    root.mkdir()
    (root / "try-forever-a.patch").write_text("original", encoding="utf-8")

    with HeldDirectoryCustody(root) as held:
        original_identity = held.root_identity
        moved = tmp_path / "patches-original"
        root.rename(moved)
        root.mkdir()
        (root / "try-forever-a.patch").write_text("replacement", encoding="utf-8")

        observed = held.observe_utf8_regular_file(
            "try-forever-a.patch",
            max_bytes=1024,
        )
        assert observed.utf8_text == "original"
        assert held.root_identity == original_identity


def test_candidate_enumeration_stays_on_held_root_after_path_replacement(tmp_path: Path):
    _require_posix_descriptor_surface()
    root = tmp_path / "patches"
    root.mkdir()
    (root / "try-forever-a.patch").write_text("a", encoding="utf-8")

    with HeldDirectoryCustody(root) as held:
        moved = tmp_path / "patches-original"
        root.rename(moved)
        root.mkdir()
        (root / "try-forever-b.patch").write_text("b", encoding="utf-8")

        names = held.candidate_names(
            is_candidate=_candidate_filter,
            max_entries=32,
            max_candidates=8,
        )
        assert names == ("try-forever-a.patch",)


def test_repeated_candidate_scans_get_fresh_directory_position(tmp_path: Path):
    _require_posix_descriptor_surface()
    root = tmp_path / "patches"
    root.mkdir()
    (root / "try-forever-a.patch").write_text("a", encoding="utf-8")
    (root / "try-forever-b.patch").write_text("b", encoding="utf-8")

    with HeldDirectoryCustody(root) as held:
        kwargs = dict(
            is_candidate=_candidate_filter,
            max_entries=32,
            max_candidates=8,
        )
        first = held.candidate_names(**kwargs)
        second = held.candidate_names(**kwargs)
        assert first == ("try-forever-a.patch", "try-forever-b.patch")
        assert second == first


def test_candidate_identity_captured_during_enumeration_survives_into_read(tmp_path: Path):
    _require_posix_descriptor_surface()
    root = tmp_path / "patches"
    root.mkdir()
    path = root / "try-forever-a.patch"
    path.write_text("original", encoding="utf-8")

    with HeldDirectoryCustody(root) as held:
        candidates = held.candidate_entries(
            is_candidate=_candidate_filter,
            max_entries=32,
            max_candidates=8,
        )
        assert len(candidates) == 1
        observed = held.observe_utf8_regular_file(
            candidates[0].name,
            max_bytes=1024,
            expected_candidate=candidates[0],
        )
        assert observed.identity == candidates[0].identity
        assert observed.utf8_text == "original"


def test_persistent_candidate_replacement_after_enumeration_is_rejected_before_read(tmp_path: Path):
    _require_posix_descriptor_surface()
    root = tmp_path / "patches"
    root.mkdir()
    path = root / "try-forever-a.patch"
    path.write_text("original", encoding="utf-8")

    with HeldDirectoryCustody(root) as held:
        candidate = held.candidate_entries(
            is_candidate=_candidate_filter,
            max_entries=32,
            max_candidates=8,
        )[0]
        old = root / "old.patch"
        path.rename(old)
        path.write_text("replacement", encoding="utf-8")

        with pytest.raises(
            DescriptorArtifactCustodyError,
            match="changed after held-root enumeration",
        ):
            held.observe_utf8_regular_file(
                candidate.name,
                max_bytes=1024,
                expected_candidate=candidate,
            )


def test_symlink_artifact_is_rejected_relative_to_held_root(tmp_path: Path):
    _require_posix_descriptor_surface()
    root = tmp_path / "patches"
    root.mkdir()
    target = root / "target.patch"
    target.write_text("target", encoding="utf-8")
    (root / "try-forever-alias.patch").symlink_to(target.name)

    with HeldDirectoryCustody(root) as held:
        candidate = held.candidate_entries(
            is_candidate=_candidate_filter,
            max_entries=32,
            max_candidates=8,
        )[0]
        with pytest.raises(DescriptorArtifactCustodyError, match="enumerated candidate is not"):
            held.observe_utf8_regular_file(
                candidate.name,
                max_bytes=1024,
                expected_candidate=candidate,
            )


def test_max_plus_one_byte_is_rejected_without_prefix_authority(tmp_path: Path):
    _require_posix_descriptor_surface()
    root = tmp_path / "patches"
    root.mkdir()
    (root / "try-forever-a.patch").write_bytes(b"abcd")

    with HeldDirectoryCustody(root) as held:
        with pytest.raises(DescriptorArtifactCustodyError, match="exceeds 3 byte"):
            held.observe_utf8_regular_file("try-forever-a.patch", max_bytes=3)


def test_path_traversal_name_is_rejected_before_descriptor_open(tmp_path: Path):
    _require_posix_descriptor_surface()
    root = tmp_path / "patches"
    root.mkdir()
    outside = tmp_path / "outside.patch"
    outside.write_text("outside", encoding="utf-8")

    with HeldDirectoryCustody(root) as held:
        with pytest.raises(DescriptorArtifactCustodyError, match="path traversal"):
            held.observe_utf8_regular_file("../outside.patch", max_bytes=1024)
