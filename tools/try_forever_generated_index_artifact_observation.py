#!/usr/bin/env python3
"""Bounded exact-content observation for TRY FOREVER generated indexes.

The generated-index verdict and the final-emission custody check need to refer to
the exact same artifact bytes, not merely the same path.  This helper performs a
bounded complete read, reaches EOF before returning authority-facing SHA-256,
and preserves strict UTF-8 text for the semantic inspector.

It deliberately does not decide whether the index is current, trusted, or safe
to emit.  It owns no provenance report, renderer, scheduler, phone surface, or
P0 recovery lane.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

READ_CHUNK_BYTES = 64 * 1024


class GeneratedIndexArtifactResourceLimitError(ValueError):
    """The complete generated-index artifact exceeds its declared byte budget."""


@dataclass(frozen=True)
class GeneratedIndexArtifactObservation:
    size_bytes: int
    sha256: str
    utf8_text: str


def observe_generated_index_artifact(
    path: Path,
    *,
    max_bytes: int,
) -> GeneratedIndexArtifactObservation:
    """Return exact complete artifact identity only after bounded EOF.

    ``max_bytes`` is supplied by the existing owner so this helper does not grow a
    second resource-budget authority.  Max+1 rejects without returning a prefix
    digest.  UTF-8 decoding is strict; semantic JSON parsing remains the owner's
    separate responsibility.
    """

    if max_bytes < 0:
        raise ValueError("generated-index artifact byte budget must be non-negative")

    digest = hashlib.sha256()
    payload = bytearray()
    total = 0

    with path.open("rb") as handle:
        while True:
            remaining = max_bytes - total
            read_size = min(READ_CHUNK_BYTES, remaining + 1)
            chunk = handle.read(read_size)
            if not chunk:
                raw = bytes(payload)
                return GeneratedIndexArtifactObservation(
                    size_bytes=total,
                    sha256=digest.hexdigest(),
                    utf8_text=raw.decode("utf-8"),
                )

            total += len(chunk)
            if total > max_bytes:
                raise GeneratedIndexArtifactResourceLimitError(
                    f"generated index exceeds byte budget {max_bytes}"
                )
            digest.update(chunk)
            payload.extend(chunk)
