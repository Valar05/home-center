#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
APP="$ROOT/android/operator-overlay/app"
SRC="$APP/src/main/java"
MANIFEST="$APP/src/main/AndroidManifest.xml"
OUTDIR="$APP/build/outputs/apk/debug"
WORK="$HOME/.cache/home-center/operator-overlay-termux-build"
PLATFORM_DIR="$HOME/.cache/home-center/android-platform-35"
ANDROID_JAR="${HC_ANDROID_JAR:-$PLATFORM_DIR/android.jar}"
KEYSTORE="$HOME/.local/state/home-center/adam-overlay-debug.keystore"
APK="$OUTDIR/app-debug.apk"
META_URL="${HC_ANDROID_REPOSITORY_XML:-https://dl.google.com/android/repository/repository2-1.xml}"

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
    # Deduplicate package names without assuming associative arrays on every shell build.
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
}

ensure_android_jar() {
  [ -s "$ANDROID_JAR" ] && return 0
  echo '[build] Resolving platforms;android-35 from Google SDK repository metadata'
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
}

ensure_keystore() {
  [ -s "$KEYSTORE" ] && return 0
  keytool -genkeypair -noprompt -keystore "$KEYSTORE" -storepass android -keypass android \
    -alias androiddebugkey -dname 'CN=Android Debug,O=Home Center,C=US' -keyalg RSA -keysize 2048 -validity 10000
}

install_termux_tools
ensure_android_jar
ensure_keystore

rm -rf "$WORK/classes" "$WORK/dex" "$WORK/package" "$WORK/base-unsigned.apk" "$WORK/base-signed.apk"
mkdir -p "$WORK/classes" "$WORK/dex" "$WORK/package"

# This project intentionally uses framework resources only, so there is no app res/ tree to compile.
echo '[build] Packaging manifest/resources table'
aapt2 link -o "$WORK/base-unsigned.apk" -I "$ANDROID_JAR" --manifest "$MANIFEST" --min-sdk-version 26 --target-sdk-version 35 --version-code 3 --version-name 1.2.0

echo '[build] Compiling Java against API 35 framework'
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
echo "TERMUX OVERLAY APK BUILT apk=$APK androidJar=$ANDROID_JAR"
