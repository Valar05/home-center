#!/usr/bin/env python3
"""Regression source for exact base-owner blob evidence in owner-surgery custody.

The base-owner blob is authority evidence, not display text. Uppercase or otherwise normalization-
dependent hexadecimal must not be lowercased into authority. Source existence is not execution or
TESTED evidence.
"""

from __future__ import annotations

import json
from pathlib import Path

from try_forever_owner_surgery_custody_probe import inspect_delta, inspect_patch


OWNER = "android/operator-overlay/app/src/main/java/com/homecenter/operatoroverlay/OperatorOverlayService.java"
LOWER = "a" * 40
UPPER = "A" * 40


def _write_patch(path: Path, blob: str) -> None:
    path.write_text(
        "\n".join(
            [
                f"# BASE OWNER BLOB: {blob}",
                f"# OWNER: {OWNER}",
                "# STATUS: PROPOSED_NOT_APPLIED",
                "--- a/owner",
                "+++ b/owner",
                "",
            ]
        ),
        encoding="utf-8",
    )


def _write_delta(path: Path, blob: str) -> None:
    path.write_text(
        json.dumps(
            {
                "schema": "try-forever-owner-delta.v1",
                "owner": OWNER,
                "baseBlob": blob,
                "state": "PROPOSED_NOT_APPLIED",
            }
        ),
        encoding="utf-8",
    )


def test_patch_lowercase_base_blob_is_admitted_exactly(tmp_path: Path):
    path = tmp_path / "try-forever-lower.patch"
    _write_patch(path, LOWER)
    surgery, error = inspect_patch(path)
    assert error is None
    assert surgery is not None
    assert surgery.base_blob == LOWER


def test_patch_uppercase_base_blob_is_rejected_not_normalized(tmp_path: Path):
    path = tmp_path / "try-forever-upper.patch"
    _write_patch(path, UPPER)
    surgery, error = inspect_patch(path)
    assert surgery is None
    assert error is not None
    assert "lowercase" in error.boundary


def test_delta_lowercase_base_blob_is_admitted_exactly(tmp_path: Path):
    path = tmp_path / "try-forever-lower.delta.json"
    _write_delta(path, LOWER)
    surgery, error = inspect_delta(path)
    assert error is None
    assert surgery is not None
    assert surgery.base_blob == LOWER


def test_delta_uppercase_base_blob_is_rejected_not_normalized(tmp_path: Path):
    path = tmp_path / "try-forever-upper.delta.json"
    _write_delta(path, UPPER)
    surgery, error = inspect_delta(path)
    assert surgery is None
    assert error is not None
    assert "lowercase" in error.boundary
