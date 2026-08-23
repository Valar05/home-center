#!/usr/bin/env python3
"""Regression source for the applied exact-metadata/default-owner owner surgery.

SOURCE ONLY / UNEXECUTED. This fixture proves base/result provenance and current owner source shape;
it does not promote source wiring into TESTED, runtime, deployment, delivery, or acceptance.
"""

from __future__ import annotations

import hashlib
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
OWNER = REPO_ROOT / "tools" / "try_forever_owner_surgery_custody_probe.py"
PATCH = REPO_ROOT / "patches" / "try-forever-owner-surgery-metadata-exactness-owner.patch"
EXPECTED_OWNER = "tools/try_forever_owner_surgery_custody_probe.py"
EXPECTED_STATUS = "APPLIED_SOURCE"
EXPECTED_BASE_BLOB = "523d8005212745738106733e91be6dd625caf767"
EXPECTED_RESULT_BLOB = "a96d572698dfdbc3800410446f27e77908938e4b"
EXPECTED_APPLIED_COMMIT = "2e94d752012234d7025f6271f262d27ed3a97f6c"


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
        elif line.startswith("# APPLIED COMMIT: "):
            result["applied_commit"] = line.removeprefix("# APPLIED COMMIT: ")
        elif line.startswith("# RESULT OWNER BLOB: "):
            result["result"] = line.removeprefix("# RESULT OWNER BLOB: ")
    return result


def test_applied_patch_preserves_exact_base_result_and_commit_provenance():
    headers = patch_headers(PATCH.read_text(encoding="utf-8"))
    assert headers == {
        "base": EXPECTED_BASE_BLOB,
        "status": EXPECTED_STATUS,
        "owner": EXPECTED_OWNER,
        "applied_commit": EXPECTED_APPLIED_COMMIT,
        "result": EXPECTED_RESULT_BLOB,
    }
    assert git_blob_sha1(OWNER.read_bytes()) == EXPECTED_RESULT_BLOB


def test_applied_patch_composes_existing_exact_metadata_and_fallback_organs_only():
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


def test_current_owner_source_is_wired_without_promoting_test_or_runtime_state():
    owner = OWNER.read_text(encoding="utf-8")
    assert "from try_forever_owner_surgery_metadata_exactness import" in owner
    assert "from try_forever_owner_surgery_default_owner_binding import" in owner
    assert "admit_patch_metadata(text)" in owner
    assert "admit_default_owner_from_patch(" in owner
    assert "owner = owner.strip()" not in owner
    assert '"OperatorOverlayService.java" not in text' not in owner
