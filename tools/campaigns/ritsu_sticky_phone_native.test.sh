#!/usr/bin/env bash
set -Eeuo pipefail
self="$(realpath "${BASH_SOURCE[0]}")"
dir="$(cd -P "$(dirname "$self")" && pwd -P)"
native="$dir/ritsu_sticky_phone_native.sh"
signer="$dir/ritsu_sticky_install_real.sh"
bash -n "$native"
bash -n "$signer"
for token in 'git archive "$HEAD" android/ritsu-control' ':app:testDebugUnitTest :app:assembleRelease' '-PritsuStickyInstall=true' 'RITSU_STICKY_NATIVE_SOURCE_SHA="$HEAD"' 'RITSU_STICKY_EXPECTED_SHA256='; do
  grep -Fq -- "$token" "$native" || { echo "PHONE_NATIVE_TEST_FAIL=$token";exit 2; }
done
grep -Fq 'APK_PROVENANCE=LOCALLY_COMPILED_ON_PHONE' "$signer"
grep -Fq 'LOCAL_SIGNING_IDENTITY' "$signer" || grep -Fq 'SIGNING_KEY=REUSED' "$signer"
bootstrap="$dir/ritsu_sticky_onepaste.sh"
bash -n "$bootstrap"
grep -Fq "doctor|build|install|phone|install-media)" "$bootstrap"
grep -Fq "ritsu_sticky_phone_native.sh" "$bootstrap"
grep -Fq 'key-pass env:RITSU_STICKY_SIGNING_PASSWORD' "$signer"
echo PHONE_SIGNING_PASSWORD_FILE_EOF_REGRESSION=FIXED_SCRIPT
echo PHONE_NATIVE_SCRIPT_SYNTAX=PASS
echo PHONE_NATIVE_BUILD_AND_SIGN_GATES=PASS
echo PHONE_PHYSICAL_INSTALL=UNVERIFIED
