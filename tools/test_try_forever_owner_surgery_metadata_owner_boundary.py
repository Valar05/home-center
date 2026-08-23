#!/usr/bin/env python3
"""Intentionally RED owner boundary for exact owner-surgery metadata and fallback ownership.

SOURCE ONLY / UNEXECUTED. The canonical v10 custody owner currently first-matches textual patch
headers, structurally trims CLI owner keys, does not route structured-delta owner identity through
the same exact owner-key admission, and infers the implicit default owner from an arbitrary basename
mention. This regression must stay RED until the existing owner consumes the exact contracts without
creating a second custody owner.
"""

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
OWNER = REPO_ROOT / "tools" / "try_forever_owner_surgery_custody_probe.py"


def owner_source() -> str:
    return OWNER.read_text(encoding="utf-8")


def method_body(source: str, name: str, next_name: str) -> str:
    start = source.index(f"def {name}")
    end = source.index(f"\ndef {next_name}", start)
    return source[start:end]


def test_canonical_owner_consumes_exact_patch_header_contract():
    source = owner_source()
    patch_body = method_body(source, "inspect_patch", "_reject_duplicate_json_members")
    assert "admit_patch_metadata" in patch_body
    assert "BASE_RE.search(text)" not in patch_body
    assert "STATE_RE.search(text)" not in patch_body
    assert "OWNER_RE.search(text)" not in patch_body


def test_implicit_default_owner_uses_exact_diff_binding_not_basename_substring():
    source = owner_source()
    patch_body = method_body(source, "inspect_patch", "_reject_duplicate_json_members")
    assert "admit_default_owner_from_patch" in patch_body
    assert '"OperatorOverlayService.java" not in text' not in patch_body


def test_structured_delta_owner_uses_same_exact_owner_identity_gate():
    source = owner_source()
    delta_body = method_body(source, "inspect_delta", "_group_payload")
    assert "admit_owner_identity" in delta_body


def test_cli_current_owner_identity_is_not_trim_repaired():
    source = owner_source()
    parse_body = method_body(source, "_parse_owner_blob", "main")
    assert "admit_owner_identity" in parse_body
    assert "owner = owner.strip()" not in parse_body


def test_programmatic_current_owner_map_uses_same_exact_owner_identity_gate():
    source = owner_source()
    body = method_body(source, "_admit_current_owner_blobs", "classify")
    assert "admit_owner_identity" in body
