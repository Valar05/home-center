#!/usr/bin/env python3
"""Deterministic source-capability probe for existing Operator Overlay accessibility seams.

This probe reads source text only. It does not execute Android, render UI, touch the
phone/P0 chain, or promote source evidence into TESTED/runtime/deployed evidence.

SOURCE_WIRED is deliberately narrower than raw substring presence: comments and
literals are blanked first, the public OperatorOverlayService class is isolated, and
expected markers must occur inside a direct private-void member method that owns the
consequence. Dynamic TextView semantics are evaluated separately: Android's native
TextView text remains the focused semantic value only when the owner does not replace
it with a non-null contentDescription. This is still source-structure evidence only.
It does not prove Java control flow, Android execution, runtime focus, TalkBack
behavior, deployment, or phone delivery.
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
    "createOverlay": (
        "HeartbeatDetailSurfacePolicy.maxViewportHeightPx",
        "heartbeatDetail.setVerticalScrollBarEnabled(",
        "heartbeatDetail.setMovementMethod(",
        "heartbeatDetail.setFocusable(",
        "heartbeatDetail.setClickable(",
        "heartbeatDetail.setLongClickable(",
    ),
    "showHeartbeatDetail": (
        "long presentationGeneration = ++heartbeatDetailPresentationGeneration;",
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

SPOTIFY_TEXT_MARKERS = {
    "createOverlay": ("spotifyStatus.setText(",),
    "handleSpotifyReceipt": ("spotifyStatus.setText(summary);",),
}
HOME_CENTER_STATUS_TEXT_MARKERS = {
    "createOverlay": ("status.setText(",),
    "refreshUi": ("status.setText(state);",),
}


def java_lexical_code_surface(source: str) -> str:
    """Blank Java comments and literals while preserving code shape and newlines.

    The result is a lexical evidence surface, not a Java parser. Braces inside
    comments, strings, chars, and text blocks are blanked, which also makes bounded
    class/member extraction materially stronger than raw file-wide marker search.
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


def java_named_class_surface(code_surface: str, class_name: str) -> str:
    """Return one named public class from the lexical code surface."""

    declaration = re.compile(rf"\bpublic\s+class\s+{re.escape(class_name)}\b")
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


def java_private_void_method_surface(class_surface: str, method_name: str) -> str:
    """Return one direct private-void member method from the owner class."""

    declaration = re.compile(rf"\bprivate\s+void\s+{re.escape(method_name)}\s*\(")
    depth = 0
    index = 0
    length = len(class_surface)
    while index < length:
        char = class_surface[index]
        if char == "{":
            depth += 1
            index += 1
            continue
        if char == "}":
            depth = max(0, depth - 1)
            index += 1
            continue
        if depth != 1:
            index += 1
            continue
        match = declaration.match(class_surface, index)
        if match is None:
            index += 1
            continue
        open_brace = class_surface.find("{", match.end())
        if open_brace < 0:
            return ""
        method_depth = 0
        for end in range(open_brace, length):
            method_char = class_surface[end]
            if method_char == "{":
                method_depth += 1
            elif method_char == "}":
                method_depth -= 1
                if method_depth == 0:
                    return class_surface[match.start():end + 1]
        return ""
    return ""


def owner_scopes(code_surface: str) -> dict[str, str]:
    owner_class = java_named_class_surface(code_surface, "OperatorOverlayService")
    return {
        "class": owner_class,
        "createOverlay": java_private_void_method_surface(owner_class, "createOverlay"),
        "handleSpotifyReceipt": java_private_void_method_surface(
            owner_class, "handleSpotifyReceipt"
        ),
        "refreshUi": java_private_void_method_surface(owner_class, "refreshUi"),
        "showHeartbeatDetail": java_private_void_method_surface(
            owner_class, "showHeartbeatDetail"
        ),
        "restoreHeartbeatDetailScrollAfterLayout": java_private_void_method_surface(
            owner_class, "restoreHeartbeatDetailScrollAfterLayout"
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
                "required direct owner-method scope"
            ),
            legacy_markers=(),
            wired_markers=wired_present,
        )
    return SeamVerdict(
        status="PARTIAL_UNSAFE",
        reason=(
            f"{label} is neither the complete legacy owner-method shape nor the "
            "complete expected direct method-scoped wiring"
        ),
        legacy_markers=legacy_present,
        wired_markers=wired_present,
    )


def content_description_arguments(surface: str, view_name: str) -> tuple[str, ...]:
    pattern = re.compile(
        rf"\b{re.escape(view_name)}\.setContentDescription\s*\((.*?)\)\s*;",
        re.DOTALL,
    )
    return tuple(match.group(1).strip() for match in pattern.finditer(surface))


def classify_dynamic_textview_semantics(
    scopes: dict[str, str],
    *,
    view_name: str,
    text_markers: dict[str, tuple[str, ...]],
    description_scopes: tuple[str, ...],
    label: str,
) -> SeamVerdict:
    text_present = scoped_markers(scopes, text_markers)
    required_text = required_marker_count(text_markers)
    overrides: list[str] = []
    explicit_native: list[str] = []
    for scope_name in description_scopes:
        for argument in content_description_arguments(scopes.get(scope_name, ""), view_name):
            marker = f"{scope_name}::{view_name}.setContentDescription({argument or '<literal>'})"
            if argument == "null":
                explicit_native.append(marker)
            else:
                overrides.append(marker)

    if overrides and len(text_present) == required_text and not explicit_native:
        return SeamVerdict(
            status="LEGACY_OWNER",
            reason=(
                f"{label} changes TextView text but also replaces native text semantics "
                "with a non-null contentDescription"
            ),
            legacy_markers=tuple(overrides),
            wired_markers=text_present,
        )
    if not overrides and len(text_present) == required_text:
        return SeamVerdict(
            status="SOURCE_WIRED",
            reason=(
                f"{label} keeps the dynamic TextView text as the accessibility semantic "
                "value without a non-null contentDescription override"
            ),
            legacy_markers=(),
            wired_markers=text_present + tuple(explicit_native),
        )
    return SeamVerdict(
        status="PARTIAL_UNSAFE",
        reason=(
            f"{label} has mixed/incomplete dynamic-text ownership or conflicting "
            "contentDescription semantics"
        ),
        legacy_markers=tuple(overrides),
        wired_markers=text_present + tuple(explicit_native),
    )


def probe(source: str) -> dict[str, object]:
    code_surface = java_lexical_code_surface(source)
    scopes = owner_scopes(code_surface)
    return {
        "schema": "try-forever-operator-accessibility-owner-probe.v6",
        "evidenceClass": "JAVA_DIRECT_OWNER_METHOD_SCOPED_LEXICAL_CODE_SURFACE",
        "ownerClassFound": bool(scopes["class"]),
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
        "spotifyStatusFocus": asdict(classify_dynamic_textview_semantics(
            scopes,
            view_name="spotifyStatus",
            text_markers=SPOTIFY_TEXT_MARKERS,
            description_scopes=("createOverlay", "handleSpotifyReceipt"),
            label="Spotify focused-status semantic owner",
        )),
        "homeCenterStatusFocus": asdict(classify_dynamic_textview_semantics(
            scopes,
            view_name="status",
            text_markers=HOME_CENTER_STATUS_TEXT_MARKERS,
            description_scopes=("createOverlay", "refreshUi"),
            label="Home Center dynamic-status semantic owner",
        )),
        "capabilityBoundary": {
            "sourceInspected": True,
            "lexicalLiteralsExcluded": True,
            "ownerClassScoped": True,
            "directMethodScopedSource": True,
            "nativeTextViewSemanticsSourceOnly": True,
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
