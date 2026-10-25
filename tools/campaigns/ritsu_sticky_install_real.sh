#!/usr/bin/env bash
# Real Ritsu Sticky release campaign: verify, sign and install via Android.
# Cloud-built unsigned APK is delivered as a ChatGPT attachment to Downloads.
set -Eeuo pipefail
umask 077
mode="${1:-install}"
case "$mode" in install|status) ;; *) echo "STICKY_FAIL=unknown_mode";exit 2;; esac
self="$(realpath "${BASH_SOURCE[0]}")"
repo="$(cd -P "$(dirname "$self")/../.." && pwd -P)"
cd "$repo"
case "$(git remote get-url origin)" in
  https://github.com/Valar05/home-center.git|https://github.com/Valar05/home-center|git@github.com:Valar05/home-center.git) ;;
  *) echo "STICKY_FAIL=wrong_repo";exit 2;;
esac
echo "CAMPAIGN_HEAD=$(git rev-parse HEAD)"
echo "ORIGINAL_OWNER_WORKTREE=UNTOUCHED"
echo "OLD_RITSU_APPS=UNTOUCHED"
private="$HOME/.local/share/ritsu-sticky-release"
mkdir -p "$private"
chmod 700 "$private"
key="$private/release.p12"
secretfile="$private/release.password"
fingerprint="$private/release.certificate"
if [ "$mode" = status ]; then
  if [ -s "$key" ] && [ -s "$secretfile" ] && [ -s "$fingerprint" ];then
    echo "PERSISTENT_SIGNING_KEY=AVAILABLE"
    cat "$fingerprint"
  else
    echo "PERSISTENT_SIGNING_KEY=NOT_YET_CREATED"
  fi
  exit 0
fi
src="${RITSU_STICKY_INPUT:-$HOME/storage/downloads/Ritsu-Sticky-v018-unsigned.apk}"
[ -s "$src" ] || {
  echo "STICKY_FAIL=unsigned_apk_not_in_downloads"
  echo "EXPECTED_APK=Ritsu-Sticky-v018-unsigned.apk"
  exit 2
}
expected="${RITSU_STICKY_EXPECTED_SHA256:-e57a0edf08a01ae0132acef0a885436a5e6c8a02109630ac2279acaf73d97811}"
[[ "$expected" =~ ^[0-9a-f]{64}$ ]] || { echo "STICKY_FAIL=invalid_expected_APK_hash";exit 2; }
if [ -n "${RITSU_STICKY_NATIVE_SOURCE_SHA:-}" ];then
  [ "$(git rev-parse HEAD)" = "$RITSU_STICKY_NATIVE_SOURCE_SHA" ] ||
    { echo "STICKY_FAIL=source_revision_mismatch";exit 2; }
  case "$(realpath "$src")" in
    "$HOME/.local/share/ritsu-campaigns/sticky-phone-v018/sources/$RITSU_STICKY_NATIVE_SOURCE_SHA/android/ritsu-control/app/build/outputs/apk/release/app-release-unsigned.apk") ;;
    *) echo "STICKY_FAIL=not_native_android_build_output";exit 2;;
  esac
  echo "APK_PROVENANCE=LOCALLY_COMPILED_ON_PHONE"
fi
actual="$(sha256sum "$src" | cut -d ' ' -f 1)"
[ "$actual" = "$expected" ] || {
  echo "STICKY_FAIL=unsigned_apk_checksum_mismatch"
  exit 2
}
echo "APK_SOURCE_SHA=${RITSU_STICKY_NATIVE_SOURCE_SHA:-b27434a1f650aae845d02780d4af09666080165f}"
echo "BUILD_UNSIGNED_APK_SHA256=$actual"
if ! command -v java >/dev/null 2>&1 || ! command -v keytool >/dev/null 2>&1;then
  command -v pkg >/dev/null 2>&1 || { echo "STICKY_FAIL=no_termux_package_manager";exit 2; }
  pkg install -y openjdk-21
fi
if ! command -v apksigner >/dev/null 2>&1;then
  command -v pkg >/dev/null 2>&1 || { echo "STICKY_FAIL=no_apksigner";exit 2; }
  pkg install -y apksigner
