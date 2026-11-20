#!/data/data/com.termux/files/usr/bin/bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
SELF="$ROOT/tools/campaigns/ritsu_asmr_studio_android.sh"
STATE="$HOME/.local/state/ritsu-studio"
CACHE="$HOME/.cache/ritsu-studio"
PIN=d550a598a34a232ac58155f0c91e1016fd15392a
REPO=https://github.com/Valar05/ritsu-asmr.git
APK="$HOME/storage/downloads/RitsuASMRStudio-debug.apk"
JAR="$HOME/.cache/home-center/android-platform-35/android.jar"
FRAMEWORK="$HOME/.cache/home-center/operator-overlay-termux-build/framework-res.apk"
mkdir -p "$STATE" "$CACHE"
record(){
 python3 - "$STATE/receipt.json" "$1" "$2" "$PIN" "$APK" <<'PY'
import json,os,sys,datetime
p,phase,info,pin,apk=sys.argv[1:]
x={"campaign":"RITSU_STUDIO_ANDROID_V1","phase":phase,"message":info,
   "sourceCommit":pin,"apkPath":apk,"updatedUtc":datetime.datetime.now(datetime.timezone.utc).isoformat()}
if os.path.isfile(apk):
 import hashlib
 h=hashlib.sha256()
 with open(apk,'rb') as f:
  for chunk in iter(lambda:f.read(65536),b''):h.update(chunk)
 x["apkSha256"]=h.hexdigest();x["bytes"]=os.stat(apk).st_size
tmp=p+'.tmp'
with open(tmp,'w') as f:json.dump(x,f,sort_keys=True);f.flush();os.fsync(f.fileno())
os.replace(tmp,p)
PY
}
alive(){
 [ -f "$STATE/pid" ] && kill -0 "$(cat "$STATE/pid")" 2>/dev/null
}
status(){
 [ -f "$STATE/receipt.json" ] && cat "$STATE/receipt.json" || echo PHASE=not_started
 alive && echo "WORKER=ACTIVE PID=$(cat "$STATE/pid")" || echo WORKER=NOT_CONFIRMED
 echo "LOG=$STATE/build.log"
}
doctor(){
 for cmd in python3 git tar javac keytool aapt2 d8 apksigner zip unzip sha256sum; do
  command -v "$cmd" >/dev/null || { echo "BLOCKED_TOOL_MISSING=$cmd";return 20; }
 done
 [ -s "$JAR" ] || { echo "BLOCKED_ANDROID_API35_JAR_MISSING=$JAR";return 21; }
 unzip -tqq "$JAR" || return 22
 if [ ! -s "$FRAMEWORK" ];then
  [ -x "$HOME/bin/rish" ] || { echo 'BLOCKED_FRAMEWORK_RESOURCE_MISSING';return 23; }
  mkdir -p "$(dirname "$FRAMEWORK")"
  "$HOME/bin/rish" -c 'cat /system/framework/framework-res.apk' > "$FRAMEWORK.incoming"
  unzip -tqq "$FRAMEWORK.incoming" || return 24
  mv "$FRAMEWORK.incoming" "$FRAMEWORK"
 fi
 echo DOCTOR=PASS
}
build(){
 doctor
 local repo="$CACHE/source-repo" work="$CACHE/work"
 if [ ! -d "$repo/.git" ];then mkdir -p "$repo";git -C "$repo" init -q;fi
 GIT_TERMINAL_PROMPT=0 git -C "$repo" fetch --no-tags "$REPO" "$PIN"
 git -C "$repo" cat-file -e "$PIN^{commit}"
 mkdir -p "$work"
 rm -rf "$work/stage" "$work/classes" "$work/dex"
 mkdir -p "$work/stage" "$work/classes" "$work/dex"
 git -C "$repo" archive "$PIN" android/asmr-studio | tar -x -C "$work/stage"
 local source="$work/stage/android/asmr-studio/app/src/main"
 local manifest="$work/AndroidManifest.xml"
 python3 - "$source/AndroidManifest.xml" "$manifest" <<'PY'
import sys
s=open(sys.argv[1],encoding='utf8').read().replace('<manifest ', '<manifest package="com.valar05.ritsuasmr" ',1)
open(sys.argv[2],'w',encoding='utf8').write(s)
PY
 record compiling "Private pinned source fetched"
 aapt2 link -o "$work/unsigned.apk" -I "$FRAMEWORK" --manifest "$manifest" --min-sdk-version 26 --target-sdk-version 35 --version-code 1 --version-name 0.1.0
 find "$source/java" -name '*.java' -print0 | xargs -0 javac --release 17 -classpath "$JAR" -d "$work/classes"
 find "$work/classes" -name '*.class' -print0 | xargs -0 d8 --lib "$JAR" --min-api 26 --output "$work/dex"
 cp "$work/unsigned.apk" "$work/stage.apk"
 (cd "$work/dex" && zip -q -u "$work/stage.apk" classes.dex)
 local key="$STATE/debug.keystore"
 if [ ! -s "$key" ];then
  keytool -genkeypair -noprompt -keystore "$key" -storepass android -keypass android -alias androiddebugkey -dname 'CN=Ritsu Studio,O=Valar05,C=US' -keyalg RSA -keysize 2048 -validity 10000
 fi
 apksigner sign --ks "$key" --ks-key-alias androiddebugkey --ks-pass pass:android --key-pass pass:android --out "$work/signed.apk" "$work/stage.apk"
 apksigner verify "$work/signed.apk"
 if [ -e "$APK" ];then
  cmp -s "$work/signed.apk" "$APK" || { echo 'BLOCKED_EXISTING_APK_DIFFERENT';return 30; }
 else cp "$work/signed.apk" "$APK";fi
 record built_not_installed "APK SHA-256 verified on phone; install requires user acceptance"
 echo "APK=$APK"
 sha256sum "$APK"
}
case "$1" in
 doctor)doctor;;
 status|receipts)status;;
 follow)tail -n 100 -f "$STATE/build.log";;
 build|resume)
  if alive;then status;exit 0;fi
  if [ -f "$STATE/receipt.json" ] && grep -q '"phase": "built_not_installed"' "$STATE/receipt.json";then status;exit 0;fi
  record starting "Detached phone build requested"
  nohup setsid bash "$SELF" work > "$STATE/build.log" 2>&1 < /dev/null &
  echo "$!" > "$STATE/pid"
  echo "BUILD_DISPATCHED=YES PID=$(cat "$STATE/pid")"
  ;;
 work)
  trap 'code=$?;if [ "$code" -ne 0 ];then record failed "Build exited $code; see log";fi' EXIT
  build
  ;;
 stop)
  if alive;then
    pid="$(cat "$STATE/pid")"
    sid="$(ps -o sid= -p "$pid" | tr -d ' ')"
    [ "$sid" = "$pid" ] || { echo BLOCKED_PROCESS_IDENTITY;exit 31; }
    kill -TERM -- "-$pid"
    sleep 2
    kill -0 "$pid" 2>/dev/null && kill -KILL -- "-$pid" || true
    record stopped "Operator stopped own isolated build group"
  else echo NO_ACTIVE_WORKER;fi
  ;;
 *)echo "usage: bash $SELF {doctor|build|resume|status|follow|stop|receipts}";exit 2;;
esac
