#!/usr/bin/env python3
"""Pure source-title admission for TRY FOREVER repository skill discovery.

A fallback filesystem name exposed a broader authority seam: H1 text and folder
fallback ultimately feed the same human-facing ``SkillRecord.title`` field, so
they must not have different semantic safety rules. This helper supplies one
exact admission contract while allowing the existing owner to keep its byte/
line/scan resource throats.

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
    """Compatibility base class for a skill title that cannot enter authority."""


class SkillFallbackTitleResourceLimitError(SkillFallbackTitleError):
    """Skill title exceeds the owner's declared source-title resource budget."""


class SkillFallbackTitleSemanticError(SkillFallbackTitleError):
    """Skill title contains control state unsafe for canonical human presentation."""


def admit_skill_title(value: str, *, max_chars: int) -> str:
    """Admit one exact H1/fallback title or reject without rewrite/truncation.

    ``max_chars`` is supplied by the existing owner so this helper does not grow
    an independent source-bound constant. The returned text is exact source text;
    later human-facing projection may apply separate grapheme-safe display bounds.
    """

    if max_chars < 0:
        raise ValueError("skill title character budget must be non-negative")
    if not isinstance(value, str) or not value:
        raise SkillFallbackTitleSemanticError("skill title must be non-empty text")
    if len(value) > max_chars:
        raise SkillFallbackTitleResourceLimitError(
            f"skill title exceeds source title character budget {max_chars}"
        )

    for char in value:
        if unicodedata.category(char) == "Cc":
            raise SkillFallbackTitleSemanticError(
                "skill title contains a control character"
            )
        if char in BIDI_DIRECTION_CONTROLS:
            raise SkillFallbackTitleSemanticError(
                "skill title contains an explicit bidi-direction control"
            )
    return value


def admit_fallback_title(value: str, *, max_chars: int) -> str:
    """Compatibility name for callers repairing the original fallback seam."""

    return admit_skill_title(value, max_chars=max_chars)


__all__ = [
    "BIDI_DIRECTION_CONTROLS",
    "SkillFallbackTitleError",
    "SkillFallbackTitleResourceLimitError",
    "SkillFallbackTitleSemanticError",
    "admit_fallback_title",
    "admit_skill_title",
]
