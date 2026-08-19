#!/usr/bin/env python3
"""Regression source for bounded exact generated-index artifact observation."""

import hashlib

import pytest

from try_forever_generated_index_artifact_observation import (
    GeneratedIndexArtifactResourceLimitError,
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
