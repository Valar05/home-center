#!/data/data/com.termux/files/usr/bin/bash
set -Eeuo pipefail

# VANGUARD // OVERLAY RESURRECTION — ONE-SHOT PHONE BODY
# Mission: build + signer-safe install + visibly launch the current Pocket overlay,
# then leave durable local/shared receipts. This is the recovery boundary after
# unattended Home Center ingress bodies are unavailable. It is intentionally one run.

BRANCH="campaign/vanguard-overlay-resurrection"
REPO_SLUG="Valar05/home-center"
PKG="com.homecenter.operatoroverlay"
ACTIVITY="$PKG/.MainActivity"
STATE="${HC_VANGUARD_ONE_SHOT_STATE:-$HOME/.local/state/home-center/vanguard-overlay-one-shot}"
SRC="$STATE/source"
BUILD="$STATE/build"
LOG="$STATE/run.log"
RECEIPT="$STATE/receipt.json"
SHARED="/storage/emulated/0/Download"
APK_SHARED="$SHARED/HomeCenter-Vanguard-Pocket.apk"
RECEIPT_SHARED="$SHARED/HomeCenter-Vanguard-Pocket.receipt.json"
PREVIOUS_APK="$SHARED/HomeCenter-Operator-previous.apk"
mkdir -p "$STATE" "$BUILD" "$SHARED"
: > "$LOG"
exec > >(tee -a "$LOG") 2>&1

step(){ printf '\n[VANGUARD] %s\n' "$*"; }
notice(){ command -v termux-notification >/dev/null 2>&1 && termux-notification --id 6767351 --title 'Vanguard overlay recovery' --content "$*" >/dev/null 2>&1 || true; }
json_escape(){ python3 -c 'import json,sys; print(json.dumps(sys.argv[1]))' "$1"; }

SOURCE_HEAD=""
APK_SHA=""
APK_CERT=""
INSTALLED_VERSION=""
OVERLAY_STATE=""
SHIZUKU_OK=false
REPLACED_MISMATCH=false
SOURCE_CONTRACT=false
BUILD_OK=false
INSTALL_OK=false
LAUNCH_OK=false
QUEUE_DAEMON=false
BLOCKER=""

write_receipt(){
  local ok="$1"
  python3 - "$RECEIPT" "$ok" "$SOURCE_HEAD" "$APK_SHARED" "$APK_SHA" "$APK_CERT" "$INSTALLED_VERSION" "$OVERLAY_STATE" "$SHIZUKU_OK" "$REPLACED_MISMATCH" "$SOURCE_CONTRACT" "$BUILD_OK" "$INSTALL_OK" "$LAUNCH_OK" "$QUEUE_DAEMON" "$BLOCKER" <<'PY'
import json, pathlib, sys, time
(path,ok,head,apk,sha,cert,version,overlay,shizuku,replaced,contract,build,install,launch,queue,blocker)=sys.argv[1:]
b=lambda x: str(x).lower()=="true"
obj={
 "schema":"home-center.vanguard-overlay-one-shot.v1",
 "ok":b(ok),
 "atMs":int(time.time()*1000),
 "sourceHead":head or None,
 "package":"com.homecenter.operatoroverlay",
 "apk":apk,
 "apkSha256":sha or None,
 "signingCertificateSha256":cert or None,
 "installedVersion":version or None,
 "overlayStateReadback":overlay[-8000:] if overlay else None,
 "checks":{
   "sourceContract":b(contract),"build":b(build),"shizuku":b(shizuku),
   "install":b(install),"launch":b(launch),"queueDaemonRecovered":b(queue),
 },
 "replacedSignerMismatchAfterBackup":b(replaced),
 "blocker":blocker or None,
 "truthBoundary":"ok=true means exact fetched source passed its static Pocket contract, produced a signed APK, Android package install succeeded, MainActivity launch returned success, and provider readback was attempted. It does not claim audible Pocket speech or Drew acceptance unless separately observed."
}
pathlib.Path(path).write_text(json.dumps(obj,indent=2,sort_keys=True)+"\n",encoding="utf-8")
print(json.dumps(obj,indent=2,sort_keys=True))
PY
  cp "$RECEIPT" "$RECEIPT_SHARED" 2>/dev/null || true
}

