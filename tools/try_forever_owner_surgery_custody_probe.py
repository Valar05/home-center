#!/usr/bin/env python3
"""Source-only custody probe for TRY FOREVER owner surgery artifacts.

This does not apply patches, execute Android, touch the phone/P0 chain, or promote a proposed
surgery into owner wiring. It exposes patch-order hazards when several unapplied source surgeries
target the same exact owner blob and binds that evidence to an authenticated current-owner blob
when one is supplied.

v10 treats textual ``*.patch`` and structured ``*.delta.json`` owner deltas as one finite custody
family. The canonical owner selects exactly one custody backend from exact platform-capability
evidence. When the required POSIX descriptor primitives are admitted it consumes the existing
held-directory custody organ directly; a descriptor wound fails that classification attempt closed
without a same-attempt portable retry. When those primitives are unavailable, the existing portable
pathname/root-revalidation path remains primary. Both paths feed the same exact-observation semantic
producer, preserve bounded directory/candidate/content evidence, exact current-owner custody, and
zero partial promotion authority on discovery wounds. Descriptor custody strengthens root/name
binding but does not claim universal filesystem atomicity. Regression execution, TESTED, runtime,
deployment, phone delivery, and acceptance remain separate capability states.
"""

from __future__ import annotations

import argparse
import json
import os
import re
from dataclasses import asdict, dataclass
from pathlib import Path

from try_forever_directory_handle_binding_capability import (
    current_directory_handle_binding_capability,
)
from try_forever_generated_index_artifact_observation import (
    GeneratedIndexArtifactChangedError,
    GeneratedIndexArtifactObservation,
    GeneratedIndexArtifactResourceLimitError,
    GeneratedIndexArtifactTopologyError,
    observe_generated_index_artifact,
)
from try_forever_owner_surgery_backend_policy import select_owner_surgery_backend
from try_forever_owner_surgery_metadata_exactness import (
    MAX_OWNER_IDENTITY_CODEPOINTS,
    admit_owner_identity,
)
from try_forever_owner_surgery_semantic_parser import (
    OwnerSurgerySemanticError,
    parse_owner_surgery_observation,
    project_owner_surgery_diagnostic_text,
)
from try_forever_posix_directory_handle_custody import (
    DescriptorArtifactCustodyError,
    DescriptorCustodyCleanupError,
    DescriptorInventoryCustodyError,
    HeldDirectoryCustody,
    PosixDirectoryHandleCustodyUnavailable,
)
from try_forever_skill_root_identity import (
    capture_directory_root_identity,
    revalidate_directory_root_identity,
)


PATCH_ROOT = Path("patches")
PATCH_ROOT_SUBJECT = "owner surgery patches root"
MAX_ARTIFACT_BYTES = 1_048_576
MAX_CUSTODY_ARTIFACTS = 2_048
MAX_CUSTODY_DIRECTORY_ENTRIES = 32_768
MAX_CURRENT_OWNER_ASSIGNMENT_CODEPOINTS = MAX_OWNER_IDENTITY_CODEPOINTS + 1 + 40
MAX_CURRENT_OWNER_MAP_ITEMS = MAX_CUSTODY_ARTIFACTS
MAX_CURRENT_OWNER_MAP_TOTAL_CODEPOINTS = MAX_ARTIFACT_BYTES
MAX_CURRENT_OWNER_CLI_ITEMS = MAX_CUSTODY_ARTIFACTS
MAX_CURRENT_OWNER_CLI_TOTAL_CODEPOINTS = MAX_ARTIFACT_BYTES
MAX_PROGRAMMATIC_ARGV_ITEMS = 4_096
MAX_PROGRAMMATIC_ARG_CODEPOINTS = MAX_CURRENT_OWNER_ASSIGNMENT_CODEPOINTS
MAX_PROGRAMMATIC_ARGV_TOTAL_CODEPOINTS = MAX_ARTIFACT_BYTES

SHA1_RE = re.compile(r"^[0-9a-f]{40}$")


