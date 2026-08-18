#!/usr/bin/env python3
"""Classify the existing Operator Overlay deep-detail owner source without runtime claims.

This is a repository/source evidence tool. It does not render, deploy, touch a phone,
or prove Android/TalkBack behavior. The sole purpose is to stop source capability
state from being re-derived by hand every heartbeat.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, Iterable

OWNER_DEFAULT = Path(
    "android/operator-overlay/app/src/main/java/"
    "com/homecenter/operatoroverlay/OperatorOverlayService.java"
)

REQUIRED_WIRED_MARKERS = {
    "presentation_generation": "heartbeatDetailPresentationGeneration",
    "pixel_height_policy": "HeartbeatDetailSurfacePolicy.maxViewportHeightPx",
    "scrolling_movement": "heartbeatDetail.setMovementMethod",
    "passive_focus_reassertion": "heartbeatDetail.setFocusable(presentation.keyboardFocusable)",
    "passive_click_reassertion": "heartbeatDetail.setClickable(presentation.clickable)",
    "passive_long_click_reassertion": "heartbeatDetail.setLongClickable(presentation.longClickable)",
    "generation_restore": "restoreHeartbeatDetailScrollAfterLayout",
    "scroll_clamp": "HeartbeatDetailSurfacePolicy.clampScrollY",
}

LEGACY_FORBIDDEN_MARKERS = {
    "five_line_layout_cap": "heartbeatDetail.setMaxLines(5);",
    "legacy_safe_formatter": "String safe = detail == null || detail.trim().isEmpty()",
}


def _presence(source: str, markers: Dict[str, str]) -> Dict[str, bool]:
    return {name: marker in source for name, marker in markers.items()}


def classify_source(source: str) -> dict:
    required = _presence(source, REQUIRED_WIRED_MARKERS)
    legacy = _presence(source, LEGACY_FORBIDDEN_MARKERS)

    # The owner has many unrelated END ellipses. Only classify the heartbeat detail
    # initialization block so Spotify/latest truncation cannot poison this verdict.
    detail_start = source.find("heartbeatDetail = textView(11f, false);")
    detail_end = source.find("latest = textView(14f, false);", detail_start)
    detail_block = (
        source[detail_start:detail_end]
        if detail_start >= 0 and detail_end > detail_start
        else ""
    )
    legacy["detail_end_ellipsis"] = "heartbeatDetail.setEllipsize(TextUtils.TruncateAt.END);" in detail_block

    all_required = all(required.values())
    any_legacy = any(legacy.values())
    if all_required and not any_legacy:
        state = "SOURCE_WIRED"
    elif not any(required.values()) and any_legacy:
        state = "LEGACY_OWNER"
    else:
        state = "PARTIAL_UNSAFE"

    return {
        "schema": "try-forever.heartbeat-detail-owner-probe.v1",
        "state": state,
        "required": required,
        "legacy": legacy,
        "capability": {
            "implementedOwnerSource": state == "SOURCE_WIRED",
            "tested": False,
            "runtimeUiObserved": False,
            "runtimeTalkBackObserved": False,
            "deployed": False,
            "callable": False,
            "executedOnPhone": False,
            "delivered": False,
            "accepted": False,
        },
    }


def _assert_state(source: str, expected: str) -> None:
    actual = classify_source(source)["state"]
    if actual != expected:
        raise AssertionError(f"expected {expected}, got {actual}")


def self_test() -> None:
    legacy = "\n".join(
        [
            "heartbeatDetail = textView(11f, false);",
            "heartbeatDetail.setMaxLines(5);",
            "heartbeatDetail.setEllipsize(TextUtils.TruncateAt.END);",
            "latest = textView(14f, false);",
            "String safe = detail == null || detail.trim().isEmpty()",
        ]
    )
    wired = "\n".join(
        [
            "heartbeatDetail = textView(11f, false);",
            "heartbeatDetail.setEllipsize(null);",
            "latest = textView(14f, false);",
            *REQUIRED_WIRED_MARKERS.values(),
        ]
    )
    partial = "\n".join(
        [
            "heartbeatDetail = textView(11f, false);",
            "heartbeatDetail.setEllipsize(null);",
            "latest = textView(14f, false);",
            "HeartbeatDetailSurfacePolicy.maxViewportHeightPx",
        ]
    )
    _assert_state(legacy, "LEGACY_OWNER")
    _assert_state(wired, "SOURCE_WIRED")
    _assert_state(partial, "PARTIAL_UNSAFE")


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", nargs="?", default=str(OWNER_DEFAULT))
    parser.add_argument("--require-wired", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.self_test:
        self_test()
        print(json.dumps({"selfTest": "PASS"}, sort_keys=True))
        return 0

    path = Path(args.path)
    source = path.read_text(encoding="utf-8")
    result = classify_source(source)
    result["path"] = path.as_posix()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if not args.require_wired or result["state"] == "SOURCE_WIRED" else 3


if __name__ == "__main__":
    raise SystemExit(main())
