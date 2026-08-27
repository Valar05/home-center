#!/usr/bin/env python3
"""RED source regression for direct semantic-id lookup source-work custody.

SOURCE ONLY / UNEXECUTED. Direct accessibility/model lookup helpers currently trim and
case-fold arbitrary caller Strings before a broad source-work gate. This fixture pins an
existing-owner repair without claiming regression execution, TESTED, runtime TalkBack,
deployment, phone delivery, or P0 action.
"""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FRAME_ACCESSIBILITY = ROOT / (
    "android/operator-overlay/app/src/main/java/com/homecenter/operatoroverlay/"
    "HeartbeatFrameAccessibility.java"
)
VIEW_MODEL = ROOT / (
    "android/operator-overlay/app/src/main/java/com/homecenter/operatoroverlay/"
    "HeartbeatOverlayViewModel.java"
)


def ordered(source: str, earlier: str, later: str) -> None:
    left = source.find(earlier)
    right = source.find(later)
    assert left >= 0, f"missing source-boundary marker: {earlier}"
    assert right >= 0, f"missing downstream-work marker: {later}"
    assert left < right, f"{earlier!r} must occur before {later!r}"


def main() -> int:
    frame = FRAME_ACCESSIBILITY.read_text(encoding="utf-8")
    model = VIEW_MODEL.read_text(encoding="utf-8")

    assert (
        "MAX_DIRECT_NODE_ID_SOURCE_CODE_UNITS =\n"
        "            HeartbeatEnvelopeParser.MAX_ENVELOPE_SOURCE_CODE_UNITS"
        in frame
    ), "frame accessibility must reuse the canonical broad direct-source ceiling"
    assert frame.count("String target = boundedLookupId(nodeId);") >= 2, (
        "both stable-id detail lookup and focus-index lookup must cross one bounded helper"
    )
    ordered(
        frame,
        "value.length() > MAX_DIRECT_NODE_ID_SOURCE_CODE_UNITS",
        "clean(value).toLowerCase(Locale.ROOT)",
    )

    assert (
        "MAX_DIRECT_CONTROL_ID_SOURCE_CODE_UNITS =\n"
        "            HeartbeatEnvelopeParser.MAX_ENVELOPE_SOURCE_CODE_UNITS"
        in model
    ), "UI model lookup must reuse the canonical broad direct-source ceiling"
    assert "String target = boundedControlLookupId(id);" in model
    ordered(
        model,
        "value.length() > MAX_DIRECT_CONTROL_ID_SOURCE_CODE_UNITS",
        "clean(value).toLowerCase(Locale.ROOT)",
    )

    assert "new HeartbeatOverlayViewModel" not in frame
    assert "new HeartbeatFrameAccessibility" not in model
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
