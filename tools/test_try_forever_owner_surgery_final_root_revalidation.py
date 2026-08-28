#!/usr/bin/env python3
"""RED regression source for owner-surgery custody after artifact observation.

Current v7 revalidates the named patches root after bounded traversal, then parses admitted
artifacts. This fixture moves the root after that post-scan check but before the first artifact
read. Promotion authority must remain zero until the canonical probe adds a final root revalidation
after all artifact observations.

Source fixture only. It does not apply the prepared v8 patch or claim regression execution.
"""

from pathlib import Path
from tempfile import TemporaryDirectory

import try_forever_owner_surgery_custody_probe as custody


OWNER = "android/operator-overlay/app/src/main/java/com/homecenter/operatoroverlay/OperatorOverlayService.java"
BASE = "c5de1411a6b68087ae17aff83c032af754587150"


def patch(name: str) -> str:
    return (
        "# STATUS: CORRECTED_PROPOSED_NOT_APPLIED\n"
        f"# BASE OWNER BLOB: {BASE}\n"
        f"# OWNER: {OWNER}\n"
        f"# fixture: {name}\n"
        "diff --git a/owner b/owner\n"
    )


def main() -> int:
    # Control: stable root may emit the admitted surgery record.
    with TemporaryDirectory() as tmp:
        root = Path(tmp) / "patches"
        root.mkdir()
        (root / "try-forever-a.patch").write_text(patch("stable"), encoding="utf-8")
        stable = custody.classify(root, {OWNER: BASE})
        assert len(stable["surgeries"]) == 1
        assert stable["evidenceComplete"] is True

    # Hostile case: replace the named root only after traversal/post-scan revalidation has
    # completed. The candidate path is intentionally reused by the replacement root so current
    # v7 can parse plausible evidence from the wrong directory object unless a final root gate
    # brackets artifact observation too.
    with TemporaryDirectory() as tmp:
        base_root = Path(tmp)
        root = base_root / "patches"
        root.mkdir()
        (root / "try-forever-a.patch").write_text(patch("original"), encoding="utf-8")

        replacement = base_root / "replacement"
        replacement.mkdir()
        (replacement / "try-forever-a.patch").write_text(patch("replacement"), encoding="utf-8")
        displaced = base_root / "patches-old"

        real_inspect_patch = custody.inspect_patch
        replaced = False

        def replace_after_scan_then_inspect(path: Path):
            nonlocal replaced
            if not replaced:
                root.rename(displaced)
                replacement.rename(root)
                replaced = True
            return real_inspect_patch(path)

        custody.inspect_patch = replace_after_scan_then_inspect
        try:
            result = custody.classify(root, {OWNER: BASE})
        finally:
            custody.inspect_patch = real_inspect_patch

        assert replaced is True
        assert result["surgeries"] == []
        assert result["collisionSets"] == []
        assert result["staleBaseGroups"] == []
        assert result["unverifiedBaseGroups"] == []
        assert result["evidenceComplete"] is False
        assert any(
            error["artifact_kind"] == "artifact_root"
            and (
                "device/inode identity changed" in error["boundary"]
                or "identity is unavailable" in error["boundary"]
            )
            for error in result["discoveryErrors"]
        )
        assert result["capability"].get("artifactRootFinalRevalidation") is True

    print("TRY FOREVER owner surgery final-root regression source: late persistent drift fails closed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
