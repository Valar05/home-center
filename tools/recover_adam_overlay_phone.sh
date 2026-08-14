#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
PROJECT="$ROOT/android/operator-overlay"
PACKAGE="com.homecenter.operatoroverlay"
STATE="$HOME/.local/state/home-center"
RECEIPT="$STATE/adam-overlay-recovery.json"
APK="$PROJECT/app/build/outputs/apk/debug/app-debug.apk"
STAGED="/data/local/tmp/home-center-operator-overlay.apk"
PRIOR_APK="/data/local/tmp/home-center-operator-overlay-prior.apk"
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
OLD_APK_PATH="$(rish "pm path '$PACKAGE' 2>/dev/null | sed -n 's/^package://p' | head -1" 2>/dev/null || true)"
OLD_APK_SHA=""
if [ -n "$OLD_APK_PATH" ]; then
  OLD_APK_SHA="$(rish "set -e; cp '$OLD_APK_PATH' '$PRIOR_APK'; chmod 600 '$PRIOR_APK'; sha256sum '$PRIOR_APK'" 2>&1 | grep -Eo '[0-9a-f]{64}' | tail -1)"
  [ -n "$OLD_APK_SHA" ] || { record 0 blocked 'Could not preserve and hash the exact prior APK; candidate was not installed.'; exit 7; }
fi
set +e
INSTALL_OUT="$(rish "pm install -r '$STAGED'" 2>&1)"; INSTALL_RC=$?
set -e
printf '%s\n' "$INSTALL_OUT" > "$STATE/adam-overlay-recovery-install.txt"
if [ $INSTALL_RC -ne 0 ] || ! printf '%s\n' "$INSTALL_OUT" | grep -q 'Success'; then
  record 0 blocked "Android install failed without uninstalling the accepted package: ${INSTALL_OUT:0:1000}"
  exit 8
fi
start_overlay
if ! verify_overlay; then
  if [ -z "$OLD_APK_PATH" ] || [ -z "$OLD_APK_SHA" ]; then
    record 0 rollback_unavailable 'Candidate verification failed and no accepted prior APK existed to restore.'
    exit 9
  fi
  set +e
  ROLLBACK_OUT="$(rish "pm install -r -d '$PRIOR_APK'" 2>&1)"; ROLLBACK_RC=$?
  set -e
  printf '%s\n' "$ROLLBACK_OUT" > "$STATE/adam-overlay-recovery-rollback.txt"
  if [ $ROLLBACK_RC -ne 0 ] || ! printf '%s\n' "$ROLLBACK_OUT" | grep -q 'Success'; then
    record 0 rollback_failed "Candidate verification failed and exact-prior reinstall failed: ${ROLLBACK_OUT:0:1000}"
    exit 10
  fi
  if ! start_overlay || ! verify_overlay; then
    record 0 rollback_failed 'Exact prior APK reinstalled but prior runtime verification failed.'
    exit 11
  fi
  RESTORED_APK_PATH="$(rish "pm path '$PACKAGE' 2>/dev/null | sed -n 's/^package://p' | head -1" 2>/dev/null || true)"
  RESTORED_APK_SHA="$(rish "sha256sum '$RESTORED_APK_PATH'" 2>&1 | grep -Eo '[0-9a-f]{64}' | tail -1)"
  if [ "$RESTORED_APK_SHA" != "$OLD_APK_SHA" ]; then
    record 0 rollback_failed "Prior runtime returned but installed APK hash did not match preserved prior: expected=$OLD_APK_SHA actual=$RESTORED_APK_SHA"
    exit 12
  fi
  rish "rm -f '$STAGED' '$PRIOR_APK'" >/dev/null 2>&1 || true
  record 0 rolled_back "Candidate verification failed; exact prior APK restored and hash-verified: sha256=$OLD_APK_SHA"
  exit 9
fi
rish "rm -f '$STAGED' '$PRIOR_APK'" >/dev/null 2>&1 || true
record 1 local_build "Built and installed locally on phone; sha256=$SHA"
