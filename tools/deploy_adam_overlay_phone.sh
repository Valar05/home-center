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

python tools/test_adam_overlay_contract.py
python -m py_compile tools/adam.py tools/vlad_swarm_daemon.py

install_generated() {
  local build_receipt="$STATE/adam-overlay-build-receipt.json"
  local apk="$HOME/storage/downloads/home-center-operator-overlay.apk"
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
  local real_apk sha staged_sha
  real_apk="$(readlink -f "$apk")"
  sha="$(sha256sum "$real_apk" | awk '{print $1}')"
  staged_sha="$("$RISH_BIN" -c "set -e; cp '$real_apk' '$staged'; chmod 644 '$staged'; sha256sum '$staged'" 2>&1 | grep -Eo '[0-9a-f]{64}' | tail -1)"
  [ "$sha" = "$staged_sha" ] || { echo 'BLOCKED: staged APK hash mismatch.' >&2; return 4; }
  "$RISH_BIN" -c "pm install -r '$staged'" | tee "$STATE/adam-overlay-install.txt"
  "$RISH_BIN" -c "appops set $PACKAGE SYSTEM_ALERT_WINDOW allow"
  "$RISH_BIN" -c "pm grant $PACKAGE android.permission.POST_NOTIFICATIONS 2>/dev/null || true"
  "$RISH_BIN" -c "am force-stop $PACKAGE; am start-foreground-service -n $PACKAGE/.OperatorOverlayService >/dev/null 2>&1 || am start -n $PACKAGE/.MainActivity >/dev/null"
  sleep 2
  "$RISH_BIN" -c "rm -f '$staged'" || true
  local state
  state="$("$RISH_BIN" -c "content query --uri content://com.homecenter.operatoroverlay.state/state" 2>&1)"
  printf '%s\n' "$state" | grep -q 'adam_request_id=' || { echo 'BLOCKED: installed overlay does not expose Adam request state.' >&2; return 5; }
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
  if [ -s "$LOCAL_APK" ]; then
    install_local_apk "$LOCAL_APK"
  else
    cat >&2 <<EOF
BLOCKED: no current generated Adam overlay artifact and no locally built APK exists.
Source is ready at: $SOURCE_SHA
Expected local APK: $LOCAL_APK
GitHub hosted Android build has failed before runner execution, so this script refuses to install a stale overlay.
Build the existing android/operator-overlay project on any authorized Android-capable workstation, place app-debug.apk at the path above (or set HC_ADAM_OVERLAY_APK), then rerun this same command. No source changes are required.
EOF
    exit 21
  fi
fi

# Restart the already-installed swarm daemon so it consumes Adam overlay requests.
bash tools/setup_vlad_swarm_daemon.sh

echo "ADAM OVERLAY DEPLOYED receipt=$RECEIPT"
