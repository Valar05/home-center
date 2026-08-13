#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
STATE_ROOT="${HC_SPOTIFY_RADIO_DEPLOY_STATE:-$HOME/.local/state/home-center/spotify-overlay-radio-deploy}"
PACKAGE="com.homecenter.operatoroverlay"
APK="$ROOT/android/operator-overlay/app/build/outputs/apk/debug/app-debug.apk"
BUILD_RECEIPT="$ROOT/android/operator-overlay/app/build/outputs/apk/debug/operator-overlay-build-receipt.json"
DEPLOY_RECEIPT="$STATE_ROOT/deploy-receipt.json"
STAGED_APK="/data/local/tmp/home-center-spotify-overlay-radio.apk"
RISH_BIN="${RISH:-$(command -v rish 2>/dev/null || true)}"
[ -n "$RISH_BIN" ] || RISH_BIN="$HOME/bin/rish"

mkdir -p "$STATE_ROOT"
[ -x "$RISH_BIN" ] || { echo 'BLOCKED: rish missing; Android package authority is required.' >&2; exit 2; }
[ -d "$ROOT/.git" ] || git -C "$ROOT" rev-parse --git-dir >/dev/null 2>&1 || { echo 'BLOCKED: deploy root is not a Git worktree.' >&2; exit 3; }
[ -z "$(git -C "$ROOT" status --porcelain=v1)" ] || { echo 'BLOCKED: Spotify radio deploy requires a clean isolated worktree.' >&2; exit 4; }
SOURCE_COMMIT="$(git -C "$ROOT" rev-parse HEAD)"
SOURCE_BRANCH="$(git -C "$ROOT" branch --show-current)"

python "$ROOT/tools/spotify_radio_contract_test.py"
python "$ROOT/tools/spotify_overlay_radio_contract_test.py"
python -m py_compile \
  "$ROOT/tools/spotify_radio.py" \
  "$ROOT/tools/adam.py" \
  "$ROOT/tools/vlad_swarm_daemon.py"
bash -n "$ROOT/tools/setup_spotify_radio.sh"
bash -n "$ROOT/tools/build_operator_overlay_termux.sh"

bash "$ROOT/tools/build_operator_overlay_termux.sh"
[ -s "$APK" ] || { echo "BLOCKED: overlay APK missing after build: $APK" >&2; exit 5; }
[ -s "$BUILD_RECEIPT" ] || { echo "BLOCKED: overlay build receipt missing: $BUILD_RECEIPT" >&2; exit 6; }

APK_SHA="$(sha256sum "$APK" | awk '{print $1}')"
APK_BYTES="$(stat -c '%s' "$APK")"
NEW_SIGNER="$(apksigner verify --print-certs "$APK" | sed -nE 's/^.*certificate SHA-256 digest:[[:space:]]*//p' | head -1)"
[ -n "$NEW_SIGNER" ] || { echo 'BLOCKED: new APK signer digest missing.' >&2; exit 7; }

PRIOR_STATE="$($RISH_BIN -c "content query --uri content://com.homecenter.operatoroverlay.state/state" 2>&1 || true)"
PRIOR_VERSION="$($RISH_BIN -c "dumpsys package $PACKAGE 2>/dev/null | grep -E 'versionName=|versionCode=' | head -4" 2>&1 || true)"
PRIOR_BASE_PATH="$($RISH_BIN -c "pm path $PACKAGE 2>/dev/null | sed -n 's/^package://p' | head -1" 2>&1 || true)"
PRIOR_SIGNER=""
if [ -n "$PRIOR_BASE_PATH" ]; then
  PRIOR_APK="$STATE_ROOT/installed-overlay-before.apk"
  if "$RISH_BIN" -c "cat '$PRIOR_BASE_PATH'" > "$PRIOR_APK" 2>/dev/null && [ -s "$PRIOR_APK" ]; then
    PRIOR_SIGNER="$(apksigner verify --print-certs "$PRIOR_APK" 2>/dev/null | sed -nE 's/^.*certificate SHA-256 digest:[[:space:]]*//p' | head -1 || true)"
  fi
fi

cat "$APK" | "$RISH_BIN" -c "cat > '$STAGED_APK'; chmod 644 '$STAGED_APK'"
STAGED_SHA="$($RISH_BIN -c "sha256sum '$STAGED_APK'" 2>&1 | grep -Eo '[0-9a-f]{64}' | tail -1)"
[ "$STAGED_SHA" = "$APK_SHA" ] || { echo 'BLOCKED: staged APK SHA-256 mismatch.' >&2; exit 8; }

set +e
INSTALL_OUTPUT="$($RISH_BIN -c "pm install -r '$STAGED_APK'" 2>&1)"
INSTALL_RC=$?
set -e
REPLACED_PACKAGE=false
if [ "$INSTALL_RC" -ne 0 ] || ! printf '%s\n' "$INSTALL_OUTPUT" | grep -q 'Success'; then
  if printf '%s\n' "$INSTALL_OUTPUT" | grep -Eqi 'UPDATE_INCOMPATIBLE|signatures do not match|incompatible'; then
    REPLACED_PACKAGE=true
    $RISH_BIN -c "am force-stop $PACKAGE 2>/dev/null || true; pm uninstall $PACKAGE" > "$STATE_ROOT/uninstall.txt" 2>&1
    INSTALL_OUTPUT="$($RISH_BIN -c "pm install '$STAGED_APK'" 2>&1)"
    printf '%s\n' "$INSTALL_OUTPUT" | grep -q 'Success' || { echo 'BLOCKED: package-only replacement install failed.' >&2; exit 9; }
  else
    printf '%s\n' "$INSTALL_OUTPUT" >&2
    echo 'BLOCKED: Android package installation failed outside the signer-replacement contract.' >&2
    exit 10
  fi
