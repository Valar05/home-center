#!/usr/bin/env python3
"""Deterministic source-capability probe for existing Operator Overlay accessibility seams.

This probe reads source text only. It does not execute Android, render UI, touch the
phone/P0 chain, or promote source evidence into TESTED/runtime/deployed evidence.

SOURCE_WIRED is deliberately narrower than raw substring presence: comments and
literals are blanked first, then expected markers must occur inside the native owner
method that is supposed to own each consequence. This is still source-structure
evidence only. It does not prove Java control flow, Android execution, runtime focus,
TalkBack behavior, deployment, or phone delivery.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class SeamVerdict:
    status: str
    reason: str
    legacy_markers: tuple[str, ...]
    wired_markers: tuple[str, ...]


DEEP_DETAIL_LEGACY = {
    "createOverlay": (
        "heartbeatDetail.setMaxLines(5);",
        "heartbeatDetail.setEllipsize(TextUtils.TruncateAt.END);",
    ),
}
DEEP_DETAIL_WIRED = {
    "class": (
        "private long heartbeatDetailPresentationGeneration;",
    ),
    "createOverlay": (
        "HeartbeatDetailSurfacePolicy.maxViewportHeightPx",
        "heartbeatDetail.setVerticalScrollBarEnabled(",
        "heartbeatDetail.setMovementMethod(",
        "heartbeatDetail.setFocusable(",
        "heartbeatDetail.setClickable(",
        "heartbeatDetail.setLongClickable(",
    ),
    "showHeartbeatDetail": (
        "HeartbeatDetailSurfacePolicy.fromDetail",
        "presentation.verticallyScrollable",
        "presentation.keyboardFocusable",
        "presentation.clickable",
        "presentation.longClickable",
        "restoreHeartbeatDetailScrollAfterLayout(",
        "heartbeatDetail.scrollTo(0, 0);",
        "heartbeatDetail.announceForAccessibility(presentation.contentDescription);",
    ),
    "restoreHeartbeatDetailScrollAfterLayout": (
        "presentationGeneration != heartbeatDetailPresentationGeneration",
        "HeartbeatDetailSurfacePolicy.clampScrollY",
    ),
}

SPOTIFY_SPEECH_LEGACY = {
    "handleSpotifyReceipt": (
        "summary.substring(0, 160)",
    ),
}
SPOTIFY_SPEECH_WIRED = {
    "handleSpotifyReceipt": (
        "HeartbeatPlainTextBudget.boundedWithEllipsis(summary, 160)",
    ),
}


def java_lexical_code_surface(source: str) -> str:
    """Blank Java comments and literals while preserving code shape and newlines.

    The result is a lexical evidence surface, not a Java parser. Braces inside
    comments, strings, chars, and text blocks are blanked, which also makes bounded
    method-body extraction materially stronger than file-wide marker search.
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
            if next_three == '"""':
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
            if next_three == '"""':
                out.extend("   ")
                index += 3
                state = "code"
                continue
            out.append(blank(char))
            index += 1
            continue

        raise AssertionError(f"unknown lexical state: {state}")

    return "".join(out)


def java_private_void_method_surface(code_surface: str, method_name: str) -> str:
    """Return one private-void method declaration/body from a lexical code surface.

    This deliberately targets only the concrete methods whose ownership matters for
    the current OperatorOverlayService accessibility seams. It is not a general Java
    parser and therefore cannot promote the result beyond method-scoped source
    structure evidence.
    """

    declaration = re.compile(
        rf"\bprivate\s+void\s+{re.escape(method_name)}\s*\("
    )
    match = declaration.search(code_surface)
    if match is None:
        return ""
    open_brace = code_surface.find("{", match.end())
    if open_brace < 0:
        return ""
    depth = 0
    for index in range(open_brace, len(code_surface)):
        char = code_surface[index]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return code_surface[match.start():index + 1]
    return ""


def owner_scopes(code_surface: str) -> dict[str, str]:
    return {
        "class": code_surface,
        "createOverlay": java_private_void_method_surface(code_surface, "createOverlay"),
        "handleSpotifyReceipt": java_private_void_method_surface(
            code_surface, "handleSpotifyReceipt"
        ),
        "showHeartbeatDetail": java_private_void_method_surface(
            code_surface, "showHeartbeatDetail"
        ),
        "restoreHeartbeatDetailScrollAfterLayout": java_private_void_method_surface(
            code_surface, "restoreHeartbeatDetailScrollAfterLayout"
        ),
    }


def scoped_markers(
    scopes: dict[str, str],
    requirements: dict[str, tuple[str, ...]],
) -> tuple[str, ...]:
    present: list[str] = []
    for scope_name, markers in requirements.items():
        surface = scopes.get(scope_name, "")
        for marker in markers:
            if marker in surface:
                present.append(f"{scope_name}::{marker}")
    return tuple(present)


def required_marker_count(requirements: dict[str, tuple[str, ...]]) -> int:
    return sum(len(markers) for markers in requirements.values())


def classify_scoped(
    scopes: dict[str, str],
    *,
    legacy: dict[str, tuple[str, ...]],
    wired: dict[str, tuple[str, ...]],
    label: str,
) -> SeamVerdict:
    legacy_present = scoped_markers(scopes, legacy)
    wired_present = scoped_markers(scopes, wired)
    expected_wired = required_marker_count(wired)

    if legacy_present and not wired_present:
        return SeamVerdict(
            status="LEGACY_OWNER",
            reason=(
                f"{label} still exposes the legacy shape inside the owning method; "
                "owner repair is not implemented"
            ),
            legacy_markers=legacy_present,
            wired_markers=(),
        )
    if not legacy_present and len(wired_present) == expected_wired:
        return SeamVerdict(
            status="SOURCE_WIRED",
            reason=(
                f"{label} contains every expected existing-organ marker inside its "
                "required owner method scope"
            ),
            legacy_markers=(),
            wired_markers=wired_present,
        )
    return SeamVerdict(
        status="PARTIAL_UNSAFE",
        reason=(
            f"{label} is neither the complete legacy owner-method shape nor the "
            "complete expected method-scoped wiring"
        ),
        legacy_markers=legacy_present,
        wired_markers=wired_present,
    )


def probe(source: str) -> dict[str, object]:
    code_surface = java_lexical_code_surface(source)
    scopes = owner_scopes(code_surface)
    return {
        "schema": "try-forever-operator-accessibility-owner-probe.v4",
        "evidenceClass": "JAVA_METHOD_SCOPED_LEXICAL_CODE_SURFACE",
        "deepDetail": asdict(classify_scoped(
            scopes,
            legacy=DEEP_DETAIL_LEGACY,
            wired=DEEP_DETAIL_WIRED,
            label="heartbeat deep-detail owner",
        )),
        "spotifyAnnouncement": asdict(classify_scoped(
            scopes,
            legacy=SPOTIFY_SPEECH_LEGACY,
            wired=SPOTIFY_SPEECH_WIRED,
            label="Spotify accessibility announcement owner",
        )),
        "capabilityBoundary": {
            "sourceInspected": True,
            "lexicalLiteralsExcluded": True,
            "methodScopedSource": True,
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