@dataclass(frozen=True)
class Surgery:
    path: str
    artifact_kind: str
    owner: str
    base_blob: str
    state: str
    promotion_candidate: bool
    artifact_byte_count: int
    artifact_sha256: str


@dataclass(frozen=True)
class DiscoveryError:
    path: str
    artifact_kind: str
    boundary: str


class ArtifactAdmissionError(ValueError):
    """Recognized surgery evidence could not be safely admitted."""


def _artifact_kind_for_name(name: str) -> str | None:
    if not name.startswith("try-forever-"):
        return None
    if name.endswith(".delta.json"):
        return "delta_json"
    if name.endswith(".patch"):
        return "patch"
    return None


def _admit_classification_root(root: Path) -> Path:
    """Admit one exact platform Path before caller-owned path callbacks can participate."""

    if type(root) is not type(PATCH_ROOT):
        raise ValueError("owner surgery root must be one exact platform Path")
    return root


def _admit_classification_budget(value: int, *, field: str, maximum: int) -> int:
    """Admit exact integer controls before comparison/truthiness can execute caller code."""

    if type(value) is not int:
        raise ValueError(f"{field} must be one exact built-in integer")
    if value < 0 or value > maximum:
        raise ValueError(f"{field} must be between 0 and {maximum}")
    return value


def _observe_bounded_utf8(path: Path) -> GeneratedIndexArtifactObservation:
    """Reuse the existing finite regular-artifact organ and retain exact observation identity."""

    try:
        return observe_generated_index_artifact(
            path,
            max_bytes=MAX_ARTIFACT_BYTES,
        )
    except GeneratedIndexArtifactResourceLimitError as exc:
        raise ArtifactAdmissionError(
            f"artifact exceeds {MAX_ARTIFACT_BYTES} byte custody budget"
        ) from exc
    except GeneratedIndexArtifactTopologyError as exc:
        raise ArtifactAdmissionError(
            f"artifact is not one ordinary finite regular-file object: {exc}"
        ) from exc
    except GeneratedIndexArtifactChangedError as exc:
        raise ArtifactAdmissionError(
            f"artifact changed during bounded custody observation: {exc}"
        ) from exc
    except UnicodeDecodeError as exc:
        raise ArtifactAdmissionError(
            f"artifact is not strict UTF-8 at byte {exc.start}"
        ) from exc
    except OSError as exc:
        raise ArtifactAdmissionError(
            f"artifact observation failed: {type(exc).__name__}: {exc}"
        ) from exc


def _read_bounded_utf8(path: Path) -> str:
    """Compatibility text projection from the exact finite artifact observation."""

    return _observe_bounded_utf8(path).utf8_text


def _error(path: Path, artifact_kind: str, exc: Exception) -> DiscoveryError:
    exception_type = project_owner_surgery_diagnostic_text(type(exc).__name__)
    exception_message = project_owner_surgery_diagnostic_text(str(exc))
    return DiscoveryError(
        path=path.as_posix(),
        artifact_kind=artifact_kind,
        boundary=(
            "Owner surgery artifact excluded from custody authority: "
            f"{exception_type}: {exception_message}"
        ),
    )


def _root_error(root: Path, boundary: str) -> DiscoveryError:
    return _error(root, "artifact_root", ArtifactAdmissionError(boundary))


