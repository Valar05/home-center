#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
STATE="$HOME/.local/state/home-center"
mkdir -p "$STATE"
RECEIPT="$STATE/adam-overlay-deploy-receipt.json"
PACKAGE="com.homecenter.operatoroverlay"
RISH_BIN="${RISH:-$(command -v rish 2>/dev/null || true)}"
[ -n "$RISH_BIN" ] || RISH_BIN="$HOME/bin/rish"

cd "$ROOT"
git fetch origin main generated/operator-overlay-apk || true
git checkout main >/dev/null 2>&1 || true
git pull --ff-only origin main
SOURCE_SHA="$(git rev-parse HEAD)"

bash tools/run_fortress_local_contracts.sh

install_generated() {
  local build_receipt="$STATE/adam-overlay-build-receipt.json"
  git show "origin/generated/operator-overlay-apk:operator-overlay-receipt.json" > "$build_receipt" 2>/dev/null || return 1
  local artifact_source
  artifact_source="$(python - "$build_receipt" <<'PY'
import json,sys
print(json.load(open(sys.argv[1],encoding='utf-8')).get('sourceCommit',''))
PY
)"
  [ -n "$artifact_source" ] || return 1
  git merge-base --is-ancestor "$SOURCE_SHA" "$artifact_source" 2>/dev/null || return 1
  bash tools/setup_android_operator_overlay.sh
  return 0
}

install_local_apk() {
  local apk="$1"
  [ -x "$RISH_BIN" ] || { echo 'BLOCKED: rish missing; Shizuku authority required.' >&2; return 2; }
  [ -s "$apk" ] || { echo "BLOCKED: APK missing: $apk" >&2; return 3; }
  local staged="/data/local/tmp/home-center-operator-overlay.apk"
  local real_apk sha staged_sha install_out
  real_apk="$(readlink -f "$apk")"
  sha="$(sha256sum "$real_apk" | awk '{print $1}')"
  staged_sha="$("$RISH_BIN" -c "set -e; cp '$real_apk' '$staged'; chmod 644 '$staged'; sha256sum '$staged'" 2>&1 | grep -Eo '[0-9a-f]{64}' | tail -1)"
  [ "$sha" = "$staged_sha" ] || { echo 'BLOCKED: staged APK hash mismatch.' >&2; return 4; }

  set +e
  install_out="$("$RISH_BIN" -c "pm install -r '$staged'" 2>&1)"
  local install_rc=$?
  set -e
  printf '%s\n' "$install_out" | tee "$STATE/adam-overlay-install.txt"
  if [ $install_rc -ne 0 ] || ! printf '%s\n' "$install_out" | grep -q 'Success'; then
    if printf '%s\n' "$install_out" | grep -Eqi 'UPDATE_INCOMPATIBLE|signatures do not match|incompatible'; then
      echo '[deploy] Existing overlay uses another signing key; replacing only com.homecenter.operatoroverlay.'
      "$RISH_BIN" -c "am force-stop $PACKAGE 2>/dev/null || true; pm uninstall $PACKAGE" | tee "$STATE/adam-overlay-uninstall.txt"
      install_out="$("$RISH_BIN" -c "pm install '$staged'" 2>&1)"
      printf '%s\n' "$install_out" | tee "$STATE/adam-overlay-install-after-replace.txt"
      printf '%s\n' "$install_out" | grep -q 'Success' || { echo 'BLOCKED: replacement install failed.' >&2; return 5; }
    else
      echo 'BLOCKED: Android package install failed for a reason other than signing-key replacement.' >&2
      return 5
    fi
  fi

  "$RISH_BIN" -c "appops set $PACKAGE SYSTEM_ALERT_WINDOW allow"
  "$RISH_BIN" -c "pm grant $PACKAGE android.permission.POST_NOTIFICATIONS 2>/dev/null || true"
  "$RISH_BIN" -c "am force-stop $PACKAGE; am start-foreground-service -n $PACKAGE/.OperatorOverlayService >/dev/null 2>&1 || am start -n $PACKAGE/.MainActivity >/dev/null"
  sleep 2
  "$RISH_BIN" -c "rm -f '$staged'" || true
  local state
  state="$("$RISH_BIN" -c "content query --uri content://com.homecenter.operatoroverlay.state/state" 2>&1)"
  printf '%s\n' "$state" | grep -q 'adam_request_id=' || { echo 'BLOCKED: installed overlay does not expose Adam request state.' >&2; return 6; }
  python - "$RECEIPT" "$SOURCE_SHA" "$sha" "$state" <<'PY'
import json,sys,time
path,source,sha,state=sys.argv[1:]
obj={
  'schema':'adam-overlay-phone-deploy-v1',
  'ok':True,
  'sourceCommit':source,
  'apkSha256':sha,
  'package':'com.homecenter.operatoroverlay',
  'adamStateVisible':'adam_request_id=' in state,
  'verifiedAtEpoch':int(time.time()),
  'state':state[-3000:],
}
open(path,'w',encoding='utf-8').write(json.dumps(obj,indent=2,sort_keys=True)+'\n')
print(json.dumps(obj,indent=2,sort_keys=True))
PY
}

if install_generated; then
  state="$("$RISH_BIN" -c "content query --uri content://com.homecenter.operatoroverlay.state/state" 2>&1)"
  printf '%s\n' "$state" | grep -q 'adam_request_id=' || { echo 'BLOCKED: generated APK installed but Adam request state is absent.' >&2; exit 20; }
  sha="$(sha256sum "$HOME/storage/downloads/home-center-operator-overlay.apk" | awk '{print $1}')"
  python - "$RECEIPT" "$SOURCE_SHA" "$sha" "$state" <<'PY'
import json,sys,time
path,source,sha,state=sys.argv[1:]
obj={'schema':'adam-overlay-phone-deploy-v1','ok':True,'sourceCommit':source,'apkSha256':sha,'package':'com.homecenter.operatoroverlay','adamStateVisible':True,'verifiedAtEpoch':int(time.time()),'state':state[-3000:]}
open(path,'w',encoding='utf-8').write(json.dumps(obj,indent=2,sort_keys=True)+'\n')
print(json.dumps(obj,indent=2,sort_keys=True))
PY
else
  LOCAL_APK="${HC_ADAM_OVERLAY_APK:-$ROOT/android/operator-overlay/app/build/outputs/apk/debug/app-debug.apk}"
  if [ ! -s "$LOCAL_APK" ]; then
    echo '[deploy] No current generated APK; forging locally on phone.'
    bash tools/recover_adam_overlay_phone.sh
  else
    install_local_apk "$LOCAL_APK"
  fi
fi

bash tools/install_adam_cli.sh
bash tools/install_fortress_resume_phone.sh
bash tools/setup_vlad_swarm_daemon.sh
bash tools/accept_adam_cli_phone.sh
echo "ADAM OVERLAY + CLI ACCEPTED overlay_receipt=$RECEIPT cli_receipt=$STATE/adam-cli-install-receipt.json acceptance=$STATE/adam-cli-phone-acceptance.json fortress_resume=$STATE/fortress-resume-install.json"
