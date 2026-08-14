#!/usr/bin/env python3
"""Shared fail-closed classifier for phone-local nicotine tracker text."""
from __future__ import annotations

import re
import unicodedata


TRACKING_WORD = re.compile(r"\btrack(?:er|ing)?\b", re.IGNORECASE)
EVENT_KIND = re.compile(r"\b(?:hunger|tank|puffs?|exposure)\b", re.IGNORECASE)
LEADING_EVENT_KIND = re.compile(
    r"^(?:nicotine\s+)?(?:hunger|tank|puffs?|exposure)\b",
    re.IGNORECASE,
)


def _default_ignorable(codepoint: int) -> bool:
    return (
        codepoint == 0x034F
        or codepoint == 0x061C
        or 0x115F <= codepoint <= 0x1160
        or 0x17B4 <= codepoint <= 0x17B5
        or 0x180B <= codepoint <= 0x180F
        or 0x200B <= codepoint <= 0x200F
        or 0x202A <= codepoint <= 0x202E
        or 0x2060 <= codepoint <= 0x206F
        or codepoint == 0x3164
        or 0xFE00 <= codepoint <= 0xFE0F
        or codepoint == 0xFEFF
        or codepoint == 0xFFA0
        or 0x1BCA0 <= codepoint <= 0x1BCA3
        or 0x1D173 <= codepoint <= 0x1D17A
        or 0xE0000 <= codepoint <= 0xE0FFF
    )


def classification_text(value: str) -> str:
    """Compatibility-normalize only the private classification copy."""
    normalized = unicodedata.normalize("NFKD", str(value or ""))
    return "".join(
        character
        for character in normalized
        if unicodedata.category(character) not in {"Cf", "Mn", "Me"}
        and not _default_ignorable(ord(character))
    )


def is_local_tracker_like(value: str) -> bool:
    normalized = classification_text(value).strip()
    lowered = normalized.lower()
    if "/track" in lowered:
        return True
    if TRACKING_WORD.search(normalized) and EVENT_KIND.search(normalized):
        return True
    return bool(LEADING_EVENT_KIND.search(normalized))
