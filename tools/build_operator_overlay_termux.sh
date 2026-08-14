#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

# Strict release build: all tools, SDK bytes, caches, and signer must already
# exist and be pinned. This script never installs packages, downloads bytes, or
# generates a signing identity.
ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
PROJECT="$ROOT/android/operator-overlay"
APP="$PROJECT/app"
GRADLE_FILE="$APP/build.gradle"
APK="$APP/build/outputs/apk/debug/app-debug.apk"
GRADLE_BIN="${HC_GRADLE:-}"
GRADLE_SHA256="${HC_GRADLE_SHA256:-}"
SDK_ROOT="${HC_ANDROID_SDK_ROOT:-${ANDROID_SDK_ROOT:-${ANDROID_HOME:-}}}"
ANDROID_JAR_SHA256="${HC_ANDROID_JAR_SHA256:-}"
ANDROID_USER_HOME="${HC_ANDROID_USER_HOME:-${ANDROID_USER_HOME:-$HOME/.android}}"
KEYSTORE="$ANDROID_USER_HOME/debug.keystore"
KEYSTORE_SHA256="${HC_OPERATOR_OVERLAY_KEYSTORE_SHA256:-}"
SIGNER_SHA256="${HC_OPERATOR_OVERLAY_SIGNER_SHA256:-}"

block() { printf 'BLOCKED: %s\n' "$*" >&2; exit 30; }
need_cmd() { command -v "$1" >/dev/null 2>&1 || block "preexisting tool missing: $1"; }
require_pin() { [ -n "$2" ] || block "required release pin missing: $1"; }
verify_sha256() {
  local label="$1" path="$2" expected="$3" actual
  [ -f "$path" ] || block "$label missing: $path"
  actual="$(sha256sum "$path" | awk '{print $1}')"
  [ "$actual" = "${expected,,}" ] || block "$label SHA-256 mismatch expected=${expected,,} actual=$actual"
}

need_cmd python3
need_cmd sha256sum
need_cmd aapt2
need_cmd apksigner
require_pin HC_GRADLE "$GRADLE_BIN"
require_pin HC_GRADLE_SHA256 "$GRADLE_SHA256"
require_pin HC_ANDROID_SDK_ROOT "$SDK_ROOT"
require_pin HC_ANDROID_JAR_SHA256 "$ANDROID_JAR_SHA256"
require_pin HC_OPERATOR_OVERLAY_KEYSTORE_SHA256 "$KEYSTORE_SHA256"
require_pin HC_OPERATOR_OVERLAY_SIGNER_SHA256 "$SIGNER_SHA256"
[ -x "$GRADLE_BIN" ] || block "pinned Gradle executable is unavailable: $GRADLE_BIN"
[ -d "$SDK_ROOT" ] || block "pinned Android SDK is unavailable: $SDK_ROOT"
[ -d "${GRADLE_USER_HOME:-$HOME/.gradle}/caches" ] || block "preexisting Gradle dependency cache missing"
[ -f "$GRADLE_FILE" ] || block "Gradle metadata source missing: $GRADLE_FILE"

verify_sha256 "Gradle executable" "$GRADLE_BIN" "$GRADLE_SHA256"
ANDROID_JAR="$SDK_ROOT/platforms/android-35/android.jar"
verify_sha256 "Android API 35 jar" "$ANDROID_JAR" "$ANDROID_JAR_SHA256"
verify_sha256 "overlay signing keystore" "$KEYSTORE" "$KEYSTORE_SHA256"

read -r MIN_SDK TARGET_SDK VERSION_CODE VERSION_NAME < <(python3 - "$GRADLE_FILE" <<'PY'
import re,sys
text=open(sys.argv[1],encoding='utf-8').read()
def exactly(pattern,name):
    values=re.findall(pattern,text,re.MULTILINE)
    if len(values)!=1: raise SystemExit(f"BLOCKED: expected one Gradle {name}, found {len(values)}")
    return values[0]
print(
    exactly(r'^\s*minSdk\s+(\d+)\s*$', 'minSdk'),
    exactly(r'^\s*targetSdk\s+(\d+)\s*$', 'targetSdk'),
    exactly(r'^\s*versionCode\s+(\d+)\s*$', 'versionCode'),
    exactly(r'^\s*versionName\s+[\'\"]([^\'\"]+)[\'\"]\s*$', 'versionName'),
)
PY
)
[ -n "$MIN_SDK" ] && [ -n "$TARGET_SDK" ] && [ -n "$VERSION_CODE" ] && [ -n "$VERSION_NAME" ] \
  || block "Gradle version metadata parse failed"

export ANDROID_HOME="$SDK_ROOT"
export ANDROID_SDK_ROOT="$SDK_ROOT"
export ANDROID_USER_HOME

"$GRADLE_BIN" --offline --no-daemon --console=plain -p "$PROJECT" \
  testDebugUnitTest assembleDebug
[ -f "$APK" ] || block "Gradle completed without the expected APK: $APK"

BADGING="$(aapt2 dump badging "$APK")"
APK_VERSION_CODE="$(printf '%s\n' "$BADGING" | sed -n "s/^package:.*versionCode='\([^']*\)'.*/\1/p" | head -1)"
APK_VERSION_NAME="$(printf '%s\n' "$BADGING" | sed -n "s/^package:.*versionName='\([^']*\)'.*/\1/p" | head -1)"
APK_MIN_SDK="$(printf '%s\n' "$BADGING" | sed -n "s/^sdkVersion:'\([^']*\)'.*/\1/p" | head -1)"
APK_TARGET_SDK="$(printf '%s\n' "$BADGING" | sed -n "s/^targetSdkVersion:'\([^']*\)'.*/\1/p" | head -1)"
[ "$APK_VERSION_CODE" = "$VERSION_CODE" ] || block "APK versionCode diverges from Gradle"
[ "$APK_VERSION_NAME" = "$VERSION_NAME" ] || block "APK versionName diverges from Gradle"
[ "$APK_MIN_SDK" = "$MIN_SDK" ] || block "APK minSdk diverges from Gradle"
[ "$APK_TARGET_SDK" = "$TARGET_SDK" ] || block "APK targetSdk diverges from Gradle"

ACTUAL_SIGNER="$(apksigner verify --print-certs "$APK" \
  | sed -n 's/^Signer #1 certificate SHA-256 digest: //p' | head -1 | tr '[:upper:]' '[:lower:]')"
[ "$ACTUAL_SIGNER" = "${SIGNER_SHA256,,}" ] \
  || block "APK signer mismatch expected=${SIGNER_SHA256,,} actual=$ACTUAL_SIGNER"

APK_SHA256="$(sha256sum "$APK" | awk '{print $1}')"
printf 'TERMUX OVERLAY APK BUILT sha256=%s versionCode=%s versionName=%s minSdk=%s targetSdk=%s signer=%s apk=%s\n' \
  "$APK_SHA256" "$VERSION_CODE" "$VERSION_NAME" "$MIN_SDK" "$TARGET_SDK" "$ACTUAL_SIGNER" "$APK"

