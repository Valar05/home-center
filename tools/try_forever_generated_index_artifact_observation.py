#!/usr/bin/env python3
"""Bounded exact-content observation for TRY FOREVER generated indexes.

The generated-index verdict and the final-emission custody check need to refer to
the exact same artifact bytes, not merely the same path. This helper admits only
an ordinary finite regular-file object, performs a bounded complete read, reaches
EOF before returning authority-facing SHA-256, and preserves strict UTF-8 text
for the semantic inspector.

It deliberately does not decide whether the index is current, trusted, or safe
to emit. It owns no provenance report, renderer, scheduler, phone surface, or
P0 recovery lane.
"""

from __future__ import annotations

import hashlib
import os
import stat
from dataclasses import dataclass
from pathlib import Path

READ_CHUNK_BYTES = 64 * 1024


class GeneratedIndexArtifactResourceLimitError(ValueError):
    """The complete generated-index artifact exceeds its declared byte budget."""


class GeneratedIndexArtifactTopologyError(ValueError):
    """The generated-index path is not one ordinary finite regular file."""


@dataclass(frozen=True)
class GeneratedIndexArtifactObservation:
    size_bytes: int
    sha256: str
    utf8_text: str


def _require_preopen_regular_file(path: Path) -> None:
    """Reject redirectors and special files before authority-facing open/read.

    This is an admission gate, not atomic path binding. The later descriptor
    check verifies the object actually opened. Platforms exposing O_NONBLOCK and
    O_NOFOLLOW also receive those flags to prevent common FIFO/symlink races from
    turning the evidence lane into an indefinite special-file wait.
    """

    metadata = path.lstat()
    if not stat.S_ISREG(metadata.st_mode):
        raise GeneratedIndexArtifactTopologyError(
            "generated-index artifact must be an ordinary non-redirecting regular file"
        )


def _open_regular_file_descriptor(path: Path) -> int:
    _require_preopen_regular_file(path)

    flags = os.O_RDONLY
    flags |= getattr(os, "O_BINARY", 0)
    flags |= getattr(os, "O_NONBLOCK", 0)
    flags |= getattr(os, "O_NOFOLLOW", 0)

    descriptor = os.open(path, flags)
    try:
        opened = os.fstat(descriptor)
        if not stat.S_ISREG(opened.st_mode):
            raise GeneratedIndexArtifactTopologyError(
                "opened generated-index artifact is not an ordinary regular file"
            )
        return descriptor
    except BaseException:
        os.close(descriptor)
        raise


def observe_generated_index_artifact(
    path: Path,
    *,
    max_bytes: int,
) -> GeneratedIndexArtifactObservation:
    """Return exact complete artifact identity only after bounded EOF.

    ``max_bytes`` is supplied by the existing owner so this helper does not grow a
    second resource-budget authority. Max+1 rejects without returning a prefix
    digest. UTF-8 decoding is strict; semantic JSON parsing remains the owner's
    separate responsibility.

    Finite regular-file topology is checked before authority-facing content I/O
    and again on the opened descriptor. This closes special-file/FIFO admission;
    it does not claim a universal wall-clock deadline for arbitrary storage or
    atomic cross-filesystem path custody.
    """

    if max_bytes < 0:
        raise ValueError("generated-index artifact byte budget must be non-negative")

    digest = hashlib.sha256()
    payload = bytearray()
    total = 0
    descriptor = _open_regular_file_descriptor(path)

    try:
        with os.fdopen(descriptor, "rb", closefd=False) as handle:
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
    finally:
        os.close(descriptor)
