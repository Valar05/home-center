#!/usr/bin/env python3
"""Deterministic source-capability probe for existing Operator Overlay accessibility seams.

This probe reads source text only. It does not execute Android, render UI, touch the
phone/P0 chain, or promote source markers into TESTED/runtime/deployed evidence.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class SeamVerdict:
    status: str
    reason: str
    legacy_markers: tuple[str, ...]
    wired_markers: tuple[str, ...]


DEEP_DETAIL_LEGACY = (
    "heartbeatDetail.setMaxLines(5);",
    "heartbeatDetail.setEllipsize(TextUtils.TruncateAt.END);",
)
DEEP_DETAIL_WIRED = (
    "HeartbeatDetailSurfacePolicy.fromDetail",
    "HeartbeatDetailSurfacePolicy.maxViewportHeightPx",
    "HeartbeatDetailSurfacePolicy.clampScrollY",
)

SPOTIFY_SPEECH_LEGACY = (
    "summary.substring(0, 160)",
)
SPOTIFY_SPEECH_WIRED = (
    "HeartbeatPlainTextBudget.boundedWithEllipsis(summary, 160)",
)


def classify(source: str, *, legacy: tuple[str, ...], wired: tuple[str, ...], label: str) -> SeamVerdict:
    legacy_present = tuple(marker for marker in legacy if marker in source)
    wired_present = tuple(marker for marker in wired if marker in source)

    if legacy_present and not wired_present:
        return SeamVerdict(
            status="LEGACY_OWNER",
            reason=f"{label} still exposes the legacy source shape; owner repair is not implemented",
            legacy_markers=legacy_present,
            wired_markers=(),
        )
    if not legacy_present and len(wired_present) == len(wired):
        return SeamVerdict(
            status="SOURCE_WIRED",
            reason=f"{label} contains the complete expected existing-organ source markers",
            legacy_markers=(),
            wired_markers=wired_present,
        )
    return SeamVerdict(
        status="PARTIAL_UNSAFE",
        reason=f"{label} is neither the complete legacy shape nor the complete expected wired shape",
        legacy_markers=legacy_present,
        wired_markers=wired_present,
    )


def probe(source: str) -> dict[str, object]:
    return {
        "schema": "try-forever-operator-accessibility-owner-probe.v1",
        "deepDetail": asdict(classify(
            source,
            legacy=DEEP_DETAIL_LEGACY,
            wired=DEEP_DETAIL_WIRED,
            label="heartbeat deep-detail owner",
        )),
        "spotifyAnnouncement": asdict(classify(
            source,
            legacy=SPOTIFY_SPEECH_LEGACY,
            wired=SPOTIFY_SPEECH_WIRED,
            label="Spotify accessibility announcement owner",
        )),
        "capabilityBoundary": {
            "sourceInspected": True,
            "tested": False,
            "runtimeUi": False,
            "runtimeTalkBack": False,
            "phoneDelivery": False,
            "p0Mutation": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    args = parser.parse_args()
    source = args.source.read_text(encoding="utf-8")
    print(json.dumps(probe(source), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
