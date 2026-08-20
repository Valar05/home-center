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
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from try_forever_generated_index_alias_policy import (
    GeneratedIndexAliasError,
    resolve_consistent_alias,
)
from try_forever_generated_index_json_policy import (
    GeneratedIndexJsonError,
    parse_generated_index_json,
)
from try_forever_generated_index_timestamp_policy import (
    GeneratedIndexTimestampError,
    parse_generated_index_timestamp,
)
from try_forever_generated_index_artifact_observation import (
    GeneratedIndexArtifactChangedError,
    GeneratedIndexArtifactResourceLimitError,
    GeneratedIndexArtifactTopologyError,
    observe_generated_index_artifact,
)
from try_forever_provenance_cli_evidence_policy import (
    ProvenanceCliEvidenceError,
    admit_cli_evidence,
)
from try_forever_provenance_emission_composition import (
    compose_provenance_emission,
    needs_generated_index_artifact_revalidation,
)
from try_forever_provenance_report_path import (
    project_report_path,
    project_repository_relative_report_path,
)
from try_forever_repository_emission_observation import observe_repository_emission
from try_forever_skill_content_custody import (
    SkillContentCustodyChangedError,
    SkillContentCustodyResourceLimitError,
    SkillContentCustodyTextError,
    SkillContentCustodyTitleResourceLimitError,
    SkillContentCustodyTopologyError,
    observe_skill_content,
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
from try_forever_skill_tracked_authority import require_tracked_skill_candidates
from try_forever_tracked_skill_observation import observe_tracked_skill_candidates

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
    inspection_sha256: str = ""


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
    return f"<repo-path>...#{digest}"


def project_skill_record_for_report(record: SkillRecord) -> dict[str, Any]:
    """Project report display text without rewriting repository-skill identity."""

    payload = asdict(record)
    payload["path"] = project_repository_relative_report_path(
        record.path,
    ).display_path
    return payload


def project_discovery_error_for_report(error: DiscoveryError) -> dict[str, Any]:
    """Project diagnostic record paths only at report serialization."""

    payload = asdict(error)
    payload["path"] = project_repository_relative_report_path(
        error.path,
        max_chars=MAX_DISCOVERY_ERROR_PATH_CHARS,
    ).display_path
    if error.related_path:
        payload["related_path"] = project_repository_relative_report_path(
            error.related_path,
            max_chars=MAX_DISCOVERY_ERROR_PATH_CHARS,
        ).display_path
    return payload


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

    tracked_observation = observe_tracked_skill_candidates(repo_root, relative_candidates)
    if tracked_observation.status != "OBSERVED":
        return [], [
            DiscoveryError(
                path="skills",
                stage="repository",
                error_type="TrackedSkillObservationUnavailable",
                reason=(
                    "Git-tracked skill identity observation failed closed before "
                    f"repository-skill content authority work: {tracked_observation.reason}"
                ),
            )
        ]

    tracked_authority = require_tracked_skill_candidates(
        relative_candidates,
        tracked_observation.tracked_paths,
    )
    if tracked_authority.status != "STABLE":
        return [], [
            DiscoveryError(
                path=bounded_error_path(path),
                stage="repository",
                error_type="UntrackedSkillCandidate",
                reason=(
                    "discovered SKILL.md is not present in the bounded exact Git-tracked "
                    "identity set; partial repository-skill authority is forbidden"
                ),
            )
            for path in tracked_authority.untracked_paths
        ]

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
            file_pre_io = capture_skill_file_identity(path)
        except OSError as error:
            errors.append(
                discovery_error(
                    relative=relative,
                    stage="identity",
                    error=error,
                    reason="skill file identity could not be revalidated immediately before title/hash content I/O",
                )
            )
            continue

        pre_io_verdict = revalidate_skill_file_identity(file_before, file_pre_io)
        if pre_io_verdict.status != "STABLE":
            errors.append(
                DiscoveryError(
                    path=bounded_error_path(relative),
                    stage="identity",
                    error_type=skill_file_identity_error_type(pre_io_verdict.status),
                    reason=(
                        "pre-I/O skill file identity/topology revalidation rejected "
                        f"authority-facing content work: {pre_io_verdict.reason}"
                    ),
                )
            )
            continue

        try:
            content = observe_skill_content(
                path,
                max_bytes=MAX_SKILL_HASH_BYTES,
                max_title_scan_bytes=MAX_SKILL_TITLE_SCAN_BYTES,
                max_title_line_bytes=MAX_SKILL_TITLE_LINE_BYTES,
                max_title_chars=MAX_SKILL_TITLE_CHARS,
            )
        except SkillContentCustodyTitleResourceLimitError as error:
            errors.append(
                discovery_error(
                    relative=relative,
                    stage="title",
                    error=error,
                    reason="skill title extraction exceeded the declared resource budget inside one content observation",
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
        except SkillContentCustodyTextError as error:
            errors.append(
                discovery_error(
                    relative=relative,
                    stage="title",
                    error=error,
                    reason="skill file is not valid UTF-8 across the complete observed artifact",
                )
            )
            continue
        except SkillContentCustodyResourceLimitError as error:
            errors.append(
                discovery_error(
                    relative=relative,
                    stage="hash",
                    error=error,
                    reason="skill file exceeds the declared complete-content byte budget",
                )
            )
            continue
        except (SkillContentCustodyTopologyError, SkillContentCustodyChangedError) as error:
            errors.append(
                discovery_error(
                    relative=relative,
                    stage="identity",
                    error=error,
                    reason="single-artifact skill content custody rejected topology or object drift",
                )
            )
            continue
        except OSError as error:
            errors.append(
                discovery_error(
                    relative=relative,
                    stage="content",
                    error=error,
                    reason="single-artifact skill content could not be observed",
                )
            )
            continue

        title = content.title
        sha256 = content.sha256

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
    """Preserve the historical optional-return owner API while using exact admission."""

    try:
        return parse_generated_index_timestamp(value)
    except GeneratedIndexTimestampError:
        return None


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

    try:
        observation = observe_generated_index_artifact(
            path,
            max_bytes=MAX_GENERATED_INDEX_BYTES,
        )
        data = parse_generated_index_json(observation.utf8_text)
    except FileNotFoundError:
        return IndexVerdict(
            status="UNRESOLVED",
            reason="generated index path does not exist",
            path=str(path),
            source_head="",
            generated_at="",
            dirty_source=None,
            age_hours=None,
        )
    except (
        GeneratedIndexArtifactResourceLimitError,
        GeneratedIndexArtifactTopologyError,
        GeneratedIndexArtifactChangedError,
    ) as error:
        return IndexVerdict(
            status="UNRESOLVED",
            reason=f"generated index artifact admission rejected: {type(error).__name__}",
            path=str(path),
            source_head="",
            generated_at="",
            dirty_source=None,
            age_hours=None,
        )
    except (OSError, UnicodeDecodeError, GeneratedIndexJsonError) as error:
        return IndexVerdict(
            status="UNRESOLVED",
            reason=f"generated index is unreadable strict UTF-8 JSON: {type(error).__name__}",
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
        inspection_sha256=observation.sha256,
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

    try:
        cli_evidence = admit_cli_evidence(
            expected_head=args.expected_head,
            max_index_age_hours=args.max_index_age_hours,
        )
    except ProvenanceCliEvidenceError as error:
        parser.error(str(error))

    repo_root = Path(args.repo_root).resolve()
    snapshot_before = observe_repository_emission(repo_root)
    skills, discovery_errors = discover_skills(repo_root)
    snapshot_after = observe_repository_emission(repo_root)
    snapshot = assess_repository_snapshot(
        head_before=(snapshot_before.head if snapshot_before.status == "OBSERVED" else ""),
        head_after=(snapshot_after.head if snapshot_after.status == "OBSERVED" else ""),
        dirty_before=(snapshot_before.dirty if snapshot_before.status == "OBSERVED" else None),
        dirty_after=(snapshot_after.dirty if snapshot_after.status == "OBSERVED" else None),
    )

    now = datetime.now(timezone.utc)
    index_path = resolve_repo_path(repo_root, args.generated_index)
    stable_head = snapshot.head_after if snapshot.status == "STABLE_CLEAN" else ""
    stable_dirty = False if snapshot.status == "STABLE_CLEAN" else None
    index = inspect_generated_index(
        index_path,
        current_head=stable_head,
        current_tree_dirty=stable_dirty,
        max_age_hours=cli_evidence.max_index_age_hours,
        now=now,
    )

    observed_head = snapshot.head_after or snapshot.head_before
    head_error = ""
    if cli_evidence.expected_head and observed_head != cli_evidence.expected_head:
        head_error = (
            f"expected head {cli_evidence.expected_head}, observed {observed_head or '<unavailable>'}"
        )

    certification = certify_repository_skills(
        skills,
        snapshot_status=snapshot.status,
        expected_head_error=head_error,
    )

    emission_index_sha256 = ""
    emission_index_readable = False
    if index_path is not None and needs_generated_index_artifact_revalidation(index.status):
        try:
            emission_observation = observe_generated_index_artifact(
                index_path,
                max_bytes=MAX_GENERATED_INDEX_BYTES,
            )
            emission_index_sha256 = emission_observation.sha256
            emission_index_readable = True
        except (
            FileNotFoundError,
            GeneratedIndexArtifactResourceLimitError,
            GeneratedIndexArtifactTopologyError,
            GeneratedIndexArtifactChangedError,
            OSError,
            UnicodeDecodeError,
        ):
            emission_index_sha256 = ""
            emission_index_readable = False

    final_repository_observation = observe_repository_emission(repo_root)
    composition = compose_provenance_emission(
        prior_repository_authoritative=certification.authoritative,
        certified_head=(snapshot.head_after if snapshot.status == "STABLE_CLEAN" else ""),
        final_repository_observation=final_repository_observation,
        prior_generated_index_status=index.status,
        prior_generated_index_reason=index.reason,
        inspected_generated_index_sha256=index.inspection_sha256,
        emission_generated_index_sha256=emission_index_sha256,
        emission_generated_index_readable=emission_index_readable,
    )

    repository_path = project_report_path(repo_root, repo_root)
    generated_index_path = project_report_path(repo_root, index_path)
    final_head = (
        final_repository_observation.head
        if final_repository_observation.status == "OBSERVED"
        else ""
    )
    final_dirty = (
        final_repository_observation.dirty
        if final_repository_observation.status == "OBSERVED"
        else None
    )
    emitted_records = (
        certification.records if composition.repository_authoritative else ()
    )
    generated_index_report = {
        "status": composition.generated_index_status,
        "reason": composition.generated_index_reason,
        "inspectionStatus": index.status,
        "inspectionReason": index.reason,
        "path": generated_index_path.display_path,
        "pathScope": generated_index_path.scope,
        "sourceHead": index.source_head,
        "generatedAt": index.generated_at,
        "dirtySource": index.dirty_source,
        "ageHours": index.age_hours,
        "inspectionSha256": index.inspection_sha256,
        "emissionSha256": emission_index_sha256,
        "emissionArtifactStatus": composition.generated_index_artifact_status,
        "emissionArtifactReason": composition.generated_index_artifact_reason,
        "currentnessWithheld": composition.generated_index_currentness_withheld,
    }

    result = {
        "schema": "try-forever-skill-provenance.v6",
        "repositoryRoot": repository_path.display_path,
        "repositoryRootScope": repository_path.scope,
        "currentHead": final_head,
        "currentTreeDirty": final_dirty,
        "repositorySnapshot": asdict(snapshot),
        "reportEmissionRepository": {
            "status": composition.repository_status,
            "reason": composition.repository_reason,
            "authoritative": composition.repository_authoritative,
            "observedHead": final_head,
            "observedDirty": final_dirty,
        },
        "cliEvidence": {
            "expectedHead": cli_evidence.expected_head,
            "maxIndexAgeHours": cli_evidence.max_index_age_hours,
        },
        "expectedHeadError": head_error,
        "skillAuthority": {
            "status": certification.status,
            "reason": certification.reason,
            "authoritativeAtCertification": certification.authoritative,
            "emissionAuthoritative": composition.repository_authoritative,
            "emissionStatus": composition.repository_status,
            "emissionReason": composition.repository_reason,
        },
        "discoveredSkillCount": len(skills),
        "skillCount": len(emitted_records),
        "skills": [project_skill_record_for_report(record) for record in emitted_records],
        "discoveryErrors": [
            project_discovery_error_for_report(error) for error in discovery_errors
        ],
        "generatedIndex": generated_index_report,
        "authority": {
            "repositorySkill": "authority-facing records survive emission only after bounded direct discovery, exact Git-tracked candidate admission, STABLE_CLEAN certification, expected-head binding, and one late preservation-only repository observation; failed tracked custody or late custody zeroes emitted repository-skill authority",
            "generatedIndex": "bounded strict-UTF-8 JSON discovery aid with typed alias consistency and finite no-follow initial artifact admission; prior VERIFIED_CURRENT survives only when exact inspection SHA and late artifact SHA match under stable final repository custody",
            "reportPaths": "operator-facing paths are portable display projections only; root/generated-index paths use absolute/external projection, skill/discovery-error paths use the repository-relative display channel, collision-safe invisible/control projection applies to every serialized path family, and exact internal Path/record identities remain authority inputs rather than display text",
        },
        "capabilityBoundary": emitted_capability_boundary(),
    }
    print(json.dumps(result, indent=2, sort_keys=True))

    final_repository_failure = not composition.repository_authoritative
    final_index_strict_failure = (
        bool(args.generated_index)
        and composition.generated_index_status != "VERIFIED_CURRENT"
    )
    if args.strict and (
        head_error
        or discovery_errors
        or final_repository_failure
        or final_index_strict_failure
    ):
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
