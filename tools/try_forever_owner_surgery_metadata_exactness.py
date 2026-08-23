#!/usr/bin/env python3
"""Supporting exact-metadata contract for owner-surgery custody.

This module owns no surgery classification, promotion authority, patch execution, overlay controller,
phone lane, or P0 work. It exists to close two source-evidence ambiguities before the canonical v10
custody owner adopts them:

1. authenticated owner identity is exact machine evidence, not text to repair with ``strip()``;
2. textual patch base/state/owner headers are cardinality-one evidence, never first-match evidence.

The canonical owner remains ``try_forever_owner_surgery_custody_probe.py``. Until that owner consumes
this contract, these rules are SUPPORTING SOURCE only.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from try_forever_owner_surgery_state_policy import admit_owner_surgery_state


SCHEMA = "try-forever-owner-surgery-metadata-exactness.v1"
SHA1_RE = re.compile(r"^[0-9a-f]{40}$")
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
    """Admit one owner identity without trimming or case/Unicode normalization.

    Internal spaces remain legal. Leading/trailing whitespace does not: accepting it would make CLI
    and programmatic custody disagree about which exact machine key was authenticated.
    """

    if not isinstance(value, str) or not value:
        raise OwnerSurgeryMetadataError(f"{field} must be one non-empty string")
    if value != value.strip():
        raise OwnerSurgeryMetadataError(
            f"{field} must already be exact owner identity; leading/trailing whitespace is not admitted"
        )
    return value


def _one_header_value(pattern: re.Pattern[str], text: str, *, field: str) -> str:
    matches = list(pattern.finditer(text))
    if not matches:
        raise OwnerSurgeryMetadataError(f"patch is missing {field}")
    if len(matches) != 1:
        raise OwnerSurgeryMetadataError(
            f"patch must contain exactly one {field}; observed {len(matches)}"
        )
    return matches[0].group(1)


def admit_patch_metadata(text: object) -> PatchMetadataAdmission:
    """Admit cardinality-one textual patch metadata without first-match authority."""

    if not isinstance(text, str):
        raise OwnerSurgeryMetadataError("patch text must be one string")

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
    owner_headers = list(OWNER_HEADER_RE.finditer(text))
    if len(owner_headers) > 1:
        raise OwnerSurgeryMetadataError(
            f"patch must contain at most one explicit owner header; observed {len(owner_headers)}"
        )

    if SHA1_RE.fullmatch(base_blob) is None:
        raise OwnerSurgeryMetadataError(
            "patch base-owner blob must already be 40 lowercase hexadecimal characters"
        )

    state_admission = admit_owner_surgery_state(state_text)
    explicit_owner = (
        admit_owner_identity(owner_headers[0].group(1), field="patch owner")
        if owner_headers
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
        "patchHeaderCardinalityExact": True,
        "malformedDuplicateHeadersCounted": True,
        "headerRecognitionLineLocal": True,
        "crlfFramingPreserved": True,
        "canonicalOwnerConsumption": False,
        "regressionExecuted": False,
        "tested": False,
        "runtimeUi": False,
        "runtimeTalkBack": False,
        "phoneDelivered": False,
    }
