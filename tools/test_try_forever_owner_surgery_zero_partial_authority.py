#!/usr/bin/env python3
"""Source regression for exhaustive owner-surgery promotion authority.

Canonical v10 now marks a wounded inventory with ``evidenceComplete=false`` and suppresses every
promotion-authority group while preserving safely parsed sibling surgeries as diagnostics. This
fixture locks that source contract for current, stale, and unverified owner custody.

SOURCE ONLY. This regression has not been observed executing in an authorized test lane.
"""

from pathlib import Path
from tempfile import TemporaryDirectory

from try_forever_owner_surgery_custody_probe import classify


OWNER = "android/operator-overlay/app/src/main/java/com/homecenter/operatoroverlay/OperatorOverlayService.java"
BASE = "c5de1411a6b68087ae17aff83c032af754587150"
STALE = "1111111111111111111111111111111111111111"


def patch(name: str, *, base: str = BASE) -> str:
    return (
        "# STATUS: CORRECTED_PROPOSED_NOT_APPLIED\n"
        f"# BASE OWNER BLOB: {base}\n"
        f"# OWNER: {OWNER}\n"
        f"# fixture: {name}\n"
        "diff --git a/owner b/owner\n"
    )


def assert_no_partial_authority(result: dict[str, object]) -> None:
    assert result["schema"] == "try-forever-owner-surgery-custody.v10"
    assert result["evidenceComplete"] is False
    assert len(result["surgeries"]) == 2, result["surgeries"]
    assert len(result["discoveryErrors"]) == 1, result["discoveryErrors"]
    assert result["collisionSets"] == []
    assert result["staleBaseGroups"] == []
    assert result["unverifiedBaseGroups"] == []


def main() -> int:
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "try-forever-good-a.patch").write_text(patch("a"), encoding="utf-8")
        (root / "try-forever-good-b.patch").write_text(patch("b"), encoding="utf-8")
        # Matching artifact is finite ordinary UTF-8 but cannot earn surgery authority.
        (root / "try-forever-bad.patch").write_text(
            f"# BASE OWNER BLOB: {BASE}\n# OWNER: {OWNER}\n",
            encoding="utf-8",
        )

        current = classify(root, {OWNER: BASE})
        assert_no_partial_authority(current)

        moved = classify(root, {OWNER: STALE})
        assert_no_partial_authority(moved)

        unverified = classify(root)
        assert_no_partial_authority(unverified)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
