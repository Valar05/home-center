#!/usr/bin/env python3
"""Apply the bounded Spotify radio additions to the existing Adam overlay."""
from __future__ import annotations

import argparse
from pathlib import Path


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{path}: expected one anchor, found {count}: {old[:120]!r}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def apply(root: Path) -> None:
    service = root / "android/operator-overlay/app/src/main/java/com/homecenter/operatoroverlay/OperatorOverlayService.java"
    state = root / "android/operator-overlay/app/src/main/java/com/homecenter/operatoroverlay/OperatorState.java"
    build = root / "android/operator-overlay/app/build.gradle"

    replace_once(
        service,
        '        adamModeRow.addView(adamModeButton("VLAD", "vlad", "Ask Vlad for a bounded consultation"));\n',
        '        adamModeRow.addView(adamModeButton("VLAD", "vlad", "Ask Vlad for a bounded consultation"));\n'
        '        adamModeRow.addView(adamModeButton("RADIO", "radio", "Control promptable Spotify Fortress Radio"));\n',
    )

    radio_row = """        LinearLayout radioRow = new LinearLayout(this);
        radioRow.setOrientation(LinearLayout.HORIZONTAL);
        radioRow.setGravity(Gravity.START | Gravity.CENTER_VERTICAL);
        radioRow.setPadding(0, dp(4), 0, 0);

        Button radioPreviousButton = button("⏮");
        radioPreviousButton.setContentDescription("Fortress Radio previous track");
        radioPreviousButton.setOnClickListener(v -> submitAdamQuickRequest("previous"));
        radioRow.addView(radioPreviousButton);

        Button radioToggleButton = button("⏯");
        radioToggleButton.setContentDescription("Fortress Radio play or pause");
        radioToggleButton.setOnClickListener(v -> submitAdamQuickRequest("toggle"));
        radioRow.addView(radioToggleButton);

        Button radioNextButton = button("⏭");
        radioNextButton.setContentDescription("Fortress Radio next track");
        radioNextButton.setOnClickListener(v -> submitAdamQuickRequest("next"));
        radioRow.addView(radioNextButton);

        Button radioStatusButton = button("Radio status");
        radioStatusButton.setContentDescription("Read Fortress Radio Spotify status");
        radioStatusButton.setOnClickListener(v -> submitAdamQuickRequest("status"));
        radioRow.addView(radioStatusButton);

"""
    replace_once(
        service,
        '        LinearLayout actionRow = new LinearLayout(this);\n',
        radio_row + '        LinearLayout actionRow = new LinearLayout(this);\n',
    )

    replace_once(
        service,
        '        details.addView(adamInputRow);\n        details.addView(actionRow);\n',
        '        details.addView(adamInputRow);\n        details.addView(radioRow);\n        details.addView(actionRow);\n',
    )

    helper = """    private void submitAdamQuickRequest(String text) {
        OperatorState.submitAdamRequest(this, "radio", text, System.currentTimeMillis());
        adamMode = "radio";
        if (adamInput != null) {
            adamInput.setText("");
            adamInput.setHint("Adam — radio • sent");
            adamInput.setContentDescription("Adam input. Current mode radio.");
            adamInput.announceForAccessibility("Sent to Adam radio");
        }
    }

"""
    replace_once(
        service,
        '    private void submitAdamRequest() {\n',
        helper + '    private void submitAdamRequest() {\n',
    )

    replace_once(
        state,
        'cleanMode.equals("continue") || cleanMode.equals("vlad")))',
        'cleanMode.equals("continue") || cleanMode.equals("vlad") || cleanMode.equals("radio")))',
    )

    replace_once(build, "        versionCode 3\n", "        versionCode 4\n")
    replace_once(build, "        versionName '1.2.0'\n", "        versionName '1.3.0'\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    args = parser.parse_args()
    root = Path(args.root).resolve()
    apply(root)
    print("apply_spotify_overlay_radio_patch: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
