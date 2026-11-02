#!/usr/bin/env bash
# Ritsu Sticky v0.18 APK: copy the already-signed file to Android Downloads.
# Never rebuild, re-sign, install, open, uninstall or touch the owner's repo.
set -Eeuo pipefail
umask 077
fail(){ printf 'DOWNLOADS_COPY=FAIL REASON=%s\n' "$*" >&2; exit 2; }
command -v sha256sum >/dev/null 2>&1 || fail 'sha256sum_missing'
command -v unzip >/dev/null 2>&1 || fail 'unzip_missing'

primary="$HOME/.local/share/ritsu-sticky-release/Ritsu-Sticky-v0.18.0.apk"
if [ -n "${RITSU_STICKY_SIGNED_APK:-}" ]; then
  src="$RITSU_STICKY_SIGNED_APK"
elif [ -s "$primary" ]; then
  src="$primary"
else
  shopt -s nullglob
  candidates=("$HOME"/.cache/ritsu-sticky-v018/Ritsu-Sticky-v0.18.0-*.apk)
  shopt -u nullglob
  [ "${#candidates[@]}" -eq 1 ] || fail 'signed_apk_missing_or_ambiguous; set RITSU_STICKY_SIGNED_APK to exact signed APK'
  src="${candidates[0]}"
fi
[ -f "$src" ] && [ -s "$src" ] || fail 'signed_source_file_missing_or_empty'
case "$(basename "$src")" in
  Ritsu-Sticky-v0.18.0.apk|Ritsu-Sticky-v0.18.0-*.apk) ;;
  *) fail 'source_filename_not_a_Ritsu_Sticky_signed_release' ;;
esac
unzip -tqq "$src" || fail 'source_apk_zip_integrity_failed'
source_sha="$(sha256sum "$src" | awk '{print $1}')"
source_bytes="$(wc -c < "$src" | tr -d ' ')"
[ "$source_bytes" -gt 0 ] || fail 'source_zero_bytes'
if [ -s "$src.sha256" ]; then
  recorded="$(head -n 1 "$src.sha256" | awk '{print $1}')"
  [ "$recorded" = "$source_sha" ] || fail 'source_sha256_receipt_mismatch'
fi
if command -v apksigner >/dev/null 2>&1; then
  apksigner verify "$src" >/dev/null 2>&1 || fail 'apk_signature_invalid'
  echo 'SIGNATURE_VERIFIED=PASS'
else
  echo 'SIGNATURE_VERIFIED=UNAVAILABLE_no_apksigner_in_PATH'
fi
if command -v aapt >/dev/null 2>&1; then
  manifest="$(aapt dump badging "$src" | grep -m1 '^package:' || true)"
  case "$manifest" in
    *"name='com.homecenter.ritsucontrol.sticky'"*"versionCode='19'"*) echo 'PACKAGE_VERIFIED=PASS' ;;
    *) fail 'APK_package_or_version_does_not_match_Sticky_v018' ;;
  esac
else
  echo 'PACKAGE_VERIFIED=UNAVAILABLE_no_aapt_in_PATH'
fi

if [ -d "$HOME/storage/downloads" ]; then
  downloads="$HOME/storage/downloads"
elif [ -d /storage/emulated/0/Download ]; then
  downloads=/storage/emulated/0/Download
else
  fail 'Android_Downloads_not_accessible; grant Termux storage permission using termux-setup-storage'
fi
[ -w "$downloads" ] || fail 'Android_Downloads_not_writable; grant Termux storage permission'
name='Ritsu-Sticky-v0.18.0.apk'
dest="$downloads/$name"
if [ -e "$dest" ]; then
  [ -f "$dest" ] || fail 'Downloads_filename_exists_but_is_not_a_regular_file'
  prior="$(sha256sum "$dest" | awk '{print $1}')"
  if [ "$prior" != "$source_sha" ]; then
    dest="$downloads/Ritsu-Sticky-v0.18.0-${source_sha:0:12}.apk"
    if [ -e "$dest" ]; then
      [ -f "$dest" ] || fail 'Downloads_hash_filename_not_a_regular_file'
      [ "$(sha256sum "$dest" | awk '{print $1}')" = "$source_sha" ] || fail 'Downloads_hash_filename_conflict_preserved'
    fi
  fi
fi
if [ ! -e "$dest" ]; then
  stage="$(mktemp "$downloads/.ritsu-sticky-copy.XXXXXX")" || fail 'cannot_create_Downloads_temp_file'
  trap 'rm -f -- "$stage"' EXIT
  cp -- "$src" "$stage" || fail 'copy_failed'
  [ "$(sha256sum "$stage" | awk '{print $1}')" = "$source_sha" ] || fail 'staged_copy_hash_mismatch'
  [ "$(wc -c < "$stage" | tr -d ' ')" = "$source_bytes" ] || fail 'staged_copy_size_mismatch'
  mv -n -- "$stage" "$dest" || fail 'publishing_Downloads_copy_failed'
  if [ -e "$stage" ]; then rm -f -- "$stage"; fi
  trap - EXIT
fi
[ -f "$dest" ] || fail 'published_Downloads_file_missing'
download_sha="$(sha256sum "$dest" | awk '{print $1}')"
download_bytes="$(wc -c < "$dest" | tr -d ' ')"
[ "$download_sha" = "$source_sha" ] && [ "$download_bytes" = "$source_bytes" ] || fail 'Downloads_readback_did_not_match_source'
printf 'SOURCE_APK=%s\nDOWNLOADS_APK=%s\nSOURCE_SHA256=%s\nDOWNLOADS_SHA256=%s\nBYTES=%s\nCOPY_VERIFIED=PASS\nOPENED=NO\nINSTALLED=NO\n' \
  "$src" "$dest" "$source_sha" "$download_sha" "$source_bytes"

# Index ONLY the verified final file after atomic publication.
# Media scanning is secondary and cannot invalidate or undo an APK copy.
case "${BASH_SOURCE[0]}" in
  */*) media_helper="${BASH_SOURCE[0]%/*}/refreshmedia" ;;
  *) media_helper="./refreshmedia" ;;
esac
if [ -f "$media_helper" ]; then
  if bash "$media_helper" "$dest"; then
    echo 'DOWNLOADS_MEDIA_REFRESH=REQUESTED'
  else
    echo 'DOWNLOADS_MEDIA_REFRESH=UNAVAILABLE_OR_FAILED_COPY_REMAINS_VALID'
  fi
else
  echo 'DOWNLOADS_MEDIA_REFRESH=UNAVAILABLE_HELPER_NOT_IN_THIS_REVISION'
fi
