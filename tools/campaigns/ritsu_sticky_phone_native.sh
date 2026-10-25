#!/data/data/com.termux/files/usr/bin/bash
# One real phone-native Ritsu Sticky APK campaign.
# GitHub cloud checks first; this phone compiles the Java/Android resources itself.
set -Eeuo pipefail
umask 077
SELF="$(realpath "${BASH_SOURCE[0]}")"
REL="tools/campaigns/ritsu_sticky_phone_native.sh"
REPO="$(cd -P "$(dirname "$SELF")/../.." && pwd -P)"
[ "$SELF" = "$REPO/$REL" ] || { echo "FAIL=entrypoint_location";exit 2; }
[ -f "$REPO/AGENTS.md" ] && [ -f "$REPO/android/ritsu-control/app/build.gradle" ] ||
  { echo "FAIL=not_full_Ritsu_repo";exit 2; }
cd "$REPO"
case "$(git remote get-url origin)" in
  https://github.com/Valar05/home-center.git|https://github.com/Valar05/home-center|git@github.com:Valar05/home-center.git) ;;
  *) echo "FAIL=repo_identity";exit 2;;
esac
HEAD="$(git rev-parse HEAD)"
[ "${RITSU_STICKY_PIN:-}" = "$HEAD" ] || { echo "FAIL=unverified_source_pin";exit 2; }
[ "$(git hash-object "$SELF")" = "$(git rev-parse "HEAD:$REL")" ] ||
  { echo "FAIL=running_script_not_committed";exit 2; }
[ -z "$(git status --porcelain=v1 --untracked-files=all)" ] ||
  { echo "FAIL=isolated_source_has_changes_preserve";exit 2; }
printf 'RESOLVED_REPO=%s\nEXECUTION_DIR=%s\nBRANCH=%s\nHEAD=%s\n' "$REPO" "$PWD" "$(git symbolic-ref --quiet --short HEAD || echo detached)" "$HEAD"
MODE="${1:-build}"
case "$MODE" in build|resume) MODE=build;; doctor|status) ;; *) echo "FAIL=unsupported_mode";exit 2;; esac
ROOT="$HOME/.local/share/ritsu-campaigns/sticky-phone-v018"
PROJECT="$ROOT/sources/$HEAD/android/ritsu-control"
APK="$HOME/storage/downloads/Ritsu-Sticky-v0.18.0.apk"
TREE="$(git rev-parse HEAD:android/ritsu-control/app)"
mkdir -p "$ROOT/log"
receipt(){ printf 'campaign=ritsu-sticky-phone-v018\nsource_tree=%s\nhead=%s\nstate=%s\ndetail=%s\n' "$TREE" "$HEAD" "$1" "$2" > "$ROOT/receipt.part";mv "$ROOT/receipt.part" "$ROOT/receipt"; }
CAMPAIGN_STAGE=inventory
fail(){ trap - ERR; echo "CAMPAIGN=FAIL STAGE=$CAMPAIGN_STAGE REASON=$*";receipt FAIL "$CAMPAIGN_STAGE: $*";exit 2; }
unhandled_error(){ local rc="$1" line="$2";trap - ERR;echo "CAMPAIGN=FAIL STAGE=$CAMPAIGN_STAGE LINE=$line EXIT=$rc";receipt FAIL "unexpected error $rc at line $line";exit "$rc"; }
trap 'unhandled_error "$?" "$LINENO"' ERR
has(){ command -v "$1" >/dev/null 2>&1; }
if [ "$MODE" = status ];then cat "$ROOT/receipt" 2>/dev/null || echo STATUS=not_started;exit 0;fi
echo "PHONE_ARCH=$(uname -m)"
if [ "$MODE" = doctor ];then
  for p in pkg gh git curl java javac aapt2 apksigner zipalign unzip;do if has "$p";then echo "PRESENT=$p";else echo "MISSING=$p";fi;done
  echo "ANDROID_SOURCE_PIN=PASS"
  echo "BUILD_NOT_STARTED=1"
  exit 0
fi
[ "$(uname -m)" = aarch64 ] || fail "requires_ARM64_Termux"
[ "$(df -Pk "$HOME" | awk 'END{print $4}')" -ge 2500000 ] || fail "requires_2_5GB_free"
has pkg || fail "Termux_pkg_missing"
needed=''
for p in gh git curl unzip aapt2 apksigner zipalign;do
  if ! has "$p";then needed="$needed $p";fi
done
if ! has javac;then needed="$needed openjdk-17";fi
if [ -n "$needed" ];then
  pkg install -y $needed > "$ROOT/log/pkg.log" 2>&1 ||
    { tail -n 20 "$ROOT/log/pkg.log";fail "Termux_dependency_install"; }
fi
for p in gh git curl unzip java javac aapt2 apksigner zipalign;do
  has "$p" || fail "missing_dependency:$p"