def _discover_artifact_candidates(
    root: Path,
    *,
    max_candidates: int,
    max_entries: int,
) -> tuple[list[tuple[Path, str]], DiscoveryError | None, int, int]:
    """Portable bounded candidate discovery with persistent root-identity revalidation."""

    try:
        root_before = capture_directory_root_identity(root)
    except OSError as exc:
        return [], _error(root, "artifact_root", exc), 0, 0

    initial_root = revalidate_directory_root_identity(
        root_before,
        root_before,
        subject=PATCH_ROOT_SUBJECT,
    )
    if initial_root.status != "STABLE":
        return [], _root_error(root, initial_root.reason), 0, 0

    candidates: list[tuple[Path, str]] = []
    entries_observed = 0
    try:
        with os.scandir(root) as entries:
            for entry in entries:
                entries_observed += 1
                if entries_observed > max_entries:
                    exc = ArtifactAdmissionError(
                        f"owner surgery directory scan exceeds {max_entries} entry custody budget"
                    )
                    return [], _error(root, "artifact_inventory", exc), len(candidates), entries_observed

                artifact_kind = _artifact_kind_for_name(entry.name)
                if artifact_kind is None:
                    continue
                candidates.append((root / entry.name, artifact_kind))
                if len(candidates) > max_candidates:
                    exc = ArtifactAdmissionError(
                        f"owner surgery candidate set exceeds {max_candidates} artifact custody budget"
                    )
                    return [], _error(root, "artifact_inventory", exc), len(candidates), entries_observed
    except OSError as exc:
        return [], _error(root, "artifact_inventory", exc), len(candidates), entries_observed

    try:
        root_after = capture_directory_root_identity(root)
    except OSError as exc:
        return [], _error(root, "artifact_root", exc), len(candidates), entries_observed

    final_root = revalidate_directory_root_identity(
        root_before,
        root_after,
        subject=PATCH_ROOT_SUBJECT,
    )
    if final_root.status != "STABLE":
        return [], _root_error(root, final_root.reason), len(candidates), entries_observed

    candidates.sort(key=lambda item: (item[0].as_posix(), item[1]))
    return candidates, None, len(candidates), entries_observed


def inspect_patch(path: Path) -> tuple[Surgery | None, DiscoveryError | None]:
    try:
        observation = _observe_bounded_utf8(path)
        semantic = parse_owner_surgery_observation(
            path=path.as_posix(),
            artifact_kind="patch",
            utf8_text=observation.utf8_text,
            byte_count=observation.size_bytes,
            sha256=observation.sha256,
        )
        return Surgery(
            path=semantic.path,
            artifact_kind=semantic.artifact_kind,
            owner=semantic.owner,
            base_blob=semantic.base_blob,
            state=semantic.state,
            promotion_candidate=semantic.promotion_candidate,
            artifact_byte_count=semantic.artifact_byte_count,
            artifact_sha256=semantic.artifact_sha256,
        ), None
    except (ArtifactAdmissionError, OwnerSurgerySemanticError, OSError, UnicodeError, ValueError) as exc:
        return None, _error(path, "patch", exc)


def inspect_delta(path: Path) -> tuple[Surgery | None, DiscoveryError | None]:
    try:
        observation = _observe_bounded_utf8(path)
        semantic = parse_owner_surgery_observation(
            path=path.as_posix(),
            artifact_kind="delta_json",
            utf8_text=observation.utf8_text,
            byte_count=observation.size_bytes,
            sha256=observation.sha256,
        )
        return Surgery(
            path=semantic.path,
            artifact_kind=semantic.artifact_kind,
            owner=semantic.owner,
            base_blob=semantic.base_blob,
            state=semantic.state,
            promotion_candidate=semantic.promotion_candidate,
            artifact_byte_count=semantic.artifact_byte_count,
            artifact_sha256=semantic.artifact_sha256,
        ), None
    except (ArtifactAdmissionError, OwnerSurgerySemanticError, OSError, UnicodeError, ValueError) as exc:
        return None, _error(path, "delta_json", exc)


