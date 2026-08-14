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


def without_format_controls(value: str) -> str:
    """Remove Unicode format controls only for classification, never persistence."""
    return "".join(
        character
        for character in str(value or "")
        if unicodedata.category(character) != "Cf"
    )


def is_local_tracker_like(value: str) -> bool:
    normalized = without_format_controls(value).strip()
    lowered = normalized.lower()
    if "/track" in lowered:
        return True
    if TRACKING_WORD.search(normalized) and EVENT_KIND.search(normalized):
        return True
    return bool(LEADING_EVENT_KIND.search(normalized))
