#!/usr/bin/env python3
"""RED source regression for interrupted-refresh diagnostic source-work custody.

SOURCE ONLY / UNEXECUTED. Exact refreshBoundary evidence is intentionally preserved on the
scene/model, but direct pre-parser rejection can currently make collapsed speech safety-scan
and render/announcement identity hash arbitrarily large diagnostic text. This fixture pins a
bounded non-authoritative projection/identity path without rewriting the exact boundary.
"""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCENE = ROOT / (
    "android/operator-overlay/app/src/main/java/com/homecenter/operatoroverlay/"
    "HeartbeatSceneGraph.java"
)
REFRESH = ROOT / (
    "android/operator-overlay/app/src/main/java/com/homecenter/operatoroverlay/"
    "HeartbeatOverlayRefreshPlan.java"
)


def ordered(source: str, earlier: str, later: str) -> None:
    left = source.find(earlier)
    right = source.find(later)
    assert left >= 0, f"missing source-boundary marker: {earlier}"
    assert right >= 0, f"missing downstream-work marker: {later}"
    assert left < right, f"{earlier!r} must occur before {later!r}"


def main() -> int:
    scene = SCENE.read_text(encoding="utf-8")
    refresh = REFRESH.read_text(encoding="utf-8")

    speech_gate = (
        "refreshBoundary.length() > HeartbeatPlainTextBudget.MAX_SOURCE_CODE_UNITS"
    )
    ordered(
        scene,
        speech_gate,
        "safeBoundedSpeech(\n                    refreshBoundary",
    )
    assert "Heartbeat refresh boundary exceeds speech source-work ceiling." in scene
    assert "this.refreshBoundary = raw(refreshBoundary);" in scene, (
        "exact source boundary must remain preserved independently from bounded speech"
    )

    assert (
        "MAX_REFRESH_BOUNDARY_IDENTITY_SOURCE_CODE_UNITS =\n"
        "            HeartbeatPlainTextBudget.MAX_SOURCE_CODE_UNITS"
        in refresh
    )
    assert "String identityBoundary = refreshBoundaryIdentity(exactBoundary);" in refresh
    assert refresh.count("identityBoundary);") >= 2, (
        "render and announcement identity must both consume the bounded diagnostic identity"
    )
    ordered(
        refresh,
        "exact.length() > MAX_REFRESH_BOUNDARY_IDENTITY_SOURCE_CODE_UNITS",
        'return "<refresh-boundary-source-limit:" + exact.length() + ">";',
    )
    assert "frame.refreshBoundary" in refresh, (
        "exact boundary remains present in the accepted frame/model evidence path"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
