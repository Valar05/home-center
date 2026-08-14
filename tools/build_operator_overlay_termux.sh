#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

# Strict source-only release builder. Every compiler/tool/cache/signer input must
# already exist and be pinned. This script never installs, downloads, refreshes
# dependencies, creates lock state, or generates a signing identity.
ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
PROJECT="$ROOT/android/operator-overlay"
APP="$PROJECT/app"
GRADLE_FILE="$APP/build.gradle"
VERIFICATION_METADATA="$PROJECT/gradle/verification-metadata.xml"
DEPENDENCY_LOCK="$APP/gradle.lockfile"
APK="$APP/build/outputs/apk/debug/app-debug.apk"
EXPECTED_PACKAGE="com.homecenter.operatoroverlay"
EXPECTED_GRADLE_VERSION="8.9"
EXPECTED_GRADLE_DISTRIBUTION_SHA256="d725d707bfabd4dfdc958c624003b3c80accc03f7037b5122c4b1d0ef15cecab"
EXPECTED_BUILD_TOOLS_VERSION="35.0.0"

SOURCE_SHA="${HC_OPERATOR_OVERLAY_SOURCE_SHA:-}"
GRADLE_HOME_PIN="${HC_GRADLE_HOME:-}"
GRADLE_DISTRIBUTION_ZIP="${HC_GRADLE_DISTRIBUTION_ZIP:-}"
GRADLE_DISTRIBUTION_SHA256="${HC_GRADLE_DISTRIBUTION_SHA256:-}"
GRADLE_TREE_SHA256="${HC_GRADLE_TREE_SHA256:-}"
GRADLE_BIN_SHA256="${HC_GRADLE_BIN_SHA256:-}"
GRADLE_USER_HOME_PIN="${HC_GRADLE_USER_HOME:-}"
VERIFICATION_METADATA_SHA256="${HC_GRADLE_VERIFICATION_METADATA_SHA256:-}"
DEPENDENCY_LOCK_SHA256="${HC_GRADLE_LOCKFILE_SHA256:-}"

JAVA_HOME_PIN="${HC_JAVA_HOME:-}"
JAVA_BIN_PIN="${HC_JAVA_BIN:-}"
JAVAC_BIN_PIN="${HC_JAVAC_BIN:-}"
JAVA_SHA256="${HC_JAVA_SHA256:-}"
JAVAC_SHA256="${HC_JAVAC_SHA256:-}"
JAVA_VERSION_LINE="${HC_JAVA_VERSION_LINE:-}"
JAVAC_VERSION_LINE="${HC_JAVAC_VERSION_LINE:-}"

SDK_ROOT="${HC_ANDROID_SDK_ROOT:-}"
ANDROID_JAR_SHA256="${HC_ANDROID_JAR_SHA256:-}"
BUILD_TOOLS_VERSION="${HC_ANDROID_BUILD_TOOLS_VERSION:-}"
BUILD_TOOLS_TREE_SHA256="${HC_ANDROID_BUILD_TOOLS_TREE_SHA256:-}"
AAPT2_PATH_PIN="${HC_AAPT2_PATH:-}"
AAPT2_SHA256="${HC_AAPT2_SHA256:-}"
AAPT2_VERSION_LINE="${HC_AAPT2_VERSION_LINE:-}"
APKSIGNER_PATH_PIN="${HC_APKSIGNER_PATH:-}"
APKSIGNER_SHA256="${HC_APKSIGNER_SHA256:-}"
APKSIGNER_VERSION_LINE="${HC_APKSIGNER_VERSION_LINE:-}"

ANDROID_USER_HOME_PIN="${HC_ANDROID_USER_HOME:-}"
KEYSTORE_SHA256="${HC_OPERATOR_OVERLAY_KEYSTORE_SHA256:-}"
SIGNER_SHA256="${HC_OPERATOR_OVERLAY_SIGNER_SHA256:-}"

