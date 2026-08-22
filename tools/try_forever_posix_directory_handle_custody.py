#!/usr/bin/env python3
"""Source-only POSIX held-directory custody for TRY FOREVER evidence artifacts.

This organ strengthens *root* custody when the local Python/OS surface exposes the required POSIX
primitives. It opens the named directory once with O_DIRECTORY|O_NOFOLLOW, keeps that descriptor as
the authority root, enumerates through the held descriptor, and opens candidate names relative to
that same descriptor.

It deliberately does not claim universal filesystem atomicity. A held root descriptor prevents a
later replacement of the root pathname from redirecting subsequent descriptor-relative work, but
candidate names may still be replaced between observations and filesystem identity reuse remains a
separate boundary. Regression execution, owner integration, runtime behavior, deployment, phone
execution, delivery, and acceptance are all separate capability states.
"""

from __future__ import annotations

import hashlib
import os
import stat
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable

from try_forever_directory_handle_binding_capability import (
    current_directory_handle_binding_capability,
)


READ_CHUNK_BYTES = 64 * 1024


class PosixDirectoryHandleCustodyUnavailable(RuntimeError):
    """The current runtime cannot safely support this descriptor-bound source path."""


class DescriptorArtifactCustodyError(ValueError):
    """A descriptor-relative candidate could not earn artifact authority."""


@dataclass(frozen=True)
class DescriptorIdentity:
    device: int
    inode: int
    size: int
    mtime_ns: int


@dataclass(frozen=True)
class DescriptorArtifactObservation:
    name: str
    utf8_text: str
    byte_count: int
    sha256: str
    identity: DescriptorIdentity

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _identity_from_stat(result: os.stat_result) -> DescriptorIdentity:
    return DescriptorIdentity(
        device=int(result.st_dev),
        inode=int(result.st_ino),
        size=int(result.st_size),
        mtime_ns=int(result.st_mtime_ns),
    )


def _same_identity(left: DescriptorIdentity, right: DescriptorIdentity) -> bool:
    return left == right


def _require_simple_name(name: str) -> str:
    if not isinstance(name, str) or not name or name in {".", ".."}:
        raise DescriptorArtifactCustodyError("candidate name must be one non-empty basename")
    if "\x00" in name or "/" in name or (os.altsep and os.altsep in name):
        raise DescriptorArtifactCustodyError("candidate name must not contain path traversal syntax")
    return name


