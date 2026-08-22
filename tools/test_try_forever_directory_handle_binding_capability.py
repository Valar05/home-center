#!/usr/bin/env python3
"""Regression source for platform-specific directory-handle custody capability.

Source fixture only. Execution and filesystem behavior must be evidenced separately.
"""

from try_forever_directory_handle_binding_capability import (
    classify_directory_handle_binding_capability,
)


def test_posix_with_all_required_primitives_is_source_ready_only():
    verdict = classify_directory_handle_binding_capability(
        os_name="posix",
        scandir_accepts_fd=True,
        open_accepts_dir_fd=True,
        stat_accepts_dir_fd=True,
        stat_accepts_follow_symlinks=True,
        has_o_directory=True,
        has_o_nofollow=True,
    )
    assert verdict.status == "SUPPORTED_POSIX_PRIMITIVES"
    assert "does not prove filesystem atomicity" in verdict.boundary


def test_non_posix_never_inherits_posix_atomicity_claim():
    verdict = classify_directory_handle_binding_capability(
        os_name="nt",
        scandir_accepts_fd=True,
        open_accepts_dir_fd=True,
        stat_accepts_dir_fd=True,
        stat_accepts_follow_symlinks=True,
        has_o_directory=True,
        has_o_nofollow=True,
    )
    assert verdict.status == "PORTABLE_ATOMIC_BINDING_UNAVAILABLE"


def test_each_missing_primitive_fails_closed():
    cases = (
        dict(scandir_accepts_fd=False, open_accepts_dir_fd=True, stat_accepts_dir_fd=True, stat_accepts_follow_symlinks=True, has_o_directory=True, has_o_nofollow=True),
        dict(scandir_accepts_fd=True, open_accepts_dir_fd=False, stat_accepts_dir_fd=True, stat_accepts_follow_symlinks=True, has_o_directory=True, has_o_nofollow=True),
        dict(scandir_accepts_fd=True, open_accepts_dir_fd=True, stat_accepts_dir_fd=False, stat_accepts_follow_symlinks=True, has_o_directory=True, has_o_nofollow=True),
        dict(scandir_accepts_fd=True, open_accepts_dir_fd=True, stat_accepts_dir_fd=True, stat_accepts_follow_symlinks=False, has_o_directory=True, has_o_nofollow=True),
        dict(scandir_accepts_fd=True, open_accepts_dir_fd=True, stat_accepts_dir_fd=True, stat_accepts_follow_symlinks=True, has_o_directory=False, has_o_nofollow=True),
        dict(scandir_accepts_fd=True, open_accepts_dir_fd=True, stat_accepts_dir_fd=True, stat_accepts_follow_symlinks=True, has_o_directory=True, has_o_nofollow=False),
    )
    for case in cases:
        verdict = classify_directory_handle_binding_capability(os_name="posix", **case)
        assert verdict.status == "PORTABLE_ATOMIC_BINDING_UNAVAILABLE"
        assert "Do not upgrade pathname pre/post revalidation" in verdict.boundary
