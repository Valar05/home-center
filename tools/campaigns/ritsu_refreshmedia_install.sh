#!/usr/bin/env bash
# Install/update repo-owned refreshmedia in the current Termux PATH.
# Does not alter the owner's checkout, Android apps, or storage files.
set -Eeuo pipefail
umask 077
fail(){ printf 'REFRESHMEDIA_INSTALL=FAIL REASON=%s\n' "$1" >&2; exit 2; }
self="$(realpath "${BASH_SOURCE[0]}")"
root="$(cd -P "$(dirname "$self")/../.." && pwd -P)"
src="$root/tools/campaigns/refreshmedia"
[ "$self" = "$root/tools/campaigns/ritsu_refreshmedia_install.sh" ] ||
  fail not_repo_owned_entrypoint
[ -f "$src" ] || fail refreshmedia_source_missing
bash -n "$src" || fail refreshmedia_syntax_error
case "$(git -C "$root" remote get-url origin)" in
  https://github.com/Valar05/home-center.git|https://github.com/Valar05/home-center|git@github.com:Valar05/home-center.git) ;;
  *) fail wrong_repository;;
esac
head="$(git -C "$root" rev-parse HEAD)"
[ -z "${RITSU_STICKY_PIN:-}" ] || [ "$head" = "$RITSU_STICKY_PIN" ] ||
  fail wrong_source_commit
[ "$(git -C "$root" hash-object "$src")" = "$(git -C "$root" rev-parse "HEAD:tools/campaigns/refreshmedia")" ] ||
  fail refreshmedia_not_committed
prefix="${PREFIX:-}"
[ -n "$prefix" ] || fail Termux_PREFIX_not_available
[ -d "$prefix/bin" ] || fail Termux_bin_not_available
dest="$prefix/bin/refreshmedia"
if [ -e "$dest" ] || [ -L "$dest" ]; then
  [ -f "$dest" ] && [ ! -L "$dest" ] ||
    fail existing_refreshmedia_path_is_not_a_regular_file
  if cmp -s "$src" "$dest"; then
    echo "REFRESHMEDIA_INSTALL=ALREADY_CURRENT"
    echo "REFRESHMEDIA_COMMAND=$dest"
    exit 0
  fi
  grep -Fq 'RITSU_REFRESHMEDIA_MANAGED_V1' "$dest" ||
    fail existing_refreshmedia_command_not_ours_preserved
fi
stage="$(mktemp "$prefix/bin/.refreshmedia-stage.XXXXXXXX")" ||
  fail cannot_stage_command
trap 'rm -f "$stage"' EXIT
cp "$src" "$stage"
chmod 755 "$stage"
cmp -s "$stage" "$src" || fail installed_bytes_mismatch
mv -f "$stage" "$dest"
trap - EXIT
[ -x "$dest" ] || fail installed_command_not_executable
cmp -s "$dest" "$src" || fail installed_command_readback_drift
resolved="$(command -v refreshmedia || true)"
[ "$resolved" = "$dest" ] ||
  fail refreshmedia_PATH_does_not_resolve_to_installed_command
echo "REFRESHMEDIA_INSTALL=PASS"
echo "REFRESHMEDIA_COMMAND=$dest"
echo "SOURCE_SHA=$head"
echo 'REFRESHMEDIA_DEFAULT=Android_Downloads_only'
echo 'REFRESHMEDIA_RUNTIME_REQUIRES=termux-api_and_Termux_API_companion'
