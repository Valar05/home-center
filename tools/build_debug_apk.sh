#!/data/data/com.termux/files/usr/bin/sh
set -eu

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
cd "$ROOT"

sh tools/run_regression_tests.sh
gradle assembleDebug --no-daemon
apksigner verify --verbose app/build/outputs/apk/debug/app-debug.apk
aapt dump badging app/build/outputs/apk/debug/app-debug.apk | sed -n '1,12p'
cp app/build/outputs/apk/debug/app-debug.apk /storage/emulated/0/Download/HomeCenter-debug.apk
am broadcast -a android.intent.action.MEDIA_SCANNER_SCAN_FILE -d file:///storage/emulated/0/Download/HomeCenter-debug.apk >/dev/null 2>&1 || true
ls -lh /storage/emulated/0/Download/HomeCenter-debug.apk
