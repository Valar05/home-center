#!/usr/bin/env python3
"""Exact timestamp admission for TRY FOREVER generated-index provenance.

The current provenance owner broad-strips string timestamps before parsing. That
can erase edge control/whitespace evidence and allow metadata that is not exact
canonical text to participate in a VERIFIED_CURRENT verdict. This pure policy
keeps the existing numeric seconds/milliseconds convention and naive-as-UTC
compatibility while rejecting normalization-dependent string input.

It owns no JSON I/O, repository authority, renderer, phone surface, P0 lane,
deployment, or acceptance path.
"""

from __future__ import annotations

import math
import unicodedata
from datetime import datetime, timezone
from typing import Any

from try_forever_skill_title_fallback_policy import BIDI_DIRECTION_CONTROLS


class GeneratedIndexTimestampError(ValueError):
    """Generated-index timestamp metadata cannot enter provenance semantics."""


def parse_generated_index_timestamp(value: Any) -> datetime:
    """Parse one exact timestamp value without broad-whitespace laundering."""

    if type(value) in (int, float):
        raw = float(value)
        if not math.isfinite(raw):
            raise GeneratedIndexTimestampError("timestamp number must be finite")
        if raw > 10_000_000_000:
            raw /= 1000.0
        try:
            return datetime.fromtimestamp(raw, tz=timezone.utc)
        except (OverflowError, OSError, ValueError) as error:
            raise GeneratedIndexTimestampError("timestamp number is out of range") from error

    if not isinstance(value, str) or not value:
        raise GeneratedIndexTimestampError("timestamp must be non-empty text or a finite number")
    if value != value.strip():
        raise GeneratedIndexTimestampError(
            "timestamp text must not depend on leading/trailing whitespace normalization"
        )
    for character in value:
        if unicodedata.category(character) == "Cc":
            raise GeneratedIndexTimestampError("timestamp text contains a control character")
        if character in BIDI_DIRECTION_CONTROLS:
            raise GeneratedIndexTimestampError(
                "timestamp text contains an explicit bidi-direction control"
            )

    text = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as error:
        raise GeneratedIndexTimestampError("timestamp text is not ISO-8601 compatible") from error
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


__all__ = ["GeneratedIndexTimestampError", "parse_generated_index_timestamp"]
