#!/usr/bin/env python3
"""Deterministically port the existing Android overlay to the one-input Beard UI.

This mutates only known presentation/request wiring. It deliberately preserves
screen touch-guard, drag/collapse/hide, Spotify plumbing, and service behavior.
Fail closed if the expected source shape has drifted.
"""
from __future__ import annotations

import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT = ROOT / "android/operator-overlay/app/src/main/java/com/homecenter/operatoroverlay/OperatorOverlayService.java"


def once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"BEARD_PORT_BLOCKED {label}: expected exactly 1 match, found {count}")
    return text.replace(old, new, 1)


def port(text: str) -> str:
    # Guard the safety contract before any mutation.
    for required in [
        "private WindowManager.LayoutParams guardParams;",
        "private View touchGuard;",
        "private void syncTouchGuard(boolean active)",
        "OverlayUiPolicy.touchGuardActive(",
        "FLAG_NOT_TOUCH_MODAL",
    ]:
        if required not in text:
            raise SystemExit(f"BEARD_PORT_BLOCKED safety contract missing: {required}")

    text = once(text, 'private String adamMode = "terminal";', 'private String adamMode = "auto";', "default mode")
    text = once(text, 'adamInput.setHint("Adam — terminal");', 'adamInput.setHint("Talk to Adam…");', "input hint")
    text = once(
        text,
        'adamInput.setContentDescription("Adam input. Current mode terminal.");',
        'adamInput.setContentDescription("Talk to Adam naturally. Routing is automatic; fixed phone commands stay deterministic.");',
        "input accessibility",
    )
    text = once(text, 'Button adamSendButton = button("Send");', 'Button adamSendButton = button("Ask");', "send label")
    text = once(
        text,
        'adamSendButton.setContentDescription("Send request to Adam using the selected explicit mode");',
        'adamSendButton.setContentDescription("Send a natural-language request to Adam using automatic routing");',
        "send accessibility",
    )

    # Keep old mode/Spotify construction code as dormant plumbing for minimum-risk surgery,
    # but remove both racks from the visible overlay.
    text = once(text, '        details.addView(adamModeRow);\n', '', "hide mode rack")
    text = once(text, '        root.addView(spotifyRow);\n', '', "hide Spotify rack")

    # Add the smallest useful deterministic action strip. These buttons use the exact
    # same request transport as typed Beard commands; no bespoke shell execution.
    anchor = '        details.addView(statusRow);\n'
    quick = '''        LinearLayout quickActionRow = new LinearLayout(this);\n        quickActionRow.setOrientation(LinearLayout.HORIZONTAL);\n        quickActionRow.setGravity(Gravity.START | Gravity.CENTER_VERTICAL);\n        quickActionRow.setPadding(0, dp(4), 0, dp(2));\n        quickActionRow.addView(quickRequestButton("Restart", "restart", "Restart or repair Home Center overlay"));\n        quickActionRow.addView(quickRequestButton("Night", "night", "Read cheap Night Core battery and relay status"));\n        quickActionRow.addView(quickRequestButton("Chrome", "chrome", "Open Chromium through the deterministic phone controller"));\n        quickActionRow.addView(quickRequestButton("Canary", "canary", "Run the physical phone acceptance canary"));\n\n        details.addView(statusRow);\n        details.addView(quickActionRow);\n'''
    text = once(text, anchor, quick, "quick action row")

    # Neutral send state: users should never have to manage internal routing modes.
    text = once(
        text,
        '        adamInput.setHint("Adam — " + adamMode + " • sent");\n        adamInput.announceForAccessibility("Sent to Adam " + adamMode);',
        '        adamInput.setHint("Talk to Adam…");\n        adamInput.announceForAccessibility("Sent to Adam");',
        "neutral send state",
    )

    helper_anchor = '    private Button adamModeButton(String label, String mode, String description) {\n'
    helper = '''    private Button quickRequestButton(String label, String request, String description) {\n        Button value = button(label);\n        value.setContentDescription(description);\n        value.setOnClickListener(v -> {\n            OperatorState.submitAdamRequest(this, "auto", request, System.currentTimeMillis());\n            if (adamInput != null) {\n                adamInput.setHint("Talk to Adam…");\n                adamInput.announceForAccessibility(label + " sent to Adam");\n            }\n        });\n        return value;\n    }\n\n    private Button adamModeButton(String label, String mode, String description) {\n'''
    text = once(text, helper_anchor, helper, "quick action helper")

    # Postconditions: visible old racks gone, safety remains.
    for forbidden in ["details.addView(adamModeRow);", "root.addView(spotifyRow);"]:
        if forbidden in text:
            raise SystemExit(f"BEARD_PORT_BLOCKED visible rack remains: {forbidden}")
    for required in [
        'private String adamMode = "auto";',
        'adamInput.setHint("Talk to Adam…")',
        'Button adamSendButton = button("Ask")',
        'quickRequestButton("Restart", "restart"',
        'quickRequestButton("Night", "night"',
        'quickRequestButton("Chrome", "chrome"',
        'quickRequestButton("Canary", "canary"',
        'OperatorState.submitAdamRequest(this, "auto", request, System.currentTimeMillis())',
        "private void syncTouchGuard(boolean active)",
        "OverlayUiPolicy.touchGuardActive(",
    ]:
        if required not in text:
            raise SystemExit(f"BEARD_PORT_BLOCKED postcondition missing: {required}")
    return text


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", nargs="?", default=str(DEFAULT))
    parser.add_argument("--check", action="store_true", help="Validate transform without writing")
    args = parser.parse_args()
    path = Path(args.path)
    before = path.read_text(encoding="utf-8")
    after = port(before)
    if args.check:
        print("Android Beard one-input transform: PASS")
        return 0
    path.write_text(after, encoding="utf-8")
    print(f"Android Beard one-input transform: WROTE {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
