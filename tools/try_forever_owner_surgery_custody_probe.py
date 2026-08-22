#!/usr/bin/env python3
"""Source-only custody probe for TRY FOREVER owner surgery artifacts.

This does not apply patches, execute Android, touch the phone/P0 chain, or promote a proposed
surgery into owner wiring. It exposes patch-order hazards when several unapplied source surgeries
target the same exact owner blob and binds that evidence to an authenticated current-owner blob
when one is supplied.

v10 treats textual ``*.patch`` and structured ``*.delta.json`` owner deltas as one finite custody
family. The named ``patches`` root is admitted and revalidated through the existing portable
no-follow root-identity organ around bounded non-recursive traversal, then revalidated again after
all admitted artifact observations before any surgery/collision/stale/unverified authority is
emitted. Directory-entry work, matching-candidate collection, and each admitted finite ordinary
artifact remain independently bounded. Promotion readiness is admitted by exact canonical state,
never by a ``PROPOSED`` substring or by regex/whitespace normalization. Authenticated current-owner
blob custody is also exact: normalization-dependent blob text cannot be repaired into authority.
Root redirectors, persistent root drift, unavailable identity, or invalid state/evidence fail
closed. This is persistent-drift evidence, not an atomic filesystem binding claim.
"""

from __future__ import annotations

import argparse
import json
import os
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

from try_forever_generated_index_artifact_observation import (
    GeneratedIndexArtifactChangedError,
    GeneratedIndexArtifactResourceLimitError,
    GeneratedIndexArtifactTopologyError,
    observe_generated_index_artifact,
)
from try_forever_skill_root_identity import (
    capture_directory_root_identity,
    revalidate_directory_root_identity,
)
from try_forever_owner_surgery_state_policy import admit_owner_surgery_state


PATCH_ROOT = Path("patches")
PATCH_ROOT_SUBJECT = "owner surgery patches root"
DEFAULT_OWNER = "android/operator-overlay/app/src/main/java/com/homecenter/operatoroverlay/OperatorOverlayService.java"
DELTA_SCHEMA = "try-forever-owner-delta.v1"
MAX_ARTIFACT_BYTES = 1_048_576
MAX_CUSTODY_ARTIFACTS = 2_048
MAX_CUSTODY_DIRECTORY_ENTRIES = 32_768

BASE_RE = re.compile(r"^#\s*(?:BASE OWNER BLOB|Base owner blob|Base blob)\s*:\s*([0-9a-f]{40})\s*$", re.I | re.M)
OWNER_RE = re.compile(r"^#\s*(?:OWNER|Target|Base path)\s*:\s*(\S+)\s*$", re.I | re.M)
STATE_RE = re.compile(r"^#\s*(?:STATUS|State)\s*: ([^\r\n]*)$", re.I | re.M)
SHA1_RE = re.compile(r"^[0-9a-f]{40}$")
DELTA_BASE_KEYS = ("baseBlob", "ownerBaseBlob", "baseOwnerBlob")
DELTA_STATE_KEYS = ("state", "status")


@dataclass(frozen=True)
class Surgery:
    path: str
    artifact_kind: str
    owner: str
    base_blob: str
    state: str
    promotion_candidate: bool


@dataclass(frozen=True)
class DiscoveryError:
    path: str
    artifact_kind: str
    boundary: str


class ArtifactAdmissionError(ValueError):
    """Recognized surgery evidence could not be safely admitted."""


def _promotion_candidate(state: str) -> bool:
    return admit_owner_surgery_state(state).promotion_candidate


def _artifact_kind_for_name(name: str) -> str | None:
    if not name.startswith("try-forever-"):
        return None
    if name.endswith(".delta.json"):
        return "delta_json"
    if name.endswith(".patch"):
        return "patch"
    return None


