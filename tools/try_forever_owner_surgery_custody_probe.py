#!/usr/bin/env python3
"""Source-only custody probe for TRY FOREVER owner surgery artifacts.

This does not apply patches, execute Android, touch the phone/P0 chain, or promote a proposed
surgery into owner wiring. It exposes patch-order hazards when several unapplied source surgeries
target the same exact owner blob and can optionally bind that evidence to an authenticated
current-owner blob supplied by the caller.
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

BASE_RE = re.compile(r"^#\s*(?:BASE OWNER BLOB|Base owner blob|Base blob)\s*:\s*([0-9a-f]{40})\s*$", re.I | re.M)
OWNER_RE = re.compile(r"^#\s*(?:OWNER|Target|Base path)\s*:\s*(\S+OperatorOverlayService\.java)\s*$", re.I | re.M)
STATE_RE = re.compile(r"^#\s*(?:STATUS|State)\s*:\s*([^\n]+?)\s*$", re.I | re.M)
SHA1_RE = re.compile(r"^[0-9a-f]{40}$")


@dataclass(frozen=True)
class Surgery:
    path: str
    owner: str
    base_blob: str
    state: str
    promotion_candidate: bool


def _promotion_candidate(state: str) -> bool:
    upper = state.upper()
    if any(token in upper for token in ("REJECTED", "SUPERSEDED", "APPLIED_SOURCE")):
        return False
    return "PROPOSED" in upper


def inspect_patch(path: Path) -> Surgery | None:
    text = path.read_text(encoding="utf-8")
    if "OperatorOverlayService.java" not in text:
        return None
    base = BASE_RE.search(text)
    state = STATE_RE.search(text)
    if base is None or state is None:
        return None
    owner_match = OWNER_RE.search(text)
    owner = owner_match.group(1) if owner_match else DEFAULT_OWNER
    state_text = state.group(1).strip()
    return Surgery(
        path=path.as_posix(),
        owner=owner,
        base_blob=base.group(1).lower(),
        state=state_text,
        promotion_candidate=_promotion_candidate(state_text),
    )


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
    for path in sorted(root.glob("try-forever-*.patch")):
        surgery = inspect_patch(path)
        if surgery is not None:
            surgeries.append(surgery)

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
        "schema": "try-forever-owner-surgery-custody.v2",
        "surgeries": [asdict(item) for item in surgeries],
        "currentOwnerBlobs": current_owner_blobs,
        "collisionSets": collision_sets,
        "staleBaseGroups": stale_base_groups,
        "unverifiedBaseGroups": unverified_base_groups,
        "capability": {
            "sourceInspection": True,
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
