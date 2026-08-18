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
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

DEFAULT_MAX_INDEX_AGE_HOURS = 14 * 24
MAX_FUTURE_SKEW_SECONDS = 5 * 60
MAX_DISCOVERY_ERROR_PATH_CHARS = 512
MAX_SKILL_TITLE_SCAN_BYTES = 64 * 1024
MAX_SKILL_TITLE_LINE_BYTES = 8 * 1024
MAX_SKILL_TITLE_CHARS = 256
MAX_SKILL_HASH_BYTES = 1024 * 1024
SKILL_HASH_CHUNK_BYTES = 64 * 1024


class SkillTitleResourceLimitError(ValueError):
    """A SKILL.md title cannot be admitted within the declared resource budget."""


class SkillHashResourceLimitError(ValueError):
    """A SKILL.md cannot earn a full-file SHA inside the declared byte budget."""


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
    """Return an exact whole-file SHA only after EOF is reached inside budget.

    The extra one-byte read at the limit distinguishes an exact-max file from a
    max+1 file. An oversized file is rejected; a prefix digest is never returned
    as repository-skill authority.
    """

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
    """Read one bounded H1 title without truncating hostile input into authority."""

    scanned_bytes = 0
    with path.open("rb") as handle:
        while scanned_bytes < MAX_SKILL_TITLE_SCAN_BYTES:
            remaining_scan = MAX_SKILL_TITLE_SCAN_BYTES - scanned_bytes
            read_limit = min(MAX_SKILL_TITLE_LINE_BYTES, remaining_scan)
            raw_line = handle.readline(read_limit + 1)
            if not raw_line:
                return path.parent.name

            scanned_bytes += len(raw_line)
            if len(raw_line) > read_limit:
                raise SkillTitleResourceLimitError(
                    "skill title scan exceeded its byte/line budget"
                )

            line = raw_line.decode("utf-8")
            stripped = line.strip()
            if stripped.startswith("# "):
                title = stripped[2:].strip()
                if len(title) > MAX_SKILL_TITLE_CHARS:
                    raise SkillTitleResourceLimitError(
                        "skill title exceeds its character budget"
                    )
                return title

        if handle.read(1):
            raise SkillTitleResourceLimitError(
                "skill title was not resolved within the scan budget"
            )
    return path.parent.name


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
    if not value:
        return None
    candidate = Path(value)
    if not candidate.is_absolute():
        candidate = repo_root / candidate
    return candidate.resolve()


def discover_skills(repo_root: Path) -> tuple[list[SkillRecord], list[DiscoveryError]]:
    """Discover independent skill records with fail-closed per-file isolation.

    Cheap bounded title admission intentionally precedes whole-file hashing. A
    malformed/over-budget title therefore cannot force an unnecessary full-file
    hash. A valid short title with an oversized body reaches the hash throat and
    is rejected there; healthy peers continue.
    """

    skills_root = repo_root / "skills"
    if not skills_root.is_dir():
        return [], [
            DiscoveryError(
                path="skills",
                stage="repository",
                error_type="MissingSkillsDirectory",
                reason="skills directory is missing",
            )
        ]

    records: list[SkillRecord] = []
    errors: list[DiscoveryError] = []
    canonical_seen: dict[str, str] = {}
    for path in sorted(skills_root.rglob("SKILL.md")):
        if not path.is_file():
            continue
        relative = path.relative_to(repo_root).as_posix()
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
        canonical = relative.casefold()
        prior = canonical_seen.get(canonical)
        if prior is not None and prior != relative:
            errors.append(
                DiscoveryError(
                    path=bounded_error_path(relative),
                    stage="identity",
                    error_type="CaseInsensitiveIdentityCollision",
                    reason="repository-skill identity collides case-insensitively with another path",
                    related_path=bounded_error_path(prior),
                )
            )
            continue
        canonical_seen[canonical] = relative

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

        records.append(SkillRecord(path=relative, sha256=sha256, title=title))
    return records, errors


def first_value(data: dict[str, Any], keys: Iterable[str]) -> Any:
    for key in keys:
        if key in data:
            return data[key]
    return None


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
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        return IndexVerdict(
            status="UNRESOLVED",
            reason=f"generated index is unreadable JSON: {type(error).__name__}",
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

    source_head = str(
        first_value(data, ("sourceHead", "source_head", "gitHead", "git_head")) or ""
    )
    generated_raw = first_value(
        data,
        (
            "generatedAt",
            "generated_at",
            "generatedAtMs",
            "generated_at_ms",
            "updatedAt",
            "updated_at",
        ),
    )
    generated_dt = parse_timestamp(generated_raw)
    dirty_raw = first_value(
        data, ("dirtySource", "dirty_source", "sourceDirty", "source_dirty")
    )
    dirty_source = dirty_raw if isinstance(dirty_raw, bool) else None
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

    result = {
        "schema": "try-forever-skill-provenance.v2",
        "repositoryRoot": str(repo_root),
        "currentHead": observed_head,
        "currentTreeDirty": dirty_after,
        "repositorySnapshot": asdict(snapshot),
        "expectedHeadError": head_error,
        "skillCount": len(skills),
        "skills": [asdict(record) for record in skills],
        "discoveryErrors": [asdict(error) for error in discovery_errors],
        "generatedIndex": asdict(index),
        "authority": {
            "repositorySkill": "direct current-tree skills/**/SKILL.md readback under a STABLE_CLEAN pre/post discovery snapshot",
            "generatedIndex": "discovery aid only unless VERIFIED_CURRENT; never substitutes for direct skill existence",
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
