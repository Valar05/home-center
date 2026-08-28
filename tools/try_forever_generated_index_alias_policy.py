#!/usr/bin/env python3
"""Pure alias-contract policy for generated skill-index evidence.

Generated indexes remain discovery aids. This helper owns no repository
traversal, JSON I/O, renderer, scheduler, phone surface, or P0 lane. It only
prevents multiple supported field aliases from becoming a silent first-wins
provenance channel and bounds scalar text before operator/report projection.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Iterable

MAX_GENERATED_INDEX_SCALAR_TEXT_CHARS = 256


class GeneratedIndexAliasError(ValueError):
    """Base class for generated-index alias contract failures."""


class GeneratedIndexAliasConflictError(GeneratedIndexAliasError):
    """Two supported aliases declare different typed values."""


class GeneratedIndexAliasTypeError(GeneratedIndexAliasError):
    """A supported alias uses a value shape that the field does not admit."""


class GeneratedIndexAliasResourceLimitError(GeneratedIndexAliasError):
    """A scalar alias value exceeds the operator/report resource budget."""


@dataclass(frozen=True)
class ResolvedAlias:
    field: str
    present_keys: tuple[str, ...]
    value: Any


def _typed_equal(left: Any, right: Any) -> bool:
    return type(left) is type(right) and left == right


def resolve_consistent_alias(
    data: dict[str, Any],
    keys: Iterable[str],
    *,
    field: str,
    allowed_types: tuple[type, ...],
    max_string_chars: int = MAX_GENERATED_INDEX_SCALAR_TEXT_CHARS,
) -> ResolvedAlias:
    """Resolve one alias family without allowing first-wins ambiguity."""

    present = tuple(key for key in keys if key in data)
    if not present:
        return ResolvedAlias(field=field, present_keys=(), value=None)

    values = tuple(data[key] for key in present)
    for value in values:
        # bool is an int subclass; typed membership keeps it out unless bool is
        # explicitly listed by the caller.
        if type(value) not in allowed_types:
            raise GeneratedIndexAliasTypeError(
                f"generated index field {field} has unsupported scalar type"
            )
        if isinstance(value, str) and len(value) > max_string_chars:
            raise GeneratedIndexAliasResourceLimitError(
                f"generated index field {field} exceeds scalar text budget {max_string_chars}"
            )
        if isinstance(value, float) and not math.isfinite(value):
            raise GeneratedIndexAliasTypeError(
                f"generated index field {field} must use a finite number"
            )

    first = values[0]
    if any(not _typed_equal(first, value) for value in values[1:]):
        raise GeneratedIndexAliasConflictError(
            f"generated index field {field} has conflicting supported aliases"
        )
    return ResolvedAlias(field=field, present_keys=present, value=first)
