#!/usr/bin/env python3
"""Regression source for bounded exact generated-index artifact observation."""

import hashlib
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

import try_forever_generated_index_artifact_observation as artifact_observation
from try_forever_generated_index_artifact_observation import (
    WINDOWS_FILE_ATTRIBUTE_REPARSE_POINT,
    GeneratedIndexArtifactChangedError,
    GeneratedIndexArtifactResourceLimitError,
    GeneratedIndexArtifactTopologyError,
    observe_generated_index_artifact,
)
from try_forever_generated_index_emission_policy import (
    assess_generated_index_artifact_custody,
)


def _with_windows_reparse_metadata(metadata, *, tag=0xA000001A):
    return SimpleNamespace(
        st_mode=metadata.st_mode,
        st_ino=metadata.st_ino,
        st_dev=metadata.st_dev,
        st_size=metadata.st_size,
        st_mtime=metadata.st_mtime,
        st_mtime_ns=getattr(metadata, "st_mtime_ns", int(metadata.st_mtime * 1_000_000_000)),
        st_file_attributes=WINDOWS_FILE_ATTRIBUTE_REPARSE_POINT,
        st_reparse_tag=tag,
    )


def test_exact_budget_reaches_eof_and_returns_whole_artifact_sha(tmp_path):
    payload = b'{"sourceHead":"abc"}'
    path = tmp_path / "index.json"
    path.write_bytes(payload)

    observed = observe_generated_index_artifact(path, max_bytes=len(payload))

    assert observed.size_bytes == len(payload)
    assert observed.sha256 == hashlib.sha256(payload).hexdigest()
    assert observed.utf8_text == payload.decode("utf-8")


def test_max_plus_one_rejects_without_prefix_authority(tmp_path):
    path = tmp_path / "index.json"
    path.write_bytes(b"12345")

    with pytest.raises(GeneratedIndexArtifactResourceLimitError):
        observe_generated_index_artifact(path, max_bytes=4)


def test_invalid_utf8_does_not_become_semantic_index_text(tmp_path):
    path = tmp_path / "index.json"
    path.write_bytes(b"{\xff}")

    with pytest.raises(UnicodeDecodeError):
        observe_generated_index_artifact(path, max_bytes=32)


@pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="FIFO fixture requires os.mkfifo")
def test_non_regular_fifo_fails_closed_before_authority_open(tmp_path, monkeypatch):
    path = tmp_path / "index.json"
    os.mkfifo(path)

    def forbidden_open(*_args, **_kwargs):
        raise AssertionError("special-file rejection must happen before os.open")

    monkeypatch.setattr(os, "open", forbidden_open)
    with pytest.raises(GeneratedIndexArtifactTopologyError):
        observe_generated_index_artifact(path, max_bytes=1024)


def test_windows_reparse_regular_file_shape_fails_closed_before_authority_open(tmp_path, monkeypatch):
    path = tmp_path / "index.json"
    path.write_text('{"cloud":"stub"}', encoding="utf-8")
    real_lstat = Path.lstat
    fake_reparse = _with_windows_reparse_metadata(path.stat())

    def reparse_lstat(self):
        if self == path:
            return fake_reparse
        return real_lstat(self)

    def forbidden_open(*_args, **_kwargs):
        raise AssertionError("Windows reparse-point rejection must happen before os.open")

    monkeypatch.setattr(Path, "lstat", reparse_lstat)
    monkeypatch.setattr(artifact_observation.os, "open", forbidden_open)

    with pytest.raises(GeneratedIndexArtifactTopologyError, match="reparse-point"):
        observe_generated_index_artifact(path, max_bytes=1024)


def test_opened_descriptor_reparse_metadata_fails_closed_after_preopen_admission(tmp_path, monkeypatch):
    path = tmp_path / "index.json"
    path.write_text('{"ordinary":"before-open"}', encoding="utf-8")
    fake_reparse = _with_windows_reparse_metadata(path.stat())

    monkeypatch.setattr(artifact_observation.os, "fstat", lambda _descriptor: fake_reparse)

    with pytest.raises(GeneratedIndexArtifactTopologyError, match="reparse-point"):
        observe_generated_index_artifact(path, max_bytes=1024)


