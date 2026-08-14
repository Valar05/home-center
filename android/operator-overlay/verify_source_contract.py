#!/usr/bin/env python3
"""Fail-closed source contract checks for the operator overlay release."""

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent.parent
JAVA = ROOT / "app/src/main/java/com/homecenter/operatoroverlay"
SERVICE = (JAVA / "OperatorOverlayService.java").read_text(encoding="utf-8")
MAIN = (JAVA / "MainActivity.java").read_text(encoding="utf-8")
RESTORE = (JAVA / "LocalRestoreReceiver.java").read_text(encoding="utf-8")
POLICY = (JAVA / "OverlayUiPolicy.java").read_text(encoding="utf-8")
STATE = (JAVA / "OperatorState.java").read_text(encoding="utf-8")
PROVIDER = (JAVA / "OperatorStateProvider.java").read_text(encoding="utf-8")
MANIFEST = (ROOT / "app/src/main/AndroidManifest.xml").read_text(encoding="utf-8")
GRADLE = (ROOT / "app/build.gradle").read_text(encoding="utf-8")
OPERATOR = (REPO / "tools/android_operator_overlay.py").read_text(encoding="utf-8")
TERMUX_BUILD = (REPO / "tools/build_operator_overlay_termux.sh").read_text(
    encoding="utf-8"
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def method_body(source: str, signature: str) -> str:
    start = source.index(signature)
    opening = source.index("{", start)
    depth = 0
    for index in range(opening, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[opening + 1:index]
    raise AssertionError(f"unterminated method: {signature}")


def verify_quit_support_button() -> None:
    require('button("FREE QUIT KIT")' in SERVICE, "permanent button label missing")
    require(
        'QUIT_SUPPORT_URI = "tel:+18332839355";' in SERVICE,
        "quit support URI is not exact",
    )
    dialer = method_body(SERVICE, "private void openQuitSupportDialer()")
    require("Intent.ACTION_DIAL" in dialer, "button must use ACTION_DIAL")
    require("Uri.parse(QUIT_SUPPORT_URI)" in dialer, "fixed URI not used")
    require(".putExtra(" not in dialer, "dialer intent must not carry extras")
    require("OperatorState" not in dialer and "Log." not in dialer, "button press cannot emit telemetry")
    require("ACTION_CALL" not in SERVICE, "ACTION_CALL is forbidden")
    require("CALL_PHONE" not in SERVICE + MANIFEST, "CALL_PHONE is forbidden")
    require("MIN_TOUCH_TARGET_DP = 48" in POLICY, "touch target must be at least 48dp")
    require(
        "setMinHeight(dp(OverlayUiPolicy.MIN_TOUCH_TARGET_DP))" in SERVICE
        and "setMinWidth(dp(OverlayUiPolicy.MIN_TOUCH_TARGET_DP))" in SERVICE,
        "overlay buttons must inherit the 48dp minimum",
    )


def verify_touch_through() -> None:
    require("touchGuard" not in SERVICE, "full-screen touchGuard is forbidden")
    require("guardParams" not in SERVICE, "full-screen guard params are forbidden")
    require(
        "WindowManager.LayoutParams.MATCH_PARENT" not in SERVICE,
        "overlay service cannot own a MATCH_PARENT touch surface",
    )


def verify_local_restore_only() -> None:
    require("ACTION_RESTORE" not in SERVICE + MAIN, "remote restore action is forbidden")
    require("setControlEnabled" not in MAIN, "launcher lifecycle cannot change control")
    require("setOverlayHidden" not in MAIN, "launcher lifecycle cannot change visibility")
    on_create = method_body(MAIN, "protected void onCreate(Bundle savedInstanceState)")
    on_resume = method_body(MAIN, "protected void onResume()")
    require("requestCapture" not in on_create + on_resume, "capture cannot auto-start")
    require(
        'android:name=".LocalRestoreReceiver" android:exported="false"' in MANIFEST,
        "local restore receiver must remain nonexported",
    )
    require("PendingIntent.getBroadcast" in RESTORE, "notification must use app-private receiver")
    require("FLAG_IMMUTABLE" in RESTORE, "restore PendingIntent must be immutable")
    control_off = RESTORE.index("OperatorState.setControlEnabled(context, false)")
    screen_clear = RESTORE.index("OperatorState.clearScreenActivity(context)")
    unhide = RESTORE.index("OperatorState.setOverlayHidden(")
    require(
        control_off < screen_clear < unhide,
        "local restore must fail closed before changing visibility",
    )
    require(
        'android:permission="android.permission.DUMP"' in MANIFEST,
        "exported service must retain its privileged permission boundary",
    )
    require(
        "operator_overlay_start is retired" in OPERATOR,
        "unsafe remote recovery action must fail closed",
    )
    require("am start -n" not in OPERATOR, "remote launcher invocation is forbidden")


def verify_monotonic_version() -> None:
    require(re.search(r"\bversionCode\s+5\b", GRADLE) is not None, "versionCode must be 5")
    require("versionName '1.4.0'" in GRADLE, "versionName must be 1.4.0")
    require(
        '--version-code "$VERSION_CODE" --version-name "$VERSION_NAME"' in TERMUX_BUILD,
        "phone build must derive the app version from build.gradle",
    )


def verify_maintenance_proof() -> None:
    for field in (
        '"state_schema_version"',
        '"feature_quit_kit_dial_v1"',
        '"overlay_x"',
        '"overlay_y"',
    ):
        require(field in PROVIDER, f"maintenance proof field missing: {field}")
    require(
        "STATE_SCHEMA_VERSION = 2" in PROVIDER,
        "state provider schema must be version 2",
    )
    migration = method_body(
        STATE,
        "static boolean restoreMigrationState(Context context, Bundle extras)",
    )
    require(
        "KEY_OVERLAY_X" in migration and "KEY_OVERLAY_Y" in migration,
        "migration must preserve both overlay coordinates",
    )
    require(
        ".putBoolean(KEY_CONTROL_ENABLED, false)" in migration,
        "migration must keep control fail closed",
    )


if __name__ == "__main__":
    verify_quit_support_button()
    verify_touch_through()
    verify_local_restore_only()
    verify_monotonic_version()
    verify_maintenance_proof()
    print("operator overlay source contract: PASS")
