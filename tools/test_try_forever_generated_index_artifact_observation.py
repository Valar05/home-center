#!/usr/bin/env python3
"""Regression source for bounded exact generated-index artifact observation."""

import hashlib
import os
from pathlib import Path

import pytest

from try_forever_generated_index_artifact_observation import (
    GeneratedIndexArtifactResourceLimitError,
    GeneratedIndexArtifactTopologyError,
    observe_generated_index_artifact,
)
from try_forever_generated_index_emission_policy import (
    assess_generated_index_artifact_custody,
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
