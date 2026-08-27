#!/usr/bin/env python3
"""Source-only regression for direct refresh-plan selection/focus source-work custody.

UNEXECUTED. This pins the existing HeartbeatOverlayRefreshPlan owner so direct callers cannot
spend arbitrary trim/case-fold work before the already-bounded semantic-id lookup organs run.
"""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OWNER = ROOT / (
    "android/operator-overlay/app/src/main/java/com/homecenter/operatoroverlay/"
    "HeartbeatOverlayRefreshPlan.java"
)


def main() -> int:
    source = OWNER.read_text(encoding="utf-8")

    assert (
        "MAX_DIRECT_SELECTION_ID_SOURCE_CODE_UNITS =\n"
        "            HeartbeatEnvelopeParser.MAX_ENVELOPE_SOURCE_CODE_UNITS"
        in source
    )
    helper = source.index("private static String boundedSelectionId(String value)")
    gate = source.index(
        "value.length() > MAX_DIRECT_SELECTION_ID_SOURCE_CODE_UNITS",
        helper,
    )
    trim = source.index("return clean(value);", helper)
    assert gate < trim, "direct selection source gate must precede trim"

    from_frame = source.index("public static Plan fromFrame(")
    assert source.index("boundedSelectionId(selectedControlId)", from_frame) > from_frame

    viewport = source.index("public static String viewportAnchorId(")
    assert source.index("boundedSelectionId(selectedControlId)", viewport) > viewport
    assert source.index("boundedSelectionId(keyboardFocusedControlId)", viewport) > viewport

    assert "String selected = clean(selectedControlId);" not in source
    assert "String focused = clean(keyboardFocusedControlId);" not in source
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
