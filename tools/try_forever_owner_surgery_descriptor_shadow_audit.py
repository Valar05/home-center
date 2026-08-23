#!/usr/bin/env python3
"""Non-authoritative shadow audit for TRY FOREVER owner-surgery descriptor custody.

This organ composes the existing canonical portable v10 custody owner with the existing POSIX
held-directory custody source without changing promotion authority. It is intentionally a staging
surface: canonical v10 remains the authority producer while the descriptor backend independently
checks root/candidate topology, bounded work, exact bytes, and UTF-8 custody against the same
repository state.

A descriptor wound here does not trigger portable fallback because no descriptor authority was ever
admitted. Likewise a shadow match does not mean canonical-owner descriptor integration, TESTED,
runtime, deployment, phone delivery, or acceptance.
"""

from __future__ import annotations

from pathlib import Path
from typing import Mapping

from try_forever_directory_handle_binding_capability import (
    current_directory_handle_binding_capability,
)
from try_forever_owner_surgery_custody_probe import (
    MAX_ARTIFACT_BYTES,
    MAX_CUSTODY_ARTIFACTS,
    MAX_CUSTODY_DIRECTORY_ENTRIES,
    PATCH_ROOT,
    _artifact_kind_for_name,
    classify,
)
from try_forever_posix_directory_handle_custody import (
    DescriptorArtifactCustodyError,
    DescriptorCustodyCleanupError,
    HeldDirectoryCustody,
    PosixDirectoryHandleCustodyUnavailable,
)


SCHEMA = "try-forever-owner-surgery-descriptor-shadow.v1"
SUPPORTED = "SUPPORTED_POSIX_PRIMITIVES"


def _artifact_paths_from_portable(result: Mapping[str, object]) -> tuple[str, ...]:
    paths: set[str] = set()
    surgeries = result.get("surgeries")
    if isinstance(surgeries, list):
        for item in surgeries:
            if isinstance(item, Mapping):
                path = item.get("path")
                if isinstance(path, str) and path:
                    paths.add(path)
    errors = result.get("discoveryErrors")
    if isinstance(errors, list):
        for item in errors:
            if not isinstance(item, Mapping):
                continue
            if item.get("artifact_kind") not in {"patch", "delta_json"}:
                continue
            path = item.get("path")
            if isinstance(path, str) and path:
                paths.add(path)
    return tuple(sorted(paths))


def audit_descriptor_shadow(
    root: Path = PATCH_ROOT,
    current_owner_blobs: dict[str, str] | None = None,
    *,
    max_candidates: int = MAX_CUSTODY_ARTIFACTS,
    max_entries: int = MAX_CUSTODY_DIRECTORY_ENTRIES,
    max_artifact_bytes: int = MAX_ARTIFACT_BYTES,
) -> dict[str, object]:
    """Run a descriptor custody shadow beside canonical portable v10 authority.

    The canonical result is always produced first and remains the only authority result. The shadow
    may report MATCH, DIVERGED, UNAVAILABLE, or WOUND, but never collision/stale/unverified promotion
    groups and never ownerEvidenceAdmitted=true.
    """

    portable = classify(
        root,
        current_owner_blobs,
        max_candidates=max_candidates,
        max_entries=max_entries,
    )
    capability = current_directory_handle_binding_capability()
    base: dict[str, object] = {
        "schema": SCHEMA,
        "canonicalAuthorityBackend": "PORTABLE_PATHNAME_REVALIDATION",
        "canonicalEvidenceComplete": bool(portable.get("evidenceComplete")),
        "canonicalArtifactDirectoryEntriesObserved": portable.get(
            "artifactDirectoryEntriesObserved"
        ),
        "canonicalArtifactCandidatesObserved": portable.get(
            "artifactCandidatesObserved"
        ),
        "descriptorCapabilityStatus": capability.status,
        "descriptorAuthorityAdmitted": False,
        "ownerMutation": False,
        "regressionExecuted": False,
        "tested": False,
        "runtimeUi": False,
        "runtimeTalkBack": False,
        "phoneDelivered": False,
    }

    if capability.status != SUPPORTED:
        return {
            **base,
            "status": "DESCRIPTOR_UNAVAILABLE",
            "boundary": capability.boundary,
            "descriptorArtifactDirectoryEntriesObserved": None,
            "descriptorArtifactCandidatesObserved": None,
            "artifactSetMatch": None,
            "metricsMatch": None,
        }

    try:
        with HeldDirectoryCustody(root) as held:
            inventory = held.candidate_inventory(
                is_candidate=lambda name: _artifact_kind_for_name(name) is not None,
                max_entries=max_entries,
                max_candidates=max_candidates,
            )
            descriptor_paths = tuple(
                sorted((root / item.name).as_posix() for item in inventory.candidates)
            )
            observations = []
            for candidate in inventory.candidates:
                observed = held.observe_utf8_regular_file(
                    candidate.name,
                    max_bytes=max_artifact_bytes,
                    expected_candidate=candidate,
                )
                observations.append(
                    {
                        "path": (root / observed.name).as_posix(),
                        "byteCount": observed.byte_count,
                        "sha256": observed.sha256,
                    }
                )
    except (
        PosixDirectoryHandleCustodyUnavailable,
        DescriptorArtifactCustodyError,
        DescriptorCustodyCleanupError,
    ) as exc:
        return {
            **base,
            "status": "DESCRIPTOR_WOUND",
            "boundary": f"{type(exc).__name__}: {exc}",
            "descriptorArtifactDirectoryEntriesObserved": None,
            "descriptorArtifactCandidatesObserved": None,
            "artifactSetMatch": False,
            "metricsMatch": False,
        }

    portable_paths = _artifact_paths_from_portable(portable)
    metrics_match = (
        inventory.entries_observed == portable.get("artifactDirectoryEntriesObserved")
        and inventory.candidates_observed == portable.get("artifactCandidatesObserved")
    )
    artifact_set_match = descriptor_paths == portable_paths
    status = "SHADOW_MATCH" if metrics_match and artifact_set_match else "SHADOW_DIVERGED"

    return {
        **base,
        "status": status,
        "boundary": (
            "Descriptor custody independently matched canonical portable inventory evidence; "
            "this is shadow evidence only, not owner integration or promotion authority."
            if status == "SHADOW_MATCH"
            else "Descriptor shadow differs from canonical portable inventory evidence; stop before owner integration."
        ),
        "descriptorArtifactDirectoryEntriesObserved": inventory.entries_observed,
        "descriptorArtifactCandidatesObserved": inventory.candidates_observed,
        "artifactSetMatch": artifact_set_match,
        "metricsMatch": metrics_match,
        "descriptorArtifacts": observations,
    }


if __name__ == "__main__":
    import json

    print(json.dumps(audit_descriptor_shadow(), indent=2, sort_keys=True))
