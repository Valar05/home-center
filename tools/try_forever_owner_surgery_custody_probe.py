#!/usr/bin/env python3
"""Source-only custody probe for TRY FOREVER owner surgery artifacts.

This does not apply patches, execute Android, touch the phone/P0 chain, or promote a proposed
surgery into owner wiring. It exists to expose patch-order hazards when several unapplied source
surgeries target the same exact owner blob.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path


PATCH_ROOT = Path("patches")
DEFAULT_OWNER = "android/operator-overlay/app/src/main/java/com/homecenter/operatoroverlay/OperatorOverlayService.java"

BASE_RE = re.compile(r"^#\s*(?:BASE OWNER BLOB|Base owner blob|Base blob)\s*:\s*([0-9a-f]{40})\s*$", re.I | re.M)
OWNER_RE = re.compile(r"^#\s*(?:OWNER|Target|Base path)\s*:\s*(\S+OperatorOverlayService\.java)\s*$", re.I | re.M)
STATE_RE = re.compile(r"^#\s*(?:STATUS|State)\s*:\s*([^\n]+?)\s*$", re.I | re.M)


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


def classify(root: Path = PATCH_ROOT) -> dict[str, object]:
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

    collisions = []
    for (owner, base_blob), group in sorted(active_groups.items()):
        if len(group) < 2:
            continue
        collisions.append({
            "owner": owner,
            "baseBlob": base_blob,
            "status": "COLLISION_SET",
            "promotionCandidates": [asdict(item) for item in group],
            "boundary": (
                "Multiple unapplied surgeries share one exact owner/base custody. Applying one "
                "stales the others unless they are deliberately ordered, rebased, or converged."
            ),
        })

    return {
        "schema": "try-forever-owner-surgery-custody.v1",
        "surgeries": [asdict(item) for item in surgeries],
        "collisionSets": collisions,
        "capability": {
            "sourceInspection": True,
            "patchApplied": False,
            "ownerWired": False,
            "regressionExecuted": False,
            "tested": False,
            "runtimeUi": False,
            "runtimeTalkBack": False,
            "phoneDelivered": False,
        },
    }


def main() -> int:
    print(json.dumps(classify(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