def _discover_descriptor_surgeries(
    root: Path,
    *,
    max_candidates: int,
    max_entries: int,
) -> tuple[list[Surgery], list[DiscoveryError], int, int]:
    """Consume held-root custody directly inside the canonical owner.

    A descriptor setup, inventory, artifact, or cleanup wound returns zero surgery authority and
    never invokes portable pathname custody in the same classification attempt. Bounded work counts
    already observed before an inventory/cleanup wound remain receipt evidence, and an artifact
    custody wound retains the already-identified artifact path/kind. Semantic wounds remain diagnostic
    discovery errors for their individual artifact. Downstream zero-partial-authority policy suppresses
    every promotion group whenever any discovery error exists.
    """

    surgeries: list[Surgery] = []
    discovery_errors: list[DiscoveryError] = []
    candidates_observed = 0
    entries_observed = 0
    try:
        with HeldDirectoryCustody(root) as held:
            inventory = held.candidate_inventory(
                is_candidate=lambda name: _artifact_kind_for_name(name) is not None,
                max_entries=max_entries,
                max_candidates=max_candidates,
            )
            candidates_observed = inventory.candidates_observed
            entries_observed = inventory.entries_observed
            for candidate in inventory.candidates:
                artifact_kind = _artifact_kind_for_name(candidate.name)
                assert artifact_kind in {"patch", "delta_json"}
                path = root / candidate.name
                try:
                    observation = held.observe_utf8_regular_file(
                        candidate.name,
                        max_bytes=MAX_ARTIFACT_BYTES,
                        expected_candidate=candidate,
                    )
                    semantic = parse_owner_surgery_observation(
                        path=path.as_posix(),
                        artifact_kind=artifact_kind,
                        utf8_text=observation.utf8_text,
                        byte_count=observation.byte_count,
                        sha256=observation.sha256,
                    )
                except DescriptorArtifactCustodyError as exc:
                    return (
                        [],
                        [_error(path, artifact_kind, exc)],
                        candidates_observed,
                        entries_observed,
                    )
                except OwnerSurgerySemanticError as exc:
                    discovery_errors.append(_error(path, artifact_kind, exc))
                    continue
                surgeries.append(
                    Surgery(
                        path=semantic.path,
                        artifact_kind=semantic.artifact_kind,
                        owner=semantic.owner,
                        base_blob=semantic.base_blob,
                        state=semantic.state,
                        promotion_candidate=semantic.promotion_candidate,
                        artifact_byte_count=semantic.artifact_byte_count,
                        artifact_sha256=semantic.artifact_sha256,
                    )
                )
    except DescriptorInventoryCustodyError as exc:
        return (
            [],
            [_error(root, "artifact_inventory", exc)],
            exc.candidates_observed,
            exc.entries_observed,
        )
    except (
        PosixDirectoryHandleCustodyUnavailable,
        DescriptorArtifactCustodyError,
        DescriptorCustodyCleanupError,
    ) as exc:
        return (
            [],
            [_error(root, "descriptor_backend", exc)],
            candidates_observed,
            entries_observed,
        )

    return surgeries, discovery_errors, candidates_observed, entries_observed


def _group_payload(owner: str, base_blob: str, group: list[Surgery], status: str) -> dict[str, object]:
    return {
        "owner": owner,
        "baseBlob": base_blob,
        "status": status,
        "promotionCandidates": [asdict(item) for item in group],
    }


def _admit_current_owner_blobs(values: dict[str, str] | None) -> dict[str, str]:
    """Admit one finite authenticated current-owner map before authority-facing traversal."""

    if values is None:
        return {}
    if type(values) is not dict:
        raise ValueError("current owner custody requires one exact built-in dict")
    if len(values) > MAX_CURRENT_OWNER_MAP_ITEMS:
        raise ValueError(
            "current owner custody exceeds source ceiling "
            f"{MAX_CURRENT_OWNER_MAP_ITEMS:,} entries"
        )

    result: dict[str, str] = {}
    total_codepoints = 0
    for owner, blob in values.items():
        admitted_owner = admit_owner_identity(owner, field="current owner")
        if type(blob) is not str or len(blob) != 40 or SHA1_RE.fullmatch(blob) is None:
            raise ValueError(
                "current owner custody requires exact built-in 40-lowercase-hex blob strings"
            )
        total_codepoints += len(admitted_owner) + len(blob)
        if total_codepoints > MAX_CURRENT_OWNER_MAP_TOTAL_CODEPOINTS:
            raise ValueError(
                "current owner custody aggregate exceeds source ceiling "
                f"{MAX_CURRENT_OWNER_MAP_TOTAL_CODEPOINTS:,} code points"
            )
        if admitted_owner in result:
            raise ValueError(f"duplicate admitted current owner identity: {admitted_owner}")
        result[admitted_owner] = blob
    return result


