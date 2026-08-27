#!/usr/bin/env python3
"""Source fixture for canonical owner-surgery discovery diagnostic projection convergence.

SOURCE ONLY / UNEXECUTED. The shared semantic diagnostic projector and canonical v10 consumer are
SOURCE_WIRED. Canonical path/artifact evidence remains exact; only human-facing exception type and
message text cross the bounded ASCII-safe projector. This fixture proves no regression execution,
TESTED, runtime, deployment, phone delivery, or P0 capability.
"""

from pathlib import Path

import try_forever_owner_surgery_custody_probe as custody
from try_forever_owner_surgery_semantic_parser import (
    MAX_SEMANTIC_DIAGNOSTIC_SEGMENT_CHARS,
    OwnerSurgerySemanticError,
    project_owner_surgery_diagnostic_text,
    source_receipt as semantic_source_receipt,
)


MAX_BOUNDARY_CODEPOINTS = 320


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


def main() -> int:
    _assert_shared_projector_source_wired()

    capability = custody.classify(Path("patches"))["capability"]
    assert capability["boundedAsciiDiscoveryDiagnosticProjection"] is True
    assert capability["regressionExecuted"] is False
    assert capability["tested"] is False

    _assert_canonical_projection(ValueError("line-one\nline-two"))
    _assert_canonical_projection(ValueError("bidi:\u202eattack"))
    _assert_canonical_projection(ValueError("surrogate:\ud800"))
    _assert_canonical_projection(ValueError("x" * 50_000))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
