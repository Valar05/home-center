#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
APP="$ROOT/android/operator-overlay/app"
SRC="$APP/src/main/java"
MANIFEST="$APP/src/main/AndroidManifest.xml"
GRADLE_CONFIG="$APP/build.gradle"
OUTDIR="$APP/build/outputs/apk/debug"
WORK="$HOME/.cache/home-center/operator-overlay-termux-build"
PLATFORM_DIR="$HOME/.cache/home-center/android-platform-35"
ANDROID_JAR="${HC_ANDROID_JAR:-$PLATFORM_DIR/android.jar}"
FRAMEWORK_RES="${HC_FRAMEWORK_RES_APK:-$WORK/framework-res.apk}"
KEYSTORE="$HOME/.local/state/home-center/adam-overlay-debug.keystore"
APK="$OUTDIR/app-debug.apk"
META_URL="${HC_ANDROID_REPOSITORY_XML:-https://dl.google.com/android/repository/repository2-1.xml}"
PACKAGE_NAME="com.homecenter.operatoroverlay"
RISH_BIN="${RISH:-$(command -v rish 2>/dev/null || true)}"
[ -n "$RISH_BIN" ] || RISH_BIN="$HOME/bin/rish"

VERSION_LINE="$(python - "$GRADLE_CONFIG" <<'PY'
import re,sys
text=open(sys.argv[1],encoding='utf-8').read()
codes=re.findall(r'(?m)^\s*versionCode\s+(\d+)\s*$',text)
names=re.findall(r"(?m)^\s*versionName\s+'([^']+)'\s*$",text)
if len(codes)!=1 or len(names)!=1:
    raise SystemExit('BLOCKED: build.gradle must define exactly one versionCode and versionName')
