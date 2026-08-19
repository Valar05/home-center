#!/usr/bin/env python3
"""Regression source for single-command report-emission repository observation."""

from try_forever_repository_emission_observation import (
    parse_porcelain_v2_branch_status,
)


HEAD = "0123456789abcdef0123456789abcdef01234567"
HEAD_SHA256 = "0123456789abcdef" * 4


def test_clean_porcelain_v2_observation_keeps_head_and_cleanliness_together():
    observed = parse_porcelain_v2_branch_status(
        f"# branch.oid {HEAD}\n# branch.head feature/provenance\n"
    )
    assert observed.status == "OBSERVED"
    assert observed.head == HEAD
    assert observed.dirty is False


def test_sha256_repository_object_id_is_also_canonical():
    observed = parse_porcelain_v2_branch_status(
        f"# branch.oid {HEAD_SHA256}\n# branch.head future-object-format\n"
    )
    assert observed.status == "OBSERVED"
    assert observed.head == HEAD_SHA256
    assert observed.dirty is False


def test_tracked_change_marks_same_observation_dirty():
    observed = parse_porcelain_v2_branch_status(
        f"# branch.oid {HEAD}\n"
        "1 .M N... 100644 100644 100644 abc def tools/probe.py\n"
    )
    assert observed.status == "OBSERVED"
    assert observed.head == HEAD
    assert observed.dirty is True


def test_untracked_change_marks_same_observation_dirty():
    observed = parse_porcelain_v2_branch_status(
        f"# branch.oid {HEAD}\n? receipts/new.json\n"
    )
    assert observed.status == "OBSERVED"
    assert observed.dirty is True


def test_unborn_missing_or_malformed_oid_fails_closed():
    unborn = parse_porcelain_v2_branch_status(
        "# branch.oid (initial)\n# branch.head main\n"
    )
    missing = parse_porcelain_v2_branch_status("# branch.head main\n")
    malformed = parse_porcelain_v2_branch_status(
        "# branch.oid NOT-A-CANONICAL-OID\n# branch.head main\n"
    )
    uppercase = parse_porcelain_v2_branch_status(
        f"# branch.oid {HEAD.upper()}\n# branch.head main\n"
    )
    for observed in (unborn, missing, malformed, uppercase):
        assert observed.status == "UNAVAILABLE"
        assert observed.head == ""
        assert observed.dirty is None


def test_comment_headers_do_not_create_false_dirty_state():
    observed = parse_porcelain_v2_branch_status(
        f"# branch.oid {HEAD}\n"
        "# branch.head (detached)\n"
        "# branch.upstream origin/main\n"
        "# branch.ab +0 -0\n"
    )
    assert observed.status == "OBSERVED"
    assert observed.dirty is False
