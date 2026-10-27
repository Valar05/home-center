#!/usr/bin/env bash
# Ritsu Sticky v0.18: sign a GitHub-compiled APK on the owner's phone.
# Never uninstalls or changes any existing application or Git checkout.
set -Eeuo pipefail
umask 077
mode="${1:-install}"
case "$mode" in install|status|verify) ;; *) echo "RELEASE_ERROR=unknown_mode";exit 2;; esac
self="$(realpath "${BASH_SOURCE[0]}")"
repo="$(cd -P "$(dirname "$self")/../.." && pwd -P)"
cd "$repo"
remote="$(git remote get-url origin)"
case "$remote" in https://github.com/Valar05/home-center.git|https://github.com/Valar05/home-center|git@github.com:Valar05/home-center.git) ;; *) echo "RELEASE_ERROR=wrong_repo";exit 2;; esac
head="$(git rev-parse HEAD)"
private="${RITSU_STICKY_PRIVATE:-$HOME/.local/share/ritsu-sticky-signing}"
cache="${RITSU_STICKY_CACHE:-$HOME/.cache/ritsu-sticky-v018}"
key="$private/sticky-release.p12"
passfile="$private/sticky-release.password"
certfile="$private/sticky-release.certificate.sha256"
mkdir -p "$private" "$cache"
chmod 700 "$private" "$cache"
echo "SOURCE_SHA=$head"
echo "PRIVATE_SIGNING_DIR=$private"
echo "OLD_RITSU_APPLICATIONS=UNTOUCHED"
if [ "$mode" = status ]; then
  if [ -s "$key" ] && [ -s "$passfile" ] && [ -s "$certfile" ]; then
    echo "DURABLE_SIGNING_KEY=AVAILABLE"
    echo "SIGNER_CERT_SHA256=$(cat "$certfile")"
  else
    echo "DURABLE_SIGNING_KEY=NOT_PROVISIONED"
  fi
  find "$cache" -maxdepth 1 -type f -name 'Ritsu-Sticky-*.apk' -print
  exit 0
fi
command -v curl >/dev/null 2>&1 || {
  if command -v pkg >/dev/null 2>&1; then pkg install -y curl; else echo "RELEASE_ERROR=curl_missing";exit 2;fi
}
if ! command -v java >/dev/null 2>&1 || ! command -v keytool >/dev/null 2>&1; then
  if command -v pkg >/dev/null 2>&1; then
    echo "JAVA_PREFLIGHT=INSTALL_OPENJDK_17"
    pkg install -y openjdk-17
  else
    echo "RELEASE_ERROR=java_keytool_unavailable"
    exit 2
  fi
fi
command -v java >/dev/null && command -v keytool >/dev/null || { echo "RELEASE_ERROR=java_install_failed";exit 2; }
base="https://raw.githubusercontent.com/Valar05/home-center/generated/ritsu-sticky-unsigned/ritsu-sticky-v018"
for file in unsigned-aligned.apk apksigner.jar unsigned-aligned.apk.sha256 apksigner.jar.sha256 source-receipt.txt; do
  if [ ! -s "$cache/$file" ]; then
    curl --fail --location --retry 3 --connect-timeout 15 --max-time 120 \
      "$base/$file" -o "$cache/$file.tmp"
    mv "$cache/$file.tmp" "$cache/$file"
  fi
done
(
  cd "$cache"
  sha256sum --check unsigned-aligned.apk.sha256
  sha256sum --check apksigner.jar.sha256
)
grep -Fx "SOURCE_SHA=$head" "$cache/source-receipt.txt" >/dev/null || {
  echo "RELEASE_ERROR=cloud_source_does_not_match_pinned_checkout"
  exit 2
}
grep -Fx "APPLICATION_ID=com.homecenter.ritsucontrol.sticky" "$cache/source-receipt.txt" >/dev/null || {
  echo "RELEASE_ERROR=wrong_application_package"
  exit 2
}
grep -Fx "VERSION_CODE=19" "$cache/source-receipt.txt" >/dev/null || {
  echo "RELEASE_ERROR=unexpected_version"
  exit 2
}
java -jar "$cache/apksigner.jar" version >/dev/null || {
  echo "RELEASE_ERROR=signing_tool_not_runnable"
  exit 2
}
if [ "$mode" = verify ]; then
  echo "CLOUD_UNSIGNED_APK_AND_SIGNER=VERIFIED"
  exit 0
