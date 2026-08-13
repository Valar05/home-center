#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SERVICE = ROOT / "android/operator-overlay/app/src/main/java/com/homecenter/operatoroverlay/OperatorOverlayService.java"
STATE = ROOT / "android/operator-overlay/app/src/main/java/com/homecenter/operatoroverlay/OperatorState.java"
BUILD = ROOT / "android/operator-overlay/app/build.gradle"
ADAM = ROOT / "tools/adam.py"


def require(text: str, needle: str) -> None:
    assert needle in text, needle


def forbid(text: str, needle: str) -> None:
    assert needle not in text, needle


def main() -> int:
    service = SERVICE.read_text(encoding="utf-8")
    state = STATE.read_text(encoding="utf-8")
    build = BUILD.read_text(encoding="utf-8")
    adam = ADAM.read_text(encoding="utf-8")

    for marker in (
        'adamModeButton("TERM", "terminal"',
        'adamModeButton("CHAT", "chat"',
        'adamModeButton("CONT", "continue"',
        'adamModeButton("VLAD", "vlad"',
        'adamModeButton("RADIO", "radio"',
        'submitAdamQuickRequest("previous")',
        'submitAdamQuickRequest("toggle")',
        'submitAdamQuickRequest("next")',
        'submitAdamQuickRequest("status")',
        'Fortress Radio previous track',
        'Fortress Radio play or pause',
        'Fortress Radio next track',
        'Read Fortress Radio Spotify status',
        'OperatorState.submitAdamRequest(this, "radio"',
        'details.addView(radioRow);',
        'OperatorState.setControlEnabled(this, false);',
        'OperatorState.setMuted(this',
        'private void handleControlButton()',
        'OperatorState.setControlEnabled(this, true);',
    ):
        require(service, marker)

    require(state, 'cleanMode.equals("radio")')
    require(build, "versionCode 4")
    require(build, "versionName '1.3.0'")
    require(adam, 'ONE_SHOT_MODES = ("terminal", "chat", "continue", "vlad", "radio")')
    require(adam, 'handledBy="spotify-radio"')
    require(adam, 'provider="spotify-android"')

    # The visible local button remains the only enable authority. Radio
    # controls submit through the existing Adam provider and do not bypass it
    # with anonymous global media keys or a new remote-enable action.
    forbid(service, "dispatchMediaKeyEvent")
    forbid(service, "KEYCODE_MEDIA_NEXT")
    forbid(service, "KEYCODE_MEDIA_PLAY_PAUSE")
    forbid(service, "ACTION_ENABLE_CONTROL")
    forbid(service, "REMOTE_ENABLE_CONTROL")

    print("spotify_overlay_radio_contract_test: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
