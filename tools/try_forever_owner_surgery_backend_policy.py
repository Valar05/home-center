#!/usr/bin/env python3
"""Pure backend-selection contract for TRY FOREVER owner-surgery custody.

This module does not inspect the repository, apply patches, execute Android, touch Phone/P0, or
replace the canonical v10 custody owner. It defines how a future composition may choose between the
portable pathname-revalidation backend and the stronger POSIX held-directory backend without
silently weakening evidence after a stronger backend has already been admitted.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass


SUPPORTED_POSIX = "SUPPORTED_POSIX_PRIMITIVES"
PORTABLE_UNAVAILABLE = "PORTABLE_ATOMIC_BINDING_UNAVAILABLE"
PORTABLE_BACKEND = "PORTABLE_PATHNAME_REVALIDATION"
DESCRIPTOR_BACKEND = "HELD_DIRECTORY_DESCRIPTOR"

REQUIRED_OWNER_EVIDENCE_FIELDS = (
    "artifactDirectoryEntriesObserved",
    "artifactCandidatesObserved",
)


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


if __name__ == "__main__":
    import json

    print(json.dumps(select_owner_surgery_backend(SUPPORTED_POSIX).to_dict(), indent=2, sort_keys=True))