block() { printf 'BLOCKED: %s\n' "$*" >&2; exit 30; }
need_cmd() { command -v "$1" >/dev/null 2>&1 || block "preexisting tool missing: $1"; }
require_pin() { [ -n "$2" ] || block "required release pin missing: $1"; }
require_absolute() {
  case "$2" in
    /*) ;;
    *) block "$1 must be an absolute path" ;;
  esac
}
require_sha256() {
  [[ "$2" =~ ^[a-fA-F0-9]{64}$ ]] || block "$1 must be exactly 64 hexadecimal characters"
}
verify_sha256() {
  local label="$1" path="$2" expected="$3" actual
  [ -f "$path" ] || block "$label missing: $path"
  require_sha256 "$label SHA-256" "$expected"
  actual="$(sha256sum "$path" | awk '{print $1}')"
  [ "$actual" = "${expected,,}" ] \
    || block "$label SHA-256 mismatch expected=${expected,,} actual=$actual"
}
verify_tree_sha256() {
  local label="$1" path="$2" expected="$3" actual
  [ -d "$path" ] || block "$label directory missing: $path"
  require_sha256 "$label tree SHA-256" "$expected"
  actual="$(python3 - "$path" <<'PY'
import hashlib
import os
import sys
from pathlib import Path

root = Path(sys.argv[1])
digest = hashlib.sha256()
for item in sorted(root.rglob("*"), key=lambda value: value.relative_to(root).as_posix()):
    relative = item.relative_to(root).as_posix().encode("utf-8")
    if item.is_symlink():
        digest.update(b"L\0" + relative + b"\0" + os.readlink(item).encode("utf-8") + b"\0")
    elif item.is_dir():
        digest.update(b"D\0" + relative + b"\0")
    elif item.is_file():
        content = hashlib.sha256(item.read_bytes()).digest()
        digest.update(b"F\0" + relative + b"\0" + content)
    else:
        raise SystemExit("BLOCKED: unsupported filesystem entry in pinned tool tree")
print(digest.hexdigest())
PY
)"
  [ "$actual" = "${expected,,}" ] \
    || block "$label tree SHA-256 mismatch expected=${expected,,} actual=$actual"
}

need_cmd git
need_cmd python3
need_cmd sha256sum
require_pin HC_OPERATOR_OVERLAY_SOURCE_SHA "$SOURCE_SHA"
[[ "$SOURCE_SHA" =~ ^[a-f0-9]{40}$ ]] \
  || block "HC_OPERATOR_OVERLAY_SOURCE_SHA must be a full lowercase commit SHA"
[ "$(git -C "$ROOT" rev-parse --show-toplevel 2>/dev/null)" = "$ROOT" ] \
  || block "builder must run from the expected Home Center git worktree"
git -C "$ROOT" cat-file -e "$SOURCE_SHA^{commit}" 2>/dev/null \
  || block "expected source SHA is not a local commit"
[ "$(git -C "$ROOT" rev-parse HEAD)" = "$SOURCE_SHA" ] \
  || block "checked-out HEAD does not equal HC_OPERATOR_OVERLAY_SOURCE_SHA"
SCOPED_STATUS="$(git -C "$ROOT" status --porcelain=v1 --untracked-files=all -- \
  .github/workflows/operator-overlay-android.yml \
  android/operator-overlay \
  tools/adam.py \
  tools/nicotine_tracker_guard.py \
  tools/vlad_swarm_daemon.py \
  tools/install_adam_cli.sh \
  tools/build_operator_overlay_termux.sh \
  tools/test_adam_nicotine_tracker_contract.py)"
[ -z "$SCOPED_STATUS" ] || block "release source scope is not clean"

for pin in \
  HC_GRADLE_HOME HC_GRADLE_DISTRIBUTION_ZIP HC_GRADLE_DISTRIBUTION_SHA256 \
  HC_GRADLE_TREE_SHA256 HC_GRADLE_BIN_SHA256 HC_GRADLE_USER_HOME \
  HC_GRADLE_VERIFICATION_METADATA_SHA256 HC_GRADLE_LOCKFILE_SHA256 \
  HC_JAVA_HOME HC_JAVA_BIN HC_JAVAC_BIN HC_JAVA_SHA256 HC_JAVAC_SHA256 \
  HC_JAVA_VERSION_LINE HC_JAVAC_VERSION_LINE HC_ANDROID_SDK_ROOT \
  HC_ANDROID_JAR_SHA256 HC_ANDROID_BUILD_TOOLS_VERSION \
  HC_ANDROID_BUILD_TOOLS_TREE_SHA256 HC_AAPT2_PATH HC_AAPT2_SHA256 \
  HC_AAPT2_VERSION_LINE HC_APKSIGNER_PATH HC_APKSIGNER_SHA256 \
  HC_APKSIGNER_VERSION_LINE HC_ANDROID_USER_HOME \
  HC_OPERATOR_OVERLAY_KEYSTORE_SHA256 HC_OPERATOR_OVERLAY_SIGNER_SHA256; do
  require_pin "$pin" "${!pin:-}"
done

for pair in \
  "HC_GRADLE_HOME:$GRADLE_HOME_PIN" \
  "HC_GRADLE_DISTRIBUTION_ZIP:$GRADLE_DISTRIBUTION_ZIP" \
  "HC_GRADLE_USER_HOME:$GRADLE_USER_HOME_PIN" \
  "HC_JAVA_HOME:$JAVA_HOME_PIN" \
  "HC_JAVA_BIN:$JAVA_BIN_PIN" \
  "HC_JAVAC_BIN:$JAVAC_BIN_PIN" \
  "HC_ANDROID_SDK_ROOT:$SDK_ROOT" \
  "HC_AAPT2_PATH:$AAPT2_PATH_PIN" \
  "HC_APKSIGNER_PATH:$APKSIGNER_PATH_PIN" \
  "HC_ANDROID_USER_HOME:$ANDROID_USER_HOME_PIN"; do
  require_absolute "${pair%%:*}" "${pair#*:}"
done

[ "$GRADLE_DISTRIBUTION_SHA256" = "$EXPECTED_GRADLE_DISTRIBUTION_SHA256" ] \
  || block "Gradle distribution pin must match approved Gradle $EXPECTED_GRADLE_VERSION"
[ "$BUILD_TOOLS_VERSION" = "$EXPECTED_BUILD_TOOLS_VERSION" ] \
  || block "Android build tools must be exactly $EXPECTED_BUILD_TOOLS_VERSION"
GRADLE_BIN="$GRADLE_HOME_PIN/bin/gradle"
JAVA_BIN="$JAVA_HOME_PIN/bin/java"
JAVAC_BIN="$JAVA_HOME_PIN/bin/javac"
BUILD_TOOLS="$SDK_ROOT/build-tools/$BUILD_TOOLS_VERSION"
AAPT2="$BUILD_TOOLS/aapt2"
APKSIGNER="$BUILD_TOOLS/apksigner"
ANDROID_JAR="$SDK_ROOT/platforms/android-35/android.jar"
KEYSTORE="$ANDROID_USER_HOME_PIN/debug.keystore"
[ "$JAVA_BIN_PIN" = "$JAVA_BIN" ] || block "HC_JAVA_BIN is outside pinned HC_JAVA_HOME"
[ "$JAVAC_BIN_PIN" = "$JAVAC_BIN" ] || block "HC_JAVAC_BIN is outside pinned HC_JAVA_HOME"
[ "$AAPT2_PATH_PIN" = "$AAPT2" ] || block "HC_AAPT2_PATH is outside pinned build-tools directory"
[ "$APKSIGNER_PATH_PIN" = "$APKSIGNER" ] \
  || block "HC_APKSIGNER_PATH is outside pinned build-tools directory"
[ -x "$GRADLE_BIN" ] || block "pinned Gradle executable is unavailable: $GRADLE_BIN"
[ -x "$JAVA_BIN" ] || block "pinned Java executable is unavailable: $JAVA_BIN"
[ -x "$JAVAC_BIN" ] || block "pinned javac executable is unavailable: $JAVAC_BIN"
[ -x "$AAPT2" ] || block "pinned aapt2 executable is unavailable: $AAPT2"
[ -f "$APKSIGNER" ] || block "pinned apksigner is unavailable: $APKSIGNER"
[ -d "$GRADLE_USER_HOME_PIN/caches" ] || block "preexisting Gradle dependency cache missing"

verify_sha256 "Gradle 8.9 distribution archive" \
  "$GRADLE_DISTRIBUTION_ZIP" "$GRADLE_DISTRIBUTION_SHA256"
verify_tree_sha256 "Gradle 8.9 distribution" "$GRADLE_HOME_PIN" "$GRADLE_TREE_SHA256"
verify_sha256 "Gradle executable" "$GRADLE_BIN" "$GRADLE_BIN_SHA256"
"$GRADLE_BIN" --version | grep -Fx "Gradle $EXPECTED_GRADLE_VERSION" >/dev/null \
  || block "pinned Gradle version mismatch"
verify_sha256 "Java executable" "$JAVA_BIN" "$JAVA_SHA256"
verify_sha256 "javac executable" "$JAVAC_BIN" "$JAVAC_SHA256"
[ "$("$JAVA_BIN" -version 2>&1 | sed -n '1p')" = "$JAVA_VERSION_LINE" ] \
  || block "pinned Java version mismatch"
[ "$("$JAVAC_BIN" -version 2>&1 | sed -n '1p')" = "$JAVAC_VERSION_LINE" ] \
  || block "pinned javac version mismatch"
verify_sha256 "Android API 35 jar" "$ANDROID_JAR" "$ANDROID_JAR_SHA256"
verify_tree_sha256 "Android build tools" "$BUILD_TOOLS" "$BUILD_TOOLS_TREE_SHA256"
verify_sha256 "aapt2" "$AAPT2" "$AAPT2_SHA256"
verify_sha256 "apksigner" "$APKSIGNER" "$APKSIGNER_SHA256"
[ "$("$AAPT2" version 2>&1 | sed -n '1p')" = "$AAPT2_VERSION_LINE" ] \
  || block "pinned aapt2 version mismatch"
[ "$("$APKSIGNER" version 2>&1 | sed -n '1p')" = "$APKSIGNER_VERSION_LINE" ] \
  || block "pinned apksigner version mismatch"
verify_sha256 "overlay signing keystore" "$KEYSTORE" "$KEYSTORE_SHA256"

[ -f "$GRADLE_FILE" ] || block "Gradle metadata source missing: $GRADLE_FILE"
verify_sha256 "Gradle dependency verification metadata" \
  "$VERIFICATION_METADATA" "$VERIFICATION_METADATA_SHA256"
verify_sha256 "Gradle app dependency lock" "$DEPENDENCY_LOCK" "$DEPENDENCY_LOCK_SHA256"
grep -F '<verify-metadata>true</verify-metadata>' "$VERIFICATION_METADATA" >/dev/null \
  || block "Gradle verification metadata does not verify artifact metadata"
grep -F '<sha256 value=' "$VERIFICATION_METADATA" >/dev/null \
  || block "Gradle verification metadata has no artifact SHA-256 pins"
grep -Eq '^[^#[:space:]][^=]*=.*$' "$DEPENDENCY_LOCK" \
  || block "Gradle dependency lock has no resolved modules"

read -r APPLICATION_ID MIN_SDK TARGET_SDK VERSION_CODE VERSION_NAME < <(python3 - "$GRADLE_FILE" <<'PY'
import re
import sys

text = open(sys.argv[1], encoding="utf-8").read()
def exactly(pattern, name):
    values = re.findall(pattern, text, re.MULTILINE)
    if len(values) != 1:
        raise SystemExit(f"BLOCKED: expected one Gradle {name}, found {len(values)}")
    return values[0]

print(
    exactly(r"^\s*applicationId\s+['\"]([^'\"]+)['\"]\s*$", "applicationId"),
    exactly(r"^\s*minSdk\s+(\d+)\s*$", "minSdk"),
    exactly(r"^\s*targetSdk\s+(\d+)\s*$", "targetSdk"),
    exactly(r"^\s*versionCode\s+(\d+)\s*$", "versionCode"),
    exactly(r"^\s*versionName\s+['\"]([^'\"]+)['\"]\s*$", "versionName"),
)
PY
)
[ "$APPLICATION_ID" = "$EXPECTED_PACKAGE" ] \
  || block "Gradle applicationId must be exactly $EXPECTED_PACKAGE"
[ "$VERSION_CODE" -gt 4 ] || block "release versionCode must be monotonic after 4"
[ "$VERSION_NAME" != "1.3.0" ] || block "release versionName must advance after 1.3.0"

python3 "$ROOT/tools/test_adam_nicotine_tracker_contract.py"

export ANDROID_HOME="$SDK_ROOT"
export ANDROID_SDK_ROOT="$SDK_ROOT"
export ANDROID_USER_HOME="$ANDROID_USER_HOME_PIN"
export GRADLE_USER_HOME="$GRADLE_USER_HOME_PIN"
export JAVA_HOME="$JAVA_HOME_PIN"

"$GRADLE_BIN" --offline --no-daemon --console=plain \
  --dependency-verification=strict -p "$PROJECT" testDebugUnitTest assembleDebug
[ -f "$APK" ] || block "Gradle completed without the expected APK: $APK"

BADGING="$("$AAPT2" dump badging "$APK")"
APK_PACKAGE="$(printf '%s\n' "$BADGING" | sed -n "s/^package: name='\([^']*\)'.*/\1/p" | head -1)"
APK_VERSION_CODE="$(printf '%s\n' "$BADGING" | sed -n "s/^package:.*versionCode='\([^']*\)'.*/\1/p" | head -1)"
APK_VERSION_NAME="$(printf '%s\n' "$BADGING" | sed -n "s/^package:.*versionName='\([^']*\)'.*/\1/p" | head -1)"
APK_MIN_SDK="$(printf '%s\n' "$BADGING" | sed -n "s/^sdkVersion:'\([^']*\)'.*/\1/p" | head -1)"
APK_TARGET_SDK="$(printf '%s\n' "$BADGING" | sed -n "s/^targetSdkVersion:'\([^']*\)'.*/\1/p" | head -1)"
[ "$APK_PACKAGE" = "$EXPECTED_PACKAGE" ] || block "APK package id diverges from release contract"
[ "$APK_VERSION_CODE" = "$VERSION_CODE" ] || block "APK versionCode diverges from Gradle"
[ "$APK_VERSION_NAME" = "$VERSION_NAME" ] || block "APK versionName diverges from Gradle"
[ "$APK_MIN_SDK" = "$MIN_SDK" ] || block "APK minSdk diverges from Gradle"
[ "$APK_TARGET_SDK" = "$TARGET_SDK" ] || block "APK targetSdk diverges from Gradle"

ACTUAL_SIGNER="$("$APKSIGNER" verify --print-certs "$APK" \
  | sed -n 's/^Signer #1 certificate SHA-256 digest: //p' | head -1 | tr '[:upper:]' '[:lower:]')"
[ "$ACTUAL_SIGNER" = "${SIGNER_SHA256,,}" ] \
  || block "APK signer mismatch expected=${SIGNER_SHA256,,} actual=$ACTUAL_SIGNER"

APK_SHA256="$(sha256sum "$APK" | awk '{print $1}')"
printf 'TERMUX OVERLAY APK BUILT sha256=%s package=%s versionCode=%s versionName=%s minSdk=%s targetSdk=%s signer=%s source=%s apk=%s\n' \
  "$APK_SHA256" "$APK_PACKAGE" "$VERSION_CODE" "$VERSION_NAME" "$MIN_SDK" \
  "$TARGET_SDK" "$ACTUAL_SIGNER" "$SOURCE_SHA" "$APK"
