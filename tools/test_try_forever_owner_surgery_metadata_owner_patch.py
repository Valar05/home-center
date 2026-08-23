#!/usr/bin/env python3
"""Regression source for the prepared exact-metadata/default-owner surgery.

SOURCE ONLY / UNEXECUTED. This fixture proves patch provenance and the capability membrane; it does
not call a prepared patch implemented until authenticated owner source changes.
"""

from __future__ import annotations

import hashlib
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
OWNER = REPO_ROOT / "tools" / "try_forever_owner_surgery_custody_probe.py"
PATCH = REPO_ROOT / "patches" / "try-forever-owner-surgery-metadata-exactness-owner.patch"
EXPECTED_OWNER = "tools/try_forever_owner_surgery_custody_probe.py"
EXPECTED_STATUS = "CORRECTED_PROPOSED_NOT_APPLIED"


def git_blob_sha1(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def patch_headers(text: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in text.splitlines():
        if line.startswith("# BASE OWNER BLOB: "):
            result["base"] = line.removeprefix("# BASE OWNER BLOB: ")
        elif line.startswith("# STATUS: "):
            result["status"] = line.removeprefix("# STATUS: ")
        elif line.startswith("# OWNER: "):
            result["owner"] = line.removeprefix("# OWNER: ")
    return result


def test_prepared_patch_is_locked_to_exact_current_owner_blob():
    owner_bytes = OWNER.read_bytes()
    headers = patch_headers(PATCH.read_text(encoding="utf-8"))
    assert headers == {
        "base": git_blob_sha1(owner_bytes),
        "status": EXPECTED_STATUS,
        "owner": EXPECTED_OWNER,
    }


def test_prepared_patch_composes_existing_exact_metadata_and_fallback_organs_only():
    patch = PATCH.read_text(encoding="utf-8")
    assert "admit_patch_metadata" in patch
    assert "admit_owner_identity" in patch
    assert "admit_default_owner_from_patch" in patch
    assert "BASE_RE.search(text)" in patch
    assert "STATE_RE.search(text)" in patch
    assert "OWNER_RE.search(text)" in patch
    assert "+        metadata = admit_patch_metadata(text)" in patch
    assert "+            owner = admit_default_owner_from_patch(" in patch
    assert "+        owner = admit_owner_identity(payload.get(\"owner\"), field=\"delta owner\")" in patch
    assert "+        owner = admit_owner_identity(owner, field=\"--current-owner owner\")" in patch


def test_patch_provenance_does_not_launder_current_owner_into_source_wired():
    owner = OWNER.read_text(encoding="utf-8")
    assert "BASE_RE.search(text)" in owner
    assert "STATE_RE.search(text)" in owner
    assert "OWNER_RE.search(text)" in owner
    assert '"OperatorOverlayService.java" not in text' in owner
    assert "owner = owner.strip()" in owner
    assert "from try_forever_owner_surgery_metadata_exactness import" not in owner
    assert "from try_forever_owner_surgery_default_owner_binding import" not in owner
