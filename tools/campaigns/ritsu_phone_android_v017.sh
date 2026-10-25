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
# The GitHub Trees endpoint is NOT recursive by default. The Android app's
# files live beneath src/main and src/test; without recursive=1, this yields
# only build.gradle and silently stops before Gradle. Proven expected 36 blobs.
gh api "repos/Valar05/home-center/git/trees/$TREE?recursive=1" \
  --jq 'if .truncated then error("pinned source tree truncated") else .tree[] | select(.type=="blob") | [.sha,.path] | @tsv end' > "$ROOT/tree.tsv.part" ||
  fail 'Recursive pinned Android source tree unavailable or truncated'
mv "$ROOT/tree.tsv.part" "$ROOT/tree.tsv"
declared="$(wc -l < "$ROOT/tree.tsv" | tr -d ' ')"
[ "$declared" = 36 ] || fail "Pinned Android tree expected 36 files, got $declared"
echo "RECURSIVE_TREE_VERIFIED=36"
count=0
while IFS="$(printf '\t')" read -r hash relative; do
 [ -n "$hash" ] || continue
 case "$relative" in /*|*..*) fail 'Source path invalid';; esac
 fetch "$hash" "$PROJECT/app/$relative"
 count=$((count+1))
done < "$ROOT/tree.tsv"
[ "$count" -eq 36 ] || fail "Source blob fetch incomplete: $count of 36 files"
[ -f "$PROJECT/app/src/main/AndroidManifest.xml" ] || fail 'Android manifest missing'
[ -f "$PROJECT/app/src/main/java/com/homecenter/ritsucontrol/RitsuLocalSync.java" ] || fail 'Direct SSE transport source missing'
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
# Android 35 SDK is required and should NOT be downgraded for an obsolete
# Termux AAPT2. The pre-July-2026 package cannot parse Android 35 resources.
# Termux shipped a fixed native aapt2 in package 16.0.0.4. Smoke-test the
# *actual* framework jar, not merely 'aapt2 version', before any Gradle call.
native="$(command -v aapt2)"
jar="$ANDROID_HOME/platforms/android-35/android.jar"
unzip -tqq "$jar" > "$ROOT/log/android35-jar-integrity.log" 2>&1 ||
 fail 'Android 35 framework JAR is not a valid ZIP; refusing to blame AAPT2'
mkdir -p "$ROOT/aapt2-smoke"
cat > "$ROOT/aapt2-smoke/AndroidManifest.xml" <<'AAPT2_SMOKE_MANIFEST'
<manifest xmlns:android="http://schemas.android.com/apk/res/android"
    package="com.homecenter.ritsucontrol.smoke">
  <uses-sdk android:minSdkVersion="26" android:targetSdkVersion="35"/>
  <application/>
</manifest>
AAPT2_SMOKE_MANIFEST
test_aapt2(){
 "$native" link -o "$ROOT/aapt2-smoke/smoke.apk" -I "$jar" \
    --manifest "$ROOT/aapt2-smoke/AndroidManifest.xml" \
    --min-sdk-version 26 --target-sdk-version 35 \
    > "$ROOT/log/aapt2-link-smoke.log" 2>&1
}
"$native" version > "$ROOT/log/aapt2.log" 2>&1 || fail 'Native AAPT2 cannot execute'
previous="$(dpkg-query -W -f='${Version}' aapt2 2>/dev/null || true)"
echo "AAPT2_INSTALLED_VERSION=$previous"
if test_aapt2; then
 echo 'AAPT2_ANDROID35=PASS existing_toolchain'
else
 echo 'AAPT2_ANDROID35=FAIL older_binary'
 echo 'AAPT2_REPAIR=isolated_signed_upstream_key_and_mirrors'
 # Separate, trusted-key-pinned repository configuration: not the phone-wide APT.
 # Play Store Termux 2026.10 keyring can omit upstream Termux autobuilds.
 # Retrieve the exact upstream signing key from its immutable, published Git blob.
 repair="$ROOT/aapt2-official"
 lists="$repair/lists"
 sources="$repair/official-main.list"
 key="$repair/termux-autobuilds.gpg"
 mkdir -p "$lists/partial" "$repair/unpacked"
 keysha="c5ed76a1b9a1f2bc2e296bdd5ca50cf1f1f12706"
 if [ ! -f "$key" ] || [ "$(git hash-object "$key")" != "$keysha" ]; then
   gh api "repos/termux/termux-packages/git/blobs/$keysha" --jq .content |
     base64 -d > "$key.tmp" || fail "Cannot retrieve pinned official signing key"
   [ "$(git hash-object "$key.tmp")" = "$keysha" ] ||
     fail "Upstream signing key Git blob mismatch"
   mv "$key.tmp" "$key"
 fi
 echo "TERMUX_UPSTREAM_SIGNING_KEY_BLOB=$keysha"
 if command -v gpg >/dev/null 2>&1; then
   gpg --show-keys --with-colons --fingerprint "$key" > "$ROOT/log/upstream-key.txt" 2>&1 ||
     fail "Pinned Termux keyring cannot be parsed"
   grep -q "CC72CF8BA7DBFA0182877D045A897D96E57CF20C" "$ROOT/log/upstream-key.txt" ||
     fail "Official autobuilds signing key fingerprint mismatch"
 fi
 aptargs=(-o "Dir::Etc::sourcelist=$sources" -o "Dir::Etc::sourceparts=-" -o "Dir::State::lists=$lists" -o "APT::Get::List-Cleanup=0")
 # Additional officially listed mirrors; every candidate must pass the same GPG check.
 endpoints=(
   "https://packages.termux.dev/apt/termux-main"
   "https://packages-cf.termux.dev/apt/termux-main"
   "https://mirror.freedif.org/termux/apt/termux-main"
   "https://termux.librehat.com/apt/termux-main"
   "https://mirrors.aliyun.com/termux/termux-main"
 )
 selected=""
 for endpoint in "${endpoints[@]}"; do
   printf "deb [signed-by=%s] %s stable main\n" "$key" "$endpoint" > "$sources"
   echo "AAPT2_APT_TRY=$endpoint"
   if apt-get "${aptargs[@]}" update > "$ROOT/log/aapt2-signed-apt-index.log" 2>&1; then
     selected="$endpoint"
     break
   fi
   echo "AAPT2_APT_UNAVAILABLE=$endpoint"
   tail -n 5 "$ROOT/log/aapt2-signed-apt-index.log" |
     sed 's/^/APT_DIAG: /' || true
 done
 [ -n "$selected" ] ||
   fail "No upstream-signed Termux mirror accessible; inspect $ROOT/log/aapt2-signed-apt-index.log"
 echo "AAPT2_SIGNED_MIRROR=$selected"
 candidate="$(apt-cache "${aptargs[@]}" policy aapt2 | awk '/Candidate:/ {print $2;exit}')"
 echo "AAPT2_UPSTREAM_CANDIDATE=$candidate"
 [ -n "$candidate" ] && [ "$candidate" != "(none)" ] ||
   fail "Signed official mirror offers no AAPT2"
 dpkg --compare-versions "$candidate" ge "16.0.0.4" ||
   fail "Official AAPT2 candidate too old: $candidate"
 (cd "$repair" && apt-get "${aptargs[@]}" download "aapt2=$candidate") > "$ROOT/log/aapt2-signed-download.log" 2>&1 ||
   fail "Verified official AAPT2 .deb fetch failed"
 deb=""
 for entry in "$repair"/aapt2_*_aarch64.deb; do
   [ ! -f "$entry" ] || { deb="$entry"; break; }
 done
 [ -n "$deb" ] || fail "Downloaded AAPT2 ARM64 package missing"
 dpkg-deb -x "$deb" "$repair/unpacked" || fail "Official package extraction failed"
 candidatebin="$(find "$repair/unpacked" -type f -name aapt2 -print -quit)"
 [ -n "$candidatebin" ] && [ -x "$candidatebin" ] ||
   fail "Package does not contain executable ARM64 AAPT2"
 native="$candidatebin"
 echo "AAPT2_ISOLATED_BINARY=$native"
 "$native" version > "$ROOT/log/aapt2.log" 2>&1 ||
   fail "New AAPT2 cannot start; inspect $ROOT/log/aapt2.log for missing libraries"
 test_aapt2 ||
   fail "New AAPT2 cannot link SDK 35; inspect $ROOT/log/aapt2-link-smoke.log"
 echo 'AAPT2_ANDROID35=PASS isolated_signed_official_toolchain'
fi
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
