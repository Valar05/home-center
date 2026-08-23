#!/usr/bin/env python3
"""Non-authoritative shadow audit for TRY FOREVER owner-surgery descriptor custody.

This organ composes the existing canonical portable v10 custody owner with the existing POSIX
held-directory custody source without changing promotion authority. It is intentionally a staging
surface: canonical v10 remains the authority producer while the descriptor backend independently
checks root/candidate topology, bounded work, exact bytes, and UTF-8 custody against the same
repository state.

A descriptor wound here does not trigger portable fallback because no descriptor authority was ever
admitted. Likewise a shadow match does not mean canonical-owner descriptor integration, TESTED,
runtime, deployment, phone delivery, or acceptance. When normal shadow comparison completes, the
existing temporal-binding policy is also evaluated so exact later-read agreement can be separated
from proof that those bytes produced the canonical result.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Mapping

from try_forever_directory_handle_binding_capability import (
    current_directory_handle_binding_capability,
)
from try_forever_generated_index_artifact_observation import (
    GeneratedIndexArtifactChangedError,
    GeneratedIndexArtifactResourceLimitError,
    GeneratedIndexArtifactTopologyError,
    observe_generated_index_artifact,
)
from try_forever_owner_surgery_backend_policy import PORTABLE_UNAVAILABLE
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


SCHEMA = "try-forever-owner-surgery-descriptor-shadow.v3"
CANONICAL_SCHEMA = "try-forever-owner-surgery-custody.v10"
SUPPORTED = "SUPPORTED_POSIX_PRIMITIVES"


class PortableShadowArtifactError(ValueError):
    """Portable finite-artifact staging evidence could not be observed exactly."""


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


def _canonical_evidence_complete(result: Mapping[str, object]) -> bool:
    """Preserve the canonical boolean contract instead of truthiness-normalizing it."""

    value = result.get("evidenceComplete")
    if not isinstance(value, bool):
        raise ValueError("canonical evidenceComplete must be one boolean")
    return value


def _canonical_result_sha256(result: Mapping[str, object]) -> str:
    """Bind the shadow receipt to the exact canonical result it accompanied.

    This fingerprint is evidence identity for the canonical result payload, not filesystem
    atomicity and not a replacement for canonical artifact-content custody.
    """

    try:
        encoded = json.dumps(
            result,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ValueError(f"canonical result is not deterministic JSON evidence: {exc}") from exc
    return hashlib.sha256(encoded).hexdigest()


def _portable_shadow_artifacts(
    paths: tuple[str, ...],
    *,
    max_artifact_bytes: int,
) -> list[dict[str, object]]:
    """Observe exact portable-path bytes for shadow comparison only.

    These observations never replace or reinterpret canonical v10 authority. They exist so a
    descriptor SHADOW_MATCH means the pathname and held-directory staging mechanisms agree on the
    exact compared bytes, not merely on filenames and work counters.
    """

    observations: list[dict[str, object]] = []
    for path_text in paths:
        path = Path(path_text)
        try:
            observed = observe_generated_index_artifact(
                path,
                max_bytes=max_artifact_bytes,
            )
        except (
            GeneratedIndexArtifactResourceLimitError,
            GeneratedIndexArtifactTopologyError,
            GeneratedIndexArtifactChangedError,
            UnicodeDecodeError,
            OSError,
        ) as exc:
            raise PortableShadowArtifactError(
                f"portable shadow artifact observation failed for {path_text}: "
                f"{type(exc).__name__}: {exc}"
            ) from exc
        observations.append(
            {
                "path": path.as_posix(),
                "byteCount": observed.size_bytes,
                "sha256": observed.sha256,
            }
        )
    return observations


def _artifact_identity_map(
    observations: list[dict[str, object]],
) -> dict[str, tuple[object, object]]:
    result: dict[str, tuple[object, object]] = {}
    for item in observations:
        path = item.get("path")
        if not isinstance(path, str) or not path:
            raise ValueError("shadow artifact observation requires one path")
        if path in result:
            raise ValueError(f"duplicate shadow artifact observation path: {path}")
        result[path] = (item.get("byteCount"), item.get("sha256"))
    return result


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
    may report MATCH, DIVERGED, CANONICAL_SCHEMA_WOUND, CANONICAL_WOUND, PORTABLE_SHADOW_WOUND,
    UNAVAILABLE, CAPABILITY_WOUND, or DESCRIPTOR_WOUND, but never collision/stale/unverified
    promotion groups and never ownerEvidenceAdmitted=true. A completed comparison also carries the
    non-authoritative temporal-binding result for the same canonical payload.
    """

    portable = classify(
        root,
        current_owner_blobs,
        max_candidates=max_candidates,
        max_entries=max_entries,
    )
    canonical_schema = portable.get("schema")
    canonical_result_sha256 = _canonical_result_sha256(portable)
    base: dict[str, object] = {
        "schema": SCHEMA,
        "canonicalAuthorityBackend": "PORTABLE_PATHNAME_REVALIDATION",
        "canonicalAuthoritySchema": canonical_schema,
        "canonicalResultSha256": canonical_result_sha256,
        "canonicalEvidenceComplete": None,
        "canonicalArtifactDirectoryEntriesObserved": portable.get(
            "artifactDirectoryEntriesObserved"
        ),
        "canonicalArtifactCandidatesObserved": portable.get(
            "artifactCandidatesObserved"
        ),
        "descriptorCapabilityStatus": None,
        "descriptorAuthorityAdmitted": False,
        "ownerMutation": False,
        "regressionExecuted": False,
        "tested": False,
        "runtimeUi": False,
        "runtimeTalkBack": False,
        "phoneDelivered": False,
    }

    if canonical_schema != CANONICAL_SCHEMA:
        return {
            **base,
            "status": "CANONICAL_SCHEMA_WOUND",
            "boundary": (
                "Descriptor shadow v3 is defined only beside canonical owner-surgery custody v10; "
                f"refusing to reinterpret schema {canonical_schema!r}."
            ),
            "portableShadowArtifacts": [],
            "descriptorArtifacts": [],
            "descriptorArtifactDirectoryEntriesObserved": None,
            "descriptorArtifactCandidatesObserved": None,
            "artifactSetMatch": None,
            "metricsMatch": None,
            "contentIdentityMatch": None,
        }

    canonical_evidence_complete = _canonical_evidence_complete(portable)
    base["canonicalEvidenceComplete"] = canonical_evidence_complete

    if not canonical_evidence_complete:
        return {
            **base,
            "status": "CANONICAL_WOUND",
            "boundary": (
                "Canonical portable custody is incomplete; descriptor shadow staging stops before "
                "capability or artifact comparison so a wounded authority result cannot be decorated as SHADOW_MATCH."
            ),
            "portableShadowArtifacts": [],
            "descriptorArtifacts": [],
            "descriptorArtifactDirectoryEntriesObserved": None,
            "descriptorArtifactCandidatesObserved": None,
            "artifactSetMatch": None,
            "metricsMatch": None,
            "contentIdentityMatch": None,
        }

    capability = current_directory_handle_binding_capability()
    base["descriptorCapabilityStatus"] = capability.status

    if capability.status == PORTABLE_UNAVAILABLE:
        return {
            **base,
            "status": "DESCRIPTOR_UNAVAILABLE",
            "boundary": capability.boundary,
            "portableShadowArtifacts": [],
            "descriptorArtifacts": [],
            "descriptorArtifactDirectoryEntriesObserved": None,
            "descriptorArtifactCandidatesObserved": None,
            "artifactSetMatch": None,
            "metricsMatch": None,
            "contentIdentityMatch": None,
        }

    if capability.status != SUPPORTED:
        return {
            **base,
            "status": "CAPABILITY_WOUND",
            "boundary": (
                "Descriptor shadow capability status is not one admitted platform state; "
                f"refusing to normalize {capability.status!r} into descriptor unavailability."
            ),
            "portableShadowArtifacts": [],
            "descriptorArtifacts": [],
            "descriptorArtifactDirectoryEntriesObserved": None,
            "descriptorArtifactCandidatesObserved": None,
            "artifactSetMatch": None,
            "metricsMatch": None,
            "contentIdentityMatch": None,
        }

    portable_paths = _artifact_paths_from_portable(portable)
    try:
        portable_shadow_artifacts = _portable_shadow_artifacts(
            portable_paths,
            max_artifact_bytes=max_artifact_bytes,
        )
    except PortableShadowArtifactError as exc:
        return {
            **base,
            "status": "PORTABLE_SHADOW_WOUND",
            "boundary": str(exc),
            "portableShadowArtifacts": [],
            "descriptorArtifacts": [],
            "descriptorArtifactDirectoryEntriesObserved": None,
            "descriptorArtifactCandidatesObserved": None,
            "artifactSetMatch": None,
            "metricsMatch": None,
            "contentIdentityMatch": None,
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
            observations: list[dict[str, object]] = []
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
            "portableShadowArtifacts": portable_shadow_artifacts,
            "descriptorArtifacts": [],
            "descriptorArtifactDirectoryEntriesObserved": None,
            "descriptorArtifactCandidatesObserved": None,
            "artifactSetMatch": False,
            "metricsMatch": False,
            "contentIdentityMatch": False,
        }

    metrics_match = (
        inventory.entries_observed == portable.get("artifactDirectoryEntriesObserved")
        and inventory.candidates_observed == portable.get("artifactCandidatesObserved")
    )
    artifact_set_match = descriptor_paths == portable_paths
    portable_identity = _artifact_identity_map(portable_shadow_artifacts)
    descriptor_identity = _artifact_identity_map(observations)
    content_identity_match = portable_identity == descriptor_identity
    status = (
        "SHADOW_MATCH"
        if metrics_match and artifact_set_match and content_identity_match
        else "SHADOW_DIVERGED"
    )

    result = {
        **base,
        "status": status,
        "boundary": (
            "Descriptor custody independently matched portable shadow inventory and exact content "
            "identity for the canonical-result fingerprint carried by this receipt; temporal binding "
            "is reported separately and grants no promotion authority or filesystem atomicity."
            if status == "SHADOW_MATCH"
            else "Descriptor shadow differs from portable staging evidence; stop before owner integration."
        ),
        "descriptorArtifactDirectoryEntriesObserved": inventory.entries_observed,
        "descriptorArtifactCandidatesObserved": inventory.candidates_observed,
        "artifactSetMatch": artifact_set_match,
        "metricsMatch": metrics_match,
        "contentIdentityMatch": content_identity_match,
        "portableShadowArtifacts": portable_shadow_artifacts,
        "descriptorArtifacts": observations,
    }

    # Local import avoids a module-import cycle: the temporal policy imports this module's stable
    # schema/result-identity helpers, while this owner path consumes that policy only after this
    # module is fully initialized and the shadow comparison result exists.
    from try_forever_owner_surgery_shadow_temporal_binding import evaluate_temporal_content_binding

    temporal_binding = evaluate_temporal_content_binding(portable, result)
    return {
        **result,
        "temporalContentBinding": temporal_binding,
        "temporalBindingProven": temporal_binding.get("temporalBindingProven") is True,
    }


if __name__ == "__main__":
    print(json.dumps(audit_descriptor_shadow(), indent=2, sort_keys=True))
