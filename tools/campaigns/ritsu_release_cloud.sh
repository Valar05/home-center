#!/usr/bin/env bash
# Repo-owned stable Android release. Used inside GitHub Actions.
set -Eeuo pipefail
umask 077
MODE="${1:-doctor}"
SELF="$(realpath "${BASH_SOURCE[0]}")"
REPO="$(cd -P "$(dirname "$SELF")/../.." && pwd -P)"
[ "$SELF" = "$REPO/tools/campaigns/ritsu_release_cloud.sh" ] || {
  echo "RELEASE_FAIL=not_the_repo_owned_entrypoint"; exit 2;
}
cd "$REPO"
REMOTE="$(git remote get-url origin)"
case "$REMOTE" in
  https://github.com/Valar05/home-center|https://github.com/Valar05/home-center.git|git@github.com:Valar05/home-center.git)
    ;;
  *) echo "RELEASE_FAIL=wrong_repository"; exit 2;;
esac
SOURCE_SHA="$(git rev-parse HEAD)"
[ -z "${GITHUB_SHA:-}" ] || [ "$SOURCE_SHA" = "$GITHUB_SHA" ] || {
  echo "RELEASE_FAIL=source_revision_mismatch"; exit 2;
}
echo "RELEASE_REPO=$REPO"
echo "RELEASE_COMMIT=$SOURCE_SHA"
echo "RELEASE_WORKDIR=$PWD"
echo "RELEASE_BRANCH=$(git symbolic-ref --quiet --short HEAD || echo detached)"
fail(){ echo "RELEASE_FAIL=$1"; exit 2; }
case "$MODE" in doctor|build) ;; *) fail invalid_mode;; esac
APP_GRADLE="$REPO/android/ritsu-control/app/build.gradle"
[ -f "$APP_GRADLE" ] || fail missing_android_project
PKG="com.homecenter.ritsucontrol.phone"
VERSION_CODE="$(awk '$1=="versionCode" {v=$2} END{print v}' "$APP_GRADLE")"
VERSION_NAME="$(awk '$1=="versionName" {gsub(/\047/,"",$2);v=$2} END{print v}' "$APP_GRADLE")"
[[ "$VERSION_CODE" =~ ^[0-9]+$ ]] && [ -n "$VERSION_NAME" ] || fail invalid_android_version
grep -Fq -- "'$PKG'" "$APP_GRADLE" || fail package_id_not_in_gradle
echo "RELEASE_PACKAGE=$PKG"
echo "RELEASE_VERSION_CODE=$VERSION_CODE"
echo "RELEASE_VERSION_NAME=$VERSION_NAME"

# Explicit durable identity. No generated debug keys or plaintext in Git.
for name in RITSU_APK_KEYSTORE_B64 RITSU_APK_KEYSTORE_PASSWORD \
            RITSU_APK_KEY_PASSWORD RITSU_APK_KEY_ALIAS RITSU_APK_SIGNER_SHA256; do
  [ -n "${!name:-}" ] || fail "missing_protected_signing_config_$name"
done
EXPECTED_CERT="$(printf '%s' "$RITSU_APK_SIGNER_SHA256" | tr '[:upper:]' '[:lower:]' | tr -d ':')"
[[ "$EXPECTED_CERT" =~ ^[0-9a-f]{64}$ ]] || fail invalid_locked_signer_fingerprint
TEMP="$(mktemp -d "${RUNNER_TEMP:-/tmp}/ritsu-apk-signing.XXXXXX")"
KEYFILE="$TEMP/ritsu-upload.jks"
trap 'rm -rf "$TEMP"' EXIT
if ! printf '%s' "$RITSU_APK_KEYSTORE_B64" | base64 --decode > "$KEYFILE"; then
  fail invalid_encoded_keystore
fi
[ -s "$KEYFILE" ] || fail empty_keystore
if ! keytool -list -v -keystore "$KEYFILE" \
  -storepass:env RITSU_APK_KEYSTORE_PASSWORD \
  -alias "$RITSU_APK_KEY_ALIAS" > "$TEMP/keytool.txt" 2>&1; then
  fail invalid_keystore_alias_or_password
fi
ACTUAL_CERT="$(awk '/SHA256:/ {gsub(":","",$2);print tolower($2);exit}' "$TEMP/keytool.txt")"
[ "$ACTUAL_CERT" = "$EXPECTED_CERT" ] || fail signing_certificate_mismatch
echo "RELEASE_SIGNER_SHA256=$ACTUAL_CERT"

