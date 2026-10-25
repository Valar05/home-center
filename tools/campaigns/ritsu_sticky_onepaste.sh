#!/usr/bin/env bash
# Ritsu Sticky Snippets: isolated one-paste source bootstrap.
# Does NOT touch the caller's current repository or install an APK.
set -Eeuo pipefail
umask 077
mode="${1:-doctor}"
case "$mode" in doctor|build|install) ;; *) echo "BOOTSTRAP_FAIL=invalid_mode"; exit 2;; esac
pin="${RITSU_STICKY_PIN:?Set RITSU_STICKY_PIN to the verified 40-character Git commit}"
[[ "$pin" =~ ^[a-f0-9]{40}$ ]] || { echo "BOOTSTRAP_FAIL=invalid_pin"; exit 2; }
for executable in git bash; do
  command -v "$executable" >/dev/null 2>&1 || {
    echo "BOOTSTRAP_FAIL=missing_$executable"; exit 2;
  }
done
url="https://github.com/Valar05/home-center.git"
work="${RITSU_STICKY_WORKDIR:-$HOME/.local/share/ritsu-campaigns/sticky-${pin:0:12}}"
[ -n "$work" ] && [ "$work" != "/" ] || { echo "BOOTSTRAP_FAIL=bad_workdir";exit 2; }
parent="$(dirname "$work")"
mkdir -p "$parent"
# This private checkout must be completely isolated from the owner's
# GodotProjects/home-center, which may have valuable local changes.
if [ -e "$work" ]; then
  [ -d "$work/.git" ] || { echo "BOOTSTRAP_FAIL=existing_path_not_checkout";exit 2; }
  actual="$(git -C "$work" remote get-url origin)" || exit 2
  [ "$actual" = "$url" ] || { echo "BOOTSTRAP_FAIL=wrong_checkout_remote";exit 2; }
  [ -z "$(git -C "$work" status --porcelain=v1 --untracked-files=all)" ] ||
    { echo "BOOTSTRAP_FAIL=isolated_checkout_dirty_preserved";exit 2; }
else
  mkdir "$work"
  git -C "$work" init -q
  git -C "$work" remote add origin "$url"
fi
echo "ORIGINAL_WORKTREE=UNTOUCHED"
echo "ISOLATED_CHECKOUT=$work"
echo "PINNED_SOURCE=$pin"
GIT_LFS_SKIP_SMUDGE=1 git -C "$work" fetch --no-tags --depth=1 --filter=blob:none origin "$pin"
git -C "$work" sparse-checkout init --cone
git -C "$work" sparse-checkout set android/ritsu-control tools/campaigns
GIT_LFS_SKIP_SMUDGE=1 git -C "$work" checkout --detach -q "$pin"
head="$(git -C "$work" rev-parse HEAD)"
[ "$head" = "$pin" ] || { echo "BOOTSTRAP_FAIL=revision_mismatch";exit 2; }
echo "SOURCE_SHA_VERIFIED=$head"
echo "ISOLATED_BRANCH=$(git -C "$work" symbolic-ref --short -q HEAD || echo detached)"
if [ "$mode" = doctor ]; then
  bash "$work/tools/campaigns/ritsu_sticky_campaign.sh" doctor
  echo "BOOTSTRAP_RESULT=SOURCE_AND_STICKY_PREFLIGHT_VERIFIED"
  echo "APK_RELEASE=BLOCKED_PENDING_EXISTING_SIGNING_IDENTITY"
elif [ "$mode" = install ]; then
  bash "$work/tools/campaigns/ritsu_sticky_install_real.sh" install
else
  bash "$work/tools/campaigns/ritsu_sticky_campaign.sh" build
fi
