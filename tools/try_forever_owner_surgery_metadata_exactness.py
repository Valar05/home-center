#!/usr/bin/env python3
"""Supporting exact-metadata contract for owner-surgery custody.

This module owns no surgery classification, promotion authority, patch execution, overlay controller,
phone lane, or P0 work. It closes three source-evidence ambiguities before the canonical v10 custody
owner groups or promotes surgery artifacts:

1. authenticated owner identity is an exact bounded built-in string, not caller-owned Python text and
   not text to repair with ``strip()``;
2. textual patch base/state/owner headers are cardinality-one evidence, never first-match evidence;
3. owner identity has a small source ceiling before it can become a report/group key.

The canonical owner remains ``try_forever_owner_surgery_custody_probe.py`` and consumes this contract.
That is source wiring only, not regression execution, TESTED, runtime, deployment, delivery, or
acceptance.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from try_forever_owner_surgery_state_policy import admit_owner_surgery_state


SCHEMA = "try-forever-owner-surgery-metadata-exactness.v1"
SHA1_RE = re.compile(r"^[0-9a-f]{40}$")
MAX_OWNER_IDENTITY_CODEPOINTS = 4_096
# Header-name recognition is intentionally separate from value admission. A malformed second header
# still counts as duplicate authority evidence and cannot disappear merely because its value would
# fail later validation. Horizontal whitespace is line-local; ``\s`` is deliberately avoided here
# because it can consume newlines and blur authority records across lines. A terminal CR is framing
# for a CRLF line, not part of the authority value.
BASE_HEADER_RE = re.compile(
    r"^#[ \t]*(?:BASE OWNER BLOB|Base owner blob|Base blob)[ \t]*:[ \t]*(.*?)[ \t]*(?:\r)?$",
    re.I | re.M,
)
OWNER_HEADER_RE = re.compile(
    r"^#[ \t]*(?:OWNER|Target|Base path)[ \t]*:[ \t]*(.*?)[ \t]*(?:\r)?$",
    re.I | re.M,
)
STATE_HEADER_RE = re.compile(
    r"^#[ \t]*(?:STATUS|State)[ \t]*:[ \t]*(.*?)[ \t]*(?:\r)?$",
    re.I | re.M,
)


class OwnerSurgeryMetadataError(ValueError):
    """Owner-surgery machine evidence is ambiguous or normalization-dependent."""


@dataclass(frozen=True)
class PatchMetadataAdmission:
    base_blob: str
    state: str
    promotion_candidate: bool
    explicit_owner: str | None


def admit_owner_identity(value: object, *, field: str = "owner") -> str:
    """Admit one owner identity without callbacks, trimming, or Unicode normalization.

    Owner identity is machine evidence. A ``str`` subclass can override methods such as ``strip`` and
    execute caller-owned Python before evidence admission, so this boundary accepts only the exact
    built-in ``str`` container. Internal spaces remain legal. Leading/trailing whitespace does not.
    """

    if type(value) is not str or not value:
        raise OwnerSurgeryMetadataError(
            f"{field} must be one non-empty exact built-in string"
        )
    if len(value) > MAX_OWNER_IDENTITY_CODEPOINTS:
        raise OwnerSurgeryMetadataError(
            f"{field} exceeds owner-identity source ceiling "
            f"{MAX_OWNER_IDENTITY_CODEPOINTS} code points"
        )
    if value != value.strip():
        raise OwnerSurgeryMetadataError(
            f"{field} must already be exact owner identity; leading/trailing whitespace is not admitted"
        )
    return value


def _first_two_matches(pattern: re.Pattern[str], text: str) -> tuple[re.Match[str] | None, re.Match[str] | None]:
    """Observe only enough matching headers to decide cardinality-one authority.

    Canonical custody already gives this policy bounded artifact text. This additional throat avoids
    materializing an adversarial list of every matching header when the only useful distinction is
    zero, one, or at least two.
    """

    matches = pattern.finditer(text)
    first = next(matches, None)
    second = next(matches, None)
    return first, second


def _one_header_value(pattern: re.Pattern[str], text: str, *, field: str) -> str:
    first, second = _first_two_matches(pattern, text)
    if first is None:
        raise OwnerSurgeryMetadataError(f"patch is missing {field}")
    if second is not None:
        raise OwnerSurgeryMetadataError(
            f"patch must contain exactly one {field}; observed 2 or more"
        )
    return first.group(1)


def admit_patch_metadata(text: object) -> PatchMetadataAdmission:
    """Admit cardinality-one textual patch metadata without first-match authority."""

    if type(text) is not str:
        raise OwnerSurgeryMetadataError("patch text must be one exact built-in string")

    base_blob = _one_header_value(
        BASE_HEADER_RE,
        text,
        field="base-owner blob header",
    )
    state_text = _one_header_value(
        STATE_HEADER_RE,
        text,
        field="state/status header",
    )
    owner_first, owner_second = _first_two_matches(OWNER_HEADER_RE, text)
    if owner_second is not None:
        raise OwnerSurgeryMetadataError(
            "patch must contain at most one explicit owner header; observed 2 or more"
        )

    if SHA1_RE.fullmatch(base_blob) is None:
        raise OwnerSurgeryMetadataError(
            "patch base-owner blob must already be 40 lowercase hexadecimal characters"
        )

    state_admission = admit_owner_surgery_state(state_text)
    explicit_owner = (
        admit_owner_identity(owner_first.group(1), field="patch owner")
        if owner_first is not None
        else None
    )

    return PatchMetadataAdmission(
        base_blob=base_blob,
        state=state_admission.state,
        promotion_candidate=state_admission.promotion_candidate,
        explicit_owner=explicit_owner,
    )


def source_receipt() -> dict[str, object]:
    return {
        "schema": SCHEMA,
        "ownerIdentityExact": True,
        "exactBuiltinOwnerStringAdmission": True,
        "boundedOwnerIdentityAdmission": True,
        "ownerIdentityCodepointCeiling": MAX_OWNER_IDENTITY_CODEPOINTS,
        "patchHeaderCardinalityExact": True,
        "headerCardinalityScanBounded": True,
        "malformedDuplicateHeadersCounted": True,
        "headerRecognitionLineLocal": True,
        "crlfFramingPreserved": True,
        "canonicalOwnerConsumption": True,
        "regressionExecuted": False,
        "tested": False,
        "runtimeUi": False,
        "runtimeTalkBack": False,
        "deployed": False,
        "callable": False,
        "executed": False,
        "delivered": False,
        "accepted": False,
        "phoneDelivered": False,
    }
