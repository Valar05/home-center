#!/usr/bin/env python3
"""Source-only custody probe for TRY FOREVER owner surgery artifacts.

This does not apply patches, execute Android, touch the phone/P0 chain, or promote a proposed
surgery into owner wiring. It exposes patch-order hazards when several unapplied source surgeries
target the same exact owner blob and binds that evidence to an authenticated current-owner blob
when one is supplied.

v4 treats textual ``*.patch`` and structured ``*.delta.json`` owner deltas as one finite custody
family. Every matching artifact must either become an admitted surgery record or a bounded
``discoveryError``. Malformed/unreadable/over-budget evidence therefore cannot silently disappear
or crash an allegedly exhaustive inventory.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable


PATCH_ROOT = Path("patches")
DEFAULT_OWNER = "android/operator-overlay/app/src/main/java/com/homecenter/operatoroverlay/OperatorOverlayService.java"
DELTA_SCHEMA = "try-forever-owner-delta.v1"
MAX_ARTIFACT_BYTES = 1_048_576

BASE_RE = re.compile(r"^#\s*(?:BASE OWNER BLOB|Base owner blob|Base blob)\s*:\s*([0-9a-f]{40})\s*$", re.I | re.M)
OWNER_RE = re.compile(r"^#\s*(?:OWNER|Target|Base path)\s*:\s*(\S+)\s*$", re.I | re.M)
STATE_RE = re.compile(r"^#\s*(?:STATUS|State)\s*:\s*([^\n]+?)\s*$", re.I | re.M)
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
    upper = state.upper()
    if any(token in upper for token in ("REJECTED", "SUPERSEDED", "APPLIED_SOURCE")):
        return False
    return "PROPOSED" in upper


def _read_bounded_utf8(path: Path) -> str:
    try:
        with path.open("rb") as handle:
            payload = handle.read(MAX_ARTIFACT_BYTES + 1)
    except OSError as exc:
        raise ArtifactAdmissionError(f"artifact read failed: {type(exc).__name__}: {exc}") from exc

    if len(payload) > MAX_ARTIFACT_BYTES:
        raise ArtifactAdmissionError(
            f"artifact exceeds {MAX_ARTIFACT_BYTES} byte custody budget"
        )
    try:
        return payload.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise ArtifactAdmissionError(
            f"artifact is not strict UTF-8 at byte {exc.start}"
        ) from exc


def _error(path: Path, artifact_kind: str, exc: Exception) -> DiscoveryError:
    return DiscoveryError(
        path=path.as_posix(),
        artifact_kind=artifact_kind,
        boundary=(
            f"Owner surgery artifact excluded from custody authority: "
            f"{type(exc).__name__}: {exc}"
        ),
    )


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

        state_text = state.group(1).strip()
        if not state_text:
            raise ArtifactAdmissionError("patch state/status must not be blank")

        return Surgery(
            path=path.as_posix(),
            artifact_kind="patch",
            owner=owner,
            base_blob=base.group(1).lower(),
            state=state_text,
            promotion_candidate=_promotion_candidate(state_text),
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

        base_blob = _consistent_delta_string(payload, DELTA_BASE_KEYS, "base owner blob").lower()
        if SHA1_RE.fullmatch(base_blob) is None:
            raise ValueError("base owner blob must be 40 lowercase hexadecimal characters")

        state_text = _consistent_delta_string(payload, DELTA_STATE_KEYS, "state/status").strip()
        if not state_text:
            raise ValueError("state/status must not be blank")

        return Surgery(
            path=path.as_posix(),
            artifact_kind="delta_json",
            owner=owner,
            base_blob=base_blob,
            state=state_text,
            promotion_candidate=_promotion_candidate(state_text),
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


def classify(
    root: Path = PATCH_ROOT,
    current_owner_blobs: dict[str, str] | None = None,
) -> dict[str, object]:
    current_owner_blobs = {
        owner: blob.lower()
        for owner, blob in (current_owner_blobs or {}).items()
    }
    surgeries: list[Surgery] = []
    discovery_errors: list[DiscoveryError] = []

    for path in sorted(root.glob("try-forever-*.patch")):
        surgery, error = inspect_patch(path)
        if surgery is not None:
            surgeries.append(surgery)
        if error is not None:
            discovery_errors.append(error)

    for path in sorted(root.glob("try-forever-*.delta.json")):
        surgery, error = inspect_delta(path)
        if surgery is not None:
            surgeries.append(surgery)
        if error is not None:
            discovery_errors.append(error)

    surgeries.sort(key=lambda item: (item.owner, item.base_blob, item.path))
    discovery_errors.sort(key=lambda item: item.path)

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
        "schema": "try-forever-owner-surgery-custody.v4",
        "artifactKindsScanned": ["patch", "delta_json"],
        "artifactReadBudgetBytes": MAX_ARTIFACT_BYTES,
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
            "boundedArtifactRead": True,
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
        blob = blob.strip().lower()
        if not separator or not owner or not SHA1_RE.fullmatch(blob):
            raise ValueError("--current-owner must be OWNER=40-lowercase-hex-blob")
        if owner in result and result[owner] != blob:
            raise ValueError(f"conflicting current owner blob for {owner}")
        result[owner] = blob
    return result


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
