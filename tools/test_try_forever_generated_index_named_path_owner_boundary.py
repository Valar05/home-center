#!/usr/bin/env python3
"""Owner-boundary regression for generated-index named-path preservation.

The finite-artifact custody gate can reject symlinks/reparse topology only if the
existing provenance owner keeps the caller's named path intact. Lexical path
normalization and the finite-artifact observer are now both source-wired in the
sole provenance owner; these fixtures pin that composition without claiming the
regressions have executed in CI.

This fixture owns no second probe, renderer, phone surface, or P0 lane.
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import try_forever_skill_provenance_probe as probe


def _lexical_absolute(path: Path) -> Path:
    return Path(os.path.abspath(os.fspath(path)))


def test_relative_generated_index_symlink_spelling_survives_owner_resolution(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    target = tmp_path / "external-index.json"
    target.write_text('{"sourceHead":"abc"}', encoding="utf-8")
    alias = repo / "generated-index.json"
    try:
        alias.symlink_to(target)
    except (NotImplementedError, OSError):
        pytest.skip("symlink fixture unavailable")

    resolved = probe.resolve_repo_path(repo, "generated-index.json")

    assert resolved == _lexical_absolute(alias)
    assert resolved.is_symlink(), (
        "owner path admission must preserve the named redirector until the "
        "no-follow artifact topology gate can reject it"
    )


def test_absolute_generated_index_symlink_spelling_survives_owner_resolution(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    target = tmp_path / "external-index.json"
    target.write_text('{"sourceHead":"abc"}', encoding="utf-8")
    alias = tmp_path / "generated-index-link.json"
    try:
        alias.symlink_to(target)
    except (NotImplementedError, OSError):
        pytest.skip("symlink fixture unavailable")

    resolved = probe.resolve_repo_path(repo, str(alias))

    assert resolved == _lexical_absolute(alias)
    assert resolved.is_symlink()


def test_regular_relative_path_is_made_absolute_without_requiring_existence(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    candidate = repo / "not-created-yet.json"

    resolved = probe.resolve_repo_path(repo, "not-created-yet.json")

    assert resolved == _lexical_absolute(candidate)
    assert not resolved.exists()


def test_owner_inspection_rejects_named_symlink_before_json_semantics(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    target = tmp_path / "external-index.json"
    target.write_text(
        '{"sourceHead":"abc123","generatedAt":"2026-08-19T10:00:00+00:00","dirtySource":false}',
        encoding="utf-8",
    )
    alias = repo / "generated-index.json"
    try:
        alias.symlink_to(target)
    except (NotImplementedError, OSError):
        pytest.skip("symlink fixture unavailable")

    named_path = probe.resolve_repo_path(repo, "generated-index.json")
    verdict = probe.inspect_generated_index(
        named_path,
        current_head="abc123",
        current_tree_dirty=False,
        max_age_hours=24.0,
        now=datetime(2026, 8, 19, 10, 1, tzinfo=timezone.utc),
    )

    assert verdict.status == "UNRESOLVED"
    assert "GeneratedIndexArtifactTopologyError" in verdict.reason
    assert verdict.source_head == ""