def classify(
    root: Path = PATCH_ROOT,
    current_owner_blobs: dict[str, str] | None = None,
    *,
    max_candidates: int = MAX_CUSTODY_ARTIFACTS,
    max_entries: int = MAX_CUSTODY_DIRECTORY_ENTRIES,
) -> dict[str, object]:
    root = _admit_classification_root(root)
    max_candidates = _admit_classification_budget(
        max_candidates,
        field="max_candidates",
        maximum=MAX_CUSTODY_ARTIFACTS,
    )
    max_entries = _admit_classification_budget(
        max_entries,
        field="max_entries",
        maximum=MAX_CUSTODY_DIRECTORY_ENTRIES,
    )
    current_owner_custody_provided = current_owner_blobs is not None
    current_owner_blobs = _admit_current_owner_blobs(current_owner_blobs)

    capability = current_directory_handle_binding_capability()
    selection = select_owner_surgery_backend(capability.status)
    surgeries: list[Surgery] = []
    discovery_errors: list[DiscoveryError] = []

    if selection.descriptor_selected:
        (
            surgeries,
            discovery_errors,
            candidates_observed,
            entries_observed,
        ) = _discover_descriptor_surgeries(
            root,
            max_candidates=max_candidates,
            max_entries=max_entries,
        )
    else:
        try:
            authority_root_before = capture_directory_root_identity(root)
        except OSError as exc:
            authority_root_before = None
            candidates = []
            inventory_error = _error(root, "artifact_root", exc)
            candidates_observed = 0
            entries_observed = 0
        else:
            candidates, inventory_error, candidates_observed, entries_observed = _discover_artifact_candidates(
                root,
                max_candidates=max_candidates,
                max_entries=max_entries,
            )

        if inventory_error is not None:
            discovery_errors.append(inventory_error)
        else:
            for path, artifact_kind in candidates:
                if artifact_kind == "patch":
                    surgery, error = inspect_patch(path)
                elif artifact_kind == "delta_json":
                    surgery, error = inspect_delta(path)
                else:
                    raise AssertionError(f"unknown owner surgery artifact kind: {artifact_kind}")
                if surgery is not None:
                    surgeries.append(surgery)
                if error is not None:
                    discovery_errors.append(error)

            assert authority_root_before is not None
            try:
                authority_root_after = capture_directory_root_identity(root)
            except OSError as exc:
                surgeries.clear()
                discovery_errors.append(_error(root, "artifact_root", exc))
            else:
                authority_verdict = revalidate_directory_root_identity(
                    authority_root_before,
                    authority_root_after,
                    subject=PATCH_ROOT_SUBJECT,
                )
                if authority_verdict.status != "STABLE":
                    surgeries.clear()
                    discovery_errors.append(_root_error(root, authority_verdict.reason))

    surgeries.sort(key=lambda item: (item.owner, item.base_blob, item.path))
    discovery_errors.sort(key=lambda item: (item.path, item.artifact_kind))

    active_groups: dict[tuple[str, str], list[Surgery]] = {}
    if not discovery_errors:
        for surgery in surgeries:
            if not surgery.promotion_candidate:
                continue
            active_groups.setdefault((surgery.owner, surgery.base_blob), []).append(surgery)

    collision_sets: list[dict[str, object]] = []
    stale_base_groups: list[dict[str, object]] = []
    unverified_base_groups: list[dict[str, object]] = []

    for (owner, base_blob), group in sorted(active_groups.items()):
        current_blob = current_owner_blobs.get(owner)
        if current_blob is None:
            payload = _group_payload(owner, base_blob, group, "UNVERIFIED_BASE_GROUP")
            payload["boundary"] = (
                "Promotion source exists, but no authenticated current-owner blob was supplied; "
                "current-base readiness is unproven."
            )
            unverified_base_groups.append(payload)
            continue

        if base_blob != current_blob:
            payload = _group_payload(owner, base_blob, group, "STALE_BASE_GROUP")
            payload["currentOwnerBlob"] = current_blob
            payload["boundary"] = (
                "Promotion candidates target an owner blob that is not current. Rebase or retire "
                "them before any promotion decision."
            )
            stale_base_groups.append(payload)
            continue

        if len(group) < 2:
            continue
        payload = _group_payload(owner, base_blob, group, "CURRENT_BASE_COLLISION_SET")
        payload["currentOwnerBlob"] = current_blob
        payload["boundary"] = (
            "Multiple unapplied surgeries share the authenticated current owner/base custody. "
            "Applying one stales the others unless they are deliberately ordered, rebased, or converged."
        )
        collision_sets.append(payload)

    return {
        "schema": "try-forever-owner-surgery-custody.v10",
        "backend": selection.backend,
        "portableFallbackAttempted": False,
        "artifactKindsScanned": ["patch", "delta_json"],
        "artifactReadBudgetBytes": MAX_ARTIFACT_BYTES,
        "artifactCandidateBudget": max_candidates,
        "artifactCandidatesObserved": candidates_observed,
        "artifactDirectoryEntryBudget": max_entries,
        "artifactDirectoryEntriesObserved": entries_observed,
        "surgeries": [asdict(item) for item in surgeries],
        "artifactContentWitnesses": [
            {
                "path": item.path,
                "byteCount": item.artifact_byte_count,
                "sha256": item.artifact_sha256,
            }
            for item in surgeries
        ],
        "discoveryErrors": [asdict(item) for item in discovery_errors],
        "evidenceComplete": not discovery_errors,
        "currentOwnerBlobs": current_owner_blobs,
        "collisionSets": collision_sets,
        "staleBaseGroups": stale_base_groups,
        "unverifiedBaseGroups": unverified_base_groups,
        "capability": {
            "sourceInspection": True,
            "patchArtifactInspection": True,
            "deltaArtifactInspection": True,
            "artifactRootIdentityRevalidation": selection.portable_is_primary,
            "artifactRootFinalRevalidation": selection.portable_is_primary,
            "descriptorRootCustody": selection.descriptor_selected,
            "selectedBackend": selection.backend,
            "portableFallbackAttempted": False,
            "sameObservationArtifactContentWitnesses": True,
            "exactOwnerSurgeryStateAdmission": True,
            "nonNormalizingPatchStateHeader": True,
            "exactCurrentOwnerMapAdmission": True,
            "exactCurrentOwnerBlobAdmission": True,
            "boundedCurrentOwnerMapAdmission": True,
            "currentOwnerMapItemCeiling": MAX_CURRENT_OWNER_MAP_ITEMS,
            "currentOwnerMapTotalCodepointCeiling": MAX_CURRENT_OWNER_MAP_TOTAL_CODEPOINTS,
            "exactCurrentOwnerCliListAdmission": True,
            "boundedCurrentOwnerCliListAdmission": True,
            "currentOwnerCliItemCeiling": MAX_CURRENT_OWNER_CLI_ITEMS,
            "currentOwnerCliTotalCodepointCeiling": MAX_CURRENT_OWNER_CLI_TOTAL_CODEPOINTS,
            "boundedCurrentOwnerCliAssignmentAdmission": True,
            "currentOwnerCliAssignmentCodepointCeiling": MAX_CURRENT_OWNER_ASSIGNMENT_CODEPOINTS,
            "exactProgrammaticArgvAdmission": True,
            "boundedProgrammaticArgvAdmission": True,
            "programmaticArgvItemCeiling": MAX_PROGRAMMATIC_ARGV_ITEMS,
            "programmaticArgCodepointCeiling": MAX_PROGRAMMATIC_ARG_CODEPOINTS,
            "programmaticArgvTotalCodepointCeiling": MAX_PROGRAMMATIC_ARGV_TOTAL_CODEPOINTS,
            "currentOwnerCustodyPresencePreserved": True,
            "exactClassificationRootAdmission": True,
            "exactClassificationBudgetAdmission": True,
            "substringPromotionAuthority": False,
            "artifactRootAtomicBinding": False,
            "boundedArtifactDirectoryScan": True,
            "boundedArtifactCandidateSet": True,
            "boundedArtifactRead": True,
            "finiteRegularArtifactCustody": True,
            "boundedAsciiDiscoveryDiagnosticProjection": True,
            "currentOwnerCustodyProvided": current_owner_custody_provided,
            "patchApplied": False,
            "ownerWired": True,
            "regressionExecuted": False,
            "tested": False,
            "runtimeUi": False,
            "runtimeTalkBack": False,
            "phoneDelivered": False,
        },
    }


