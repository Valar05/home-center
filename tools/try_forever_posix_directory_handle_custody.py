#!/usr/bin/env python3
"""Source-only POSIX held-directory custody for TRY FOREVER evidence artifacts.

This organ strengthens *root* custody when the local Python/OS surface exposes the required POSIX
primitives. It opens the named directory once with O_DIRECTORY|O_NOFOLLOW, keeps that descriptor as
the authority root, enumerates through fresh descriptor-relative directory handles, captures each
candidate object's no-follow identity during that held-root enumeration, and opens candidate names
relative to that same held authority root.

It deliberately does not claim universal filesystem atomicity. A held root descriptor prevents a
later replacement of the root pathname from redirecting subsequent descriptor-relative work. A
captured candidate identity also rejects persistent candidate replacement between enumeration and
authority-facing open/read. Candidate swap-and-restore between observations and filesystem identity
reuse remain separate boundaries. Regression execution, owner integration, runtime behavior,
deployment, phone execution, delivery, and acceptance are all separate capability states.
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
class DescriptorCandidate:
    """One candidate name plus its held-root no-follow enumeration identity."""

    name: str
    identity: DescriptorIdentity
    mode: int

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class DescriptorCandidateInventory:
    """One bounded held-root inventory with both candidate identities and scan-work evidence."""

    candidates: tuple[DescriptorCandidate, ...]
    entries_observed: int

    @property
    def candidates_observed(self) -> int:
        return len(self.candidates)

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


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


def _directory_open_flags() -> int:
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    return flags


class HeldDirectoryCustody:
    """One held POSIX directory descriptor and bounded descriptor-relative operations."""

    def __init__(self, path: Path | str):
        capability = current_directory_handle_binding_capability()
        if capability.status != "SUPPORTED_POSIX_PRIMITIVES":
            raise PosixDirectoryHandleCustodyUnavailable(capability.boundary)

        self.path = Path(path)
        try:
            self.fd = os.open(os.fspath(self.path), _directory_open_flags())
        except OSError:
            self.fd = -1
            raise PosixDirectoryHandleCustodyUnavailable(
                "held directory open failed before descriptor custody could be established"
            ) from None
        try:
            try:
                opened = os.fstat(self.fd)
            except OSError:
                raise PosixDirectoryHandleCustodyUnavailable(
                    "held directory descriptor identity read failed"
                ) from None
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
            try:
                os.close(self.fd)
            except OSError:
                pass
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

    def candidate_inventory(
        self,
        *,
        is_candidate: Callable[[str], bool],
        max_entries: int,
        max_candidates: int,
    ) -> DescriptorCandidateInventory:
        """Enumerate bounded candidates and retain both identities and total scan-work evidence.

        A new `open(".", dir_fd=self.fd)` is intentional. Directory descriptors can carry stream
        position; reusing the authority descriptor directly for repeated scans can make later scans
        depend on earlier enumeration. The fresh scan handle stays anchored to the held root while
        giving each bounded inventory pass an independent directory position.

        Capturing each matching entry's no-follow identity here does not make candidate-name custody
        atomic. It does, however, let the later authority-facing open reject persistent replacement
        that occurred after enumeration instead of silently treating the replacement as the object
        that was enumerated.

        `entries_observed` deliberately counts unrelated entries too. A future canonical-owner
        composition can therefore preserve v10's artifactDirectoryEntriesObserved evidence rather
        than replacing it with candidate count and quietly weakening the receipt.

        Authority-facing scan-handle open, enumeration, and candidate stat failures stay inside the
        custody error domain. A failed inventory returns no partial candidate authority.
        """

        if max_entries < 0 or max_candidates < 0:
            raise ValueError("custody budgets must be non-negative")
        entries_seen = 0
        candidates: list[DescriptorCandidate] = []
        try:
            scan_fd = os.open(".", _directory_open_flags(), dir_fd=self.fd)
        except OSError:
            raise DescriptorArtifactCustodyError(
                "held-directory scan handle open failed"
            ) from None
        try:
            try:
                with os.scandir(scan_fd) as entries:
                    for entry in entries:
                        entries_seen += 1
                        if entries_seen > max_entries:
                            raise DescriptorArtifactCustodyError(
                                f"held-directory scan exceeds {max_entries} entry budget"
                            )
                        name = _require_simple_name(entry.name)
                        if not is_candidate(name):
                            continue
                        try:
                            observed = entry.stat(follow_symlinks=False)
                        except OSError:
                            raise DescriptorArtifactCustodyError(
                                "candidate identity stat failed during held-directory enumeration"
                            ) from None
                        identity = _identity_from_stat(observed)
                        if identity.inode == 0:
                            raise DescriptorArtifactCustodyError(
                                "enumerated candidate exposes no stable inode identity"
                            )
                        candidates.append(
                            DescriptorCandidate(
                                name=name,
                                identity=identity,
                                mode=int(observed.st_mode),
                            )
                        )
                        if len(candidates) > max_candidates:
                            raise DescriptorArtifactCustodyError(
                                f"held-directory candidate set exceeds {max_candidates} budget"
                            )
            except OSError:
                raise DescriptorArtifactCustodyError(
                    "held-directory enumeration I/O failed"
                ) from None
        finally:
            os.close(scan_fd)
        candidates.sort(key=lambda item: item.name)
        return DescriptorCandidateInventory(
            candidates=tuple(candidates),
            entries_observed=entries_seen,
        )

    def candidate_entries(
        self,
        *,
        is_candidate: Callable[[str], bool],
        max_entries: int,
        max_candidates: int,
    ) -> tuple[DescriptorCandidate, ...]:
        """Compatibility projection over `candidate_inventory`; identity evidence remains available."""

        return self.candidate_inventory(
            is_candidate=is_candidate,
            max_entries=max_entries,
            max_candidates=max_candidates,
        ).candidates

    def candidate_names(
        self,
        *,
        is_candidate: Callable[[str], bool],
        max_entries: int,
        max_candidates: int,
    ) -> tuple[str, ...]:
        """Compatibility projection over `candidate_inventory`; full evidence remains available."""

        return tuple(
            item.name
            for item in self.candidate_inventory(
                is_candidate=is_candidate,
                max_entries=max_entries,
                max_candidates=max_candidates,
            ).candidates
        )

    def observe_utf8_regular_file(
        self,
        name: str,
        *,
        max_bytes: int,
        expected_candidate: DescriptorCandidate | None = None,
    ) -> DescriptorArtifactObservation:
        """Observe one named regular file through the held root descriptor.

        The candidate is no-follow stat'ed relative to the held root, optionally required to match
        the identity captured during held-root enumeration, opened relative to the same descriptor
        with O_NOFOLLOW, read completely within the byte budget, then revalidated both through the
        open descriptor and through the still-held directory descriptor. Strict UTF-8 is part of
        custody admission; malformed bytes and authority-facing filesystem I/O failures stay inside
        the DescriptorArtifactCustodyError domain rather than leaking raw decoder/OS exceptions.
        """

        name = _require_simple_name(name)
        if max_bytes < 0:
            raise ValueError("artifact byte budget must be non-negative")
        if expected_candidate is not None:
            if expected_candidate.name != name:
                raise DescriptorArtifactCustodyError(
                    "expected candidate identity belongs to a different basename"
                )
            if not stat.S_ISREG(expected_candidate.mode):
                raise DescriptorArtifactCustodyError(
                    "enumerated candidate is not an ordinary regular file"
                )

        try:
            pre = os.stat(name, dir_fd=self.fd, follow_symlinks=False)
        except OSError:
            raise DescriptorArtifactCustodyError(
                "candidate unavailable during pre-open descriptor-relative stat"
            ) from None
        if not stat.S_ISREG(pre.st_mode):
            raise DescriptorArtifactCustodyError("candidate is not an ordinary regular file")
        pre_identity = _identity_from_stat(pre)
        if pre_identity.inode == 0:
            raise DescriptorArtifactCustodyError("candidate exposes no stable inode identity")
        if expected_candidate is not None and not _same_identity(
            expected_candidate.identity,
            pre_identity,
        ):
            raise DescriptorArtifactCustodyError(
                "candidate identity changed after held-root enumeration"
            )

        flags = os.O_RDONLY | os.O_NOFOLLOW
        if hasattr(os, "O_CLOEXEC"):
            flags |= os.O_CLOEXEC
        if hasattr(os, "O_NONBLOCK"):
            flags |= os.O_NONBLOCK

        try:
            artifact_fd = os.open(name, flags, dir_fd=self.fd)
        except OSError:
            raise DescriptorArtifactCustodyError(
                "candidate open failed after pre-open identity admission"
            ) from None
        try:
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
            except OSError:
                raise DescriptorArtifactCustodyError(
                    "candidate descriptor I/O failed during bounded custody"
                ) from None

            raw = b"".join(chunks)
            try:
                utf8_text = raw.decode("utf-8", errors="strict")
            except UnicodeDecodeError:
                raise DescriptorArtifactCustodyError(
                    "candidate content is not strict UTF-8"
                ) from None
            return DescriptorArtifactObservation(
                name=name,
                utf8_text=utf8_text,
                byte_count=total,
                sha256=digest.hexdigest(),
                identity=opened_identity,
            )
        finally:
            os.close(artifact_fd)
