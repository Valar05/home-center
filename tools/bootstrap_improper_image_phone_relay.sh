#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

# Bootstrap invariant: relay recovery must not depend on Git LFS payload
# availability or on Shizuku/rish. Only deterministic executable source is
# checked out. The one Markdown file needed by the contract test is materialized
# with `git show`, which reads the Git blob directly and never asks LFS to smudge.
export GIT_LFS_SKIP_SMUDGE=1
export GIT_CONFIG_COUNT=2
export GIT_CONFIG_KEY_0=filter.lfs.smudge
export GIT_CONFIG_VALUE_0='git-lfs smudge --skip -- %f'
export GIT_CONFIG_KEY_1=filter.lfs.process
export GIT_CONFIG_VALUE_1='git-lfs filter-process --skip'

TARGET_SHA="39f38e1de30e76e5edd8d554779f9fcb9a8be439"
STATE="$HOME/.local/state/home-center/improper-image-delivery"
SOURCE="$STATE/bootstrap-source"
LEGACY_WORKTREE="$HOME/.cache/fortress/improper-image-${TARGET_SHA:0:8}"
DOC_REL="docs/IMPROPER_IMAGE_DELIVERY_CAMPAIGN.md"
mkdir -p "$STATE" "$(dirname "$LEGACY_WORKTREE")"

[ -f "$HOME/.config/home-center/codex-hub.json" ] || {
  echo 'BLOCKED: Home Center pairing config is missing; do not attempt image repair.' >&2
  exit 2
}

if [ ! -d "$SOURCE/.git" ]; then
  rm -rf "$SOURCE"
  gh repo clone Valar05/home-center "$SOURCE" -- --filter=blob:none --no-checkout
fi
cd "$SOURCE"
git fetch --no-tags origin "$TARGET_SHA"
git cat-file -e "$TARGET_SHA^{commit}"

# Scrub stale worktrees from earlier LFS-failing bootstrap attempts.
for stale in "$HOME/.cache/fortress/improper-image-dd6d89c6" "$LEGACY_WORKTREE"; do
  if git worktree list --porcelain | grep -Fqx "worktree $stale"; then
    git worktree remove --force "$stale" 2>/dev/null || true
  fi
  rm -rf "$stale"
done
git worktree prune

# Cone mode selects only deterministic tools. Evidence images under docs/evidence
# are unreachable, so missing LFS objects cannot participate in relay recovery.
git sparse-checkout set --cone tools
git checkout --detach --force "$TARGET_SHA"

# The contract test audits this exact Markdown file. Read the plain Git blob
# directly instead of widening the sparse checkout into docs/.
mkdir -p "$SOURCE/docs"
git show "$TARGET_SHA:$DOC_REL" > "$SOURCE/$DOC_REL"

test -f "$SOURCE/tools/test_improper_image_delivery_contract.py"
test -f "$SOURCE/tools/test_phone_relay_shizuku_independence.py"
test -f "$SOURCE/tools/setup_android_phone_home_center_relay.sh"
test -f "$SOURCE/tools/android_phone_home_center_relay.py"
test -s "$SOURCE/$DOC_REL"

python3 "$SOURCE/tools/test_improper_image_delivery_contract.py"
bash "$SOURCE/tools/setup_android_phone_home_center_relay.sh"

cat <<EOF
HOME CENTER PHONE RELAY RETURNED
Pinned source: $TARGET_SHA
Checkout surface: tools/ only
Contract doc: materialized directly from pinned Git blob
LFS surface: excluded
Shizuku baseline: excluded
Image canary: not claimed by bootstrap; Home Center may now dispatch tools/improper_image_delivery_campaign.sh through phone_shell
Do not run another repair or image script manually. Return to ChatGPT/Home Center.
EOF
