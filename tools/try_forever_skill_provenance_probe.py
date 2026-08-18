#!/usr/bin/env python3
"""Deterministic repository-local provenance probe for TRY FOREVER skill lights.

This tool deliberately uses only the checked-out repository as authority for
``repository_skill`` provenance. Generated indexes may help discovery, but they
cannot prove that a current ``skills/**/SKILL.md`` exists.

It owns no network calls, renderer, scheduler, phone surface, or P0 recovery.
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


@dataclass(frozen=True)
class SkillRecord:
    path: str
    sha256: str
    title: str


@dataclass(frozen=True)
class IndexVerdict:
    status: str
    reason: str
    path: str
    source_head: str
    generated_at: str
    dirty_source: bool | None
    age_hours: float | None


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def markdown_title(path: Path) -> str:
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if stripped.startswith("# "):
                return stripped[2:].strip()
    return path.parent.name


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


def discover_skills(repo_root: Path) -> tuple[list[SkillRecord], list[str]]:
    skills_root = repo_root / "skills"
    if not skills_root.is_dir():
        return [], ["skills directory is missing"]

    records: list[SkillRecord] = []
    errors: list[str] = []
    canonical_seen: dict[str, str] = {}
    for path in sorted(skills_root.rglob("SKILL.md")):
        if not path.is_file():
            continue
        if not is_within(path, skills_root):
            errors.append(f"skill path escapes skills root: {path}")
            continue
        relative = path.relative_to(repo_root).as_posix()
        canonical = relative.casefold()
        prior = canonical_seen.get(canonical)
        if prior is not None and prior != relative:
            errors.append(
                f"case-insensitive repository-skill identity collision: {prior} vs {relative}"
            )
            continue
        canonical_seen[canonical] = relative
        records.append(
            SkillRecord(
                path=relative,
                sha256=sha256_file(path),
                title=markdown_title(path),
            )
        )
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

    source_head = str(first_value(data, ("sourceHead", "source_head", "gitHead", "git_head")) or "")
    generated_raw = first_value(
        data,
        ("generatedAt", "generated_at", "generatedAtMs", "generated_at_ms", "updatedAt", "updated_at"),
    )
    generated_dt = parse_timestamp(generated_raw)
    dirty_raw = first_value(data, ("dirtySource", "dirty_source", "sourceDirty", "source_dirty"))
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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--generated-index")
    parser.add_argument("--max-index-age-hours", type=float, default=DEFAULT_MAX_INDEX_AGE_HOURS)
    parser.add_argument("--expected-head", default="")
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    head = git_head(repo_root)
    dirty = git_dirty(repo_root)
    skills, discovery_errors = discover_skills(repo_root)
    now = datetime.now(timezone.utc)
    index_path = resolve_repo_path(repo_root, args.generated_index)
    index = inspect_generated_index(
        index_path,
        current_head=head,
        current_tree_dirty=dirty,
        max_age_hours=max(0.0, args.max_index_age_hours),
        now=now,
    )

    head_error = ""
    if args.expected_head and head != args.expected_head:
        head_error = f"expected head {args.expected_head}, observed {head or '<unavailable>'}"

    result = {
        "schema": "try-forever-skill-provenance.v1",
        "repositoryRoot": str(repo_root),
        "currentHead": head,
        "currentTreeDirty": dirty,
        "expectedHeadError": head_error,
        "skillCount": len(skills),
        "skills": [asdict(record) for record in skills],
        "discoveryErrors": discovery_errors,
        "generatedIndex": asdict(index),
        "authority": {
            "repositorySkill": "direct current-tree skills/**/SKILL.md readback",
            "generatedIndex": "discovery aid only unless VERIFIED_CURRENT; never substitutes for direct skill existence",
        },
        "capabilityBoundary": {
            "sourceProbe": True,
            "probeExecutedByThisArtifact": False,
            "tested": False,
            "runtimeUi": False,
            "phoneDelivery": False,
        },
    }
    print(json.dumps(result, indent=2, sort_keys=True))

    index_strict_failure = bool(args.generated_index) and index.status != "VERIFIED_CURRENT"
    if args.strict and (head_error or discovery_errors or index_strict_failure):
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