fi
if ! command -v zipalign >/dev/null 2>&1;then
  command -v pkg >/dev/null 2>&1 || { echo "STICKY_FAIL=no_zipalign";exit 2; }
  pkg install -y zipalign
fi
for program in keytool apksigner zipalign;do
  command -v "$program" >/dev/null 2>&1 || { echo "STICKY_FAIL=missing_$program";exit 2; }
done
if [ -e "$key" ] || [ -e "$secretfile" ] || [ -e "$fingerprint" ];then
  [ -s "$key" ] && [ -s "$secretfile" ] && [ -s "$fingerprint" ] || {
    echo "STICKY_FAIL=incomplete_signer_do_not_replace"
    exit 2
  }
  echo "SIGNING_KEY=REUSED"
else
  secret="$(head -c 32 /dev/urandom | od -An -tx1 | tr -d ' \n')"
  printf '%s\n' "$secret" > "$secretfile"
  chmod 600 "$secretfile"
  keytool -genkeypair -noprompt -storetype PKCS12 \
    -keystore "$key" -alias ritsusticky -storepass "$secret" -keypass "$secret" \
    -keyalg RSA -keysize 3072 -validity 10000 \
    -dname "CN=Ritsu Sticky,O=Home Center,C=US" >/dev/null 2>&1 || {
      echo "STICKY_FAIL=key_creation_failed"
      exit 2
    }
  chmod 600 "$key"
  echo "SIGNING_KEY=CREATED_FOR_SEPARATE_PACKAGE"
fi
digest="$(keytool -list -v -keystore "$key" -storepass "$(cat "$secretfile")" \
  -alias ritsusticky | sed -n 's/.*SHA256: //p' | head -n 1 | tr -d ':' | tr '[:upper:]' '[:lower:]')"
[[ "$digest" =~ ^[a-f0-9]{64}$ ]] || { echo "STICKY_FAIL=key_digest_invalid";exit 2; }
if [ -s "$fingerprint" ];then
  [ "$(cat "$fingerprint")" = "$digest" ] || {
    echo "STICKY_FAIL=signer_changed_do_not_replace"
    exit 2
  }
else
  printf '%s\n' "$digest" > "$fingerprint"
fi
aligned="$private/unsigned-aligned.apk"
zipalign -f -p 4 "$src" "$aligned"
out="$private/Ritsu-Sticky-v0.18.0.apk"
temp="$private/staging-signed.apk"
apksigner sign --ks "$key" --ks-type PKCS12 --ks-key-alias ritsusticky \
  --ks-pass "file:$secretfile" --key-pass "file:$secretfile" \
  --out "$temp" "$aligned"
apksigner verify --verbose --print-certs "$temp" > "$private/apk-verify.txt"
signed="$(sed -n 's/.*Signer #1 certificate SHA-256 digest: //p' "$private/apk-verify.txt" | head -n 1)"
[ "$signed" = "$digest" ] || {
  echo "STICKY_FAIL=apk_certificate_mismatch"
  exit 2
}
mv "$temp" "$out"
sha256sum "$out" > "$out.sha256"
echo "SIGNED_APK_CERT_SHA256=$signed"
echo "SIGNED_APK_SHA256=$(sha256sum "$out" | cut -d ' ' -f 1)"
echo "SIGNED_APK=$out"
if [ -d "$HOME/storage/downloads" ] && [ -w "$HOME/storage/downloads" ];then
  cp "$out" "$HOME/storage/downloads/Ritsu-Sticky-v0.18.0.apk"
  echo "DOWNLOADS_APK=$HOME/storage/downloads/Ritsu-Sticky-v0.18.0.apk"
else
  echo "DOWNLOADS_NOT_GRANTED=APK_REMAINS_PRIVATE"
fi
echo "PREVIOUS_PACKAGE_DATA=UNTOUCHED"
echo "NEW_PACKAGE_PAIRING=SEPARATE_REQUIRES_USER_PAIRING"
echo "KEEP_SIGNING_KEY_PRIVATE_FOR_FUTURE_UPDATES=$private"
if command -v termux-open >/dev/null 2>&1;then
  termux-open --view --content-type application/vnd.android.package-archive "$out" || true
fi
echo "ANDROID_INSTALL_APPROVAL_REQUIRED=1"
