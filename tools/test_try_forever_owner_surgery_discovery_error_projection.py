#!/usr/bin/env python3
"""Source fixture for owner-surgery discovery diagnostic projection custody.

SOURCE ONLY / UNEXECUTED. The shared semantic organ owns a finite 4,096-code-point diagnostic
source-work throat and callback-free exception projection, and canonical v10 now consumes that helper
inside ``_error(...)`` instead of executing caller-owned ``Exception.__str__``/``__repr__``. Canonical
path/artifact evidence remains exact. This fixture proves no regression execution, TESTED, runtime,
deployment, phone delivery, or P0 capability.
"""

from pathlib import Path

import try_forever_owner_surgery_custody_probe as custody
import try_forever_owner_surgery_semantic_parser as semantic
from try_forever_owner_surgery_semantic_parser import (
    MAX_SEMANTIC_DIAGNOSTIC_SEGMENT_CHARS,
    MAX_SEMANTIC_DIAGNOSTIC_SOURCE_CODEPOINTS,
    MAX_SEMANTIC_EXCEPTION_ARGS,
    OwnerSurgerySemanticError,
    project_owner_surgery_diagnostic_text,
    project_owner_surgery_exception_diagnostic,
    source_receipt as semantic_source_receipt,
)


MAX_BOUNDARY_CODEPOINTS = 320


def _assert_shared_projector_source_wired() -> None:
    receipt = semantic_source_receipt()
    assert receipt["boundedAsciiDiagnosticProjection"] is True
    assert receipt["publicDiagnosticProjection"] is True
    assert receipt["diagnosticSegmentCharCeiling"] == MAX_SEMANTIC_DIAGNOSTIC_SEGMENT_CHARS
    assert receipt["diagnosticSourceCodepointCeiling"] == MAX_SEMANTIC_DIAGNOSTIC_SOURCE_CODEPOINTS
    assert receipt["finiteDiagnosticSourceWork"] is True
    assert receipt["callbackFreeExceptionDiagnosticProjection"] is True
    assert receipt["exceptionDiagnosticArgCeiling"] == MAX_SEMANTIC_EXCEPTION_ARGS
    assert receipt["oversizeDiagnosticWholeIdentityPreserved"] is False
    assert receipt["regressionExecuted"] is False
    assert receipt["tested"] is False

    assert project_owner_surgery_diagnostic_text("line-one\nline-two") == "line-one\\nline-two"
    assert project_owner_surgery_diagnostic_text("bidi:\u202eattack").isascii()
    assert project_owner_surgery_diagnostic_text("surrogate:\ud800").isascii()
    long_projection = project_owner_surgery_diagnostic_text("x" * 50_000)
    assert long_projection == "<text-over-source-ceiling:50000cp>"
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


def _assert_shared_exception_projector_is_callback_free() -> None:
    class HostileError(Exception):
        callback_executed = False

        def __str__(self) -> str:
            type(self).callback_executed = True
            raise AssertionError("shared exception projector executed caller-owned __str__")

        def __repr__(self) -> str:
            type(self).callback_executed = True
            raise AssertionError("shared exception projector executed caller-owned __repr__")

    kind, message = project_owner_surgery_exception_diagnostic(
        HostileError("line-one\nline-two")
    )
    assert kind == "HostileError"
    assert message == "line-one\\nline-two"
    assert HostileError.callback_executed is False

    class HostilePayload:
        callback_executed = False

        def __str__(self) -> str:
            type(self).callback_executed = True
            raise AssertionError("exception payload __str__ executed")

        def __repr__(self) -> str:
            type(self).callback_executed = True
            raise AssertionError("exception payload __repr__ executed")

    kind, message = project_owner_surgery_exception_diagnostic(
        HostileError(HostilePayload())
    )
    assert kind == "HostileError"
    assert message == "<exception-payload-omitted>"
    assert HostileError.callback_executed is False
    assert HostilePayload.callback_executed is False

    too_many = tuple(f"arg-{index}" for index in range(MAX_SEMANTIC_EXCEPTION_ARGS + 1))
    kind, message = project_owner_surgery_exception_diagnostic(HostileError(*too_many))
    assert kind == "HostileError"
    assert message == f"<exception-payload:{MAX_SEMANTIC_EXCEPTION_ARGS + 1}-args>"
    assert HostileError.callback_executed is False


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


def _assert_canonical_exception_callbacks_never_execute() -> None:
    class HostileError(Exception):
        callback_executed = False

        def __str__(self) -> str:
            type(self).callback_executed = True
            raise AssertionError("canonical discovery executed caller-owned Exception.__str__")

        def __repr__(self) -> str:
            type(self).callback_executed = True
            raise AssertionError("canonical discovery executed caller-owned Exception.__repr__")

    _assert_canonical_projection(HostileError("safe-base-args"))
    assert HostileError.callback_executed is False


def _assert_oversize_source_collapses_before_whole_identity_digest() -> None:
    original = semantic._diagnostic_digest

    def forbidden_digest(_: str) -> str:
        raise AssertionError("whole-source diagnostic digest executed beyond source-work throat")

    semantic._diagnostic_digest = forbidden_digest
    try:
        projection = semantic.project_owner_surgery_diagnostic_text(
            "x" * (MAX_SEMANTIC_DIAGNOSTIC_SOURCE_CODEPOINTS + 1)
        )
    finally:
        semantic._diagnostic_digest = original

    assert projection == (
        f"<text-over-source-ceiling:{MAX_SEMANTIC_DIAGNOSTIC_SOURCE_CODEPOINTS + 1}cp>"
    )
    assert projection.isascii()
    assert len(projection) <= MAX_SEMANTIC_DIAGNOSTIC_SEGMENT_CHARS


def main() -> int:
    _assert_shared_projector_source_wired()
    _assert_shared_exception_projector_is_callback_free()
    _assert_canonical_projection(ValueError("line-one\nline-two"))
    _assert_canonical_projection(ValueError("bidi:\u202eattack"))
    _assert_canonical_projection(ValueError("surrogate:\ud800"))
    _assert_canonical_projection(ValueError("x" * 50_000))
    _assert_canonical_exception_callbacks_never_execute()
    _assert_oversize_source_collapses_before_whole_identity_digest()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
