#!/usr/bin/env python3
"""Source fixture for owner-surgery discovery diagnostic projection custody.

SOURCE ONLY / UNEXECUTED. Canonical v10 already consumes the shared ASCII-safe diagnostic projector,
but two independent source boundaries remain RED: canonical ``_error(...)`` still invokes caller-owned
``Exception.__str__`` before projection, and the shared projector still hashes arbitrarily large exact
strings after its returned-text ceiling is known. Canonical path/artifact evidence remains exact.
This fixture proves no regression execution, TESTED, runtime, deployment, phone delivery, or P0
capability.
"""

from pathlib import Path

import try_forever_owner_surgery_custody_probe as custody
import try_forever_owner_surgery_semantic_parser as semantic
from try_forever_owner_surgery_semantic_parser import (
    MAX_SEMANTIC_DIAGNOSTIC_SEGMENT_CHARS,
    OwnerSurgerySemanticError,
    project_owner_surgery_diagnostic_text,
    source_receipt as semantic_source_receipt,
)


MAX_BOUNDARY_CODEPOINTS = 320
PROPOSED_DIAGNOSTIC_SOURCE_CODEPOINTS = 4_096


def _assert_shared_projector_source_wired() -> None:
    receipt = semantic_source_receipt()
    assert receipt["boundedAsciiDiagnosticProjection"] is True
    assert receipt["publicDiagnosticProjection"] is True
    assert receipt["diagnosticSegmentCharCeiling"] == MAX_SEMANTIC_DIAGNOSTIC_SEGMENT_CHARS
    assert receipt["regressionExecuted"] is False
    assert receipt["tested"] is False

    assert project_owner_surgery_diagnostic_text("line-one\nline-two") == "line-one\\nline-two"
    assert project_owner_surgery_diagnostic_text("bidi:\u202eattack").isascii()
    assert project_owner_surgery_diagnostic_text("surrogate:\ud800").isascii()
    long_projection = project_owner_surgery_diagnostic_text("x" * 50_000)
    assert long_projection.startswith("<text>...#")
    assert len(long_projection) <= MAX_SEMANTIC_DIAGNOSTIC_SEGMENT_CHARS

    class HostileText(str):
        def __len__(self) -> int:
            raise AssertionError("caller-owned diagnostic __len__ executed")

    try:
        project_owner_surgery_diagnostic_text(HostileText("hostile"))
    except OwnerSurgerySemanticError:
        pass
    else:
        raise AssertionError("shared projector admitted a str subclass")


def _assert_canonical_projection(exc: Exception) -> None:
    error = custody._error(
        Path("patches/try-forever-diagnostic-projection.patch"),
        "patch",
        exc,
    )
    boundary = error.boundary
    assert len(boundary) <= MAX_BOUNDARY_CODEPOINTS
    assert all(ord(ch) < 128 for ch in boundary)
    assert "\n" not in boundary
    assert "\r" not in boundary
    assert "\u202e" not in boundary.lower()
    assert "\ud800" not in boundary.lower()


def _assert_exception_str_callback_never_executes() -> None:
    class HostileError(Exception):
        callback_executed = False

        def __str__(self) -> str:
            type(self).callback_executed = True
            raise AssertionError("caller-owned Exception.__str__ executed before projection")

    try:
        _assert_canonical_projection(HostileError("safe-base-args"))
    except AssertionError:
        pass
    assert HostileError.callback_executed is False, (
        "canonical discovery projection must not invoke caller-owned Exception.__str__"
    )


def _assert_oversize_source_collapses_before_whole_identity_digest() -> None:
    original = semantic._diagnostic_digest

    def forbidden_digest(_: str) -> str:
        raise AssertionError("whole-source diagnostic digest executed beyond source-work throat")

    semantic._diagnostic_digest = forbidden_digest
    try:
        projection = semantic.project_owner_surgery_diagnostic_text(
            "x" * (PROPOSED_DIAGNOSTIC_SOURCE_CODEPOINTS + 1)
        )
    finally:
        semantic._diagnostic_digest = original

    assert projection.isascii()
    assert len(projection) <= MAX_SEMANTIC_DIAGNOSTIC_SEGMENT_CHARS
    assert "source" in projection.lower()


def main() -> int:
    _assert_shared_projector_source_wired()
    _assert_canonical_projection(ValueError("line-one\nline-two"))
    _assert_canonical_projection(ValueError("bidi:\u202eattack"))
    _assert_canonical_projection(ValueError("surrogate:\ud800"))
    _assert_canonical_projection(ValueError("x" * 50_000))
    _assert_exception_str_callback_never_executes()
    _assert_oversize_source_collapses_before_whole_identity_digest()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
