#!/usr/bin/env bash
set -Eeuo pipefail
[ "${GITHUB_ACTIONS:-}" = true ] || exit 2
source="$(cd -P "$(dirname "$0")/../.." && pwd -P)"
pin="$(git -C "$source" rev-parse HEAD)"
root="$(mktemp -d)"
original="$root/GodotProjects/home-center"
mkdir -p "$original/tools" "$root/elsewhere"
for name in home_center_phone_relay_recover.sh phone_hands_watchdog.sh ssh_axis.py; do
  printf '%s\n' "valuable uncommitted $name" > "$original/tools/$name"
done
before="$(cd "$original" && sha256sum tools/* | sha256sum | cut -d ' ' -f 1)"
(
  cd "$original"
  RITSU_STICKY_PIN="$pin" RITSU_STICKY_WORKDIR="$root/isolated" \
    bash "$source/tools/campaigns/ritsu_sticky_onepaste.sh" doctor
)
after="$(cd "$original" && sha256sum tools/* | sha256sum | cut -d ' ' -f 1)"
[ "$before" = "$after" ] || { echo "FAIL=modified_original"; exit 2; }
(
  cd "$root/elsewhere"
  RITSU_STICKY_PIN="$pin" RITSU_STICKY_WORKDIR="$root/isolated" \
    bash "$source/tools/campaigns/ritsu_sticky_onepaste.sh" doctor
)
[ "$(git -C "$root/isolated" rev-parse HEAD)" = "$pin" ]
echo "ISOLATED_BOOTSTRAP_CI=PASS"
echo "ORIGINAL_FILES_PRESERVED=PASS"
echo "ARBITRARY_CWD_AND_RERUN=PASS"
