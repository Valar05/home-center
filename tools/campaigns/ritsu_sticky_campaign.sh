#!/usr/bin/env bash
# Ritsu Sticky Snippets: repo-owned GitHub cloud verification campaign.
set -Eeuo pipefail
mode="${1:-doctor}"
self="$(realpath "${BASH_SOURCE[0]}")"
repo="$(cd -P "$(dirname "$self")/../.." && pwd -P)"
[ "$self" = "$repo/tools/campaigns/ritsu_sticky_campaign.sh" ] || {
  echo 'STICKY_FAIL=wrong_script_location'; exit 2;
}
cd "$repo"
origin="$(git remote get-url origin)"
case "$origin" in
  https://github.com/Valar05/home-center|https://github.com/Valar05/home-center.git|git@github.com:Valar05/home-center.git) ;;
  *) echo 'STICKY_FAIL=wrong_repository'; exit 2;;
esac
head="$(git rev-parse HEAD)"
[ -z "${GITHUB_SHA:-}" ] || [ "$GITHUB_SHA" = "$head" ] || {
  echo 'STICKY_FAIL=source_sha_mismatch'; exit 2;
}
echo "RESOLVED_REPO=$repo"
echo "EXECUTION_DIR=$PWD"
echo "BRANCH=$(git symbolic-ref --quiet --short HEAD || echo detached)"
echo "HEAD=$head"
[ "$mode" = doctor ] || [ "$mode" = build ] || {
  echo 'STICKY_FAIL=unknown_mode';exit 2;
}
test -f android/ritsu-control/app/src/main/java/com/homecenter/ritsucontrol/StickySnippets.java
test -f android/ritsu-control/app/src/main/java/com/homecenter/ritsucontrol/StickyText.java
test -f android/ritsu-control/app/src/test/java/com/homecenter/ritsucontrol/StickyTextTest.java
grep -Fq "versionCode 19" android/ritsu-control/app/build.gradle
grep -Fq "versionName '0.18.0'" android/ritsu-control/app/build.gradle
grep -Fq 'StickyText.compose' android/ritsu-control/app/src/main/java/com/homecenter/ritsucontrol/RitsuControlService.java
grep -Fq 'StickyText.compose' android/ritsu-control/app/src/main/java/com/homecenter/ritsucontrol/MainActivity.java
grep -Fq 'ACTION_CREATE_DOCUMENT' android/ritsu-control/app/src/main/java/com/homecenter/ritsucontrol/MainActivity.java
grep -Fq 'ACTION_OPEN_DOCUMENT' android/ritsu-control/app/src/main/java/com/homecenter/ritsucontrol/MainActivity.java
bash -n "$repo/tools/campaigns/ritsu_sticky_install_real.sh" || { echo STICKY_FAIL=installer_syntax; exit 2; }
grep -Fq 'e57a0edf08a01ae0132acef0a885436a5e6c8a02109630ac2279acaf73d97811' "$repo/tools/campaigns/ritsu_sticky_install_real.sh" || {
  echo STICKY_FAIL=installer_artifact_hash_not_locked; exit 2;
}
if [ "$mode" = doctor ]; then echo STICKY_PREFLIGHT=PASS; echo STICKY_INSTALLER_SCRIPT_SYNTAX=PASS; exit 0; fi
command -v gradle >/dev/null || { echo STICKY_FAIL=gradle_missing;exit 2; }
sdk="${ANDROID_HOME:-${ANDROID_SDK_ROOT:-}}"
test -f "$sdk/platforms/android-35/android.jar" || {
  echo STICKY_FAIL=android_sdk35_missing;exit 2;
}
gradle -p android/ritsu-control :app:testDebugUnitTest :app:assembleRelease \
  -PritsuPhoneInstall=true --no-daemon --stacktrace
apk="android/ritsu-control/app/build/outputs/apk/release/app-release-unsigned.apk"
test -s "$apk"
"$sdk/build-tools/35.0.0/aapt" dump badging "$apk" |
  grep -F "package: name='com.homecenter.ritsucontrol.phone' versionCode='19' versionName='0.18.0'"
unzip -tqq "$apk"
echo "STICKY_SOURCE_SHA=$head"
echo 'STICKY_UNIT_TESTS=PASS'
echo 'STICKY_UNSIGNED_APK_COMPILED=PASS'
echo 'STICKY_INSTALLABLE_UPGRADE=NOT_RELEASED_SIGNING_IDENTITY_UNVERIFIED'
