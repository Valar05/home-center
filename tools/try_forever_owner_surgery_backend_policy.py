#!/usr/bin/env python3
"""Pure backend-selection contract for TRY FOREVER owner-surgery custody.

This module does not inspect the repository, apply patches, execute Android, touch Phone/P0, or
replace the canonical v10 custody owner. It defines how a future composition may choose between the
portable pathname-revalidation backend and the stronger POSIX held-directory backend without
silently weakening evidence after a stronger backend has already been admitted.

Direct machine inputs cross exact admission before semantic reads. Capability/failure controls are
exact built-in strings with bounded source throats, selection records are exact and internally
canonical, and backend results reuse the repository's existing bounded one-observation exact-JSON
snapshot organ. This is custody composition, not a second validator or owner.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import re

from try_forever_operator_receipt_snapshot_custody import snapshot_json_mapping
from try_forever_owner_surgery_state_policy import admit_owner_surgery_state


SUPPORTED_POSIX = "SUPPORTED_POSIX_PRIMITIVES"
PORTABLE_UNAVAILABLE = "PORTABLE_ATOMIC_BINDING_UNAVAILABLE"
PORTABLE_BACKEND = "PORTABLE_PATHNAME_REVALIDATION"
DESCRIPTOR_BACKEND = "HELD_DIRECTORY_DESCRIPTOR"
MAX_CAPABILITY_STATUS_CODEPOINTS = 128
MAX_FAILURE_BOUNDARY_CODEPOINTS = 4_096

REQUIRED_OWNER_EVIDENCE_FIELDS = (
    "artifactDirectoryEntriesObserved",
    "artifactCandidatesObserved",
    "discoveryErrors",
    "currentOwnerBlobs",
    "capability",
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
    """Select one backend from one exact admitted platform-capability token."""

    if type(capability_status) is not str:
        raise ValueError("capability status must be one exact built-in string")
    if len(capability_status) > MAX_CAPABILITY_STATUS_CODEPOINTS:
        raise ValueError(
            "capability status exceeds source ceiling "
            f"{MAX_CAPABILITY_STATUS_CODEPOINTS} code points"
        )

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


def _require_exact_selection(
    selection: OwnerSurgeryBackendSelection,
) -> OwnerSurgeryBackendSelection:
    """Admit only one exact, internally canonical backend-selection record."""

    if type(selection) is not OwnerSurgeryBackendSelection:
        raise ValueError("selection must be one exact OwnerSurgeryBackendSelection")

    if type(selection.backend) is not str:
        raise ValueError("selection backend must be one exact built-in string")
    if type(selection.capability_status) is not str:
        raise ValueError("selection capability status must be one exact built-in string")
    if len(selection.capability_status) > MAX_CAPABILITY_STATUS_CODEPOINTS:
        raise ValueError(
            "selection capability status exceeds source ceiling "
            f"{MAX_CAPABILITY_STATUS_CODEPOINTS} code points"
        )
    if type(selection.descriptor_selected) is not bool:
        raise ValueError("selection descriptor_selected must be one exact boolean")
    if type(selection.portable_is_primary) is not bool:
        raise ValueError("selection portable_is_primary must be one exact boolean")
    if type(selection.fallback_after_backend_failure) is not bool:
        raise ValueError("selection fallback_after_backend_failure must be one exact boolean")
    if type(selection.required_owner_evidence_fields) is not tuple or any(
        type(field) is not str for field in selection.required_owner_evidence_fields
    ):
        raise ValueError("selection required_owner_evidence_fields must be one exact string tuple")
    if type(selection.boundary) is not str or not selection.boundary:
        raise ValueError("selection boundary must be one non-empty exact built-in string")
    if len(selection.boundary) > MAX_FAILURE_BOUNDARY_CODEPOINTS:
        raise ValueError(
            "selection boundary exceeds source ceiling "
            f"{MAX_FAILURE_BOUNDARY_CODEPOINTS} code points"
        )

    expected = select_owner_surgery_backend(selection.capability_status)
    if selection != expected:
        raise ValueError("selection must match the canonical backend decision for its capability")
    return selection


def classify_selected_backend_failure(
    selection: OwnerSurgeryBackendSelection,
    failure_boundary: str,
) -> dict[str, object]:
    """Project one exact bounded backend failure without inventing a weaker retry path."""

    admitted_selection = _require_exact_selection(selection)
    if type(failure_boundary) is not str or not failure_boundary:
        raise ValueError("failure boundary must be one non-empty exact built-in string")
    if len(failure_boundary) > MAX_FAILURE_BOUNDARY_CODEPOINTS:
        raise ValueError(
            "failure boundary exceeds source ceiling "
            f"{MAX_FAILURE_BOUNDARY_CODEPOINTS} code points"
        )
    return {
        "backend": admitted_selection.backend,
        "status": "FAIL_CLOSED",
        "boundary": failure_boundary,
        "portableFallbackAttempted": False,
        "ownerEvidenceAdmitted": False,
    }


def _nonnegative_int(result: dict[str, object], field: str) -> int:
    value = result.get(field)
    if type(value) is not int or value < 0:
        raise ValueError(f"{field} must be one non-negative integer")
    return value


def _admit_current_owner_blobs(result: dict[str, object]) -> dict[str, str]:
    raw = result.get("currentOwnerBlobs")
    if type(raw) is not dict:
        raise ValueError("currentOwnerBlobs must be one mapping")

    admitted: dict[str, str] = {}
    for owner, blob in raw.items():
        if type(owner) is not str or not owner:
            raise ValueError("currentOwnerBlobs keys must be non-empty owner strings")
        if type(blob) is not str or SHA1_RE.fullmatch(blob) is None:
            raise ValueError("currentOwnerBlobs values must be 40 lowercase hexadecimal blobs")
        admitted[owner] = blob
    return admitted


def _admit_current_owner_custody_presence(result: dict[str, object]) -> bool:
    """Preserve omitted-vs-explicit-empty custody truth from canonical v10 capability evidence."""

    capability = result.get("capability")
    if type(capability) is not dict:
        raise ValueError("backend result capability must be one mapping")
    provided = capability.get("currentOwnerCustodyProvided")
    if type(provided) is not bool:
        raise ValueError(
            "backend result capability.currentOwnerCustodyProvided must be one boolean"
        )
    return provided


def _admit_promotion_candidate(
    candidate: object,
    *,
    field: str,
    owner: str,
    base_blob: str,
) -> tuple[str, str]:
    """Bind every authority-group member back to the group identity it supposedly proves."""

    if type(candidate) is not dict:
        raise ValueError(f"{field} promotionCandidates entries must be mappings")

    if candidate.get("owner") != owner:
        raise ValueError(f"{field} promotion candidate owner must match group owner")
    if candidate.get("base_blob") != base_blob:
        raise ValueError(f"{field} promotion candidate base_blob must match group baseBlob")

    path = candidate.get("path")
    if type(path) is not str or not path:
        raise ValueError(f"{field} promotion candidate path must be one non-empty string")

    artifact_kind = candidate.get("artifact_kind")
    if type(artifact_kind) is not str or artifact_kind not in {"patch", "delta_json"}:
        raise ValueError(f"{field} promotion candidate artifact_kind is unsupported")

    state = candidate.get("state")
    if type(state) is not str or not state:
        raise ValueError(f"{field} promotion candidate state must be one non-empty string")
    try:
        state_admission = admit_owner_surgery_state(state)
    except ValueError as exc:
        raise ValueError(f"{field} promotion candidate state is not admitted") from exc
    if not state_admission.promotion_candidate:
        raise ValueError(f"{field} promotion candidate state is not promotion-ready")

    if candidate.get("promotion_candidate") is not True:
        raise ValueError(f"{field} promotion candidate must explicitly carry promotion_candidate=true")

    return artifact_kind, path


def _admit_authority_groups(
    result: dict[str, object],
    current_owner_blobs: dict[str, str],
) -> dict[str, int]:
    """Validate authority-group shape and authenticated owner/member relationships."""

    counts: dict[str, int] = {}
    seen_groups: set[tuple[str, str]] = set()
    for field in OWNER_AUTHORITY_FIELDS:
        groups = result.get(field)
        if type(groups) is not list:
            raise ValueError(f"{field} must be one list")
        counts[field] = len(groups)

        expected_status = AUTHORITY_STATUS_BY_FIELD[field]
        for group in groups:
            if type(group) is not dict:
                raise ValueError(f"{field} entries must be mappings")

            if group.get("status") != expected_status:
                raise ValueError(f"{field} entry has an invalid status")

            owner = group.get("owner")
            if type(owner) is not str or not owner:
                raise ValueError(f"{field} entry owner must be one non-empty string")

            base_blob = group.get("baseBlob")
            if type(base_blob) is not str or SHA1_RE.fullmatch(base_blob) is None:
                raise ValueError(f"{field} entry baseBlob must be 40 lowercase hexadecimal")

            group_identity = (owner, base_blob)
            if group_identity in seen_groups:
                raise ValueError("authority group owner/base identity must be unique")
            seen_groups.add(group_identity)

            promotion_candidates = group.get("promotionCandidates")
            if type(promotion_candidates) is not list:
                raise ValueError(f"{field} entry promotionCandidates must be one list")
            minimum_members = 2 if field == "collisionSets" else 1
            if len(promotion_candidates) < minimum_members:
                raise ValueError(
                    f"{field} promotionCandidates must contain at least {minimum_members} admitted member(s)"
                )

            member_identities: set[tuple[str, str]] = set()
            for candidate in promotion_candidates:
                member_identity = _admit_promotion_candidate(
                    candidate,
                    field=field,
                    owner=owner,
                    base_blob=base_blob,
                )
                if member_identity in member_identities:
                    raise ValueError(f"{field} promotion candidate artifact identity must be unique")
                member_identities.add(member_identity)

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
    result: dict[str, object],
) -> dict[str, object]:
    """Admit one future backend result without weakening canonical v10 evidence custody.

    The public result type matches runtime admission: one exact built-in ``dict`` containing exact
    JSON-shaped evidence. The existing bounded snapshot organ observes it once before any semantic
    read, so caller-owned Mapping/scalar subclasses cannot execute inside this policy or present one
    view for validation and another for authority. All checks below consume only the detached tree.
    """

    admitted_selection = _require_exact_selection(selection)
    result_snapshot = snapshot_json_mapping(result, field="backend result")

    if "backend" not in result_snapshot:
        raise ValueError("backend result must explicitly carry backend identity")
    backend = result_snapshot["backend"]
    if backend != admitted_selection.backend:
        raise ValueError("backend result identity does not match selected backend")

    if "portableFallbackAttempted" not in result_snapshot:
        raise ValueError("backend result must explicitly carry portableFallbackAttempted")
    if result_snapshot["portableFallbackAttempted"] is not False:
        raise ValueError("selected backend result must not claim a weaker fallback attempt")

    entries_observed = _nonnegative_int(result_snapshot, "artifactDirectoryEntriesObserved")
    candidates_observed = _nonnegative_int(result_snapshot, "artifactCandidatesObserved")
    if candidates_observed > entries_observed:
        raise ValueError("artifactCandidatesObserved cannot exceed artifactDirectoryEntriesObserved")

    discovery_errors = result_snapshot.get("discoveryErrors")
    if type(discovery_errors) is not list:
        raise ValueError("discoveryErrors must be one list")

    evidence_complete = result_snapshot.get("evidenceComplete")
    if type(evidence_complete) is not bool:
        raise ValueError("evidenceComplete must be one boolean")
    if evidence_complete != (len(discovery_errors) == 0):
        raise ValueError("evidenceComplete must agree with discoveryErrors emptiness")

    current_owner_blobs = _admit_current_owner_blobs(result_snapshot)
    current_owner_custody_provided = _admit_current_owner_custody_presence(result_snapshot)
    if not current_owner_custody_provided and current_owner_blobs:
        raise ValueError(
            "backend result cannot carry currentOwnerBlobs when canonical custody was omitted"
        )
    authority_counts = _admit_authority_groups(result_snapshot, current_owner_blobs)

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
        "backend": admitted_selection.backend,
        "status": "EVIDENCE_ADMITTED",
        "artifactDirectoryEntriesObserved": entries_observed,
        "artifactCandidatesObserved": candidates_observed,
        "discoveryErrorCount": len(discovery_errors),
        "evidenceComplete": evidence_complete,
        "currentOwnerCustodyProvided": current_owner_custody_provided,
        "authorityGroupCounts": authority_counts,
        "portableFallbackAttempted": False,
        "exhaustiveEvidenceAdmitted": evidence_complete,
        "ownerEvidenceAdmitted": owner_evidence_admitted,
    }


if __name__ == "__main__":
    import json

    print(json.dumps(select_owner_surgery_backend(SUPPORTED_POSIX).to_dict(), indent=2, sort_keys=True))
