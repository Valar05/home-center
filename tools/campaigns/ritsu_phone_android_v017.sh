#!/data/data/com.termux/files/usr/bin/bash
# Ritsu v0.17 phone-first, pinned Android-only GitHub source; modes doctor|build|status
set -Eeuo pipefail
umask 077
MODE="$1"
TREE=0c0e30bcfb6908a2835ce87acce63e2869facdb3
ROOT="$HOME/.local/share/ritsu-campaigns/v017-phone"
PROJECT="$ROOT/android/ritsu-control"
APK="$HOME/storage/downloads/Ritsu-Control-v0.17.0-Phone-Local.apk"
mkdir -p "$ROOT/log"
receipt(){ printf 'campaign=ritsu-phone-v017\nsource_tree=%s\nstate=%s\ndetail=%s\napk=%s\n' "$TREE" "$1" "$2" "$APK" > "$ROOT/receipt.tmp"; mv "$ROOT/receipt.tmp" "$ROOT/receipt"; }
fail(){ echo "CAMPAIGN=FAIL REASON=$*"; receipt FAIL "$*"; exit 1; }
has(){ command -v "$1" >/dev/null 2>&1; }
case "$MODE" in status) cat "$ROOT/receipt" 2>/dev/null || echo 'STATUS=unstarted'; exit 0;; doctor|build) ;; *) fail 'usage: doctor|build|status';; esac
echo "CAMPAIGN=ritsu-phone-v017 MODE=$MODE ARCH=$(uname -m)"
echo "DISK_FREE_KB=$(df -Pk "$HOME" | awk 'END{print $4}')"
for tool in gh git curl java javac aapt2 apksigner unzip; do
 if has "$tool"; then echo "PRESENT=$tool"; else echo "MISSING=$tool"; fi
done
if [ "$MODE" = doctor ]; then receipt INVENTORY complete; exit 0; fi
[ "$(uname -m)" = aarch64 ] || fail 'Requires Termux ARM64'
[ "$(df -Pk "$HOME" | awk 'END{print $4}')" -ge 2500000 ] || fail 'Need 2.5GB free'
has pkg || fail 'Termux pkg manager missing'
needed=''
has gh || needed="$needed gh"
has git || needed="$needed git"
has curl || needed="$needed curl"
has unzip || needed="$needed unzip"
has aapt2 || needed="$needed aapt2"
has apksigner || needed="$needed apksigner"
has javac || needed="$needed openjdk-17"
if [ -n "$needed" ]; then pkg install -y $needed > "$ROOT/log/pkg.log" 2>&1 || fail 'Termux package bootstrap failed'; fi
for tool in gh git curl unzip java javac aapt2 apksigner; do has "$tool" || fail "Missing $tool"; done
if ! gh auth status >/dev/null 2>&1; then
 echo 'GITHUB_LOGIN=owner_browser_required_once'
 gh auth login -h github.com -p https --web || fail 'GitHub auth incomplete'
fi
fetch(){
 hash="$1"; target="$2"
 mkdir -p "$(dirname "$target")"
 if test -f "$target" && test "$(git hash-object "$target")" = "$hash"; then return; fi
 gh api "repos/Valar05/home-center/git/blobs/$hash" --jq .content |
   base64 -d > "$target.part" || fail "GitHub blob fetch failed: $target"
 [ "$(git hash-object "$target.part")" = "$hash" ] || fail 'GitHub source SHA mismatch'
 mv "$target.part" "$target"
}
fetch 5b7ccba7c566afb5057eaea1b10b99b083851fe4 "$PROJECT/build.gradle"
fetch 72e86cba1e17acab412ae145f0c90a1971020b56 "$PROJECT/settings.gradle"
gh api "repos/Valar05/home-center/git/trees/$TREE" \
  --jq '.tree[] | select(.type=="blob") | [.sha,.path] | @tsv' > "$ROOT/tree.tsv" ||
  fail 'Pinned source tree unavailable'
