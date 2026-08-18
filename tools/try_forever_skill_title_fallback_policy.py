#!/usr/bin/env python3
"""Pure fallback-title admission for TRY FOREVER repository skill discovery.

A missing H1 may legitimately fall back to the containing directory name, but a
filesystem name is still human-facing report/accessibility text. It must not
bypass the owner's declared title bound or smuggle terminal/control or bidi
formatting state into the title surface.

This policy intentionally does *not* ban ordinary Unicode format characters as a
class. ZWSP, ZWNJ, ZWJ, WORD JOINER and ordinary combining/emoji composition may
be legitimate text. Only Cc controls and explicit bidi-direction controls are
rejected here. The policy truncates nothing into authority.
"""

from __future__ import annotations

import unicodedata

BIDI_DIRECTION_CONTROLS = frozenset(
    {
        "\u061c",  # ARABIC LETTER MARK
        "\u200e",  # LEFT-TO-RIGHT MARK
        "\u200f",  # RIGHT-TO-LEFT MARK
        "\u202a",  # LEFT-TO-RIGHT EMBEDDING
        "\u202b",  # RIGHT-TO-LEFT EMBEDDING
        "\u202c",  # POP DIRECTIONAL FORMATTING
        "\u202d",  # LEFT-TO-RIGHT OVERRIDE
        "\u202e",  # RIGHT-TO-LEFT OVERRIDE
        "\u2066",  # LEFT-TO-RIGHT ISOLATE
        "\u2067",  # RIGHT-TO-LEFT ISOLATE
        "\u2068",  # FIRST STRONG ISOLATE
        "\u2069",  # POP DIRECTIONAL ISOLATE
    }
)


class SkillFallbackTitleError(ValueError):
    """A filesystem-derived fallback title cannot enter human-facing authority."""


class SkillFallbackTitleResourceLimitError(SkillFallbackTitleError):
    """Fallback title exceeds the same declared source-title resource budget."""


class SkillFallbackTitleSemanticError(SkillFallbackTitleError):
    """Fallback title contains control state unsafe for direct human presentation."""


def admit_fallback_title(value: str, *, max_chars: int) -> str:
    """Admit one exact fallback title or reject it without rewriting/truncating.

    ``max_chars`` is supplied by the existing owner so this helper does not grow
    an independent source-bound constant. The returned string is exact source
    text; human-facing projection may apply separate accessibility policies later.
    """

    if max_chars < 0:
        raise ValueError("fallback title character budget must be non-negative")
    if not isinstance(value, str) or not value:
        raise SkillFallbackTitleSemanticError("fallback title must be non-empty text")
    if len(value) > max_chars:
        raise SkillFallbackTitleResourceLimitError(
            f"fallback title exceeds source title character budget {max_chars}"
        )

    for char in value:
        if unicodedata.category(char) == "Cc":
            raise SkillFallbackTitleSemanticError(
                "fallback title contains a control character"
            )
        if char in BIDI_DIRECTION_CONTROLS:
            raise SkillFallbackTitleSemanticError(
                "fallback title contains an explicit bidi-direction control"
            )
    return value


__all__ = [
    "BIDI_DIRECTION_CONTROLS",
    "SkillFallbackTitleError",
    "SkillFallbackTitleResourceLimitError",
    "SkillFallbackTitleSemanticError",
    "admit_fallback_title",
]