class HeldDirectoryCustody:
    """One held POSIX directory descriptor and bounded descriptor-relative operations."""

    def __init__(self, path: Path | str):
        capability = current_directory_handle_binding_capability()
        if capability.status != "SUPPORTED_POSIX_PRIMITIVES":
            raise PosixDirectoryHandleCustodyUnavailable(capability.boundary)

        flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
        if hasattr(os, "O_CLOEXEC"):
            flags |= os.O_CLOEXEC
        self.path = Path(path)
        self.fd = os.open(os.fspath(self.path), flags)
        try:
            opened = os.fstat(self.fd)
            if not stat.S_ISDIR(opened.st_mode):
                raise PosixDirectoryHandleCustodyUnavailable(
                    "held descriptor does not refer to an ordinary directory"
                )
            if int(opened.st_ino) == 0:
                raise PosixDirectoryHandleCustodyUnavailable(
                    "held directory descriptor exposes no stable inode identity"
                )
            self.root_identity = _identity_from_stat(opened)
        except Exception:
            os.close(self.fd)
            self.fd = -1
            raise

    def close(self) -> None:
        if self.fd >= 0:
            os.close(self.fd)
            self.fd = -1

    def __enter__(self) -> "HeldDirectoryCustody":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def candidate_names(
        self,
        *,
        is_candidate: Callable[[str], bool],
        max_entries: int,
        max_candidates: int,
    ) -> tuple[str, ...]:
        if max_entries < 0 or max_candidates < 0:
            raise ValueError("custody budgets must be non-negative")
        entries_seen = 0
        candidates: list[str] = []
        with os.scandir(self.fd) as entries:
            for entry in entries:
                entries_seen += 1
                if entries_seen > max_entries:
                    raise DescriptorArtifactCustodyError(
                        f"held-directory scan exceeds {max_entries} entry budget"
                    )
                name = _require_simple_name(entry.name)
                if not is_candidate(name):
                    continue
                candidates.append(name)
                if len(candidates) > max_candidates:
                    raise DescriptorArtifactCustodyError(
                        f"held-directory candidate set exceeds {max_candidates} budget"
                    )
        candidates.sort()
        return tuple(candidates)

    def observe_utf8_regular_file(
        self,
        name: str,
        *,
        max_bytes: int,
    ) -> DescriptorArtifactObservation:
        """Observe one named regular file through the held root descriptor.

        The candidate is no-follow stat'ed relative to the held root, opened relative to the same
        descriptor with O_NOFOLLOW, read completely within the byte budget, then revalidated both
        through the open descriptor and through the still-held directory descriptor.
        """

        name = _require_simple_name(name)
        if max_bytes < 0:
            raise ValueError("artifact byte budget must be non-negative")

        pre = os.stat(name, dir_fd=self.fd, follow_symlinks=False)
        if not stat.S_ISREG(pre.st_mode):
            raise DescriptorArtifactCustodyError("candidate is not an ordinary regular file")
        pre_identity = _identity_from_stat(pre)
        if pre_identity.inode == 0:
            raise DescriptorArtifactCustodyError("candidate exposes no stable inode identity")

        flags = os.O_RDONLY | os.O_NOFOLLOW
        if hasattr(os, "O_CLOEXEC"):
            flags |= os.O_CLOEXEC
        if hasattr(os, "O_NONBLOCK"):
            flags |= os.O_NONBLOCK

        artifact_fd = os.open(name, flags, dir_fd=self.fd)
        try:
            opened = os.fstat(artifact_fd)
            if not stat.S_ISREG(opened.st_mode):
                raise DescriptorArtifactCustodyError("opened candidate is not a regular file")
            opened_identity = _identity_from_stat(opened)
            if not _same_identity(pre_identity, opened_identity):
                raise DescriptorArtifactCustodyError(
                    "candidate identity changed between descriptor-relative stat and open"
                )

            chunks: list[bytes] = []
            total = 0
            digest = hashlib.sha256()
            while True:
                chunk = os.read(artifact_fd, min(READ_CHUNK_BYTES, max_bytes + 1 - total))
                if not chunk:
                    break
                total += len(chunk)
                if total > max_bytes:
                    raise DescriptorArtifactCustodyError(
                        f"candidate exceeds {max_bytes} byte custody budget"
                    )
                digest.update(chunk)
                chunks.append(chunk)

            after_fd = _identity_from_stat(os.fstat(artifact_fd))
            if not _same_identity(opened_identity, after_fd):
                raise DescriptorArtifactCustodyError(
                    "opened candidate changed during bounded descriptor read"
                )

            after_name = os.stat(name, dir_fd=self.fd, follow_symlinks=False)
            if not stat.S_ISREG(after_name.st_mode):
                raise DescriptorArtifactCustodyError(
                    "candidate name no longer identifies an ordinary regular file"
                )
            after_name_identity = _identity_from_stat(after_name)
            if not _same_identity(opened_identity, after_name_identity):
                raise DescriptorArtifactCustodyError(
                    "candidate name no longer identifies the opened artifact object"
                )

            raw = b"".join(chunks)
            return DescriptorArtifactObservation(
                name=name,
                utf8_text=raw.decode("utf-8", errors="strict"),
                byte_count=total,
                sha256=digest.hexdigest(),
                identity=opened_identity,
            )
        finally:
            os.close(artifact_fd)