# Android does not migrate private data across package names or signer IDs.
INTENT="${RITSU_RELEASE_INTENT:-upgrade}"
case "$INTENT" in
  upgrade)
    [ "${RITSU_INSTALLED_PACKAGE:-}" = "$PKG" ] ||
      fail unknown_or_mismatched_installed_package
    INSTALLED_CERT="$(printf '%s' "${RITSU_INSTALLED_CERT_SHA256:-}" | tr '[:upper:]' '[:lower:]' | tr -d ':')"
    [ "$INSTALLED_CERT" = "$EXPECTED_CERT" ] ||
      fail installed_certificate_differs_data_preservation_not_proven
    [[ "${RITSU_INSTALLED_VERSION_CODE:-}" =~ ^[0-9]+$ ]] ||
      fail installed_version_code_unverified
    [ "$VERSION_CODE" -gt "$RITSU_INSTALLED_VERSION_CODE" ] ||
      fail version_code_not_newer_than_installed_app
    echo "RELEASE_UPDATE_IDENTITY_GATE=PASS"
    ;;
  new-install)
    [ "${RITSU_CONFIRMED_NOT_INSTALLED:-}" = "true" ] ||
      fail existing_package_presence_unverified
    echo "RELEASE_UPDATE_IDENTITY_GATE=NEW_PACKAGE_NO_DATA_MIGRATION"
    ;;
  *) fail invalid_release_intent;;
esac

if [ "$MODE" = doctor ]; then
  echo "RELEASE_DOCTOR=PASS"
  exit 0
fi
command -v gradle >/dev/null 2>&1 || fail gradle_missing
SDK="${ANDROID_HOME:-${ANDROID_SDK_ROOT:-}}"
[ -d "$SDK/build-tools/35.0.0" ] || fail android_35_build_tools_missing
SIGNER="$SDK/build-tools/35.0.0/apksigner"
ALIGN="$SDK/build-tools/35.0.0/zipalign"
AAPT="$SDK/build-tools/35.0.0/aapt"
for tool in "$SIGNER" "$ALIGN" "$AAPT"; do [ -x "$tool" ] || fail android_build_tool_missing; done

# Use unsigned release output; never transient GitHub debug.keystore.
gradle -p android/ritsu-control :app:testDebugUnitTest :app:assembleRelease \
  -PritsuPhoneInstall=true --no-daemon --stacktrace
UNSIGNED="$REPO/android/ritsu-control/app/build/outputs/apk/release/app-release-unsigned.apk"
[ -s "$UNSIGNED" ] || fail unsigned_release_apk_missing
DIST="$REPO/dist/ritsu-v017"
mkdir -p "$DIST"
ALIGN_APK="$TEMP/ritsu-aligned.apk"
"$ALIGN" -f -p 4 "$UNSIGNED" "$ALIGN_APK" || fail zipalign_failed
FINAL="$DIST/Ritsu-Control-${VERSION_NAME}-Cloud-Stable.apk"
STAGING="$TEMP/ritsu-signed.apk"
"$SIGNER" sign --ks "$KEYFILE" --ks-key-alias "$RITSU_APK_KEY_ALIAS" \
  --ks-pass env:RITSU_APK_KEYSTORE_PASSWORD --key-pass env:RITSU_APK_KEY_PASSWORD \
  --out "$STAGING" "$ALIGN_APK" || fail signing_failed
"$SIGNER" verify --verbose --print-certs "$STAGING" > "$TEMP/apksigner.txt" 2>&1 ||
  fail signed_apk_verification_failed
SIGNER_DIGEST="$(awk '/certificate SHA-256 digest:/ {print tolower($NF);exit}' "$TEMP/apksigner.txt")"
[ "$SIGNER_DIGEST" = "$EXPECTED_CERT" ] || fail signed_apk_certificate_drift
"$AAPT" dump badging "$STAGING" > "$TEMP/badging.txt" || fail badging_failed
grep -Fq -- "package: name='$PKG' versionCode='$VERSION_CODE' versionName='$VERSION_NAME'" "$TEMP/badging.txt" ||
  fail built_apk_package_or_version_mismatch
unzip -tqq "$STAGING" || fail apk_archive_invalid
cp "$STAGING" "$FINAL" || fail artifact_copy_failed
"$SIGNER" verify "$FINAL" || fail final_artifact_signature_invalid
STAGING_SHA="$(sha256sum "$STAGING" | awk '{print $1}')"
FINAL_SHA="$(sha256sum "$FINAL" | awk '{print $1}')"
[ "$STAGING_SHA" = "$FINAL_SHA" ] || fail published_apk_hash_changed
cat > "$DIST/release-receipt.json" <<EOF
{
  "schema": "ritsu.cloud-stable-apk.v1",
  "sourceCommit": "$SOURCE_SHA",
  "applicationId": "$PKG",
  "versionCode": $VERSION_CODE,
  "versionName": "$VERSION_NAME",
  "signerCertificateSha256": "$EXPECTED_CERT",
  "apkSha256": "$FINAL_SHA",
  "intent": "$INTENT",
  "inPlaceUpgradeProvenOnPhone": false,
  "installedAppDataRetentionProvenOnPhone": false,
  "file": "$(basename "$FINAL")"
}
EOF
printf '%s  %s\n' "$FINAL_SHA" "$(basename "$FINAL")" > "$DIST/apk.sha256"
echo "RELEASE_APK_VERIFIED=$FINAL"
echo "RELEASE_APK_SHA256=$FINAL_SHA"
echo "RELEASE_APK_SIGNER_SHA256=$SIGNER_DIGEST"
echo "RELEASE_ON_DEVICE_DATA_RETENTION=UNVERIFIED"