fail(){
  BLOCKER="$1"
  notice "BLOCKED: $BLOCKER"
  write_receipt false || true
  printf '\n[VANGUARD] BLOCKED: %s\n' "$BLOCKER" >&2
  printf '[VANGUARD] Receipt: %s\n' "$RECEIPT_SHARED" >&2
  exit 1
}
trap 'rc=$?; if [ $rc -ne 0 ] && [ ! -s "$RECEIPT" ]; then BLOCKER="unexpected_exit_$rc"; write_receipt false || true; fi' EXIT

for c in git python3 tar sha256sum; do command -v "$c" >/dev/null 2>&1 || fail "missing_required_command:$c"; done

find_repo(){
  local c
  for c in "${HC_REPO_ROOT:-}" "$HOME/home-center" "$HOME/src/home-center" "$HOME/projects/home-center" "/storage/emulated/0/Documents/GodotProjects/home-center"; do
    [ -n "$c" ] || continue
    if [ -d "$c/.git" ] && git -C "$c" remote get-url origin 2>/dev/null | grep -q 'Valar05/home-center'; then printf '%s\n' "$c"; return 0; fi
  done
  return 1
}

step "Recover exact remote source without touching the working tree"
REPO="$(find_repo || true)"
if [ -z "$REPO" ]; then
  command -v gh >/dev/null 2>&1 || fail "home_center_checkout_missing_and_gh_unavailable"
  gh auth status >/dev/null 2>&1 || fail "home_center_checkout_missing_and_gh_not_authenticated"
  rm -rf "$STATE/repo.part"
  GIT_LFS_SKIP_SMUDGE=1 gh repo clone "$REPO_SLUG" "$STATE/repo.part" -- --filter=blob:none || fail "home_center_clone_failed"
  rm -rf "$STATE/repo"
  mv "$STATE/repo.part" "$STATE/repo"
  REPO="$STATE/repo"
fi

GIT_LFS_SKIP_SMUDGE=1 GIT_TERMINAL_PROMPT=0 git -C "$REPO" fetch --prune origin \
  "+refs/heads/$BRANCH:refs/remotes/origin/$BRANCH" \
  "+refs/heads/generated/operator-overlay-apk:refs/remotes/origin/generated/operator-overlay-apk" \
  || fail "remote_fetch_failed"
SOURCE_HEAD="$(git -C "$REPO" rev-parse "origin/$BRANCH")"
[ -n "$SOURCE_HEAD" ] || fail "campaign_head_missing"
rm -rf "$SRC.part" "$SRC"
mkdir -p "$SRC.part"
git -C "$REPO" archive "$SOURCE_HEAD" \
  android/operator-overlay \
  tools/vanguard_pocket_overlay_contract_test.py \
  tools/android_phone_home_center_relay.py \
  tools/operator_overlay_pocket_speech.py \
  campaigns/vanguard-overlay-resurrection/POCKET_TTS_KEEP_ADDENDUM.md \
  | tar -xf - -C "$SRC.part" || fail "source_materialization_failed"
mv "$SRC.part" "$SRC"

step "Run exact Pocket overlay source contract"
python3 "$SRC/tools/vanguard_pocket_overlay_contract_test.py" || fail "pocket_overlay_source_contract_failed"
SOURCE_CONTRACT=true

step "Locate the existing phone Android build body"
GRADLE_BIN="${GRADLE_BIN:-}"
if [ -z "$GRADLE_BIN" ]; then
  for g in \
    "$PREFIX/tmp/gradle-8.14.3/gradle-8.14.3/bin/gradle" \
    "$PREFIX/opt/gradle/bin/gradle" \
    "$HOME/.gradle/bin/gradle"; do
    [ -x "$g" ] && { GRADLE_BIN="$g"; break; }
  done
fi
[ -n "$GRADLE_BIN" ] || GRADLE_BIN="$(command -v gradle || true)"
[ -n "$GRADLE_BIN" ] && [ -x "$GRADLE_BIN" ] || fail "gradle_missing_on_phone"

AAPT_ARG=()
if [ -x "${PREFIX:-}/bin/aapt2" ]; then AAPT_ARG=(-Pandroid.aapt2FromMavenOverride="$PREFIX/bin/aapt2"); fi

