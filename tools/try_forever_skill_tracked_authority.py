#!/usr/bin/env python3
"""Pure tracked-set authority policy for TRY FOREVER repository skills.

Direct filesystem discovery can observe an ordinary ``skills/**/SKILL.md`` that is
not tracked by Git. A clean ``git status --untracked-files=normal`` observation is
not sufficient to rule that out because ignored files are intentionally omitted
from ordinary untracked output. Repository-skill authority therefore needs an
independent tracked-set admission gate.

This module deliberately does not run Git, walk the filesystem, render UI, touch
phone/P0 surfaces, or create a second provenance owner. It only compares exact
repository-relative identities supplied by the existing provenance pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class TrackedSkillAuthorityVerdict:
    status: str
    reason: str
    untracked_paths: tuple[str, ...]


def require_tracked_skill_candidates(
    candidate_paths: Iterable[str],
    tracked_paths: Iterable[str],
) -> TrackedSkillAuthorityVerdict:
    """Fail the whole candidate authority set when any exact path is untracked.

    The comparison is intentionally exact. Case folding, path normalization, or
    first/last-wins alias selection belong to other already-existing identity
    policies; this gate must not silently rewrite repository identity to make an
    untracked candidate appear tracked.
    """

    candidates = tuple(candidate_paths)
    tracked = frozenset(tracked_paths)
    untracked = tuple(sorted({path for path in candidates if path not in tracked}))

    if untracked:
        return TrackedSkillAuthorityVerdict(
            status="UNTRACKED_CANDIDATE",
            reason=(
                "at least one discovered SKILL.md is not present in the supplied "
                "Git-tracked identity set; partial repository-skill authority is forbidden"
            ),
            untracked_paths=untracked,
        )

    return TrackedSkillAuthorityVerdict(
        status="STABLE",
        reason="every discovered repository-skill identity is present in the supplied Git-tracked set",
        untracked_paths=(),
    )
