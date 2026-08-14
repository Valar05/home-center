#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
PROJECT="$ROOT/android/operator-overlay"
PACKAGE="com.homecenter.operatoroverlay"
STATE="$HOME/.local/state/home-center"
RECEIPT="$STATE/adam-overlay-recovery.json"
APK="$PROJECT/app/build/outputs/apk/debug/app-debug.apk"
STAGED="/data/local/tmp/home-center-operator-overlay.apk"
mkdir -p "$STATE"

RISH_BIN="${RISH:-$(command -v rish 2>/dev/null || true)}"
[ -n "$RISH_BIN" ] || RISH_BIN="$HOME/bin/rish"
[ -x "$RISH_BIN" ] || { echo 'BLOCKED: rish missing; Shizuku authority required.' >&2; exit 2; }

rish() { "$RISH_BIN" -c "$1"; }

record() {
  local ok="$1" mode="$2" detail="$3"
  python3 - "$RECEIPT" "$ok" "$mode" "$detail" <<'PY'
import json,sys,time
path,ok,mode,detail=sys.argv[1:]
obj={'schema':'adam-overlay-recovery-v1','ok':ok=='1','mode':mode,'detail':detail,'verifiedAtEpoch':int(time.time()),'device':'primary-phone','runtime':'android-native-overlay','ciUsed':False,'godotRuntimeUsed':False}
open(path,'w',encoding='utf-8').write(json.dumps(obj,indent=2,sort_keys=True)+'\n')
print(json.dumps(obj,indent=2,sort_keys=True))
PY
}

verify_overlay() {
  local state
  state="$(rish "pm list packages $PACKAGE; appops get $PACKAGE SYSTEM_ALERT_WINDOW 2>/dev/null || true; content query --uri content://com.homecenter.operatoroverlay.state/state 2>/dev/null || true" 2>&1 || true)"
  printf '%s\n' "$state" > "$STATE/adam-overlay-recovery-state.txt"
  printf '%s\n' "$state" | grep -q "package:$PACKAGE" || return 1
  printf '%s\n' "$state" | grep -q 'SYSTEM_ALERT_WINDOW: allow' || return 1
  printf '%s\n' "$state" | grep -q 'control_enabled=' || return 1
}

start_overlay() {
  rish "appops set $PACKAGE SYSTEM_ALERT_WINDOW allow" >/dev/null
  rish "pm grant $PACKAGE android.permission.POST_NOTIFICATIONS 2>/dev/null || true" >/dev/null || true
  rish "am force-stop $PACKAGE 2>/dev/null || true; am start-foreground-service -n $PACKAGE/.OperatorOverlayService >/dev/null 2>&1 || am start -n $PACKAGE/.MainActivity >/dev/null" >/dev/null
  sleep 2
}

if [ "${HC_FORCE_BUILD:-0}" != "1" ] && rish "pm list packages $PACKAGE" 2>/dev/null | grep -q "package:$PACKAGE"; then
  start_overlay
  if verify_overlay; then record 1 restart 'Existing overlay package restarted and verified on phone.'; exit 0; fi
fi

echo '[overlay] package missing or unhealthy; forging locally on phone'
GRADLE_BIN="${GRADLE_BIN:-}"
if [ -z "$GRADLE_BIN" ] && [ -x /data/data/com.termux/files/usr/tmp/gradle-8.14.3/gradle-8.14.3/bin/gradle ]; then GRADLE_BIN=/data/data/com.termux/files/usr/tmp/gradle-8.14.3/gradle-8.14.3/bin/gradle; fi
if [ -z "$GRADLE_BIN" ]; then GRADLE_BIN="$(command -v gradle 2>/dev/null || true)"; fi
[ -n "$GRADLE_BIN" ] || { record 0 blocked 'Gradle is absent on phone.'; exit 3; }
command -v java >/dev/null 2>&1 || { record 0 blocked 'Java is absent on phone.'; exit 4; }
AAPT_ARGS=()
if [ -x /data/data/com.termux/files/usr/bin/aapt2 ]; then AAPT_ARGS+=("-Pandroid.aapt2FromMavenOverride=/data/data/com.termux/files/usr/bin/aapt2"); fi
(cd "$PROJECT" && "$GRADLE_BIN" :app:assembleDebug --no-daemon "${AAPT_ARGS[@]}")
[ -s "$APK" ] || { record 0 blocked "Phone build completed without APK at $APK"; exit 5; }
REAL_APK="$(readlink -f "$APK")"
SHA="$(sha256sum "$REAL_APK" | awk '{print $1}')"
STAGED_SHA="$(rish "set -e; cp '$REAL_APK' '$STAGED'; chmod 644 '$STAGED'; sha256sum '$STAGED'" 2>&1 | grep -Eo '[0-9a-f]{64}' | tail -1)"
[ "$SHA" = "$STAGED_SHA" ] || { record 0 blocked 'Staged APK hash mismatch.'; exit 6; }
set +e
INSTALL_OUT="$(rish "pm install -r '$STAGED'" 2>&1)"; INSTALL_RC=$?
set -e
printf '%s\n' "$INSTALL_OUT" > "$STATE/adam-overlay-recovery-install.txt"
if [ $INSTALL_RC -ne 0 ] || ! printf '%s\n' "$INSTALL_OUT" | grep -q 'Success'; then
  if printf '%s\n' "$INSTALL_OUT" | grep -Eqi 'UPDATE_INCOMPATIBLE|signatures do not match|incompatible'; then
    rish "am force-stop $PACKAGE 2>/dev/null || true; pm uninstall $PACKAGE" >/dev/null
    INSTALL_OUT="$(rish "pm install '$STAGED'" 2>&1)"
    printf '%s\n' "$INSTALL_OUT" | grep -q 'Success' || { record 0 blocked 'Replacement install failed.'; exit 7; }
  else record 0 blocked "Android install failed: ${INSTALL_OUT:0:1000}"; exit 8; fi
fi
start_overlay
rish "rm -f '$STAGED'" >/dev/null 2>&1 || true
verify_overlay || { record 0 blocked 'Overlay installed but verification failed.'; exit 9; }
record 1 local_build "Built and installed locally on phone; sha256=$SHA"