step "Install the durable Home Center signer into the isolated build only"
KEY="$STATE/operator-overlay-debug.keystore"
git -C "$REPO" show "origin/generated/operator-overlay-apk:operator-overlay-debug.keystore" > "$KEY" || fail "durable_signer_recovery_failed"
[ -s "$KEY" ] || fail "durable_signer_empty"
# Do not mutate Drew's ~/.android/debug.keystore. Add a second Gradle android{} closure
# only inside the isolated source copy and bind debug to the recovered durable key.
cat >> "$SRC/android/operator-overlay/app/build.gradle" <<EOF_SIGN

android {
    signingConfigs {
        vanguardDurable {
            storeFile file('${KEY}')
            storePassword 'android'
            keyAlias 'androiddebugkey'
            keyPassword 'android'
        }
    }
    buildTypes {
        debug {
            signingConfig signingConfigs.vanguardDurable
        }
    }
}
EOF_SIGN

step "Build current Pocket overlay"
rm -rf "$BUILD" && mkdir -p "$BUILD"
(
  cd "$SRC/android/operator-overlay"
  "$GRADLE_BIN" :app:testDebugUnitTest :app:assembleDebug --no-daemon --console=plain "${AAPT_ARG[@]}"
) || fail "android_build_failed"
APK="$SRC/android/operator-overlay/app/build/outputs/apk/debug/app-debug.apk"
[ -s "$APK" ] || fail "android_apk_missing_after_build"
cp "$APK" "$APK_SHARED"
APK_SHA="$(sha256sum "$APK_SHARED" | awk '{print $1}')"
BUILD_OK=true

APKSIGNER="$(command -v apksigner || true)"
if [ -z "$APKSIGNER" ]; then
  SDK="${ANDROID_SDK_ROOT:-${ANDROID_HOME:-}}"
  if [ -n "$SDK" ] && [ -d "$SDK/build-tools" ]; then APKSIGNER="$(find "$SDK/build-tools" -type f -name apksigner 2>/dev/null | sort | tail -1)"; fi
fi
if [ -n "$APKSIGNER" ]; then
  APK_CERT="$("$APKSIGNER" verify --print-certs "$APK_SHARED" 2>/dev/null | sed -n 's/.*certificate SHA-256 digest: *//p' | head -1 | tr 'A-F' 'a-f' | tr -d ':\r')"
fi
if command -v keytool >/dev/null 2>&1; then
  KEY_CERT="$(keytool -list -v -keystore "$KEY" -storepass android -alias androiddebugkey 2>/dev/null | sed -n 's/.*SHA256: *//p' | head -1 | tr 'A-F' 'a-f' | tr -d ':\r')"
  if [ -n "$APK_CERT" ] && [ -n "$KEY_CERT" ] && [ "$APK_CERT" != "$KEY_CERT" ]; then fail "built_apk_signer_does_not_match_durable_key"; fi
fi

find_rish(){
  if command -v rish >/dev/null 2>&1; then command -v rish; return 0; fi
  for r in "$HOME/bin/rish" "$HOME/.local/bin/rish" "$HOME/rish" "/storage/emulated/0/Android/data/moe.shizuku.privileged.api/files/rish"; do [ -f "$r" ] && { printf '%s\n' "$r"; return 0; }; done
  return 1
}
RISH_BIN="$(find_rish || true)"
[ -n "$RISH_BIN" ] || fail "rish_missing"
chmod +x "$RISH_BIN" 2>/dev/null || true
rish(){ "$RISH_BIN" -c "$1"; }

shizuku_probe(){ rish 'id >/dev/null 2>&1; pm path moe.shizuku.privileged.api >/dev/null 2>&1' >/dev/null 2>&1; }

step "Recover Shizuku if possible before involving Drew"
if shizuku_probe; then
  SHIZUKU_OK=true
else
  # First try the already-observed local wireless-debugging edge without pairing or guessing credentials.
  if command -v adb >/dev/null 2>&1; then
    adb disconnect 127.0.0.1:37473 >/dev/null 2>&1 || true
    adb connect 127.0.0.1:37473 >/dev/null 2>&1 || true
    adb -s 127.0.0.1:37473 shell sh /sdcard/Android/data/moe.shizuku.privileged.api/start.sh >/dev/null 2>&1 || true
    sleep 2
  fi
  if shizuku_probe; then
    SHIZUKU_OK=true
  else
    notice 'One Android action: open Shizuku and tap Start. Vanguard is waiting; do NOT rerun anything.'
    printf '\n[VANGUARD] WAITING FOR ONE ANDROID ACTION — open Shizuku and tap Start.\n'
    printf '[VANGUARD] Do not type another command. This process will resume by itself.\n'
    for _ in $(seq 1 150); do
      if shizuku_probe; then SHIZUKU_OK=true; break; fi
      sleep 2
    done
  fi
