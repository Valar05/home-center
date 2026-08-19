#!/usr/bin/env python3
"""Portable display projection for TRY FOREVER provenance report paths.

This module is evidence-presentation policy only. It MUST NOT decide filesystem
access, repository containment, provenance authority, generated-index trust, or
runtime capability. Callers keep the exact Path or repository-relative identity
for I/O/authority and use this projection only when serializing operator-facing
report metadata.
"""

from __future__ import annotations

import hashlib
import os
import unicodedata
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

MAX_REPORT_PATH_CHARS = 256
MIN_REPORT_PATH_CHARS = 32


@dataclass(frozen=True)
class ReportPathProjection:
    display_path: str
    scope: str


def _fingerprint(text: str) -> str:
    """Bound already-allowed repository-relative text; never fingerprint host paths."""

    return hashlib.sha256(text.encode("utf-8", errors="surrogatepass")).hexdigest()


def _absolute_lexical(path: Path) -> Path:
    """Normalize spelling without using path existence as report authority."""

    return Path(os.path.abspath(os.fspath(path)))


def _validate_budget(max_chars: int) -> None:
    if max_chars < MIN_REPORT_PATH_CHARS:
        raise ValueError(
            f"report path budget must be at least {MIN_REPORT_PATH_CHARS} characters"
        )


def _display_unit(character: str) -> str:
    """Reveal non-printing semantic path text without rewriting source identity.

    Repository paths may legally contain controls or Unicode format characters on
    some filesystems. Durable operator/TalkBack evidence must not emit those
    characters raw. Backslash is escaped first so a literal source spelling such
    as ``\\u{202E}`` cannot collide with the projection of an actual U+202E.
    """

    if character == "\\":
        return "\\\\"
    category = unicodedata.category(character)
    if category in {"Cc", "Cf", "Cs"}:
        return f"\\u{{{ord(character):04X}}}"
    return character


def _bounded_relative(relative: str, *, max_chars: int) -> str:
    _validate_budget(max_chars)
    units = tuple(_display_unit(character) for character in relative)
    projected = "".join(units)
    if len(projected) <= max_chars:
        return projected

    suffix = f"...#{_fingerprint(relative)[:16]}"
    available = max_chars - len(suffix)
    prefix_units: list[str] = []
    used = 0
    for unit in units:
        if used + len(unit) > available:
            break
        prefix_units.append(unit)
        used += len(unit)
    return "".join(prefix_units) + suffix


def project_repository_relative_report_path(
    relative: str,
    *,
    max_chars: int = MAX_REPORT_PATH_CHARS,
) -> ReportPathProjection:
    """Project already-authorized repository-relative text for durable display.

    This function exists for report records whose repository-relative identity was
    established earlier by the owning provenance code. It performs no filesystem
    lookup and therefore cannot turn display projection back into authorization.
    Absolute paths and parent traversal are rejected so callers cannot accidentally
    launder host topology through the repository-relative channel.
    """

    _validate_budget(max_chars)
    if not isinstance(relative, str) or not relative:
        raise ValueError("repository-relative report path must be a non-empty string")

    lexical = PurePosixPath(relative)
    if lexical.is_absolute() or any(part == ".." for part in lexical.parts):
        raise ValueError("repository-relative report path cannot be absolute or traverse parents")

    normalized = "." if relative == "." else relative
    return ReportPathProjection(
        display_path=_bounded_relative(normalized, max_chars=max_chars),
        scope="REPOSITORY",
    )


def project_report_path(
    repo_root: Path,
    path: Path | None,
    *,
    max_chars: int = MAX_REPORT_PATH_CHARS,
) -> ReportPathProjection:
    """Project one path without leaking host-local absolute topology.

    Repository-local paths become bounded POSIX paths relative to the repository
    root. Control/format/surrogate characters are made explicit in the display
    projection while the caller retains the exact Path for I/O and authority.
    The repository root itself becomes ``.``. External paths become the constant
    marker ``<external-path>``: durable reports do not preserve a hash oracle over
    usernames, home directories, drive roots, mount points, or temp layouts.

    This is display projection only. It never changes the exact Path retained by
    the caller for I/O or provenance checks.
    """

    _validate_budget(max_chars)
    if path is None:
        return ReportPathProjection(display_path="", scope="NONE")

    repo = _absolute_lexical(repo_root)
    candidate = _absolute_lexical(path)

    try:
        relative_path = candidate.relative_to(repo)
    except ValueError:
        return ReportPathProjection(display_path="<external-path>", scope="EXTERNAL")

    relative = relative_path.as_posix()
    if relative in ("", "."):
        relative = "."
    return project_repository_relative_report_path(relative, max_chars=max_chars)
