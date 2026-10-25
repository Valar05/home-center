#!/usr/bin/env bash
# Repo-owned preflight/lint tests: no project mutation, no network, no build quota.
set -Eeuo pipefail
here="$(cd -P "$(dirname "$(realpath "${BASH_SOURCE[0]}")")" && pwd -P)"
script="$here/ritsu_phone_android_v017.sh"
contract="$here/ritsu_phone_android_v017.contract.json"
[ -f "$script" ] && [ -f "$contract" ] || { echo "FAIL=missing_campaign_or_contract"; exit 1; }
bash -n "$script"
echo "BASH_SYNTAX=PASS"
if command -v python3 >/dev/null 2>&1; then
  python3 -m json.tool "$contract" >/dev/null
  echo "CONTRACT_JSON=PASS"
fi
grep -Fq 'RESOLVED_REPO=' "$script"
grep -Fq 'EXECUTION_DIR=' "$script"
grep -Fq 'git remote get-url origin' "$script"
grep -Fq 'HEAD:android/ritsu-control/app' "$script"
grep -Fq 'download "$dependency=$abiVersion") >> "$ROOT/log/aapt2-signed-download.log" 2>&1 ||' "$script"
echo "ENTRYPOINT_GUARDS=PASS"
# The owner may run this campaign while their current cwd is a different Godot repo.
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
cp "$script" "$tmp/standalone.sh"
if bash "$tmp/standalone.sh" doctor >"$tmp/negative.log" 2>&1; then
  echo 'FAIL=standalone_script_unexpectedly_allowed'
  exit 1
fi
grep -Fq 'FAIL=self_location_not_inside_canonical_repo_layout' "$tmp/negative.log" ||
  { cat "$tmp/negative.log"; echo 'FAIL=wrong_location_not_rejected'; exit 1; }
echo "FOREIGN_WORKSPACE_REJECTION=PASS"