fi
printf '%s\n' "$INSTALL_OUTPUT" > "$STATE_ROOT/install.txt"

$RISH_BIN -c "appops set $PACKAGE SYSTEM_ALERT_WINDOW allow"
$RISH_BIN -c "pm grant $PACKAGE android.permission.POST_NOTIFICATIONS 2>/dev/null || true"
$RISH_BIN -c "am force-stop $PACKAGE; am start-foreground-service -n $PACKAGE/.OperatorOverlayService >/dev/null 2>&1 || am start -n $PACKAGE/.MainActivity >/dev/null"
sleep 2
$RISH_BIN -c "rm -f '$STAGED_APK'" >/dev/null 2>&1 || true

INSTALLED_VERSION="$($RISH_BIN -c "dumpsys package $PACKAGE 2>/dev/null | grep -E 'versionName=|versionCode=' | head -4" 2>&1)"
INSTALLED_STATE="$($RISH_BIN -c "content query --uri content://com.homecenter.operatoroverlay.state/state" 2>&1)"
INSTALLED_BASE_PATH="$($RISH_BIN -c "pm path $PACKAGE 2>/dev/null | sed -n 's/^package://p' | head -1" 2>&1)"
[ -n "$INSTALLED_BASE_PATH" ] || { echo 'BLOCKED: installed overlay package path missing.' >&2; exit 11; }
INSTALLED_APK="$STATE_ROOT/installed-overlay-after.apk"
$RISH_BIN -c "cat '$INSTALLED_BASE_PATH'" > "$INSTALLED_APK"
INSTALLED_SIGNER="$(apksigner verify --print-certs "$INSTALLED_APK" | sed -nE 's/^.*certificate SHA-256 digest:[[:space:]]*//p' | head -1)"
[ "$INSTALLED_SIGNER" = "$NEW_SIGNER" ] || { echo 'BLOCKED: installed APK signer does not match built APK.' >&2; exit 12; }
printf '%s\n' "$INSTALLED_VERSION" | grep -q 'versionName=1.3.0' || { echo 'BLOCKED: installed overlay versionName is not 1.3.0.' >&2; exit 13; }
printf '%s\n' "$INSTALLED_VERSION" | grep -Eq 'versionCode=5([[:space:]]|$)' || { echo 'BLOCKED: installed overlay versionCode is not 5.' >&2; exit 14; }
printf '%s\n' "$INSTALLED_STATE" | grep -q 'adam_request_mode=' || { echo 'BLOCKED: installed overlay Adam provider state is unreadable.' >&2; exit 15; }

RADIO_INSTALL_JSON="$(bash "$ROOT/tools/setup_spotify_radio.sh")"
RADIO_DOCTOR_JSON="$("$HOME/bin/fortress-radio" doctor)"
"$HOME/bin/fortress-radio" configure \
  --playlist-name 'Fortress Radio — Rolling Forge' \
  --seed-query 'Battles Alpine Universe' > "$STATE_ROOT/radio-configure.json"

HC_REPO_ROOT="$ROOT" bash "$ROOT/tools/setup_vlad_swarm_daemon.sh" restart > "$STATE_ROOT/adam-daemon-install.json"

python - "$DEPLOY_RECEIPT" "$SOURCE_COMMIT" "$SOURCE_BRANCH" "$APK_SHA" "$APK_BYTES" "$NEW_SIGNER" "$PRIOR_SIGNER" "$REPLACED_PACKAGE" "$PRIOR_VERSION" "$PRIOR_STATE" "$INSTALLED_VERSION" "$INSTALLED_STATE" "$RADIO_INSTALL_JSON" "$RADIO_DOCTOR_JSON" <<'PY'
import json,os,sys,time
(
 path,source,branch,apk_sha,apk_bytes,new_signer,prior_signer,replaced,
 prior_version,prior_state,installed_version,installed_state,radio_install_json,
 radio_doctor_json,
)=sys.argv[1:]
radio_install=json.loads(radio_install_json)
radio_doctor=json.loads(radio_doctor_json)
obj={
  'schema':'home-center.spotify-overlay-radio.deploy.v1',
  'ok':radio_install.get('ok') is True and radio_doctor.get('ok') is True,
  'sourceCommit':source,
  'sourceBranch':branch,
  'package':'com.homecenter.operatoroverlay',
  'apkSha256':apk_sha,
  'apkByteCount':int(apk_bytes),
  'signingCertificateSha256':new_signer,
  'priorSigningCertificateSha256':prior_signer,
  'packageOnlyReplacement':replaced=='true',
  'priorVersionRaw':prior_version[-2000:],
  'priorStateRaw':prior_state[-3000:],
  'installedVersionRaw':installed_version[-2000:],
  'installedStateRaw':installed_state[-3000:],
  'radioInstall':radio_install,
  'radioDoctor':radio_doctor,
  'visibleLocalEnableStillAuthoritative':True,
  'remoteEnableUsed':False,
  'operatorActionRequired':('control_enabled=0' in installed_state),
  'deployedAtEpoch':int(time.time()),
}
os.makedirs(os.path.dirname(path),exist_ok=True)
tmp=path+'.tmp'
open(tmp,'w',encoding='utf-8').write(json.dumps(obj,indent=2,sort_keys=True)+'\n')
os.replace(tmp,path)
print(json.dumps(obj,ensure_ascii=False,sort_keys=True))
PY