fi
# New *separate* package identity, never an attempt to overwrite an old app.
if [ -e "$key" ] || [ -e "$passfile" ] || [ -e "$certfile" ]; then
  [ -s "$key" ] && [ -s "$passfile" ] && [ -s "$certfile" ] || {
    echo "RELEASE_ERROR=incomplete_existing_signer_no_regeneration"
    exit 2
  }
  echo "SIGNER=REUSED_PRIVATE_DURABLE_KEY"
else
  secret="$(head -c 32 /dev/urandom | od -An -tx1 | tr -d ' \n')"
  printf '%s\n' "$secret" > "$passfile"
  chmod 600 "$passfile"
  keytool -genkeypair -noprompt -storetype PKCS12 -alias ritsusticky \
    -keyalg RSA -keysize 3072 -validity 10000 \
    -dname "CN=Ritsu Sticky Device Signing,O=Home Center,C=US" \
    -keystore "$key" -storepass "$secret" -keypass "$secret" >/dev/null 2>&1 || {
      echo "RELEASE_ERROR=signing_key_creation_failed"
      exit 2
    }
  chmod 600 "$key"
  echo "SIGNER=CREATED_PRIVATE_DURABLE_KEY"
fi
keytool -list -v -storetype PKCS12 -keystore "$key" \
  -storepass "$(cat "$passfile")" -alias ritsusticky > "$cache/key-certificate.txt"
actual="$(sed -n 's/.*SHA256: //p' "$cache/key-certificate.txt" | head -n 1 | tr -d ':' | tr '[:upper:]' '[:lower:]')"
[[ "$actual" =~ ^[0-9a-f]{64}$ ]] || { echo "RELEASE_ERROR=invalid_cert_digest";exit 2; }
if [ -s "$certfile" ]; then
  [ "$(cat "$certfile")" = "$actual" ] || {
    echo "RELEASE_ERROR=signing_identity_changed"
    exit 2
  }
else
  printf '%s\n' "$actual" > "$certfile"
  chmod 600 "$certfile"
fi
apk="$cache/Ritsu-Sticky-v0.18.0-${head:0:12}.apk"
java -jar "$cache/apksigner.jar" sign \
  --ks "$key" --ks-type PKCS12 --ks-key-alias ritsusticky \
  --ks-pass "file:$passfile" --key-pass "file:$passfile" \
  --out "$apk.tmp.apk" "$cache/unsigned-aligned.apk"
java -jar "$cache/apksigner.jar" verify --verbose --print-certs "$apk.tmp.apk" \
  > "$cache/apk-verification.txt"
signed="$(sed -n 's/.*Signer #1 certificate SHA-256 digest: //p' "$cache/apk-verification.txt" | head -n 1 | tr -d ':' | tr '[:upper:]' '[:lower:]')"
[ "$signed" = "$actual" ] || { echo "RELEASE_ERROR=signed_cert_mismatch";exit 2; }
mv "$apk.tmp.apk" "$apk"
sha256sum "$apk" > "$apk.sha256"
echo "SIGNED_APK_SHA256=$(sha256sum "$apk" | cut -d ' ' -f 1)"
echo "SIGNED_APK_CERT_SHA256=$actual"
echo "SIGNED_APK=$apk"
# Android Storage Access Framework remains subject to user permission.
if [ -d "$HOME/storage/downloads" ] && [ -w "$HOME/storage/downloads" ]; then
  cp "$apk" "$HOME/storage/downloads/$(basename "$apk")"
  echo "ANDROID_DOWNLOADS_APK=$HOME/storage/downloads/$(basename "$apk")"
  if command -v termux-open >/dev/null 2>&1; then
    termux-open --view --content-type application/vnd.android.package-archive \
      "$HOME/storage/downloads/$(basename "$apk")" || true
  fi
else
  echo "DOWNLOADS_NOT_ACCESSIBLE=SIGNED_APK_REMAINS_IN_PRIVATE_STORAGE"
fi
echo "INSTALLATION_REQUIRES_ANDROID_CONFIRMATION=1"
echo "PREVIOUS_RITSU_DATA_PRESERVED=OLDER_PACKAGE_UNTOUCHED"
echo "OLD_APP_PAIRING_NOT_COPIED_TO_NEW_PACKAGE=1"
