#!/data/data/com.termux/files/usr/bin/sh
set -eu

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
cd "$ROOT"

sh tools/run_regression_tests.sh

GRADLE_BIN="${GRADLE_BIN:-}"
if [ -z "$GRADLE_BIN" ] && [ -x /data/data/com.termux/files/usr/tmp/gradle-8.14.3/gradle-8.14.3/bin/gradle ]; then
  GRADLE_BIN="/data/data/com.termux/files/usr/tmp/gradle-8.14.3/gradle-8.14.3/bin/gradle"
fi
if [ -z "$GRADLE_BIN" ]; then
  GRADLE_BIN="$(command -v gradle)"
fi

AAPT_ARGS=""
if [ -x /data/data/com.termux/files/usr/bin/aapt2 ]; then
  AAPT_ARGS="-Pandroid.aapt2FromMavenOverride=/data/data/com.termux/files/usr/bin/aapt2"
fi

"$GRADLE_BIN" assembleDebug --no-daemon $AAPT_ARGS
apksigner verify --verbose app/build/outputs/apk/debug/app-debug.apk
aapt dump badging app/build/outputs/apk/debug/app-debug.apk | sed -n '1,12p'
cp app/build/outputs/apk/debug/app-debug.apk /storage/emulated/0/Download/HomeCenter-debug.apk
am broadcast -a android.intent.action.MEDIA_SCANNER_SCAN_FILE -d file:///storage/emulated/0/Download/HomeCenter-debug.apk >/dev/null 2>&1 || true
ls -lh /storage/emulated/0/Download/HomeCenter-debug.apk

sh tools/install_debug_apk_shizuku.sh /storage/emulated/0/Download/HomeCenter-debug.apk
