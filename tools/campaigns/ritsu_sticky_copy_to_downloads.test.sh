#!/usr/bin/env bash
# Host/Actions tests for the repo-owned copy-only Termux delivery.
set -Eeuo pipefail
script="$(cd -P "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)/ritsu_sticky_copy_to_downloads.sh"
bash -n "$script"
if grep -E '(^|[[:space:]])(termux-open|pm install|am start|gradle|keytool|apksigner sign|rm -rf)' "$script"; then
  echo COPY_CONTRACT=unexpected_installer_or_build_command
  exit 2
fi
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
mockHome="$tmp/home"
mkdir -p "$mockHome/.local/share/ritsu-sticky-release" "$mockHome/storage/downloads"
src="$mockHome/.local/share/ritsu-sticky-release/Ritsu-Sticky-v0.18.0.apk"
printf 'test content, not a deliverable\n' > "$tmp/AndroidManifest.xml"
(cd "$tmp" && zip -q "$src" AndroidManifest.xml)
sha256sum "$src" > "$src.sha256"
# Hide optional Android inspectors so the fixture can exercise file delivery
# deterministically without trying to masquerade as an actual signed APK.
mkdir -p "$tmp/bin"
for cmd in bash basename unzip sha256sum wc tr head awk grep mktemp cp mv rm cmp; do
  ln -s "$(command -v "$cmd")" "$tmp/bin/$cmd"
done
export PATH="$tmp/bin"
export HOME="$mockHome"
bash "$script" > "$tmp/first.log"
grep -Fq 'COPY_VERIFIED=PASS' "$tmp/first.log"
grep -Fq 'OPENED=NO' "$tmp/first.log"
grep -Fq 'INSTALLED=NO' "$tmp/first.log"
cmp "$src" "$mockHome/storage/downloads/Ritsu-Sticky-v0.18.0.apk"
bash "$script" > "$tmp/repeat.log"
grep -Fq 'COPY_VERIFIED=PASS' "$tmp/repeat.log"
printf 'existing user file is precious\n' > "$mockHome/storage/downloads/Ritsu-Sticky-v0.18.0.apk"
bash "$script" > "$tmp/collision.log"
grep -Fq 'COPY_VERIFIED=PASS' "$tmp/collision.log"
grep -Fq "DOWNLOADS_APK=$mockHome/storage/downloads/Ritsu-Sticky-v0.18.0-" "$tmp/collision.log"
grep -Fq 'existing user file is precious' "$mockHome/storage/downloads/Ritsu-Sticky-v0.18.0.apk"
printf '0f\n' > "$src.sha256"
if bash "$script" > "$tmp/mismatch.log" 2>&1; then
  echo COPY_CONTRACT=incorrectly_accepted_bad_hash
  exit 2
fi
grep -Fq 'source_sha256_receipt_mismatch' "$tmp/mismatch.log"
rm "$src" "$src.sha256"
if bash "$script" > "$tmp/missing.log" 2>&1; then
  echo COPY_CONTRACT=incorrectly_accepted_missing_artifact
  exit 2
fi
grep -Fq 'signed_apk_missing_or_ambiguous' "$tmp/missing.log"
echo RITSU_DOWNLOADS_COPY_REGRESSION=PASS
echo RITSU_DOWNLOADS_COLLISION_PRESERVATION=PASS
echo RITSU_DOWNLOADS_MISSING_AND_HASH_FAIL_CLOSED=PASS