done
# Existing authorized phone build tooling uses GitHub only for a pinned
# official Termux signing key in the legacy AAPT2 fallback.
if ! gh auth status >/dev/null 2>&1;then
  echo 'GH_AUTH_FOR_NATIVE_AAPT_FALLBACK=NEEDED'
  gh auth login -h github.com -p https --web || fail 'GitHub_auth_required'
fi
CAMPAIGN_STAGE=pinned_source_materialization
if [ ! -f "$PROJECT/app/build.gradle" ];then
  mkdir -p "$ROOT/sources/$HEAD"
  git archive "$HEAD" android/ritsu-control |
    tar -xf - -C "$ROOT/sources/$HEAD" ||
      fail "could_not_materialize_exact_Git_source"
fi
[ -f "$PROJECT/app/src/main/java/com/homecenter/ritsucontrol/StickySnippets.java" ] ||
  fail "Sticky_Snippets_source_missing"
[ -f "$PROJECT/app/src/main/java/com/homecenter/ritsucontrol/RitsuLocalSync.java" ] ||
  fail "Ritsu_local_sync_source_missing"
grep -Fq "versionCode 19" "$PROJECT/app/build.gradle" || fail "unexpected_app_version"
grep -Fq "'com.homecenter.ritsucontrol.sticky'" "$PROJECT/app/build.gradle" ||
  fail "missing_separate_sticky_package"
