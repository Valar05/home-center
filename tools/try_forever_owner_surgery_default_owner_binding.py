#!/usr/bin/env python3
"""Supporting exact default-owner binding for TRY FOREVER owner-surgery patch custody.

The canonical owner may allow an omitted explicit ``# OWNER:`` header only when the patch itself
proves that it targets exactly the canonical default owner. An arbitrary textual mention of
``OperatorOverlayService.java`` is not ownership evidence.

This module owns no patch execution, grouping authority, phone lane, P0 work, or second custody
probe. Until the canonical owner consumes this contract, it is SUPPORTING SOURCE only.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


SCHEMA = "try-forever-owner-surgery-default-owner-binding.v1"
DEFAULT_OWNER = "android/operator-overlay/app/src/main/java/com/homecenter/operatoroverlay/OperatorOverlayService.java"
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

    The finite artifact reader in the canonical custody owner is the enclosing byte/resource throat.
    This policy observes only zero/one/at-least-two ``diff --git`` headers. It performs no trimming,
    case folding, path normalization, basename matching, or arbitrary substring search.
    """

    if not isinstance(text, str):
        raise DefaultOwnerBindingError("patch text must be one string")
    if not isinstance(default_owner, str) or not default_owner:
        raise DefaultOwnerBindingError("default owner must be one non-empty exact repository path")

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
        "exactSingleDiffHeaderRequired": True,
        "multiFileFallbackRejected": True,
        "normalizationDependentPathAuthority": False,
        "canonicalOwnerConsumption": False,
        "regressionExecuted": False,
        "tested": False,
        "runtimeUi": False,
        "runtimeTalkBack": False,
        "phoneDelivered": False,
    }
