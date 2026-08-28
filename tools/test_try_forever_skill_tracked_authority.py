#!/usr/bin/env python3
"""Regression source for fail-closed Git-tracked repository-skill authority."""

from try_forever_skill_tracked_authority import require_tracked_skill_candidates


def test_all_exact_candidates_tracked_pass():
    verdict = require_tracked_skill_candidates(
        ("skills/alpha/SKILL.md", "skills/beta/SKILL.md"),
        ("skills/alpha/SKILL.md", "skills/beta/SKILL.md", "README.md"),
    )
    assert verdict.status == "STABLE"
    assert verdict.untracked_paths == ()


def test_ignored_style_untracked_skill_fails_whole_authority_set():
    verdict = require_tracked_skill_candidates(
        ("skills/alpha/SKILL.md", "skills/ignored/SKILL.md"),
        ("skills/alpha/SKILL.md",),
    )
    assert verdict.status == "UNTRACKED_CANDIDATE"
    assert verdict.untracked_paths == ("skills/ignored/SKILL.md",)
    assert "partial repository-skill authority is forbidden" in verdict.reason


def test_case_drift_is_not_rewritten_into_tracked_authority():
    verdict = require_tracked_skill_candidates(
        ("skills/Alpha/SKILL.md",),
        ("skills/alpha/SKILL.md",),
    )
    assert verdict.status == "UNTRACKED_CANDIDATE"
    assert verdict.untracked_paths == ("skills/Alpha/SKILL.md",)


def test_empty_candidate_set_is_stable_without_inventing_authority_records():
    verdict = require_tracked_skill_candidates((), ("skills/alpha/SKILL.md",))
    assert verdict.status == "STABLE"
    assert verdict.untracked_paths == ()
