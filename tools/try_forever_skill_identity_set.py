#!/usr/bin/env python3
"""Pure identity-set policy for repository skill provenance.

This module does not discover files, read the repository, render UI, schedule
work, touch a phone, or own P0 recovery. It exists so the current provenance
owner can decide whether a bounded candidate set is globally unambiguous before
any path is allowed to become repository-skill authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class SkillIdentityCollision:
    canonical_id: str
    paths: tuple[str, ...]


def casefold_skill_identity(path: str) -> str:
    """Return the existing case-insensitive ownership key for one repo path."""

    if not isinstance(path, str) or not path:
        raise ValueError("skill identity path must be a non-empty string")
    return path.casefold()


def find_case_insensitive_collisions(
    paths: Iterable[str],
) -> tuple[SkillIdentityCollision, ...]:
    """Return deterministic collision groups without choosing a winner.

    The caller may use this before title/hash work. A collision group is not a
    ranking: every member is ambiguous under the existing case-insensitive
    ownership rule, so first-wins / last-wins authority is forbidden.
    """

    groups: dict[str, set[str]] = {}
    for path in paths:
        canonical = casefold_skill_identity(path)
        groups.setdefault(canonical, set()).add(path)

    collisions = [
        SkillIdentityCollision(
            canonical_id=canonical,
            paths=tuple(sorted(members)),
        )
        for canonical, members in groups.items()
        if len(members) > 1
    ]
    collisions.sort(key=lambda collision: (collision.canonical_id, collision.paths))
    return tuple(collisions)


def has_ambiguous_skill_identity(paths: Iterable[str]) -> bool:
    """Return whether any case-insensitive owner key has multiple repo paths."""

    return bool(find_case_insensitive_collisions(paths))