def _read_bounded_utf8(path: Path) -> str:
    """Reuse the existing finite regular-artifact organ for owner-surgery evidence."""

    try:
        observation = observe_generated_index_artifact(
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
    return observation.utf8_text


def _error(path: Path, artifact_kind: str, exc: Exception) -> DiscoveryError:
    return DiscoveryError(
        path=path.as_posix(),
        artifact_kind=artifact_kind,
        boundary=(
            f"Owner surgery artifact excluded from custody authority: "
            f"{type(exc).__name__}: {exc}"
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
    """Bind root identity, then bound directory work and candidate storage before parsing.

    Every directory entry counts against ``max_entries`` even when unrelated to TRY FOREVER.
    Every matching patch/delta counts against ``max_candidates``. Max+1 on either throat withholds
    the entire promotion inventory. Root topology/identity is observed before and after traversal;
    persistent redirector/replacement drift or unavailable identity also withholds the whole
    inventory. The bracket deliberately does not claim swap-and-restore or identity-reuse immunity.
    """

    if max_candidates < 0 or max_candidates > MAX_CUSTODY_ARTIFACTS:
        raise ValueError(
            f"owner surgery candidate budget must be between 0 and {MAX_CUSTODY_ARTIFACTS}"
        )
    if max_entries < 0 or max_entries > MAX_CUSTODY_DIRECTORY_ENTRIES:
        raise ValueError(
            f"owner surgery directory-entry budget must be between 0 and {MAX_CUSTODY_DIRECTORY_ENTRIES}"
        )

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
        text = _read_bounded_utf8(path)
        base = BASE_RE.search(text)
        state = STATE_RE.search(text)
        if base is None:
            raise ArtifactAdmissionError("patch is missing an exact base-owner blob header")
        if state is None:
            raise ArtifactAdmissionError("patch is missing a state/status header")

        owner_match = OWNER_RE.search(text)
        if owner_match is None:
            if "OperatorOverlayService.java" not in text:
                raise ArtifactAdmissionError(
                    "patch is missing owner metadata and does not name the default owner"
                )
            owner = DEFAULT_OWNER
        else:
            owner = owner_match.group(1)

        base_blob = base.group(1)
        if SHA1_RE.fullmatch(base_blob) is None:
            raise ArtifactAdmissionError(
                "patch base owner blob must be 40 lowercase hexadecimal characters"
            )

        state_admission = admit_owner_surgery_state(state.group(1))

        return Surgery(
            path=path.as_posix(),
            artifact_kind="patch",
            owner=owner,
            base_blob=base_blob,
            state=state_admission.state,
            promotion_candidate=state_admission.promotion_candidate,
        ), None
    except (ArtifactAdmissionError, OSError, UnicodeError, ValueError) as exc:
        return None, _error(path, "patch", exc)


def _reject_duplicate_json_members(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON member: {key}")
        result[key] = value
    return result


def _consistent_delta_string(
    payload: dict[str, object],
    keys: tuple[str, ...],
    field_name: str,
) -> str:
    present = [(key, payload[key]) for key in keys if key in payload]
    if not present:
        raise ValueError(f"missing {field_name}")
    values: list[str] = []
    for key, raw in present:
        if not isinstance(raw, str) or not raw:
            raise ValueError(f"{key} must be a non-empty string")
        values.append(raw)
    if len(set(values)) != 1:
        raise ValueError(f"conflicting {field_name} aliases")
    return values[0]


def inspect_delta(path: Path) -> tuple[Surgery | None, DiscoveryError | None]:
    try:
        payload = json.loads(
            _read_bounded_utf8(path),
            object_pairs_hook=_reject_duplicate_json_members,
            parse_constant=lambda value: (_ for _ in ()).throw(
                ValueError(f"non-standard JSON constant: {value}")),
        )
        if not isinstance(payload, dict):
            raise ValueError("owner delta root must be an object")
        if payload.get("schema") != DELTA_SCHEMA:
            raise ValueError(f"unsupported owner delta schema: {payload.get('schema')!r}")

        owner = payload.get("owner")
        if not isinstance(owner, str) or not owner:
            raise ValueError("owner must be a non-empty string")

        base_blob = _consistent_delta_string(payload, DELTA_BASE_KEYS, "base owner blob")
        if SHA1_RE.fullmatch(base_blob) is None:
            raise ValueError("base owner blob must be 40 lowercase hexadecimal characters")

        state_admission = admit_owner_surgery_state(
            _consistent_delta_string(payload, DELTA_STATE_KEYS, "state/status")
        )

        return Surgery(
            path=path.as_posix(),
            artifact_kind="delta_json",
            owner=owner,
            base_blob=base_blob,
            state=state_admission.state,
            promotion_candidate=state_admission.promotion_candidate,
        ), None
    except (ArtifactAdmissionError, OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        return None, _error(path, "delta_json", exc)


def _group_payload(owner: str, base_blob: str, group: list[Surgery], status: str) -> dict[str, object]:
    return {
        "owner": owner,
        "baseBlob": base_blob,
        "status": status,
        "promotionCandidates": [asdict(item) for item in group],
    }


def _admit_current_owner_blobs(values: dict[str, str] | None) -> dict[str, str]:
    """Admit authenticated current-owner blob evidence without normalization or repair."""

    result: dict[str, str] = {}
    for owner, blob in (values or {}).items():
        if not isinstance(owner, str) or not owner:
            raise ValueError("current owner custody requires a non-empty owner identity")
        if not isinstance(blob, str) or SHA1_RE.fullmatch(blob) is None:
            raise ValueError("current owner custody requires a 40-lowercase-hex-blob")
        result[owner] = blob
    return result


def classify(
    root: Path = PATCH_ROOT,
    current_owner_blobs: dict[str, str] | None = None,
    *,
    max_candidates: int = MAX_CUSTODY_ARTIFACTS,
    max_entries: int = MAX_CUSTODY_DIRECTORY_ENTRIES,
) -> dict[str, object]:
    current_owner_blobs = _admit_current_owner_blobs(current_owner_blobs)
    surgeries: list[Surgery] = []
    discovery_errors: list[DiscoveryError] = []

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
        "artifactKindsScanned": ["patch", "delta_json"],
        "artifactReadBudgetBytes": MAX_ARTIFACT_BYTES,
        "artifactCandidateBudget": max_candidates,
        "artifactCandidatesObserved": candidates_observed,
        "artifactDirectoryEntryBudget": max_entries,
        "artifactDirectoryEntriesObserved": entries_observed,
        "surgeries": [asdict(item) for item in surgeries],
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
            "artifactRootIdentityRevalidation": True,
            "artifactRootFinalRevalidation": True,
            "exactOwnerSurgeryStateAdmission": True,
            "nonNormalizingPatchStateHeader": True,
            "exactCurrentOwnerBlobAdmission": True,
            "substringPromotionAuthority": False,
            "artifactRootAtomicBinding": False,
            "boundedArtifactDirectoryScan": True,
            "boundedArtifactCandidateSet": True,
            "boundedArtifactRead": True,
            "finiteRegularArtifactCustody": True,
            "currentOwnerCustodyProvided": bool(current_owner_blobs),
            "patchApplied": False,
            "ownerWired": False,
            "regressionExecuted": False,
            "tested": False,
            "runtimeUi": False,
            "runtimeTalkBack": False,
            "phoneDelivered": False,
        },
    }


def _parse_owner_blob(values: Iterable[str]) -> dict[str, str]:
    result: dict[str, str] = {}
    for raw in values:
        owner, separator, blob = raw.partition("=")
        owner = owner.strip()
        if not separator or not owner or SHA1_RE.fullmatch(blob) is None:
            raise ValueError("--current-owner must be OWNER=40-lowercase-hex-blob")
        if owner in result and result[owner] != blob:
            raise ValueError(f"conflicting current owner blob for {owner}")
        result[owner] = blob
    return _admit_current_owner_blobs(result)


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--patch-root", default=str(PATCH_ROOT))
    parser.add_argument(
        "--current-owner",
        action="append",
        default=[],
        metavar="OWNER=BLOB",
        help="Authenticated current owner blob; repeat for multiple owners.",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    try:
        current_owner_blobs = _parse_owner_blob(args.current_owner)
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