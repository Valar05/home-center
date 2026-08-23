#!/usr/bin/env python3
"""Intentionally RED owner boundary for exact owner-surgery metadata.

SOURCE ONLY / UNEXECUTED. The canonical v10 custody owner currently first-matches textual patch
headers and structurally trims CLI owner keys. This regression must stay RED until the existing owner
consumes ``admit_patch_metadata`` and ``admit_owner_identity`` without creating a second custody
owner.
"""

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
OWNER = REPO_ROOT / "tools" / "try_forever_owner_surgery_custody_probe.py"


def owner_source() -> str:
    return OWNER.read_text(encoding="utf-8")


def test_canonical_owner_consumes_exact_patch_header_contract():
    source = owner_source()
    assert "admit_patch_metadata" in source
    assert "BASE_RE.search(text)" not in source
    assert "STATE_RE.search(text)" not in source
    assert "OWNER_RE.search(text)" not in source


def test_cli_current_owner_identity_is_not_trim_repaired():
    source = owner_source()
    assert "admit_owner_identity" in source
    assert "owner = owner.strip()" not in source


def test_programmatic_current_owner_map_uses_same_exact_owner_identity_gate():
    source = owner_source()
    start = source.index("def _admit_current_owner_blobs")
    end = source.index("\ndef classify", start)
    body = source[start:end]
    assert "admit_owner_identity" in body
