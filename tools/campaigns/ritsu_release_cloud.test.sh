#!/usr/bin/env bash
set -Eeuo pipefail
here="$(cd -P "$(dirname "$(realpath "${BASH_SOURCE[0]}")")" && pwd -P)"
src="$here/ritsu_release_cloud.sh"
[ -f "$src" ] || { echo 'FAIL=release_entrypoint_missing'; exit 2; }
bash -n "$src" || { echo 'FAIL=release_entrypoint_syntax'; exit 2; }
echo 'RELEASE_BASH_SYNTAX=PASS'
assert_guard(){
  if ! grep -Fq -- "$2" "$src"; then
    echo "FAIL=release_missing_guard:$1"; exit 2;
  fi
}
assert_guard identity 'not_the_repo_owned_entrypoint'
assert_guard origin 'wrong_repository'
assert_guard sha 'source_revision_mismatch'
assert_guard package 'com.homecenter.ritsucontrol.phone'
assert_guard private_keystore 'RITSU_APK_KEYSTORE_B64'
assert_guard locked_fingerprint 'signing_certificate_mismatch'
assert_guard installed_package 'unknown_or_mismatched_installed_package'
assert_guard installed_certificate 'installed_certificate_differs_data_preservation_not_proven'
assert_guard version_monotonic 'version_code_not_newer_than_installed_app'
assert_guard no_migration 'NEW_PACKAGE_NO_DATA_MIGRATION'
assert_guard unsigned_release 'app-release-unsigned.apk'
assert_guard signer 'signed_apk_certificate_drift'
assert_guard hash 'published_apk_hash_changed'
assert_guard evidence 'installedAppDataRetentionProvenOnPhone": false'
echo 'RELEASE_IDENTITY_GUARDS=PASS'