fi
[ "$SHIZUKU_OK" = true ] || fail "shizuku_not_running_after_5_minute_wait"

step "Install current overlay; predict and repair signer mismatch"
INSTALL_OUT="$(rish "pm install -r -d '$APK_SHARED'" 2>&1 || true)"
if ! printf '%s' "$INSTALL_OUT" | grep -qi 'Success'; then
  if printf '%s' "$INSTALL_OUT" | grep -Eqi 'UPDATE_INCOMPATIBLE|signatures do not match|signature'; then
    OLD_PATH="$(rish "pm path $PKG" 2>/dev/null | sed -n 's/^package://p' | head -1 || true)"
    if [ -n "$OLD_PATH" ]; then rish "cp '$OLD_PATH' '$PREVIOUS_APK' 2>/dev/null || true" >/dev/null 2>&1 || true; fi
    rish "pm uninstall $PKG" >/dev/null 2>&1 || fail "old_overlay_signer_mismatch_and_uninstall_failed"
    REPLACED_MISMATCH=true
    INSTALL_OUT="$(rish "pm install '$APK_SHARED'" 2>&1 || true)"
  fi
fi
printf '%s\n' "$INSTALL_OUT"
printf '%s' "$INSTALL_OUT" | grep -qi 'Success' || fail "overlay_install_failed:$(printf '%s' "$INSTALL_OUT" | tail -1)"
INSTALL_OK=true

step "Restore overlay permissions and launch the service directly"
rish "pm enable --user 0 $PKG 2>/dev/null || true; appops set $PKG SYSTEM_ALERT_WINDOW allow; pm grant $PKG android.permission.POST_NOTIFICATIONS 2>/dev/null || true; pm grant $PKG android.permission.RECORD_AUDIO 2>/dev/null || true" >/dev/null 2>&1 || true
# Prefer direct service restore from shell authority so recovery does not needlessly
# throw the legacy MediaProjection consent sheet over the user's screen.
LAUNCH_OUT="$(rish "am start-foreground-service -n $PKG/.OperatorOverlayService -a com.homecenter.operatoroverlay.RESTORE" 2>&1 || true)"
printf '%s\n' "$LAUNCH_OUT"
if printf '%s' "$LAUNCH_OUT" | grep -Eqi 'Error|Exception|does not exist|not found'; then
  # MainActivity is the fallback only if Android rejects direct service restore.
  LAUNCH_OUT="$(rish "am start -n $ACTIVITY" 2>&1 || true)"
  printf '%s\n' "$LAUNCH_OUT"
fi
if printf '%s' "$LAUNCH_OUT" | grep -Eqi 'Error|Exception|does not exist|not found'; then fail "overlay_launch_failed:$(printf '%s' "$LAUNCH_OUT" | tail -1)"; fi
LAUNCH_OK=true
sleep 2

OVERLAY_STATE="$(rish "content query --uri content://com.homecenter.operatoroverlay.state/state" 2>&1 || true)"
printf '[VANGUARD] STATE %s\n' "$OVERLAY_STATE"
INSTALLED_VERSION="$(rish "dumpsys package $PKG 2>/dev/null | grep -m1 'versionName=' | cut -d= -f2" 2>/dev/null | tr -d '\r' || true)"

step "Recover future no-terminal queue if the daemon body already exists"
QUEUE_BIN="$HOME/.fortress-device-queue/bin/fortress-queue-daemon"
if [ -x "$QUEUE_BIN" ] && command -v tmux >/dev/null 2>&1; then
  tmux has-session -t fortress-device-queue 2>/dev/null || tmux new-session -d -s fortress-device-queue "$QUEUE_BIN"
  sleep 1
  tmux has-session -t fortress-device-queue 2>/dev/null && QUEUE_DAEMON=true || true
fi

BLOCKER=""
write_receipt true
notice 'Home Center Vanguard Pocket overlay installed and launched.'
printf '\n[VANGUARD] OVERLAY LAUNCHED\n'
printf '[VANGUARD] APK: %s\n' "$APK_SHARED"
printf '[VANGUARD] RECEIPT: %s\n' "$RECEIPT_SHARED"
printf '[VANGUARD] SOURCE: %s\n' "$SOURCE_HEAD"
