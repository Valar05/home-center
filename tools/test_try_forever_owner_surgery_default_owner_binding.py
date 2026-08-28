#!/usr/bin/env python3
"""Hostile regression source for exact default-owner patch binding.

SOURCE ONLY / UNEXECUTED. The canonical owner currently accepts an omitted explicit owner when the
patch text merely mentions ``OperatorOverlayService.java`` somewhere. These fixtures pin the
stronger supporting contract without claiming owner integration or TESTED state.
"""

from try_forever_owner_surgery_default_owner_binding import (
    DEFAULT_OWNER,
    DefaultOwnerBindingError,
    admit_default_owner_from_patch,
)


def exact_header() -> str:
    return f"diff --git a/{DEFAULT_OWNER} b/{DEFAULT_OWNER}"


def test_exact_single_default_owner_diff_header_is_admitted():
    result = admit_default_owner_from_patch(
        exact_header() + "\n--- a/" + DEFAULT_OWNER + "\n+++ b/" + DEFAULT_OWNER + "\n"
    )
    assert result.owner == DEFAULT_OWNER
    assert result.exact_diff_header == exact_header()


def test_arbitrary_textual_mention_is_not_owner_authority():
    text = (
        "# this patch discusses OperatorOverlayService.java but changes something else\n"
        "diff --git a/tools/other.py b/tools/other.py\n"
    )
    try:
        admit_default_owner_from_patch(text)
    except DefaultOwnerBindingError:
        pass
    else:
        raise AssertionError("arbitrary owner mention must not earn default-owner authority")


def test_missing_diff_header_is_rejected_even_with_default_owner_basename_mention():
    try:
        admit_default_owner_from_patch("OperatorOverlayService.java\n")
    except DefaultOwnerBindingError:
        pass
    else:
        raise AssertionError("basename mention is not diff ownership evidence")


def test_wrong_exact_path_is_rejected_without_normalization():
    wrong_case = DEFAULT_OWNER.replace("OperatorOverlayService.java", "operatoroverlayservice.java")
    try:
        admit_default_owner_from_patch(f"diff --git a/{wrong_case} b/{wrong_case}\n")
    except DefaultOwnerBindingError:
        pass
    else:
        raise AssertionError("case-drifted owner path must not be normalized into authority")


def test_multifile_patch_is_rejected_even_when_one_file_is_default_owner():
    text = (
        exact_header()
        + "\n"
        + "diff --git a/tools/neighbor.py b/tools/neighbor.py\n"
    )
    try:
        admit_default_owner_from_patch(text)
    except DefaultOwnerBindingError:
        pass
    else:
        raise AssertionError("implicit default-owner fallback must not bless multi-file surgery")


def test_duplicate_same_diff_header_is_still_ambiguous():
    text = exact_header() + "\n" + exact_header() + "\n"
    try:
        admit_default_owner_from_patch(text)
    except DefaultOwnerBindingError:
        pass
    else:
        raise AssertionError("duplicate diff headers remain ambiguous authority evidence")


def test_crlf_framing_does_not_change_exact_payload():
    result = admit_default_owner_from_patch(exact_header() + "\r\n")
    assert result.owner == DEFAULT_OWNER
