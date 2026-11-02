#!/usr/bin/env bash
# Host CI tests. Tests invocation semantics, not actual Android indexing.
set -Eeuo pipefail
[ "${GITHUB_ACTIONS:-}" = true ] || { echo 'MEDIA_TEST=CI_ONLY';exit 2; }
root="$(cd -P "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd -P)"
refresh="$root/tools/campaigns/refreshmedia"
installer="$root/tools/campaigns/ritsu_refreshmedia_install.sh"
bash -n "$refresh"
bash -n "$installer"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
mkdir -p "$tmp/shared/downloads" "$tmp/home/storage" "$tmp/usr/bin"
ln -s "$tmp/shared/downloads" "$tmp/home/storage/downloads"
printf 'file visible to Android\n' > "$tmp/shared/downloads/first file.mp3"
cat > "$tmp/mock-scanner" <<'MOCK'
#!/bin/bash
printf '%s\n' "$*" >> "$REFRESHMEDIA_TEST_LOG"
MOCK
chmod +x "$tmp/mock-scanner"
export GITHUB_ACTIONS=true
export RITSU_REFRESHMEDIA_TEST_MODE=1
export RITSU_REFRESHMEDIA_TEST_SHARED_ROOT="$tmp/shared"
export RITSU_REFRESHMEDIA_TEST_SCANNER="$tmp/mock-scanner"
export REFRESHMEDIA_TEST_LOG="$tmp/scan.log"
export HOME="$tmp/home"
export PREFIX="$tmp/usr"
export PATH="$PREFIX/bin:$PATH"
bash "$refresh" "$tmp/shared/downloads/first file.mp3" > "$tmp/file.out"
grep -Fq 'MEDIA_REFRESH=REQUESTED_FILE' "$tmp/file.out"
grep -Fxq "$tmp/shared/downloads/first file.mp3" "$tmp/scan.log"
bash "$refresh" > "$tmp/default.out"
grep -Fq 'MEDIA_REFRESH=REQUESTED_RECURSIVE' "$tmp/default.out"
grep -Fxq -- "-r $tmp/shared/downloads" "$tmp/scan.log"
bash "$refresh" "$tmp/shared/downloads" > "$tmp/directory.out"
grep -Fq 'MEDIA_REFRESH=REQUESTED_RECURSIVE' "$tmp/directory.out"
if bash "$refresh" "$tmp/home/storage" >"$tmp/private.out" 2>&1; then
  echo 'MEDIA_TEST=private_scan_improperly_allowed'; exit 2
fi
grep -Fq 'refused_nonshared_test_path' "$tmp/private.out"
if RITSU_REFRESHMEDIA_TEST_SCANNER="$tmp/does-not-exist" bash "$refresh" > "$tmp/missing.out" 2>&1; then
  echo 'MEDIA_TEST=missing_api_improperly_accepted'; exit 2
fi
grep -Fq 'termux_api_unavailable' "$tmp/missing.out"
bash "$installer" > "$tmp/installed.out"
grep -Fq 'REFRESHMEDIA_INSTALL=PASS' "$tmp/installed.out"
test "$(command -v refreshmedia)" = "$PREFIX/bin/refreshmedia"
cmp "$refresh" "$PREFIX/bin/refreshmedia"
bash "$installer" > "$tmp/rerun.out"
grep -Fq 'REFRESHMEDIA_INSTALL=ALREADY_CURRENT' "$tmp/rerun.out"
printf '#!/bin/bash\necho USER_OWNED_COMMAND\n' > "$PREFIX/bin/refreshmedia"
if bash "$installer" > "$tmp/collision.out" 2>&1; then
  echo 'MEDIA_TEST=overwrote_user_command'; exit 2
fi
grep -Fq 'existing_refreshmedia_command_not_ours_preserved' "$tmp/collision.out"
grep -Fq 'USER_OWNED_COMMAND' "$PREFIX/bin/refreshmedia"
echo 'REFRESHMEDIA_TEST_FILE=PASS'
echo 'REFRESHMEDIA_TEST_RECURSIVE_DEFAULT=PASS'
echo 'REFRESHMEDIA_TEST_PRIVATE_PATH_REFUSAL=PASS'
echo 'REFRESHMEDIA_TEST_MISSING_API_FAILS_CLOSED=PASS'
echo 'REFRESHMEDIA_TEST_INSTALL_AND_RERUN=PASS'
echo 'REFRESHMEDIA_TEST_EXISTING_COMMAND_PRESERVED=PASS'
