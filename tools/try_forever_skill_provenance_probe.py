#!/usr/bin/env python3
"""Deterministic repository-local provenance probe for TRY FOREVER skill lights.

Only the checked-out repository may authorize ``repository_skill`` provenance.
Generated indexes are discovery aids, never substitutes for current
``skills/**/SKILL.md`` existence. This module owns no network, renderer,
scheduler, phone surface, or P0 recovery lane.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from try_forever_generated_index_alias_policy import (
    GeneratedIndexAliasError,
    resolve_consistent_alias,
)
from try_forever_skill_directory_traversal_guard import (
    SkillDirectoryIdentity,
    capture_skill_directory_identity,
    revalidate_skill_directory_for_traversal,
)
from try_forever_skill_file_identity import (
    capture_skill_file_identity,
    revalidate_skill_file_identity,
)
from try_forever_skill_identity_set import find_case_insensitive_collisions
from try_forever_skill_root_identity import (
    capture_skill_root_identity,
    revalidate_skill_root_identity,
)
from try_forever_skill_snapshot_authority import certify_repository_skills
from try_forever_skill_title_fallback_policy import (
    SkillFallbackTitleError,
    admit_markdown_h1_title,
    admit_skill_title,
)

DEFAULT_MAX_INDEX_AGE_HOURS = 14 * 24
MAX_FUTURE_SKEW_SECONDS = 5 * 60
MAX_DISCOVERY_ERROR_PATH_CHARS = 512
MAX_SKILL_TITLE_SCAN_BYTES = 64 * 1024
MAX_SKILL_TITLE_LINE_BYTES = 8 * 1024
MAX_SKILL_TITLE_CHARS = 256
MAX_SKILL_HASH_BYTES = 1024 * 1024
SKILL_HASH_CHUNK_BYTES = 64 * 1024
MAX_SKILL_CANDIDATES = 2048
MAX_SKILL_TRAVERSAL_ENTRIES = 32768
MAX_GENERATED_INDEX_BYTES = 1024 * 1024


class SkillTitleResourceLimitError(ValueError):
    """A SKILL.md title cannot be admitted within the declared resource budget."""


class SkillHashResourceLimitError(ValueError):
    """A SKILL.md cannot earn a full-file SHA inside the declared byte budget."""


class SkillCandidateResourceLimitError(ValueError):
    """Repository skill candidate enumeration exceeded its declared count budget."""


class SkillCandidateTopologyError(ValueError):
    """A named SKILL.md candidate is not one ordinary non-redirecting file."""

    def __init__(self, path: Path):
        super().__init__(
            "SKILL.md candidate must be an ordinary non-redirecting file; "
            "partial repository-skill authority is forbidden"
        )
        self.path = path


class SkillTraversalResourceLimitError(ValueError):
    """Repository skill traversal exceeded its declared filesystem-entry budget."""


class SkillDirectoryTraversalTopologyError(ValueError):
    """A queued child directory lost repository-owned traversal identity."""

    def __init__(self, path: Path, *, status: str, reason: str):
        super().__init__(reason)
        self.path = path
        self.status = status
        self.reason = reason


@dataclass(frozen=True)
class SkillRecord:
    path: str
    sha256: str
    title: str


@dataclass(frozen=True)
class DiscoveryError:
    path: str
    stage: str
    error_type: str
    reason: str
    sha256: str = ""
    related_path: str = ""


@dataclass(frozen=True)
class IndexVerdict:
    status: str
    reason: str
    path: str
    source_head: str
    generated_at: str
    dirty_source: bool | None
    age_hours: float | None


@dataclass(frozen=True)
class RepositorySnapshotVerdict:
    status: str
    reason: str
    head_before: str
    head_after: str
    dirty_before: bool | None
    dirty_after: bool | None


def sha256_file(path: Path, *, max_bytes: int | None = None) -> str:
    """Return an exact whole-file SHA only after EOF is reached inside budget."""

    limit = MAX_SKILL_HASH_BYTES if max_bytes is None else max_bytes
    if limit < 0:
        raise ValueError("hash byte budget must be non-negative")

    digest = hashlib.sha256()
    total = 0
    with path.open("rb") as handle:
        while True:
            remaining = limit - total
            read_size = min(SKILL_HASH_CHUNK_BYTES, remaining + 1)
            chunk = handle.read(read_size)
            if not chunk:
                return digest.hexdigest()
            total += len(chunk)
            if total > limit:
                raise SkillHashResourceLimitError(
                    f"skill file exceeds whole-file hash byte budget {limit}"
                )
            digest.update(chunk)


def markdown_title(path: Path) -> str:
    """Read one bounded H1/fallback title without normalization laundering."""

    scanned_bytes = 0
    with path.open("rb") as handle:
        while scanned_bytes < MAX_SKILL_TITLE_SCAN_BYTES:
            remaining_scan = MAX_SKILL_TITLE_SCAN_BYTES - scanned_bytes
            read_limit = min(MAX_SKILL_TITLE_LINE_BYTES, remaining_scan)
            raw_line = handle.readline(read_limit + 1)
            if not raw_line:
                return admit_skill_title(
                    path.parent.name,
                    max_chars=MAX_SKILL_TITLE_CHARS,
                )

            scanned_bytes += len(raw_line)
            if len(raw_line) > read_limit:
                raise SkillTitleResourceLimitError(
                    "skill title scan exceeded its byte/line budget"
                )

            line = raw_line.decode("utf-8")
            title = admit_markdown_h1_title(
                line,
                max_chars=MAX_SKILL_TITLE_CHARS,
            )
            if title is not None:
                return title

        if handle.read(1):
            raise SkillTitleResourceLimitError(
                "skill title was not resolved within the scan budget"
            )
    return admit_skill_title(
        path.parent.name,
        max_chars=MAX_SKILL_TITLE_CHARS,
    )


def bounded_error_path(relative: str) -> str:
    """Bound operator-facing discovery error paths without inventing aliases."""

    if len(relative) <= MAX_DISCOVERY_ERROR_PATH_CHARS:
        return relative
    digest = hashlib.sha256(
        relative.encode("utf-8", errors="surrogatepass")
    ).hexdigest()[:16]
    suffix = f"...#{digest}"
    keep = max(0, MAX_DISCOVERY_ERROR_PATH_CHARS - len(suffix))
    return relative[:keep] + suffix


def discovery_error(
    *,
    relative: str,
    stage: str,
    error: BaseException,
    reason: str,
    sha256: str = "",
) -> DiscoveryError:
    """Project one per-file failure into bounded non-hostile diagnostic data."""

    return DiscoveryError(
        path=bounded_error_path(relative),
        stage=stage,
        error_type=type(error).__name__,
        reason=reason,
        sha256=sha256,
    )


def skill_file_identity_error_type(status: str) -> str:
    return {
        "REDIRECTOR_BLOCKED": "SkillFileRedirectorBlocked",
        "FILE_CHANGED": "SkillFileChanged",
        "IDENTITY_UNAVAILABLE": "SkillFileIdentityUnavailable",
    }.get(status, "SkillFileIdentityRejected")


def command_text(args: list[str], cwd: Path) -> str:
    try:
        completed = subprocess.run(
            args,
            cwd=cwd,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return ""
    return completed.stdout.strip()


def git_head(repo_root: Path) -> str:
    return command_text(["git", "rev-parse", "HEAD"], repo_root)


def git_dirty(repo_root: Path) -> bool | None:
    try:
        completed = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=repo_root,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return bool(completed.stdout.strip())


def assess_repository_snapshot(
    *,
    head_before: str,
    head_after: str,
    dirty_before: bool | None,
    dirty_after: bool | None,
) -> RepositorySnapshotVerdict:
    """Judge whether discovery was bracketed by one stable clean checkout."""

    if not head_before or not head_after:
        return RepositorySnapshotVerdict(
            status="UNSTABLE",
            reason="git HEAD was unavailable before or after skill discovery",
            head_before=head_before,
            head_after=head_after,
            dirty_before=dirty_before,
            dirty_after=dirty_after,
        )
    if head_before != head_after:
        return RepositorySnapshotVerdict(
            status="UNSTABLE",
            reason="git HEAD changed while skill discovery was in progress",
            head_before=head_before,
            head_after=head_after,
            dirty_before=dirty_before,
            dirty_after=dirty_after,
        )
    if dirty_before is None or dirty_after is None:
        return RepositorySnapshotVerdict(
            status="UNSTABLE",
            reason="checkout cleanliness was unavailable before or after skill discovery",
            head_before=head_before,
            head_after=head_after,
            dirty_before=dirty_before,
            dirty_after=dirty_after,
        )
    if dirty_before or dirty_after:
        return RepositorySnapshotVerdict(
            status="UNSTABLE",
            reason="checkout was dirty before or after skill discovery",
            head_before=head_before,
            head_after=head_after,
            dirty_before=dirty_before,
            dirty_after=dirty_after,
        )
    return RepositorySnapshotVerdict(
        status="STABLE_CLEAN",
        reason="the same clean git HEAD bracketed direct skill discovery",
        head_before=head_before,
        head_after=head_after,
        dirty_before=False,
        dirty_after=False,
    )


def is_within(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def resolve_repo_path(repo_root: Path, value: str | None) -> Path | None:
    """Normalize CLI spelling to an absolute named path without dereferencing it."""

    if not value:
        return None
    candidate = Path(value)
    if not candidate.is_absolute():
        candidate = repo_root / candidate
    return Path(os.path.abspath(os.fspath(candidate)))


def bounded_skill_candidates(
    skills_root: Path,
    *,
    max_candidates: int | None = None,
    max_entries: int | None = None,
) -> list[Path]:
    """Return deterministic SKILL.md candidates inside bounded traversal throats.

    Each queued directory carries the no-follow identity observed when its parent
    admitted it. The same path is re-observed immediately before its later scan;
    persistent redirector/type/device/inode drift fails the whole discovery. This
    remains a portable observation pair, not an atomic directory-handle binding.
    """

    candidate_limit = (
        MAX_SKILL_CANDIDATES if max_candidates is None else max_candidates
    )
    entry_limit = (
        MAX_SKILL_TRAVERSAL_ENTRIES if max_entries is None else max_entries
    )
    if candidate_limit < 0:
        raise ValueError("skill candidate budget must be non-negative")
    if entry_limit < 0:
        raise ValueError("skill traversal entry budget must be non-negative")

    candidates: list[Path] = []
    root_directory_identity = capture_skill_directory_identity(skills_root)
    stack: list[tuple[Path, SkillDirectoryIdentity]] = [
        (skills_root, root_directory_identity)
    ]
    entries_seen = 0

    while stack:
        directory, discovered_directory_identity = stack.pop()
        before_scan_identity = capture_skill_directory_identity(directory)
        traversal_verdict = revalidate_skill_directory_for_traversal(
            discovered_directory_identity,
            before_scan_identity,
        )
        if traversal_verdict.status != "STABLE":
            raise SkillDirectoryTraversalTopologyError(
                directory,
                status=traversal_verdict.status,
                reason=traversal_verdict.reason,
            )

        discovered: list[tuple[str, Path, bool, bool]] = []
        with os.scandir(directory) as iterator:
            for entry in iterator:
                entries_seen += 1
                if entries_seen > entry_limit:
                    raise SkillTraversalResourceLimitError(
                        f"skill traversal entry count exceeds declared budget {entry_limit}"
                    )

                path = Path(entry.path)
                is_directory = entry.is_dir(follow_symlinks=False)
                is_skill_file = False
                if entry.name == "SKILL.md":
                    if entry.is_symlink() or not entry.is_file(follow_symlinks=False):
                        raise SkillCandidateTopologyError(path)
                    is_skill_file = True
                discovered.append((entry.name, path, is_directory, is_skill_file))

        discovered.sort(key=lambda item: item[0])
        child_directories: list[tuple[Path, SkillDirectoryIdentity]] = []
        for _name, path, is_directory, is_skill_file in discovered:
            if is_skill_file:
                candidates.append(path)
                if len(candidates) > candidate_limit:
                    raise SkillCandidateResourceLimitError(
                        f"skill candidate count exceeds declared budget {candidate_limit}"
                    )
            if is_directory:
                child_directories.append(
                    (path, capture_skill_directory_identity(path))
                )

        for child in reversed(child_directories):
            stack.append(child)

    candidates.sort()
    return candidates


def discover_skills(repo_root: Path) -> tuple[list[SkillRecord], list[DiscoveryError]]:
    """Discover independent skill records with fail-closed resource throats."""

    skills_root = repo_root / "skills"
    try:
        root_before = capture_skill_root_identity(skills_root)
    except FileNotFoundError:
        return [], [
            DiscoveryError(
                path="skills",
                stage="repository",
                error_type="MissingSkillsDirectory",
                reason="skills directory is missing",
            )
        ]
    except OSError as error:
        return [], [
            DiscoveryError(
                path="skills",
                stage="repository",
                error_type=type(error).__name__,
                reason="skills root identity could not be observed without following redirectors",
            )
        ]

    if root_before.redirector_kind:
        error_type = (
            "JunctionSkillsRoot"
            if root_before.redirector_kind == "junction"
            else "SymlinkedSkillsRoot"
        )
        return [], [
            DiscoveryError(
                path="skills",
                stage="repository",
                error_type=error_type,
                reason=f"skills root is a {root_before.redirector_kind}; repository-skill traversal outside repository-owned topology is forbidden",
            )
        ]
    if not root_before.is_directory:
        return [], [
            DiscoveryError(
                path="skills",
                stage="repository",
                error_type="MissingSkillsDirectory",
                reason="skills root is not an ordinary directory",
            )
        ]

    try:
        candidates = bounded_skill_candidates(skills_root)
    except SkillDirectoryTraversalTopologyError as error:
        try:
            relative = error.path.relative_to(repo_root).as_posix()
        except ValueError:
            relative = "skills"
        return [], [
            DiscoveryError(
                path=bounded_error_path(relative),
                stage="traversal",
                error_type=(
                    "SkillDirectoryTraversal"
                    + error.status.title().replace("_", "")
                ),
                reason=(
                    "queued child-directory traversal identity was rejected; "
                    f"partial repository-skill authority is forbidden: {error.reason}"
                ),
            )
        ]
    except SkillCandidateTopologyError as error:
        try:
            relative = error.path.relative_to(repo_root).as_posix()
        except ValueError:
            relative = "skills"
        return [], [
            DiscoveryError(
                path=bounded_error_path(relative),
                stage="identity",
                error_type=type(error).__name__,
                reason=(
                    "SKILL.md candidate must be an ordinary non-redirecting file; "
                    "partial repository-skill authority is forbidden"
                ),
            )
        ]
    except SkillTraversalResourceLimitError as error:
        return [], [
            DiscoveryError(
                path="skills",
                stage="traversal",
                error_type=type(error).__name__,
                reason="skill filesystem traversal exceeded the declared entry budget; partial repository-skill authority is forbidden",
            )
        ]
    except SkillCandidateResourceLimitError as error:
        return [], [
            DiscoveryError(
                path="skills",
                stage="enumeration",
                error_type=type(error).__name__,
                reason="skill candidate enumeration exceeded the declared count budget; partial repository-skill authority is forbidden",
            )
        ]
    except OSError as error:
        return [], [
            DiscoveryError(
                path="skills",
                stage="traversal",
                error_type=type(error).__name__,
                reason="skill filesystem traversal could not be completed; partial repository-skill authority is forbidden",
            )
        ]

    try:
        root_after = capture_skill_root_identity(skills_root)
    except OSError as error:
        return [], [
            DiscoveryError(
                path="skills",
                stage="repository",
                error_type=type(error).__name__,
                reason="skills root identity could not be revalidated after candidate enumeration; partial repository-skill authority is forbidden",
            )
        ]

    root_verdict = revalidate_skill_root_identity(root_before, root_after)
    if root_verdict.status != "STABLE":
        error_type = (
            "SkillsRootIdentityUnavailable"
            if root_verdict.status == "IDENTITY_UNAVAILABLE"
            else "SkillsRootIdentityChanged"
        )
        return [], [
            DiscoveryError(
                path="skills",
                stage="repository",
                error_type=error_type,
                reason=root_verdict.reason,
            )
        ]

    relative_candidates = tuple(
        path.relative_to(repo_root).as_posix() for path in candidates
    )
    collisions = find_case_insensitive_collisions(relative_candidates)
    if collisions:
        collision_errors: list[DiscoveryError] = []
        for collision in collisions:
            owner = collision.paths[0]
            for alias in collision.paths[1:]:
                collision_errors.append(
                    DiscoveryError(
                        path=bounded_error_path(alias),
                        stage="identity",
                        error_type="CaseInsensitiveIdentityCollision",
                        reason=(
                            "repository-skill identity set is ambiguous under the "
                            "existing case-insensitive owner key; first-wins and "
                            "last-wins partial authority are forbidden"
                        ),
                        related_path=bounded_error_path(owner),
                    )
                )
        return [], collision_errors

    records: list[SkillRecord] = []
    errors: list[DiscoveryError] = []
    for path in candidates:
        relative = path.relative_to(repo_root).as_posix()

        try:
            file_before = capture_skill_file_identity(path)
        except OSError as error:
            errors.append(
                discovery_error(
                    relative=relative,
                    stage="identity",
                    error=error,
                    reason="skill file identity could not be observed before repository-skill authority work",
                )
            )
            continue

        before_verdict = revalidate_skill_file_identity(file_before, file_before)
        if before_verdict.status != "STABLE":
            errors.append(
                DiscoveryError(
                    path=bounded_error_path(relative),
                    stage="identity",
                    error_type=skill_file_identity_error_type(before_verdict.status),
                    reason=before_verdict.reason,
                )
            )
            continue

        if not is_within(path, skills_root):
            errors.append(
                DiscoveryError(
                    path=bounded_error_path(relative),
                    stage="identity",
                    error_type="SkillPathEscape",
                    reason="resolved skill path escapes the skills root",
                )
            )
            continue

        try:
            title = markdown_title(path)
        except SkillTitleResourceLimitError as error:
            errors.append(
                discovery_error(
                    relative=relative,
                    stage="title",
                    error=error,
                    reason="skill title extraction exceeded the declared resource budget",
                )
            )
            continue
        except SkillFallbackTitleError as error:
            errors.append(
                discovery_error(
                    relative=relative,
                    stage="title",
                    error=error,
                    reason="skill title failed the declared source resource/semantic contract",
                )
            )
            continue
        except UnicodeDecodeError as error:
            errors.append(
                discovery_error(
                    relative=relative,
                    stage="title",
                    error=error,
                    reason="skill file is not valid UTF-8 text",
                )
            )
            continue
        except OSError as error:
            errors.append(
                discovery_error(
                    relative=relative,
                    stage="title",
                    error=error,
                    reason="skill file title could not be read",
                )
            )
            continue

        try:
            sha256 = sha256_file(path)
        except SkillHashResourceLimitError as error:
            errors.append(
                discovery_error(
                    relative=relative,
                    stage="hash",
                    error=error,
                    reason="skill file exceeds the declared whole-file hash resource budget",
                )
            )
            continue
        except OSError as error:
            errors.append(
                discovery_error(
                    relative=relative,
                    stage="hash",
                    error=error,
                    reason="skill file bytes could not be read",
                )
            )
            continue

        try:
            file_after = capture_skill_file_identity(path)
        except OSError as error:
            errors.append(
                discovery_error(
                    relative=relative,
                    stage="identity",
                    error=error,
                    reason="skill file identity could not be revalidated after title/hash authority work",
                )
            )
            continue

        file_verdict = revalidate_skill_file_identity(file_before, file_after)
        if file_verdict.status != "STABLE":
            errors.append(
                DiscoveryError(
                    path=bounded_error_path(relative),
                    stage="identity",
                    error_type=skill_file_identity_error_type(file_verdict.status),
                    reason=file_verdict.reason,
                )
            )
            continue

        records.append(SkillRecord(path=relative, sha256=sha256, title=title))

    try:
        root_final = capture_skill_root_identity(skills_root)
    except OSError as error:
        return [], [
            DiscoveryError(
                path="skills",
                stage="repository",
                error_type=type(error).__name__,
                reason=(
                    "skills root identity could not be revalidated after per-file "
                    "authority work; partial repository-skill authority is forbidden"
                ),
            )
        ]

    final_root_verdict = revalidate_skill_root_identity(root_before, root_final)
    if final_root_verdict.status != "STABLE":
        error_type = (
            "SkillsRootIdentityUnavailable"
            if final_root_verdict.status == "IDENTITY_UNAVAILABLE"
            else "SkillsRootIdentityChanged"
        )
        return [], [
            DiscoveryError(
                path="skills",
                stage="repository",
                error_type=error_type,
                reason=(
                    "final skills-root revalidation rejected repository-skill "
                    f"authority: {final_root_verdict.reason}"
                ),
            )
        ]
    return records, errors


def parse_timestamp(value: Any) -> datetime | None:
    if isinstance(value, (int, float)):
        raw = float(value)
        if raw > 10_000_000_000:
            raw /= 1000.0
        try:
            return datetime.fromtimestamp(raw, tz=timezone.utc)
        except (OverflowError, OSError, ValueError):
            return None
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def inspect_generated_index(
    path: Path | None,
    *,
    current_head: str,
    current_tree_dirty: bool | None,
    max_age_hours: float,
    now: datetime,
) -> IndexVerdict:
    if path is None:
        return IndexVerdict(
            status="UNRESOLVED",
            reason="no generated index supplied; direct current-tree skill discovery remains authoritative",
            path="",
            source_head="",
            generated_at="",
            dirty_source=None,
            age_hours=None,
        )
    if not path.is_file():
        return IndexVerdict(
            status="UNRESOLVED",
            reason="generated index path does not exist",
            path=str(path),
            source_head="",
            generated_at="",
            dirty_source=None,
            age_hours=None,
        )
    try:
        with path.open("rb") as handle:
            raw = handle.read(MAX_GENERATED_INDEX_BYTES + 1)
        if len(raw) > MAX_GENERATED_INDEX_BYTES:
            return IndexVerdict(
                status="UNRESOLVED",
                reason=f"generated index exceeds byte budget {MAX_GENERATED_INDEX_BYTES}",
                path=str(path),
                source_head="",
                generated_at="",
                dirty_source=None,
                age_hours=None,
            )
        data = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        return IndexVerdict(
            status="UNRESOLVED",
            reason=f"generated index is unreadable UTF-8 JSON: {type(error).__name__}",
            path=str(path),
            source_head="",
            generated_at="",
            dirty_source=None,
            age_hours=None,
        )
    if not isinstance(data, dict):
        return IndexVerdict(
            status="UNRESOLVED",
            reason="generated index root is not an object",
            path=str(path),
            source_head="",
            generated_at="",
            dirty_source=None,
            age_hours=None,
        )

    try:
        source_alias = resolve_consistent_alias(
            data,
            ("sourceHead", "source_head", "gitHead", "git_head"),
            field="sourceHead",
            allowed_types=(str,),
        )
        generated_alias = resolve_consistent_alias(
            data,
            (
                "generatedAt",
                "generated_at",
                "generatedAtMs",
                "generated_at_ms",
                "updatedAt",
                "updated_at",
            ),
            field="generatedAt",
            allowed_types=(str, int, float),
        )
        dirty_alias = resolve_consistent_alias(
            data,
            ("dirtySource", "dirty_source", "sourceDirty", "source_dirty"),
            field="dirtySource",
            allowed_types=(bool,),
        )
    except GeneratedIndexAliasError as error:
        return IndexVerdict(
            status="UNRESOLVED",
            reason=f"generated index metadata contract rejected: {type(error).__name__}",
            path=str(path),
            source_head="",
            generated_at="",
            dirty_source=None,
            age_hours=None,
        )

    source_head = source_alias.value or ""
    generated_raw = generated_alias.value
    generated_dt = parse_timestamp(generated_raw)
    dirty_source = dirty_alias.value
    age_hours = None
    if generated_dt is not None:
        age_hours = max(0.0, (now - generated_dt).total_seconds() / 3600.0)

    path_text = str(path)
    generated_text = generated_dt.isoformat() if generated_dt is not None else ""
    if not current_head:
        return IndexVerdict(
            status="UNRESOLVED",
            reason="current git head is unavailable; generated index cannot prove current provenance",
            path=path_text,
            source_head=source_head,
            generated_at=generated_text,
            dirty_source=dirty_source,
            age_hours=age_hours,
        )
    if current_tree_dirty is None:
        return IndexVerdict(
            status="UNRESOLVED",
            reason="current checkout cleanliness is unavailable; matching HEAD alone cannot prove current provenance",
            path=path_text,
            source_head=source_head,
            generated_at=generated_text,
            dirty_source=dirty_source,
            age_hours=age_hours,
        )
    if not source_head:
        return IndexVerdict(
            status="UNRESOLVED",
            reason="generated index does not declare a source head",
            path=path_text,
            source_head="",
            generated_at=generated_text,
            dirty_source=dirty_source,
            age_hours=age_hours,
        )
    if source_head != current_head:
        return IndexVerdict(
            status="STALE",
            reason="generated index source head does not match the current checkout",
            path=path_text,
            source_head=source_head,
            generated_at=generated_text,
            dirty_source=dirty_source,
            age_hours=age_hours,
        )
    if dirty_source is True:
        return IndexVerdict(
            status="STALE",
            reason="generated index declares a dirty source tree",
            path=path_text,
            source_head=source_head,
            generated_at=generated_text,
            dirty_source=True,
            age_hours=age_hours,
        )
    if current_tree_dirty is True:
        return IndexVerdict(
            status="UNRESOLVED",
            reason="current checkout is dirty; matching HEAD alone cannot bind generated-index provenance",
            path=path_text,
            source_head=source_head,
            generated_at=generated_text,
            dirty_source=dirty_source,
            age_hours=age_hours,
        )
    if generated_dt is None:
        return IndexVerdict(
            status="UNRESOLVED",
            reason="generated index has no parseable generation timestamp",
            path=path_text,
            source_head=source_head,
            generated_at="",
            dirty_source=dirty_source,
            age_hours=None,
        )
    if generated_dt > now + timedelta(seconds=MAX_FUTURE_SKEW_SECONDS):
        return IndexVerdict(
            status="UNRESOLVED",
            reason="generated index timestamp is implausibly in the future",
            path=path_text,
            source_head=source_head,
            generated_at=generated_text,
            dirty_source=dirty_source,
            age_hours=0.0,
        )
    if age_hours is not None and age_hours > max_age_hours:
        return IndexVerdict(
            status="STALE",
            reason=f"generated index age {age_hours:.2f}h exceeds {max_age_hours:.2f}h",
            path=path_text,
            source_head=source_head,
            generated_at=generated_text,
            dirty_source=dirty_source,
            age_hours=age_hours,
        )
    if dirty_source is not False:
        return IndexVerdict(
            status="UNRESOLVED",
            reason="generated index does not explicitly prove a clean source tree",
            path=path_text,
            source_head=source_head,
            generated_at=generated_text,
            dirty_source=dirty_source,
            age_hours=age_hours,
        )
    return IndexVerdict(
        status="VERIFIED_CURRENT",
        reason="source head, clean-tree declaration, and freshness window all match",
        path=path_text,
        source_head=source_head,
        generated_at=generated_text,
        dirty_source=False,
        age_hours=age_hours,
    )


def emitted_capability_boundary() -> dict[str, bool]:
    """Capability truth for a report emitted by this executing probe process."""

    return {
        "sourceProbe": True,
        "probeExecutedByThisArtifact": True,
        "probeExecutedByThisProcess": True,
        "tested": False,
        "runtimeUi": False,
        "phoneDelivery": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--generated-index")
    parser.add_argument(
        "--max-index-age-hours", type=float, default=DEFAULT_MAX_INDEX_AGE_HOURS
    )
    parser.add_argument("--expected-head", default="")
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    head_before = git_head(repo_root)
    dirty_before = git_dirty(repo_root)
    skills, discovery_errors = discover_skills(repo_root)
    head_after = git_head(repo_root)
    dirty_after = git_dirty(repo_root)
    snapshot = assess_repository_snapshot(
        head_before=head_before,
        head_after=head_after,
        dirty_before=dirty_before,
        dirty_after=dirty_after,
    )

    now = datetime.now(timezone.utc)
    index_path = resolve_repo_path(repo_root, args.generated_index)
    stable_head = snapshot.head_after if snapshot.status == "STABLE_CLEAN" else ""
    stable_dirty = False if snapshot.status == "STABLE_CLEAN" else None
    index = inspect_generated_index(
        index_path,
        current_head=stable_head,
        current_tree_dirty=stable_dirty,
        max_age_hours=max(0.0, args.max_index_age_hours),
        now=now,
    )

    observed_head = head_after or head_before
    head_error = ""
    if args.expected_head and observed_head != args.expected_head:
        head_error = (
            f"expected head {args.expected_head}, observed {observed_head or '<unavailable>'}"
        )

    certification = certify_repository_skills(
        skills,
        snapshot_status=snapshot.status,
        expected_head_error=head_error,
    )

    result = {
        "schema": "try-forever-skill-provenance.v3",
        "repositoryRoot": str(repo_root),
        "currentHead": observed_head,
        "currentTreeDirty": dirty_after,
        "repositorySnapshot": asdict(snapshot),
        "expectedHeadError": head_error,
        "skillAuthority": {
            "status": certification.status,
            "reason": certification.reason,
            "authoritative": certification.authoritative,
        },
        "discoveredSkillCount": len(skills),
        "skillCount": certification.count,
        "skills": [asdict(record) for record in certification.records],
        "discoveryErrors": [asdict(error) for error in discovery_errors],
        "generatedIndex": asdict(index),
        "authority": {
            "repositorySkill": "authority-facing records are emitted only after bounded direct discovery plus a STABLE_CLEAN pre/post snapshot and any expected-head binding; uncertified discoveries remain diagnostic only",
            "generatedIndex": "bounded strict-UTF-8 JSON discovery aid with typed alias consistency; never substitutes for direct skill existence",
        },
        "capabilityBoundary": emitted_capability_boundary(),
    }
    print(json.dumps(result, indent=2, sort_keys=True))

    snapshot_failure = snapshot.status != "STABLE_CLEAN"
    index_strict_failure = bool(args.generated_index) and index.status != "VERIFIED_CURRENT"
    if args.strict and (
        head_error or discovery_errors or snapshot_failure or index_strict_failure
    ):
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