count=0
while IFS="$(printf '\t')" read -r hash relative; do
 [ -n "$hash" ] || continue
 case "$relative" in /*|*..*) fail 'Source path invalid';; esac
 fetch "$hash" "$PROJECT/app/$relative"
 count=$((count+1))
done < "$ROOT/tree.tsv"
[ "$count" -ge 30 ] || fail 'Android source tree incomplete'
receipt SOURCE_VERIFIED "$count authenticated hash-checked files"
echo "SOURCES=PASS COUNT=$count"
if [ -n "${ANDROID_HOME:-}" ] && [ -f "$ANDROID_HOME/platforms/android-35/android.jar" ]; then
  echo "SDK_REUSE=$ANDROID_HOME"
elif [ -f "$HOME/android-sdk/platforms/android-35/android.jar" ]; then
  ANDROID_HOME="$HOME/android-sdk"
elif [ -f "$PREFIX/opt/android-sdk/platforms/android-35/android.jar" ]; then
  ANDROID_HOME="$PREFIX/opt/android-sdk"
else
  ANDROID_HOME="$HOME/android-sdk"
fi
export ANDROID_HOME ANDROID_SDK_ROOT="$ANDROID_HOME"
manager="$ANDROID_HOME/cmdline-tools/latest/bin/sdkmanager"
if [ ! -f "$manager" ] && has sdkmanager; then
  manager="$(command -v sdkmanager)"
fi
if [ ! -f "$ANDROID_HOME/platforms/android-35/android.jar" ]; then
 if [ ! -f "$manager" ]; then
  curl -fLsS --retry 2 --max-time 360 https://dl.google.com/android/repository/commandlinetools-linux-11076708_latest.zip -o "$ROOT/tools.zip" || fail 'Official SDK tools download failed'
  mkdir -p "$ANDROID_HOME/cmdline-tools/staging" "$ANDROID_HOME/cmdline-tools/latest"
  unzip -qo "$ROOT/tools.zip" -d "$ANDROID_HOME/cmdline-tools/staging" || fail 'SDK zip invalid'
  cp -R "$ANDROID_HOME/cmdline-tools/staging/cmdline-tools/." "$ANDROID_HOME/cmdline-tools/latest/" || fail 'SDK layout failed'
  rm -f "$ROOT/tools.zip"
 fi
 (yes || true) | bash "$manager" --sdk_root="$ANDROID_HOME" 'platforms;android-35' 'build-tools;35.0.0' > "$ROOT/log/sdk.log" 2>&1 || fail 'SDK 35 bootstrap failed'
fi
[ -f "$ANDROID_HOME/platforms/android-35/android.jar" ] || fail 'SDK35 missing'
GRADLE="$HOME/.local/share/ritsu-toolchains/gradle-8.11.1/bin/gradle"
if has gradle && gradle --version 2>/dev/null | grep -q '^Gradle 8.11.1$'; then
  GRADLE="$(command -v gradle)"
  echo "GRADLE_REUSE=$GRADLE"
fi
if [ ! -f "$GRADLE" ]; then
 toolroot="$HOME/.local/share/ritsu-toolchains"; mkdir -p "$toolroot"
 curl -fLsS --retry 2 https://services.gradle.org/distributions/gradle-8.11.1-bin.zip -o "$toolroot/gradle.zip" || fail 'Gradle download failed'
 curl -fLsS --retry 2 https://services.gradle.org/distributions/gradle-8.11.1-bin.zip.sha256 -o "$toolroot/gradle.sha256" || fail 'Gradle checksum missing'
 [ "$(sha256sum "$toolroot/gradle.zip" | awk '{print $1}')" = "$(tr -d ' \r\n' < "$toolroot/gradle.sha256")" ] || fail 'Gradle SHA mismatch'
 unzip -qo "$toolroot/gradle.zip" -d "$toolroot" || fail 'Gradle unzip failed'
 rm -f "$toolroot/gradle.zip" "$toolroot/gradle.sha256"
fi
native="$(command -v aapt2)"
"$native" version > "$ROOT/log/aapt2.log" 2>&1 || fail 'Native AAPT2 unusable'
export JAVA_HOME="$(dirname "$(dirname "$(readlink -f "$(command -v java)")")")"
printf 'sdk.dir=%s\n' "$ANDROID_HOME" > "$PROJECT/local.properties"
receipt BUILDING 'Gradle tests + APK'
bash "$GRADLE" -p "$PROJECT" :app:testDebugUnitTest :app:assembleDebug -PritsuPhoneInstall=true "-Pandroid.aapt2FromMavenOverride=$native" --no-daemon --max-workers=2 > "$ROOT/log/gradle.log" 2>&1 ||
 { tail -n 40 "$ROOT/log/gradle.log"; fail 'Gradle failed'; }
file="$PROJECT/app/build/outputs/apk/debug/app-debug.apk"
[ -f "$file" ] || fail 'APK absent'
mkdir -p "$(dirname "$APK")"
cp -f "$file" "$APK" || fail 'Downloads storage unavailable'
apksigner verify "$APK" > "$ROOT/log/signature.log" 2>&1 || fail 'APK signature invalid'
receipt BUILD_PASS 'com.homecenter.ritsucontrol.phone'
echo "APK_BUILD_PASS=$APK"
echo "SHA256=$(sha256sum "$APK" | awk '{print $1}')"
