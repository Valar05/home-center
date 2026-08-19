#!/usr/bin/env python3
"""Portable display projection for TRY FOREVER provenance report paths.

This module is evidence-presentation policy only.  It MUST NOT decide filesystem
access, repository containment, provenance authority, generated-index trust, or
runtime capability.  Callers keep the exact Path object for I/O and use this
projection only when serializing operator-facing report metadata.
"""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from pathlib import Path

MAX_REPORT_PATH_CHARS = 256


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


def _bounded_relative(relative: str, *, max_chars: int) -> str:
    if max_chars <= 0:
        raise ValueError("report path budget must be positive")
    if len(relative) <= max_chars:
        return relative

    suffix = f"...#{_fingerprint(relative)[:16]}"
    if len(suffix) >= max_chars:
        return suffix[:max_chars]
    return relative[: max_chars - len(suffix)] + suffix


def project_report_path(
    repo_root: Path,
    path: Path | None,
    *,
    max_chars: int = MAX_REPORT_PATH_CHARS,
) -> ReportPathProjection:
    """Project one path without leaking host-local absolute topology.

    Repository-local paths become bounded POSIX paths relative to the repository
    root.  The repository root itself becomes ``.``.  External paths become the
    constant marker ``<external-path>``: durable reports do not preserve a hash
    oracle over usernames, home directories, drive roots, mount points, or temp
    layouts merely to distinguish diagnostic files.

    This is display projection only.  It never changes the exact Path retained by
    the caller for I/O or provenance checks.
    """

    if max_chars <= 0:
        raise ValueError("report path budget must be positive")
    if path is None:
        return ReportPathProjection(display_path="", scope="NONE")

    repo = _absolute_lexical(repo_root)
    candidate = _absolute_lexical(path)

    try:
        relative_path = candidate.relative_to(repo)
    except ValueError:
        marker = "<external-path>"
        if len(marker) > max_chars:
            return ReportPathProjection(display_path=marker[:max_chars], scope="EXTERNAL")
        return ReportPathProjection(display_path=marker, scope="EXTERNAL")

    relative = relative_path.as_posix()
    if relative in ("", "."):
        relative = "."
    return ReportPathProjection(
        display_path=_bounded_relative(relative, max_chars=max_chars),
        scope="REPOSITORY",
    )
