#!/usr/bin/env bash
# Cloud-only ephemeral APK signing smoke. Not a distributed installer.
set -Eeuo pipefail
umask 077
[ "${GITHUB_ACTIONS:-}" = true ] || { echo 'CI_SIGNING_SMOKE=not_ci';exit 2; }
repo="$(cd -P "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd -P)"
sdk="${ANDROID_HOME:-${ANDROID_SDK_ROOT:-}}"
src="$repo/android/ritsu-control/app/build/outputs/apk/release/app-release-unsigned.apk"
[ -s "$src" ] || { echo 'CI_SIGNING_SMOKE=missing_unsigned_apk';exit 2; }
for tool in zipalign apksigner aapt; do
  [ -x "$sdk/build-tools/35.0.0/$tool" ] || {
    echo "CI_SIGNING_SMOKE=missing_$tool";exit 2;
  }
done
temp="$(mktemp -d)"
trap 'rm -rf "$temp"' EXIT
secret="$(head -c 24 /dev/urandom | od -An -tx1 | tr -d ' \n')"
keytool -genkeypair -noprompt -storetype PKCS12 \
  -alias ritsusticky -keyalg RSA -keysize 3072 -validity 5 \
  -dname 'CN=GitHub Test Signer,O=CI' \
  -keystore "$temp/test-only.p12" -storepass "$secret" -keypass "$secret" \
  >/dev/null 2>&1
"$sdk/build-tools/35.0.0/zipalign" -f -p 4 "$src" "$temp/aligned.apk"
RITSU_STICKY_SMOKE_PASSWORD="$secret" "$sdk/build-tools/35.0.0/apksigner" sign \
  --ks "$temp/test-only.p12" --ks-type PKCS12 \
  --ks-key-alias ritsusticky \
  --ks-pass env:RITSU_STICKY_SMOKE_PASSWORD --key-pass env:RITSU_STICKY_SMOKE_PASSWORD \
  --out "$temp/test-signed.apk" "$temp/aligned.apk"
"$sdk/build-tools/35.0.0/apksigner" verify --verbose --print-certs \
  "$temp/test-signed.apk" > "$temp/cert.log"
"$sdk/build-tools/35.0.0/aapt" dump badging "$temp/test-signed.apk" |
 grep -F "package: name='com.homecenter.ritsucontrol.sticky' versionCode='19' versionName='0.18.0'"
unzip -tqq "$temp/test-signed.apk"
echo 'CI_SIGNING_SMOKE=PASS'
echo 'CI_SIGNING_IDENTITY=EPHEMERAL_FOR_TEST_ONLY_NOT_AN_UPGRADE_SIGNER'