def _parse_owner_blob(values: list[str]) -> dict[str, str]:
    """Admit repeated CLI owner/blob evidence before iterable or scalar callbacks can execute."""

    if type(values) is not list:
        raise ValueError("--current-owner custody requires one exact built-in list")
    if len(values) > MAX_CURRENT_OWNER_CLI_ITEMS:
        raise ValueError(
            "--current-owner custody exceeds source ceiling "
            f"{MAX_CURRENT_OWNER_CLI_ITEMS:,} assignments"
        )

    result: dict[str, str] = {}
    total_codepoints = 0
    for raw in values:
        if type(raw) is not str:
            raise ValueError("--current-owner assignment must be one exact built-in string")
        if len(raw) > MAX_CURRENT_OWNER_ASSIGNMENT_CODEPOINTS:
            raise ValueError(
                "--current-owner assignment exceeds source ceiling "
                f"{MAX_CURRENT_OWNER_ASSIGNMENT_CODEPOINTS} code points"
            )
        total_codepoints += len(raw)
        if total_codepoints > MAX_CURRENT_OWNER_CLI_TOTAL_CODEPOINTS:
            raise ValueError(
                "--current-owner custody aggregate exceeds source ceiling "
                f"{MAX_CURRENT_OWNER_CLI_TOTAL_CODEPOINTS:,} code points"
            )
        owner, separator, blob = raw.partition("=")
        if not separator:
            raise ValueError("--current-owner must be OWNER=40-lowercase-hex-blob")
        owner = admit_owner_identity(owner, field="--current-owner owner")
        if type(blob) is not str or SHA1_RE.fullmatch(blob) is None:
            raise ValueError("--current-owner must be OWNER=40-lowercase-hex-blob")
        if owner in result and result[owner] != blob:
            raise ValueError(f"conflicting current owner blob for {owner}")
        result[owner] = blob
    return _admit_current_owner_blobs(result)