def test_regular_file_still_reaches_exact_observation_after_topology_gate(tmp_path):
    payload = b'{"finite":true}'
    path = tmp_path / "index.json"
    path.write_bytes(payload)

    observed = observe_generated_index_artifact(path, max_bytes=len(payload))

    assert observed.size_bytes == len(payload)
    assert observed.sha256 == hashlib.sha256(payload).hexdigest()
    assert observed.utf8_text == payload.decode("utf-8")


def test_symlink_does_not_inherit_regular_file_authority(tmp_path):
    target = tmp_path / "real.json"
    target.write_text('{"real":true}', encoding="utf-8")
    alias = tmp_path / "index.json"
    try:
        alias.symlink_to(target)
    except (NotImplementedError, OSError):
        pytest.skip("symlink fixture unavailable")

    with pytest.raises(GeneratedIndexArtifactTopologyError):
        observe_generated_index_artifact(alias, max_bytes=1024)


def test_path_replacement_between_admission_and_open_fails_closed(tmp_path, monkeypatch):
    path = tmp_path / "index.json"
    replacement = tmp_path / "replacement.json"
    path.write_text('{"version":"a"}', encoding="utf-8")
    replacement.write_text('{"version":"b"}', encoding="utf-8")

    real_open = artifact_observation.os.open
    replaced = False

    def replacing_open(target, flags, *args, **kwargs):
        nonlocal replaced
        if Path(target) == path and not replaced:
            os.replace(replacement, path)
            replaced = True
        return real_open(target, flags, *args, **kwargs)

    monkeypatch.setattr(artifact_observation.os, "open", replacing_open)

    with pytest.raises(GeneratedIndexArtifactChangedError):
        observe_generated_index_artifact(path, max_bytes=1024)


def test_descriptor_revalidation_rejects_changed_post_read_observation(tmp_path, monkeypatch):
    path = tmp_path / "index.json"
    other = tmp_path / "other.json"
    path.write_text('{"version":"stable"}', encoding="utf-8")
    other.write_text('{"version":"other"}', encoding="utf-8")

    real_fstat = artifact_observation.os.fstat
    other_stat = other.stat()
    calls = 0

    def drifting_fstat(descriptor):
        nonlocal calls
        calls += 1
        if calls == 1:
            return real_fstat(descriptor)
        return other_stat

    monkeypatch.setattr(artifact_observation.os, "fstat", drifting_fstat)

    with pytest.raises(GeneratedIndexArtifactChangedError):
        observe_generated_index_artifact(path, max_bytes=1024)


def test_named_path_revalidation_rejects_persistent_replacement_after_open(tmp_path, monkeypatch):
    path = tmp_path / "index.json"
    other = tmp_path / "other.json"
    path.write_text('{"version":"stable"}', encoding="utf-8")
    other.write_text('{"version":"other"}', encoding="utf-8")

    real_lstat = Path.lstat
    other_stat = other.stat()
    calls = 0

    def drifting_lstat(self):
        nonlocal calls
        if self == path:
            calls += 1
            if calls >= 2:
                return other_stat
        return real_lstat(self)

    monkeypatch.setattr(Path, "lstat", drifting_lstat)

    with pytest.raises(GeneratedIndexArtifactChangedError):
        observe_generated_index_artifact(path, max_bytes=1024)


def test_external_mutation_changes_exact_artifact_custody(tmp_path):
    path = tmp_path / "index.json"
    path.write_text('{"version":"a"}', encoding="utf-8")
    inspected = observe_generated_index_artifact(path, max_bytes=1024)

    path.write_text('{"version":"b"}', encoding="utf-8")
    emission = observe_generated_index_artifact(path, max_bytes=1024)

    custody = assess_generated_index_artifact_custody(
        inspected_sha256=inspected.sha256,
        emission_sha256=emission.sha256,
    )
    assert custody.status == "CHANGED"


def test_same_exact_artifact_can_satisfy_content_custody(tmp_path):
    path = tmp_path / "index.json"
    path.write_text('{"version":"same"}', encoding="utf-8")
    inspected = observe_generated_index_artifact(path, max_bytes=1024)
    emission = observe_generated_index_artifact(path, max_bytes=1024)

    custody = assess_generated_index_artifact_custody(
        inspected_sha256=inspected.sha256,
        emission_sha256=emission.sha256,
    )
    assert custody.status == "STABLE"