print(codes[0]+'\t'+names[0])
PY
)"
IFS=$'\t' read -r VERSION_CODE VERSION_NAME <<<"$VERSION_LINE"
[[ "$VERSION_CODE" =~ ^[1-9][0-9]*$ ]] || {
  echo "BLOCKED: invalid versionCode from build.gradle: $VERSION_CODE" >&2
  exit 38
}
[[ "$VERSION_NAME" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || {
  echo "BLOCKED: invalid versionName from build.gradle: $VERSION_NAME" >&2
  exit 39
}

mkdir -p "$OUTDIR" "$WORK" "$PLATFORM_DIR" "$(dirname "$KEYSTORE")"

need_cmd() { command -v "$1" >/dev/null 2>&1; }

install_termux_tools() {
  local packages=()
  need_cmd javac || packages+=(openjdk-17)
  need_cmd keytool || packages+=(openjdk-17)
  need_cmd aapt2 || packages+=(aapt2)
  need_cmd d8 || packages+=(d8)
  need_cmd apksigner || packages+=(apksigner)
  need_cmd zip || packages+=(zip)
  need_cmd unzip || packages+=(unzip)
  need_cmd curl || packages+=(curl)

  if [ ${#packages[@]} -gt 0 ]; then
    local unique=() p seen q
    for p in "${packages[@]}"; do
      seen=0
      for q in "${unique[@]:-}"; do [ "$q" = "$p" ] && seen=1 && break; done
      [ "$seen" -eq 1 ] || unique+=("$p")
    done
    echo "[build] Installing missing Termux packages: ${unique[*]}"
    pkg install -y "${unique[@]}"
  fi

  local missing=()
  for c in javac aapt2 d8 apksigner zip unzip curl keytool; do
    need_cmd "$c" || missing+=("$c")
  done
  [ ${#missing[@]} -eq 0 ] || {
    echo "BLOCKED: required Termux build commands still unavailable after package install: ${missing[*]}" >&2
    echo "Current repositories may not expose the package that provides them; no alternate toolchain was substituted." >&2
    exit 30
  }
  [ -x "$RISH_BIN" ] || { echo 'BLOCKED: rish missing; live Android framework resources cannot be read.' >&2; exit 34; }
}

valid_android_jar() {
  [ -s "$ANDROID_JAR" ] || return 1
  unzip -tqq "$ANDROID_JAR" >/dev/null 2>&1 || return 1
  unzip -l "$ANDROID_JAR" android/Manifest.class 2>/dev/null | grep -q 'android/Manifest.class' || return 1
  return 0
}

ensure_android_jar() {
  if valid_android_jar; then
    return 0
  fi
  if [ -e "$ANDROID_JAR" ]; then
    echo "[build] Cached android.jar is invalid; replacing it: $ANDROID_JAR"
    rm -f "$ANDROID_JAR"
  fi
  echo '[build] Resolving platforms;android-35 class jar from Google SDK repository metadata'
  local xml="$WORK/repository2-1.xml" info="$WORK/platform35.json" zipfile="$WORK/platform35.zip"
  curl -fL --retry 3 --retry-delay 2 "$META_URL" -o "$xml"
  python - "$xml" "$info" <<'PY'
import json,sys,xml.etree.ElementTree as ET
root=ET.parse(sys.argv[1]).getroot()
def local(tag): return tag.rsplit('}',1)[-1]
for pkg in root.iter():
    if local(pkg.tag)!='remotePackage' or pkg.attrib.get('path')!='platforms;android-35':
        continue
    archives=None
    for child in pkg:
        if local(child.tag)=='archives': archives=child; break
    if archives is None: continue
    for archive in archives:
        complete=None
        for child in archive:
            if local(child.tag)=='complete': complete=child; break
        if complete is None: continue
        url=checksum=size=None; ctype='sha1'
        for child in complete:
            name=local(child.tag)
            if name=='url': url=(child.text or '').strip()
            elif name=='checksum':
                checksum=(child.text or '').strip(); ctype=child.attrib.get('type','sha1').lower()
            elif name=='size': size=(child.text or '').strip()
        if url and checksum:
            json.dump({'url':url,'checksum':checksum,'checksumType':ctype,'size':size},open(sys.argv[2],'w'))
            raise SystemExit(0)
raise SystemExit('platforms;android-35 archive not found in repository metadata')
PY
  local rel checksum ctype
  rel="$(python -c 'import json,sys;print(json.load(open(sys.argv[1]))["url"])' "$info")"
  checksum="$(python -c 'import json,sys;print(json.load(open(sys.argv[1]))["checksum"])' "$info")"
  ctype="$(python -c 'import json,sys;print(json.load(open(sys.argv[1]))["checksumType"])' "$info")"
  curl -fL --retry 3 --retry-delay 2 "https://dl.google.com/android/repository/$rel" -o "$zipfile"
  case "$ctype" in
    sha256) printf '%s  %s\n' "$checksum" "$zipfile" | sha256sum -c - ;;
    sha1) printf '%s  %s\n' "$checksum" "$zipfile" | sha1sum -c - ;;
    *) echo "BLOCKED: unsupported Android repository checksum type: $ctype" >&2; exit 31 ;;
  esac
  rm -rf "$PLATFORM_DIR.unpack" && mkdir -p "$PLATFORM_DIR.unpack"
  unzip -q "$zipfile" -d "$PLATFORM_DIR.unpack"
  local found
  found="$(find "$PLATFORM_DIR.unpack" -type f -name android.jar | head -1)"
  [ -s "$found" ] || { echo 'BLOCKED: downloaded Android platform archive has no android.jar' >&2; exit 32; }
  cp "$found" "$ANDROID_JAR"
  valid_android_jar || { echo "BLOCKED: extracted Android platform jar is not a valid API-35 class jar: $ANDROID_JAR" >&2; exit 33; }
}

ensure_framework_resources() {
  echo '[build] Reading live Android framework resource table through Shizuku/rish'
  rm -f "$FRAMEWORK_RES"
  "$RISH_BIN" -c 'cat /system/framework/framework-res.apk' > "$FRAMEWORK_RES"
  [ -s "$FRAMEWORK_RES" ] || { echo 'BLOCKED: framework-res.apk read produced no bytes.' >&2; exit 35; }
  unzip -tqq "$FRAMEWORK_RES" >/dev/null 2>&1 || { echo 'BLOCKED: copied framework-res.apk is not a valid APK/ZIP.' >&2; exit 36; }
  aapt2 dump resources "$FRAMEWORK_RES" >/dev/null 2>&1 || { echo 'BLOCKED: live framework-res.apk has no readable Android resource table.' >&2; exit 37; }
}

ensure_keystore() {
  [ -s "$KEYSTORE" ] && return 0
  keytool -genkeypair -noprompt -keystore "$KEYSTORE" -storepass android -keypass android \
    -alias androiddebugkey -dname 'CN=Android Debug,O=Home Center,C=US' -keyalg RSA -keysize 2048 -validity 10000
}

prepare_manifest() {
  local out="$WORK/AndroidManifest.xml"
  python - "$MANIFEST" "$out" "$PACKAGE_NAME" <<'PY'
import re,sys
src,out,pkg=sys.argv[1:]
text=open(src,encoding='utf-8').read()
if re.search(r'<manifest\b[^>]*\bpackage\s*=', text):
    rendered=text
else:
    rendered=re.sub(r'<manifest\b', f'<manifest package="{pkg}"', text, count=1)
open(out,'w',encoding='utf-8').write(rendered)
PY
  printf '%s\n' "$out"
}

install_termux_tools
ensure_android_jar
ensure_framework_resources
ensure_keystore

rm -rf "$WORK/classes" "$WORK/dex" "$WORK/package" "$WORK/base-unsigned.apk" "$WORK/base-signed.apk"
mkdir -p "$WORK/classes" "$WORK/dex" "$WORK/package"
BUILD_MANIFEST="$(prepare_manifest)"

# AAPT2 consumes the live framework resource table; javac/d8 consume the API-35 SDK class jar.
echo '[build] Packaging manifest/resources table'
aapt2 link -o "$WORK/base-unsigned.apk" -I "$FRAMEWORK_RES" --manifest "$BUILD_MANIFEST" --min-sdk-version 26 --target-sdk-version 35 --version-code "$VERSION_CODE" --version-name "$VERSION_NAME"

echo '[build] Compiling Java against API 35 framework classes'
find "$SRC" -name '*.java' -print0 | xargs -0 javac --release 17 -classpath "$ANDROID_JAR" -d "$WORK/classes"

echo '[build] Dexing classes for minSdk 26'
d8 --lib "$ANDROID_JAR" --min-api 26 --output "$WORK/dex" $(find "$WORK/classes" -name '*.class' -print)

echo '[build] Injecting classes.dex'
cp "$WORK/base-unsigned.apk" "$WORK/base-signed.apk"
(cd "$WORK/dex" && zip -q -u "$WORK/base-signed.apk" classes.dex)

echo '[build] Signing APK'
apksigner sign --ks "$KEYSTORE" --ks-key-alias androiddebugkey --ks-pass pass:android --key-pass pass:android --out "$APK" "$WORK/base-signed.apk"
apksigner verify --verbose "$APK" >/dev/null

sha256sum "$APK"
echo "TERMUX OVERLAY APK BUILT apk=$APK androidJar=$ANDROID_JAR frameworkRes=$FRAMEWORK_RES"
