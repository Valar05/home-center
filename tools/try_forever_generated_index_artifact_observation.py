#!/usr/bin/env python3
"""Bounded exact-content observation for TRY FOREVER generated indexes.

The generated-index verdict and the final-emission custody check need to refer to
the exact same artifact bytes, not merely the same path. This helper admits only
an ordinary finite regular-file object, binds the pre-open path observation to
the opened descriptor, performs a bounded complete read, reaches EOF before
returning authority-facing SHA-256, and preserves strict UTF-8 text for the
semantic inspector.

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


class GeneratedIndexArtifactChangedError(ValueError):
    """The generated-index object changed while one observation was in progress."""


@dataclass(frozen=True)
class GeneratedIndexArtifactObservation:
    size_bytes: int
    sha256: str
    utf8_text: str


def _mtime_ns(metadata: os.stat_result) -> int:
    return int(
        getattr(
            metadata,
            "st_mtime_ns",
            int(metadata.st_mtime * 1_000_000_000),
        )
    )


def _require_regular_identity(metadata: os.stat_result, *, phase: str) -> None:
    if not stat.S_ISREG(metadata.st_mode):
        raise GeneratedIndexArtifactTopologyError(
            f"generated-index artifact must be an ordinary regular file at {phase}"
        )
    if int(metadata.st_ino) == 0:
        raise GeneratedIndexArtifactTopologyError(
            "generated-index inode/file-index identity is unavailable; exact path-to-descriptor custody cannot be certified"
        )


def _same_object(left: os.stat_result, right: os.stat_result) -> bool:
    return (int(left.st_dev), int(left.st_ino)) == (
        int(right.st_dev),
        int(right.st_ino),
    )


def _same_observation(left: os.stat_result, right: os.stat_result) -> bool:
    return _same_object(left, right) and (
        int(left.st_size),
        _mtime_ns(left),
    ) == (
        int(right.st_size),
        _mtime_ns(right),
    )


def _require_preopen_regular_file(path: Path) -> os.stat_result:
    """Reject redirectors and special files before authority-facing open/read.

    This is an admission gate, not atomic path binding. The opened descriptor is
    separately compared with this no-follow observation. Platforms exposing
    O_NONBLOCK and O_NOFOLLOW also receive those flags so common FIFO/symlink
    races cannot turn the evidence lane into an indefinite special-file wait.
    """

    metadata = path.lstat()
    _require_regular_identity(metadata, phase="pre-open observation")
    return metadata


def _open_regular_file_descriptor(path: Path) -> tuple[int, os.stat_result]:
    preopen = _require_preopen_regular_file(path)

    flags = os.O_RDONLY
    flags |= getattr(os, "O_BINARY", 0)
    flags |= getattr(os, "O_NONBLOCK", 0)
    flags |= getattr(os, "O_NOFOLLOW", 0)

    descriptor = os.open(path, flags)
    try:
        opened = os.fstat(descriptor)
        _require_regular_identity(opened, phase="opened descriptor")
        if not _same_object(preopen, opened):
            raise GeneratedIndexArtifactChangedError(
                "generated-index path identity changed between no-follow admission and descriptor open"
            )
        return descriptor, opened
    except BaseException:
        os.close(descriptor)
        raise


def observe_generated_index_artifact(
    path: Path,
    *,
    max_bytes: int,
) -> GeneratedIndexArtifactObservation:
    """Return exact complete artifact identity only after bounded stable EOF.

    ``max_bytes`` is supplied by the existing owner so this helper does not grow a
    second resource-budget authority. Max+1 rejects without returning a prefix
    digest. UTF-8 decoding is strict; semantic JSON parsing remains the owner's
    separate responsibility.

    Finite regular-file topology is checked before authority-facing content I/O,
    again on the opened descriptor, and again after the complete read. The
    pre-open path identity must match the descriptor, and descriptor size/mtime
    identity must remain stable across the read. These checks detect common
    replacement and in-place mutation races; they deliberately do not claim a
    universal atomic filesystem snapshot or prove away swap-and-restore/identity
    reuse that evades both observations.
    """

    if max_bytes < 0:
        raise ValueError("generated-index artifact byte budget must be non-negative")

    digest = hashlib.sha256()
    payload = bytearray()
    total = 0
    descriptor, opened_before = _open_regular_file_descriptor(path)

    try:
        with os.fdopen(descriptor, "rb", closefd=False) as handle:
            while True:
                remaining = max_bytes - total
                read_size = min(READ_CHUNK_BYTES, remaining + 1)
                chunk = handle.read(read_size)
                if not chunk:
                    opened_after = os.fstat(descriptor)
                    _require_regular_identity(opened_after, phase="post-read descriptor")
                    if not _same_observation(opened_before, opened_after):
                        raise GeneratedIndexArtifactChangedError(
                            "generated-index descriptor identity/size/mtime changed during complete read"
                        )
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