def _admit_programmatic_argv(argv: list[str]) -> list[str]:
    """Detach one finite exact argv vector before argparse may traverse caller evidence."""

    if type(argv) is not list:
        raise ValueError("programmatic argv requires one exact built-in list")
    if len(argv) > MAX_PROGRAMMATIC_ARGV_ITEMS:
        raise ValueError(
            "programmatic argv exceeds source item ceiling "
            f"{MAX_PROGRAMMATIC_ARGV_ITEMS}"
        )

    total_codepoints = 0
    for raw in argv:
        if type(raw) is not str:
            raise ValueError("programmatic argv members must be exact built-in strings")
        if len(raw) > MAX_PROGRAMMATIC_ARG_CODEPOINTS:
            raise ValueError(
                "programmatic argv member exceeds source ceiling "
                f"{MAX_PROGRAMMATIC_ARG_CODEPOINTS} code points"
            )
        total_codepoints += len(raw)
        if total_codepoints > MAX_PROGRAMMATIC_ARGV_TOTAL_CODEPOINTS:
            raise ValueError(
                "programmatic argv exceeds total source ceiling "
                f"{MAX_PROGRAMMATIC_ARGV_TOTAL_CODEPOINTS} code points"
            )

    return argv.copy()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--patch-root", default=str(PATCH_ROOT))
    parser.add_argument(
        "--current-owner",
        action="append",
        default=[],
        metavar="OWNER=BLOB",
        help="Authenticated current owner blob; repeat for multiple owners.",
    )
    args = parser.parse_args(_admit_programmatic_argv(argv) if argv is not None else None)

    try:
        current_owner_blobs = (
            _parse_owner_blob(args.current_owner)
            if len(args.current_owner) > 0
            else None
        )
    except ValueError as exc:
        parser.error(str(exc))

    print(json.dumps(
        classify(Path(args.patch_root), current_owner_blobs),
        indent=2,
        sort_keys=True,
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
