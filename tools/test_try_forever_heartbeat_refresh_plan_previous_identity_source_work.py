#!/usr/bin/env python3
"""RED source regression for direct previous refresh identity source-work custody.

SOURCE ONLY / UNEXECUTED. Generated structure/render/announcement identities are tiny, but the
public refresh-plan decision helpers still accept arbitrary caller Strings and currently trim
them before equality. This fixture pins the existing-owner repair without claiming it exists.
"""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OWNER = ROOT / (
    "android/operator-overlay/app/src/main/java/com/homecenter/operatoroverlay/"
    "HeartbeatOverlayRefreshPlan.java"
)


def main() -> int:
    source = OWNER.read_text(encoding="utf-8")

    helper = source.index("private static String boundedPreviousIdentity(String value)")
    gate = source.index(
        "value.length() > MAX_DIRECT_SELECTION_ID_SOURCE_CODE_UNITS",
        helper,
    )
    trim = source.index("return clean(value);", helper)
    assert gate < trim, "previous identity source gate must precede trim"

    assert "!boundedPreviousIdentity(previousStructureIdentity).equals(next.structureIdentity)" in source
    assert "!boundedPreviousIdentity(previousRenderIdentity).equals(next.renderIdentity)" in source
    assert "String previous = boundedPreviousIdentity(previousAnnouncementIdentity);" in source

    assert "clean(previousStructureIdentity).equals(next.structureIdentity)" not in source
    assert "clean(previousRenderIdentity).equals(next.renderIdentity)" not in source
    assert "String previous = clean(previousAnnouncementIdentity);" not in source
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
