#!/usr/bin/env python3
"""Single-artifact content custody for TRY FOREVER repository skills.

The current provenance owner separately opens one admitted ``SKILL.md`` for title
extraction and again for whole-file SHA. Portable path identity revalidation can
detect persistent replacement around those reads, but it cannot prove that the
title and digest came from one immutable opened object when a swap-and-restore
occurs entirely between observations.

This supporting helper deliberately composes the repository's already-hardened
finite regular-file observation organ instead of growing a second no-follow/
reparse/descriptor-custody implementation. It observes one complete bounded UTF-8
artifact once, derives both title and SHA from that same observation, and owns no
repository discovery, authority certification, renderer, phone surface, P0 lane,
deployment, or acceptance path.
"""

from __future__ import annotations

import io
from dataclasses import dataclass
from pathlib import Path

from try_forever_generated_index_artifact_observation import (
    GeneratedIndexArtifactChangedError,
    GeneratedIndexArtifactResourceLimitError,
    GeneratedIndexArtifactTopologyError,
    observe_generated_index_artifact,
)
from try_forever_skill_title_fallback_policy import (
    SkillFallbackTitleError,
    admit_markdown_h1_title,
    admit_skill_title,
)


class SkillContentCustodyError(ValueError):
    """Base class for a SKILL.md content observation that cannot earn authority."""


class SkillContentCustodyResourceLimitError(SkillContentCustodyError):
    """The complete SKILL.md cannot be observed inside the declared byte budget."""


class SkillContentCustodyTopologyError(SkillContentCustodyError):
    """The named SKILL.md is not one ordinary stable finite file object."""


class SkillContentCustodyChangedError(SkillContentCustodyError):
    """The named/opened SKILL.md object changed during the single observation."""


class SkillContentCustodyTextError(SkillContentCustodyError):
    """The complete SKILL.md is not strict UTF-8 text."""


class SkillContentCustodyTitleResourceLimitError(SkillContentCustodyError):
    """The title cannot be resolved inside the owner's declared title budgets."""


@dataclass(frozen=True)
class SkillContentObservation:
    size_bytes: int
    sha256: str
    title: str


def _title_from_observed_text(
    utf8_text: str,
    *,
    fallback_title: str,
    max_scan_bytes: int,
    max_line_bytes: int,
    max_title_chars: int,
) -> str:
    """Derive title from already-observed bytes without reopening the path."""

    if min(max_scan_bytes, max_line_bytes, max_title_chars) < 0:
        raise ValueError("skill title budgets must be non-negative")

    raw = utf8_text.encode("utf-8")
    scanned_bytes = 0
    with io.BytesIO(raw) as handle:
        while scanned_bytes < max_scan_bytes:
            remaining_scan = max_scan_bytes - scanned_bytes
            read_limit = min(max_line_bytes, remaining_scan)
            raw_line = handle.readline(read_limit + 1)
            if not raw_line:
                return admit_skill_title(fallback_title, max_chars=max_title_chars)

            scanned_bytes += len(raw_line)
            if len(raw_line) > read_limit:
                raise SkillContentCustodyTitleResourceLimitError(
                    "skill title scan exceeded its byte/line budget"
                )

            title = admit_markdown_h1_title(
                raw_line.decode("utf-8"),
                max_chars=max_title_chars,
            )
            if title is not None:
                return title

        if handle.read(1):
            raise SkillContentCustodyTitleResourceLimitError(
                "skill title was not resolved within the scan budget"
            )
    return admit_skill_title(fallback_title, max_chars=max_title_chars)


def observe_skill_content(
    path: Path,
    *,
    max_bytes: int,
    max_title_scan_bytes: int,
    max_title_line_bytes: int,
    max_title_chars: int,
) -> SkillContentObservation:
    """Return one title/SHA pair derived from one bounded stable opened artifact.

    The finite artifact organ already enforces no-follow/reparse topology,
    path-to-descriptor identity, complete bounded EOF, descriptor stability, named
    path revalidation, and strict UTF-8. This wrapper translates those failure
    classes into skill-content language and derives title entirely from the returned
    observed text. There is no second ``Path.open`` between title and digest.

    This is supporting source only until the sole provenance owner consumes it.
    """

    try:
        artifact = observe_generated_index_artifact(path, max_bytes=max_bytes)
    except GeneratedIndexArtifactResourceLimitError as error:
        raise SkillContentCustodyResourceLimitError(
            "SKILL.md exceeds the declared complete-content byte budget"
        ) from error
    except GeneratedIndexArtifactTopologyError as error:
        raise SkillContentCustodyTopologyError(
            "SKILL.md failed finite regular-file topology admission"
        ) from error
    except GeneratedIndexArtifactChangedError as error:
        raise SkillContentCustodyChangedError(
            "SKILL.md changed during the single bounded content observation"
        ) from error
    except UnicodeDecodeError as error:
        raise SkillContentCustodyTextError(
            "SKILL.md must be strict UTF-8 across the complete observed artifact"
        ) from error

    try:
        title = _title_from_observed_text(
            artifact.utf8_text,
            fallback_title=path.parent.name,
            max_scan_bytes=max_title_scan_bytes,
            max_line_bytes=max_title_line_bytes,
            max_title_chars=max_title_chars,
        )
    except SkillFallbackTitleError:
        raise

    return SkillContentObservation(
        size_bytes=artifact.size_bytes,
        sha256=artifact.sha256,
        title=title,
    )


__all__ = [
    "SkillContentCustodyChangedError",
    "SkillContentCustodyError",
    "SkillContentCustodyResourceLimitError",
    "SkillContentCustodyTextError",
    "SkillContentCustodyTitleResourceLimitError",
    "SkillContentCustodyTopologyError",
    "SkillContentObservation",
    "observe_skill_content",
]
