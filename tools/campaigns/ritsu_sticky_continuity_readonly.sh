#!/data/data/com.termux/files/usr/bin/bash
# Ritsu Sticky ONLY: package identity and safe release continuity inventory.
# Does not read pairing material, passwords, keystore bytes or app-private data.
set -u
umask 077
id=com.homecenter.ritsucontrol.sticky
dir="$HOME/.local/state/ritsu-control"
mkdir -p "$dir"
out="$dir/sticky-continuity-readonly.txt"
{
 echo 'RITSU_STICKY_CONTINUITY=v1'
 printf 'UTC=%s\n' "$(date -u +%FT%TZ)"
 echo "PACKAGE=$id"
 if ! command -v pm >/dev/null 2>&1; then
   echo 'PACKAGE_QUERY=PM_UNAVAILABLE'
 else
   result="$(pm path "$id" 2>&1)"
   case "$result" in
    *'package:'*) echo 'INSTALLED=YES';;
    *) echo 'INSTALLED=NOT_OBSERVABLE';;
   esac
 fi
 if command -v dumpsys >/dev/null 2>&1; then
   # Android 17 may restrict package visibility through Termux. Report unknown,
   # never infer that an app is absent from an empty output.
   data="$(dumpsys package "$id" 2>/dev/null)"
   version="$(printf '%s\n' "$data" | grep -m1 -E '^[[:space:]]*versionCode=' | sed -E 's/^[[:space:]]*//' || true)"
   name="$(printf '%s\n' "$data" | grep -m1 -E '^[[:space:]]*versionName=' | sed -E 's/^[[:space:]]*//' || true)"
   printf 'INSTALLED_%s\n' "${version:-VERSION_CODE_UNAVAILABLE}"
   printf 'INSTALLED_%s\n' "${name:-VERSION_NAME_UNAVAILABLE}"
   if printf '%s\n' "$data" | grep -Eq 'SigningDetails|SigningInfo|signatures='; then
      echo 'SIGNING_METADATA=VISIBLE_BUT_FINGERPRINT_NOT_VERIFIED'
   else echo 'SIGNING_METADATA=UNAVAILABLE'; fi
 else echo 'PACKAGE_DETAILS=DUMPSYS_UNAVAILABLE'; fi
 echo 'TARGET_PACKAGE_ID=com.homecenter.ritsucontrol.sticky'
 echo 'SOURCE_VERSION_CODE=19'
 echo 'SOURCE_VERSION_NAME=0.18.0'
 echo 'IDENTITY_MATCH=REQUIRES_INSTALLED_CERTIFICATE_COMPARISON'
 echo 'APP_PRIVATE_PAIRING=NOT_INSPECTED'
 echo 'TERMUX_EXISTING_AUTH=PREVIOUSLY_VERIFIED_NOT_RECHECKED'
 echo 'SAFE_ACTION=KEEP_CURRENT_INSTALL_AND_DATA'
 echo 'UNINSTALL=NO'
 echo 'NEW_APK=NOT_BUILT'
} | tee "$out"
chmod 600 "$out"
echo "RECEIPT=$out"