echo "EXACT_SOURCE_SHA=$HEAD"
echo "STICKY_APP_TREE=$TREE"
receipt SOURCE_VERIFIED "Git archive $HEAD"
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
run_aapt2(){
 # Scope alternate shared libraries exclusively to the AAPT2 child process.
 if [ -n "${isolated_libdir:-}" ]; then
   LD_LIBRARY_PATH="$isolated_libdir:${LD_LIBRARY_PATH:-$PREFIX/lib}" "$native" "$@"
 else
   "$native" "$@"
 fi
}
test_aapt2(){
 run_aapt2 link -o "$ROOT/aapt2-smoke/smoke.apk" -I "$jar" \
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
 # AAPT2 16 uses Protobuf 36 / Abseil lts_20260817. The installed Termux
 # libprotobuf is older and cannot provide ZeroCopyInputStream::ReadCord.
 # All ABI dependencies come from the SAME previously authenticated signed
 # repository index, extracted into the campaign ONLY. No global pkg upgrade.
 abiRoot="$repair/abi-prefix"
 isolated_libdir="$repair/abi-libs"
 mkdir -p "$abiRoot" "$isolated_libdir"
 CAMPAIGN_STAGE=aapt2_abi_resolution
 for dependency in abseil-cpp libprotobuf fmt libc++; do
   CAMPAIGN_STAGE="aapt2_abi_$dependency"
   echo "AAPT2_ABI_RESOLVE=$dependency"
   # Avoid apt-cache | awk ... exit under pipefail: a SIGPIPE from an early
   # reader can terminate the entire script without a meaningful failure log.
   # Save producer status and parse the complete output only after it finishes.
   policy="$ROOT/log/aapt2-abi-policy-${dependency//+/plus}.log"
   if ! apt-cache "${aptargs[@]}" policy "$dependency" > "$policy" 2>&1; then
     sed -n '1,25p' "$policy" || true
     fail "APT policy query failed: $dependency"
   fi
   abiVersion="$(awk '$1=="Candidate:" {value=$2} END {print value}' "$policy")"
   echo "AAPT2_ABI_PACKAGE=$dependency VERSION=$abiVersion"
   [ -n "$abiVersion" ] && [ "$abiVersion" != "(none)" ] ||
     fail "No signed ABI dependency candidate for $dependency"
   if [ "$dependency" = "libprotobuf" ]; then
     dpkg --compare-versions "$abiVersion" ge '2:36.2' ||
       fail "Protobuf $abiVersion too old for AAPT2 16"
   fi
   if [ "$dependency" = "abseil-cpp" ]; then
     dpkg --compare-versions "$abiVersion" ge '20260817.0' ||
       fail "Abseil $abiVersion too old for protobuf lts_20260817"
   fi
   # Download only named ARM64 packages through GPG-verified APT indexes.
   packageFile=""
   for entry in "$repair"/"$dependency"_*_aarch64.deb; do
     if [ -f "$entry" ]; then packageFile="$entry"; break; fi
   done
   # Reuse only if its Debian metadata confirms the exact candidate version.
   if [ -n "$packageFile" ] &&
      [ "$(dpkg-deb -f "$packageFile" Version 2>/dev/null || true)" != "$abiVersion" ]; then
     packageFile=""
   fi
   if [ -z "$packageFile" ]; then
     echo "AAPT2_ABI_DOWNLOAD=$dependency"
     if ! (cd "$repair" && apt-get "${aptargs[@]}" download "$dependency=$abiVersion") >> "$ROOT/log/aapt2-signed-download.log" 2>&1; then
       tail -n 12 "$ROOT/log/aapt2-signed-download.log" || true
       fail "Signed dependency retrieval failed: $dependency"
     fi
     for entry in "$repair"/"$dependency"_*_aarch64.deb; do
       if [ -f "$entry" ] &&
          [ "$(dpkg-deb -f "$entry" Version 2>/dev/null || true)" = "$abiVersion" ]; then
         packageFile="$entry"
         break
       fi
     done
   fi
   [ -n "$packageFile" ] || fail "Signed ABI package file missing: $dependency"
   echo "AAPT2_ABI_EXTRACT=$dependency"
   dpkg-deb -x "$packageFile" "$abiRoot" ||
     fail "ABI package extraction failed: $dependency"
   echo "AAPT2_ABI_READY=$dependency"
 done
 CAMPAIGN_STAGE=aapt2_abi_overlay
 libs="$abiRoot$PREFIX/lib"
 [ -d "$libs" ] || fail "Official packages did not contain the Termux lib directory"
 cp -a "$libs/." "$isolated_libdir/" ||
   fail 'Unable to stage matched Protobuf and Abseil shared libraries'
 [ -e "$isolated_libdir/libprotobuf.so" ] ||
   fail "Matched libprotobuf.so missing from isolated overlay"
 [ -e "$isolated_libdir/libabsl_base.so" ] ||
   fail "Matched Abseil shared libraries missing from isolated overlay"
 echo 'AAPT2_ABI_OVERLAY=matched_signed_packages_isolated'
 if ! run_aapt2 version > "$ROOT/log/aapt2.log" 2>&1; then
   echo 'AAPT2_ABI_LINK_ERROR_BEGIN'
   sed -n '1,28p' "$ROOT/log/aapt2.log" || true
   echo 'AAPT2_ABI_LINK_ERROR_END'
   fail 'Matched AAPT2+Protobuf+Abseil still cannot launch'
 fi
 test_aapt2 || {
   sed -n '1,28p' "$ROOT/log/aapt2-link-smoke.log" || true
   fail 'Matched AAPT2 cannot link Android SDK35 after library isolation'
 }
 # Gradle invokes this wrapper; only AAPT2 sees alternate libraries.
 aapt2Wrapper="$repair/aapt2-scoped"
 {
   printf '#!%s/bin/sh\n' "$PREFIX"
   printf 'export LD_LIBRARY_PATH=%q\n' "$isolated_libdir:${LD_LIBRARY_PATH:-$PREFIX/lib}"
   printf 'exec %q "$@"\n' "$native"
 } > "$aapt2Wrapper"
 chmod 700 "$aapt2Wrapper"
 "$aapt2Wrapper" version > "$ROOT/log/aapt2-wrapper.log" 2>&1 ||
   fail 'Gradle AAPT2 wrapper cannot start'
 native="$aapt2Wrapper"
 echo 'AAPT2_GRADLE_WRAPPER=isolated_library_scope'
 echo 'AAPT2_ANDROID35=PASS isolated_signed_official_toolchain'
fi
export JAVA_HOME="$(dirname "$(dirname "$(readlink -f "$(command -v java)")")")"
printf 'sdk.dir=%s\n' "$ANDROID_HOME" > "$PROJECT/local.properties"
CAMPAIGN_STAGE=phone_gradle
receipt BUILDING 'Native phone source compilation and JUnit'
bash "$GRADLE" -p "$PROJECT" :app:testDebugUnitTest :app:assembleRelease \
  -PritsuStickyInstall=true "-Pandroid.aapt2FromMavenOverride=$native" \
  --no-daemon --max-workers=2 > "$ROOT/log/gradle.log" 2>&1 ||
  { tail -n 45 "$ROOT/log/gradle.log";fail "phone_Gradle_compile_or_test_failure"; }
file="$PROJECT/app/build/outputs/apk/release/app-release-unsigned.apk"
[ -s "$file" ] || fail "phone_compiled_apk_not_found"
unzip -tqq "$file" || fail "phone_compiled_apk_corrupt"
echo "PHONE_COMPILE_AND_UNIT_TEST=PASS"
echo "PHONE_UNSIGNED_APK_SHA256=$(sha256sum "$file" | cut -d ' ' -f1)"
CAMPAIGN_STAGE=sign_and_publish
# The signing helper keeps an immutable on-phone private keystore and
# never signs as an existing .phone/.live/etc identity.
RITSU_STICKY_INPUT="$file" \
RITSU_STICKY_EXPECTED_SHA256="$(sha256sum "$file" | cut -d ' ' -f1)" \
RITSU_STICKY_NATIVE_SOURCE_SHA="$HEAD" \
  bash "$REPO/tools/campaigns/ritsu_sticky_install_real.sh" install ||
    fail "native_APK_sign_or_install_handoff_failed"
echo "NATIVE_PHONE_APK_BUILD_AND_SIGN=PASS"
receipt BUILD_PASS "native compile/test and local signing succeeded"
