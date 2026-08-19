#!/usr/bin/env python3
"""Red owner-boundary regression for generated-index named-path preservation.

The finite-artifact custody gate can reject symlinks/reparse topology only if the
existing provenance owner hands it the caller's named path. Resolving the path
through ``Path.resolve()`` before that gate erases the redirector and converts the
check into target-file inspection.

This fixture is intentionally source evidence only until the existing owner is
wired. It owns no second probe, renderer, phone surface, or P0 lane.
"""

from __future__ import annotations

import os
import sys
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
