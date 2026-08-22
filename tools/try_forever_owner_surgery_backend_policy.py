#!/usr/bin/env python3
"""Pure backend-selection contract for TRY FOREVER owner-surgery custody.

This module does not inspect the repository, apply patches, execute Android, touch Phone/P0, or
replace the canonical v10 custody owner. It defines how a future composition may choose between the
portable pathname-revalidation backend and the stronger POSIX held-directory backend without
silently weakening evidence after a stronger backend has already been admitted.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass
import re


SUPPORTED_POSIX = "SUPPORTED_POSIX_PRIMITIVES"
PORTABLE_UNAVAILABLE = "PORTABLE_ATOMIC_BINDING_UNAVAILABLE"
PORTABLE_BACKEND = "PORTABLE_PATHNAME_REVALIDATION"
DESCRIPTOR_BACKEND = "HELD_DIRECTORY_DESCRIPTOR"

REQUIRED_OWNER_EVIDENCE_FIELDS = (
    "artifactDirectoryEntriesObserved",
    "artifactCandidatesObserved",
    "discoveryErrors",
    "currentOwnerBlobs",
)
OWNER_AUTHORITY_FIELDS = (
    "collisionSets",
    "staleBaseGroups",
    "unverifiedBaseGroups",
)
AUTHORITY_STATUS_BY_FIELD = {
    "collisionSets": "CURRENT_BASE_COLLISION_SET",
    "staleBaseGroups": "STALE_BASE_GROUP",
    "unverifiedBaseGroups": "UNVERIFIED_BASE_GROUP",
}
SHA1_RE = re.compile(r"^[0-9a-f]{40}$")


@dataclass(frozen=True)
class OwnerSurgeryBackendSelection:
    backend: str
    capability_status: str
    descriptor_selected: bool
    portable_is_primary: bool
    fallback_after_backend_failure: bool
    required_owner_evidence_fields: tuple[str, ...]
    boundary: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def select_owner_surgery_backend(capability_status: str) -> OwnerSurgeryBackendSelection:
    """Select one backend from admitted platform capability.

    Unsupported descriptor primitives do not mean failure: the canonical portable v10 pathname
    bracket remains the primary backend. When the runtime *does* admit the required POSIX
    primitives, a future canonical-owner composition may select held-descriptor custody. Once that
    stronger backend is selected for a classification attempt, descriptor setup/inventory/artifact
    failure must fail the attempt closed; it may not retry through the weaker pathname backend and
    call the result equivalent evidence.
    """

    if capability_status == SUPPORTED_POSIX:
        return OwnerSurgeryBackendSelection(
            backend=DESCRIPTOR_BACKEND,
            capability_status=capability_status,
            descriptor_selected=True,
            portable_is_primary=False,
            fallback_after_backend_failure=False,
            required_owner_evidence_fields=REQUIRED_OWNER_EVIDENCE_FIELDS,
            boundary=(
                "Held-directory custody is the selected source backend. A descriptor custody wound "
                "fails this classification attempt closed; do not silently downgrade to portable "
                "pathname custody after selection. Preserve the canonical owner evidence fields."
            ),
        )

    if capability_status == PORTABLE_UNAVAILABLE:
        return OwnerSurgeryBackendSelection(
            backend=PORTABLE_BACKEND,
            capability_status=capability_status,
            descriptor_selected=False,
            portable_is_primary=True,
            fallback_after_backend_failure=False,
            required_owner_evidence_fields=REQUIRED_OWNER_EVIDENCE_FIELDS,
            boundary=(
                "Descriptor primitives are unavailable on this platform surface. Keep canonical "
                "portable v10 pathname revalidation as the primary backend and preserve its "
                "persistent-drift/atomicity boundary."
            ),
        )

    raise ValueError(f"unsupported directory-handle capability status: {capability_status!r}")


def classify_selected_backend_failure(
    selection: OwnerSurgeryBackendSelection,
    failure_boundary: str,
) -> dict[str, object]:
    """Project a backend failure without inventing a weaker retry path."""

    if not isinstance(failure_boundary, str) or not failure_boundary:
        raise ValueError("failure boundary must be one non-empty string")
    return {
        "backend": selection.backend,
        "status": "FAIL_CLOSED",
        "boundary": failure_boundary,
        "portableFallbackAttempted": False,
        "ownerEvidenceAdmitted": False,
    }


def _nonnegative_int(result: Mapping[str, object], field: str) -> int:
    value = result.get(field)
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{field} must be one non-negative integer")
    return value


def _admit_current_owner_blobs(result: Mapping[str, object]) -> dict[str, str]:
    raw = result.get("currentOwnerBlobs")
    if not isinstance(raw, Mapping):
        raise ValueError("currentOwnerBlobs must be one mapping")

    admitted: dict[str, str] = {}
    for owner, blob in raw.items():
        if not isinstance(owner, str) or not owner:
            raise ValueError("currentOwnerBlobs keys must be non-empty owner strings")
        if not isinstance(blob, str) or SHA1_RE.fullmatch(blob) is None:
            raise ValueError("currentOwnerBlobs values must be 40 lowercase hexadecimal blobs")
        admitted[owner] = blob
    return admitted


def _admit_authority_groups(
    result: Mapping[str, object],
    current_owner_blobs: Mapping[str, str],
) -> dict[str, int]:
    """Validate authority-group shape and its relationship to authenticated owner custody.

    Canonical v10 group names carry three different meanings. Collision and stale groups only make
    sense when the named owner has authenticated current-blob evidence, while an unverified group
    means precisely that current-owner custody is absent for that owner. A future backend may not
    attach an unrelated authenticated owner blob to the result and thereby make another owner's
    unverified authority look authenticated.
    """

    counts: dict[str, int] = {}
    for field in OWNER_AUTHORITY_FIELDS:
        groups = result.get(field)
        if not isinstance(groups, list):
            raise ValueError(f"{field} must be one list")
        counts[field] = len(groups)

        expected_status = AUTHORITY_STATUS_BY_FIELD[field]
        for group in groups:
            if not isinstance(group, Mapping):
                raise ValueError(f"{field} entries must be mappings")

            if group.get("status") != expected_status:
                raise ValueError(f"{field} entry has an invalid status")

            owner = group.get("owner")
            if not isinstance(owner, str) or not owner:
                raise ValueError(f"{field} entry owner must be one non-empty string")

            base_blob = group.get("baseBlob")
            if not isinstance(base_blob, str) or SHA1_RE.fullmatch(base_blob) is None:
                raise ValueError(f"{field} entry baseBlob must be 40 lowercase hexadecimal")

            promotion_candidates = group.get("promotionCandidates")
            if not isinstance(promotion_candidates, list):
                raise ValueError(f"{field} entry promotionCandidates must be one list")

            current_blob = current_owner_blobs.get(owner)
            if field == "unverifiedBaseGroups":
                if current_blob is not None:
                    raise ValueError(
                        "unverifiedBaseGroups owner must not have authenticated current-owner custody"
                    )
                if "currentOwnerBlob" in group:
                    raise ValueError(
                        "unverifiedBaseGroups entry must not claim a currentOwnerBlob"
                    )
                continue

            if current_blob is None:
                raise ValueError(f"{field} owner is missing authenticated current-owner custody")

            group_current_blob = group.get("currentOwnerBlob")
            if group_current_blob != current_blob:
                raise ValueError(f"{field} currentOwnerBlob must match currentOwnerBlobs evidence")

            if field == "collisionSets" and base_blob != current_blob:
                raise ValueError("collisionSets baseBlob must equal authenticated current owner blob")
            if field == "staleBaseGroups" and base_blob == current_blob:
                raise ValueError("staleBaseGroups baseBlob must differ from authenticated current owner blob")

    return counts


def admit_selected_backend_result(
    selection: OwnerSurgeryBackendSelection,
    result: Mapping[str, object],
) -> dict[str, object]:
    """Admit one future backend result without weakening the canonical v10 evidence membrane.

    This is deliberately a *result* gate, not a backend implementation. It prevents a future owner
    composition from dropping published work/error/current-owner evidence, reporting impossible
    candidate/entry counts, silently switching backend identity, claiming portable fallback after a
    stronger backend was selected, carrying promotion authority out of an incomplete exhaustive
    custody result, or using authenticated custody for one owner to upgrade another owner's
    unverified promotion group.

    Canonical v10 currently exposes the three promotion-authority groups named by
    ``OWNER_AUTHORITY_FIELDS``. When ``evidenceComplete`` is false those groups must be empty before
    this composition gate will admit the result. Diagnostic ``surgeries`` may remain present; source
    inspection evidence is not itself promotion authority.
    """

    if not isinstance(result, Mapping):
        raise ValueError("backend result must be one mapping")

    backend = result.get("backend", selection.backend)
    if backend != selection.backend:
        raise ValueError("backend result identity does not match selected backend")

    if result.get("portableFallbackAttempted", False) is not False:
        raise ValueError("selected backend result must not claim a weaker fallback attempt")

    entries_observed = _nonnegative_int(result, "artifactDirectoryEntriesObserved")
    candidates_observed = _nonnegative_int(result, "artifactCandidatesObserved")
    if candidates_observed > entries_observed:
        raise ValueError("artifactCandidatesObserved cannot exceed artifactDirectoryEntriesObserved")

    discovery_errors = result.get("discoveryErrors")
    if not isinstance(discovery_errors, list):
        raise ValueError("discoveryErrors must be one list")

    evidence_complete = result.get("evidenceComplete")
    if not isinstance(evidence_complete, bool):
        raise ValueError("evidenceComplete must be one boolean")
    if evidence_complete != (len(discovery_errors) == 0):
        raise ValueError("evidenceComplete must agree with discoveryErrors emptiness")

    current_owner_blobs = _admit_current_owner_blobs(result)
    authority_counts = _admit_authority_groups(result, current_owner_blobs)

    if not evidence_complete and any(authority_counts.values()):
        raise ValueError(
            "incomplete exhaustive custody must not carry partial promotion authority groups"
        )

    current_owner_custody = bool(current_owner_blobs)
    unverified_owner_authority = authority_counts["unverifiedBaseGroups"] > 0
    owner_evidence_admitted = (
        evidence_complete
        and current_owner_custody
        and not unverified_owner_authority
    )

    return {
        "backend": selection.backend,
        "status": "EVIDENCE_ADMITTED",
        "artifactDirectoryEntriesObserved": entries_observed,
        "artifactCandidatesObserved": candidates_observed,
        "discoveryErrorCount": len(discovery_errors),
        "evidenceComplete": evidence_complete,
        "currentOwnerCustodyProvided": current_owner_custody,
        "authorityGroupCounts": authority_counts,
        "portableFallbackAttempted": False,
        "exhaustiveEvidenceAdmitted": evidence_complete,
        "ownerEvidenceAdmitted": owner_evidence_admitted,
    }


if __name__ == "__main__":
    import json

    print(json.dumps(select_owner_surgery_backend(SUPPORTED_POSIX).to_dict(), indent=2, sort_keys=True))
