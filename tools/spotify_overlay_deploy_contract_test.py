#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "tools/build_operator_overlay_termux.sh"
DEPLOY = ROOT / "tools/deploy_spotify_overlay_radio_phone.sh"
BOOTSTRAP = ROOT / "tools/bootstrap_spotify_overlay_radio_phone.sh"
SETUP = ROOT / "tools/setup_spotify_radio.sh"


def require(text: str, needle: str) -> None:
    assert needle in text, needle


def forbid(text: str, needle: str) -> None:
    assert needle not in text, needle


def main() -> int:
    build = BUILD.read_text(encoding="utf-8")
    deploy = DEPLOY.read_text(encoding="utf-8")
    bootstrap = BOOTSTRAP.read_text(encoding="utf-8")
    setup = SETUP.read_text(encoding="utf-8")

    for marker in (
        "GRADLE_CONFIG=\"$APP/build.gradle\"",
        "VERSION_CODE=\"${HC_OVERLAY_VERSION_CODE:-${OVERLAY_VERSION[0]}}\"",
        "VERSION_NAME=\"${HC_OVERLAY_VERSION_NAME:-${OVERLAY_VERSION[1]}}\"",
        '--version-code "$VERSION_CODE" --version-name "$VERSION_NAME"',
        "operator-overlay-build-receipt.json",
        "signingCertificateSha256",
        "SOURCE_COMMIT=\"$(git -C \"$ROOT\" rev-parse HEAD",
    ):
        require(build, marker)
    forbid(build, "--version-code 3 --version-name 1.2.0")

    for marker in (
        "Spotify radio deploy requires a clean isolated worktree",
        "spotify_radio_contract_test.py",
        "spotify_overlay_radio_contract_test.py",
        "build_operator_overlay_termux.sh",
        "apksigner verify --print-certs",
        "STAGED_SHA",
        "pm install -r",
        "UPDATE_INCOMPATIBLE",
        "pm uninstall $PACKAGE",
        "packageOnlyReplacement",
        "SYSTEM_ALERT_WINDOW allow",
        "versionName=1.3.0",
        "versionCode=5",
        "setup_spotify_radio.sh",
        "setup_vlad_swarm_daemon.sh",
        "visibleLocalEnableStillAuthoritative",
        "remoteEnableUsed':False",
        "operatorActionRequired",
    ):
        require(deploy, marker)
    forbid(deploy, "setControlEnabled")
    forbid(deploy, "control_enabled=1")
    forbid(deploy, "pm uninstall com.dclar.homecenter")

    for marker in (
        "spotify-overlay-radio-src",
        "GIT_LFS_SKIP_SMUDGE=1",
        "--filter=blob:none --no-checkout --single-branch",
        "sparse-checkout set android/operator-overlay tools skills config .continue",
        "HC_SPOTIFY_RADIO_EXPECTED_COMMIT",
        "dedicatedGeneratedClone",
        "dirtySharedCheckoutUsed",
        "exec bash \"$DEST/tools/deploy_spotify_overlay_radio_phone.sh\"",
    ):
        require(bootstrap, marker)
    forbid(bootstrap, "/storage/emulated/0/Documents/GodotProjects/home-center")
    forbid(bootstrap, "git -C /storage/emulated/0/Documents")

    require(setup, "home-center.spotify-radio.install-receipt.v1")
    require(setup, "spotifyCredentialsStored")
    require(setup, "spotifyWebApiUsed")

    print("spotify_overlay_deploy_contract_test: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
