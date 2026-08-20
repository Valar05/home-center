#!/usr/bin/env python3
"""Deterministic source-capability probe for existing Operator Overlay accessibility seams.

This probe reads source text only. It does not execute Android, render UI, touch the
phone/P0 chain, or promote source evidence into TESTED/runtime/deployed evidence.

SOURCE_WIRED is deliberately narrower than raw substring presence: markers must
occur on the Java lexical code surface, outside comments and string/char/text-block
literals. That is still source-structure evidence only, not control-flow or runtime
proof.
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
    "heartbeatDetail.setVerticalScrollBarEnabled(presentation.verticallyScrollable);",
    "heartbeatDetail.setMovementMethod(",
    "heartbeatDetail.setFocusable(presentation.keyboardFocusable);",
    "heartbeatDetail.setClickable(presentation.clickable);",
    "heartbeatDetail.setLongClickable(presentation.longClickable);",
    "restoreHeartbeatDetailScrollAfterLayout(",
    "heartbeatDetail.announceForAccessibility(presentation.contentDescription);",
)

SPOTIFY_SPEECH_LEGACY = (
    "summary.substring(0, 160)",
)
SPOTIFY_SPEECH_WIRED = (
    "HeartbeatPlainTextBudget.boundedWithEllipsis(summary, 160)",
)


def java_lexical_code_surface(source: str) -> str:
    """Return Java source with comments and literals blanked but line shape preserved.

    This is intentionally a lexical source-evidence filter, not a Java parser. It
    prevents inert marker text in comments, strings, chars, and text blocks from
    earning SOURCE_WIRED while preserving executable/source-structure spelling for
    deterministic marker inspection.
    """

    out: list[str] = []
    index = 0
    state = "code"
    length = len(source)

    def blank(char: str) -> str:
        return "\n" if char == "\n" else " "

    while index < length:
        char = source[index]
        next_char = source[index + 1] if index + 1 < length else ""
        next_three = source[index:index + 3]

        if state == "code":
            if next_three == '\"\"\"':
                out.extend("   ")
                index += 3
                state = "text_block"
                continue
            if char == "/" and next_char == "/":
                out.extend("  ")
                index += 2
                state = "line_comment"
                continue
            if char == "/" and next_char == "*":
                out.extend("  ")
                index += 2
                state = "block_comment"
                continue
            if char == '"':
                out.append(" ")
                index += 1
                state = "string"
                continue
            if char == "'":
                out.append(" ")
                index += 1
                state = "char"
                continue
            out.append(char)
            index += 1
            continue

        if state == "line_comment":
            out.append(blank(char))
            index += 1
            if char == "\n":
                state = "code"
            continue

        if state == "block_comment":
            if char == "*" and next_char == "/":
                out.extend("  ")
                index += 2
                state = "code"
                continue
            out.append(blank(char))
            index += 1
            continue

        if state in {"string", "char"}:
            terminator = '"' if state == "string" else "'"
            if char == "\\" and index + 1 < length:
                out.append(" ")
                out.append(blank(source[index + 1]))
                index += 2
                continue
            out.append(blank(char))
            index += 1
            if char == terminator:
                state = "code"
            continue

        if state == "text_block":
            if char == "\\" and index + 1 < length:
                out.append(" ")
                out.append(blank(source[index + 1]))
                index += 2
                continue
            if next_three == '\"\"\"':
                out.extend("   ")
                index += 3
                state = "code"
                continue
            out.append(blank(char))
            index += 1
            continue

        raise AssertionError(f"unknown lexical state: {state}")

    return "".join(out)


def classify(
    code_surface: str,
    *,
    legacy: tuple[str, ...],
    wired: tuple[str, ...],
    label: str,
) -> SeamVerdict:
    legacy_present = tuple(marker for marker in legacy if marker in code_surface)
    wired_present = tuple(marker for marker in wired if marker in code_surface)

    if legacy_present and not wired_present:
        return SeamVerdict(
            status="LEGACY_OWNER",
            reason=f"{label} still exposes the legacy lexical code shape; owner repair is not implemented",
            legacy_markers=legacy_present,
            wired_markers=(),
        )
    if not legacy_present and len(wired_present) == len(wired):
        return SeamVerdict(
            status="SOURCE_WIRED",
            reason=f"{label} contains the complete expected existing-organ markers on the Java lexical code surface",
            legacy_markers=(),
            wired_markers=wired_present,
        )
    return SeamVerdict(
        status="PARTIAL_UNSAFE",
        reason=f"{label} is neither the complete legacy shape nor the complete expected wired lexical code shape",
        legacy_markers=legacy_present,
        wired_markers=wired_present,
    )


def probe(source: str) -> dict[str, object]:
    code_surface = java_lexical_code_surface(source)
    return {
        "schema": "try-forever-operator-accessibility-owner-probe.v3",
        "evidenceClass": "JAVA_LEXICAL_CODE_SURFACE",
        "deepDetail": asdict(classify(
            code_surface,
            legacy=DEEP_DETAIL_LEGACY,
            wired=DEEP_DETAIL_WIRED,
            label="heartbeat deep-detail owner",
        )),
        "spotifyAnnouncement": asdict(classify(
            code_surface,
            legacy=SPOTIFY_SPEECH_LEGACY,
            wired=SPOTIFY_SPEECH_WIRED,
            label="Spotify accessibility announcement owner",
        )),
        "capabilityBoundary": {
            "sourceInspected": True,
            "controlFlowProven": False,
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
