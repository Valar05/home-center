#!/usr/bin/env python3
"""Strict JSON admission for TRY FOREVER generated-index evidence.

Python's default ``json.loads`` accepts repeated object names by keeping the last
value and also accepts NaN/Infinity extensions. Neither behavior is acceptable
for provenance metadata because a parser convenience must not become an
implicit last-wins authority channel.

This module is a supporting policy organ now consumed by the sole provenance
owner, ``try_forever_skill_provenance_probe.py``. It owns no filesystem I/O,
repository traversal, report serializer, runtime UI, phone surface, P0 recovery,
or separate provenance authority. Source composition does not itself prove
regression execution, TESTED state, runtime behavior, deployment, or delivery.
"""

from __future__ import annotations

import json
import math
from typing import Any

MAX_JSON_NUMBER_TOKEN_CHARS = 128


class GeneratedIndexJsonError(ValueError):
    """Base class for generated-index JSON admission failures."""


class GeneratedIndexJsonDuplicateMemberError(GeneratedIndexJsonError):
    """A JSON object repeated one member name."""


class GeneratedIndexJsonNumberError(GeneratedIndexJsonError):
    """A numeric token is non-standard, non-finite, or exceeds the token budget."""


class GeneratedIndexJsonSyntaxError(GeneratedIndexJsonError):
    """The JSON document cannot be decoded inside the declared grammar contract."""


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise GeneratedIndexJsonDuplicateMemberError(
                "generated index JSON repeats an object member name; last-wins and first-wins authority are forbidden"
            )
        out[key] = value
    return out


def _bounded_number_token(token: str, *, kind: str) -> str:
    if len(token) > MAX_JSON_NUMBER_TOKEN_CHARS:
        raise GeneratedIndexJsonNumberError(
            f"generated index JSON {kind} token exceeds declared character budget {MAX_JSON_NUMBER_TOKEN_CHARS}"
        )
    return token


def _parse_int(token: str) -> int:
    bounded = _bounded_number_token(token, kind="integer")
    try:
        return int(bounded)
    except ValueError as error:
        raise GeneratedIndexJsonNumberError(
            "generated index JSON integer token could not be admitted"
        ) from error


def _parse_float(token: str) -> float:
    bounded = _bounded_number_token(token, kind="floating-point")
    try:
        value = float(bounded)
    except ValueError as error:
        raise GeneratedIndexJsonNumberError(
            "generated index JSON floating-point token could not be admitted"
        ) from error
    if not math.isfinite(value):
        raise GeneratedIndexJsonNumberError(
            "generated index JSON floating-point token must remain finite"
        )
    return value


def _reject_nonstandard_constant(token: str) -> None:
    raise GeneratedIndexJsonNumberError(
        f"generated index JSON non-standard numeric constant {token!r} is forbidden"
    )


def parse_generated_index_json(text: str) -> Any:
    """Decode one strict generated-index JSON document without authority aliases.

    Object member names are unique at every object depth. NaN/Infinity extensions
    are rejected. Numeric tokens are bounded before numeric conversion. Decoder
    syntax, recursion, and interpreter conversion-limit failures are converted to
    one typed fail-closed family rather than escaping the provenance owner.

    This function intentionally does not require the root to be an object; the
    existing provenance owner already owns that semantic root-shape decision.
    """

    if not isinstance(text, str):
        raise GeneratedIndexJsonSyntaxError(
            "generated index JSON admission requires already-decoded UTF-8 text"
        )

    try:
        return json.loads(
            text,
            object_pairs_hook=_unique_object,
            parse_int=_parse_int,
            parse_float=_parse_float,
            parse_constant=_reject_nonstandard_constant,
        )
    except GeneratedIndexJsonError:
        raise
    except (json.JSONDecodeError, RecursionError, ValueError) as error:
        raise GeneratedIndexJsonSyntaxError(
            "generated index JSON could not be decoded inside the strict admission contract"
        ) from error


__all__ = [
    "MAX_JSON_NUMBER_TOKEN_CHARS",
    "GeneratedIndexJsonError",
    "GeneratedIndexJsonDuplicateMemberError",
    "GeneratedIndexJsonNumberError",
    "GeneratedIndexJsonSyntaxError",
    "parse_generated_index_json",
]
