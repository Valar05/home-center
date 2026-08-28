#!/usr/bin/env python3
"""Supporting exact default-owner binding for TRY FOREVER owner-surgery patch custody.

The canonical owner may allow an omitted explicit ``# OWNER:`` header only when the patch itself
proves that it targets exactly the canonical default owner. An arbitrary textual mention of
``OperatorOverlayService.java`` is not ownership evidence.

This module owns no patch execution, grouping authority, phone lane, P0 work, or second custody
probe. The canonical custody owner now consumes this contract; that is source wiring only, not
regression execution, TESTED, runtime, deployment, delivery, or acceptance.

Patch text and the default-owner identity are machine evidence, not extensible Python callback
surfaces. Both public inputs must be exact built-in strings and cross finite direct-call source
throats before regex, formatting, or equality work. The canonical custody owner's artifact throat
still composes outside this helper; direct helper safety no longer depends on that caller.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


SCHEMA = "try-forever-owner-surgery-default-owner-binding.v1"
DEFAULT_OWNER = "android/operator-overlay/app/src/main/java/com/homecenter/operatoroverlay/OperatorOverlayService.java"
MAX_DEFAULT_OWNER_PATCH_CODEPOINTS = 1_048_576
MAX_DEFAULT_OWNER_IDENTITY_CODEPOINTS = 4_096
DIFF_HEADER_RE = re.compile(r"^diff --git ([^\r\n]*)\r?$", re.M)


class DefaultOwnerBindingError(ValueError):
    """Patch text does not prove one exact default-owner diff target."""


@dataclass(frozen=True)
class DefaultOwnerBinding:
    owner: str
    exact_diff_header: str


def _first_two_diff_headers(text: str) -> tuple[re.Match[str] | None, re.Match[str] | None]:
    matches = DIFF_HEADER_RE.finditer(text)
    return next(matches, None), next(matches, None)


def admit_default_owner_from_patch(
    text: object,
    *,
    default_owner: str = DEFAULT_OWNER,
) -> DefaultOwnerBinding:
    """Admit the default owner only from exactly one canonical Git diff header.

    The canonical owner has its own finite artifact reader, but this public helper also fails closed
    under direct use. It bounds exact patch text before regex traversal and bounds the exact default
    owner before expected-header formatting/equality. It observes only zero/one/at-least-two
    ``diff --git`` headers and performs no trimming, case folding, path normalization, basename
    matching, arbitrary substring search, or callback-capable string coercion.
    """

    if type(text) is not str:
        raise DefaultOwnerBindingError("patch text must be one exact built-in string")
    if len(text) > MAX_DEFAULT_OWNER_PATCH_CODEPOINTS:
        raise DefaultOwnerBindingError(
            "patch text exceeds fallback-owner source ceiling "
            f"{MAX_DEFAULT_OWNER_PATCH_CODEPOINTS} code points"
        )
    if type(default_owner) is not str or not default_owner:
        raise DefaultOwnerBindingError(
            "default owner must be one non-empty exact built-in repository-path string"
        )
    if len(default_owner) > MAX_DEFAULT_OWNER_IDENTITY_CODEPOINTS:
        raise DefaultOwnerBindingError(
            "default owner exceeds fallback-owner source ceiling "
            f"{MAX_DEFAULT_OWNER_IDENTITY_CODEPOINTS} code points"
        )

    first, second = _first_two_diff_headers(text)
    if first is None:
        raise DefaultOwnerBindingError(
            "patch without explicit owner must contain one exact diff --git header"
        )
    if second is not None:
        raise DefaultOwnerBindingError(
            "patch without explicit owner must target exactly one diff --git file; observed 2 or more"
        )

    expected_payload = f"a/{default_owner} b/{default_owner}"
    payload = first.group(1)
    if payload != expected_payload:
        raise DefaultOwnerBindingError(
            "patch without explicit owner does not target the exact canonical default owner"
        )

    return DefaultOwnerBinding(
        owner=default_owner,
        exact_diff_header=f"diff --git {payload}",
    )


def source_receipt() -> dict[str, object]:
    return {
        "schema": SCHEMA,
        "arbitraryOwnerSubstringAuthority": False,
        "exactBuiltinPatchTextAdmission": True,
        "boundedPatchTextAdmission": True,
        "patchTextCodepointCeiling": MAX_DEFAULT_OWNER_PATCH_CODEPOINTS,
        "exactBuiltinDefaultOwnerAdmission": True,
        "boundedDefaultOwnerAdmission": True,
        "defaultOwnerCodepointCeiling": MAX_DEFAULT_OWNER_IDENTITY_CODEPOINTS,
        "exactSingleDiffHeaderRequired": True,
        "multiFileFallbackRejected": True,
        "normalizationDependentPathAuthority": False,
        "canonicalOwnerConsumption": True,
        "regressionExecuted": False,
        "tested": False,
        "runtimeUi": False,
        "runtimeTalkBack": False,
        "phoneDelivered": False,
    }
