#!/usr/bin/env bash
# Repo-owned offline preflight: full syntax + contract + regression guards.
set -Eeuo pipefail
here="$(cd -P "$(dirname "$(realpath "${BASH_SOURCE[0]}")")" && pwd -P)"
script="$here/ritsu_phone_android_v017.sh"
contract="$here/ritsu_phone_android_v017.contract.json"
[ -f "$script" ] && [ -f "$contract" ] || {
  echo "FAIL=missing_campaign_or_contract"; exit 1;
}
bash -n "$script" || { echo "FAIL=canonical_bash_syntax"; exit 1; }
echo "BASH_SYNTAX=PASS"
if command -v python3 >/dev/null 2>&1; then
  python3 -m json.tool "$contract" >/dev/null || {
    echo "FAIL=campaign_contract_json"; exit 1;
  }
  echo "CONTRACT_JSON=PASS"
fi
assert_in(){
  local label="$1" pattern="$2"
  if ! grep -Fq -- "$pattern" "$script"; then
    echo "FAIL=missing_guard:$label"
    exit 1
  fi
}
assert_in repo_identity 'git remote get-url origin'
assert_in directory_receipt 'RESOLVED_REPO='
assert_in execution_receipt 'EXECUTION_DIR='
assert_in source_tree_guard 'HEAD:android/ritsu-control/app'
assert_in script_commit_readback 'running_file_does_not_match_committed_script'
assert_in stderr_receipt 'unhandled_shell_error'
assert_in abi_resolve 'AAPT2_ABI_RESOLVE=$dependency'
assert_in abi_policy 'aapt2-abi-policy-'
assert_in abi_download 'AAPT2_ABI_DOWNLOAD=$dependency'
assert_in abi_extract 'AAPT2_ABI_EXTRACT=$dependency'
assert_in abi_ready 'AAPT2_ABI_READY=$dependency'
assert_in sdk35_resource_link 'test_aapt2'
assert_in gradle_tests ':app:testDebugUnitTest'
assert_in gradle_apk ':app:assembleDebug'
assert_in download_preflight 'Phone Downloads inaccessible'
assert_in downloads_copy_check 'APK checksum mismatch during Downloads copy'
assert_in downloads_publish_check 'Published Downloads APK checksum mismatch'
assert_in downloads_signature_check 'Published Downloads APK signature invalid'
assert_in downloads_delivery 'DOWNLOADS_APK_VERIFIED='
if grep -Fq 'policy "$dependency" | awk' "$script"; then
  echo "FAIL=unsafe_apt_cache_short_circuit_pipeline"
  exit 1
fi
echo "ENTRYPOINT_GUARDS=PASS"
echo "ABI_SILENT_EXIT_REGRESSION=PASS"
echo "DOWNLOADS_DELIVERY_REGRESSION=PASS"
# Foreign-workspace execution must fail before any network/build mutation.
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
cp "$script" "$tmp/standalone.sh"
if bash "$tmp/standalone.sh" doctor > "$tmp/negative.log" 2>&1; then
  echo "FAIL=standalone_script_unexpectedly_allowed"
  exit 1
fi
grep -Fq 'FAIL=self_location_not_inside_canonical_repo_layout' "$tmp/negative.log" ||
  { cat "$tmp/negative.log"; echo "FAIL=wrong_location_not_rejected"; exit 1; }
echo "FOREIGN_WORKSPACE_REJECTION=PASS"
