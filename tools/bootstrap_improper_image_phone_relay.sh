#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

# Bootstrap invariant: relay recovery must not depend on Git LFS payload
# availability. Only deterministic executable source plus the single contract
# document required by the acceptance test are materialized on the phone.
export GIT_LFS_SKIP_SMUDGE=1
export GIT_CONFIG_COUNT=2
export GIT_CONFIG_KEY_0=filter.lfs.smudge
export GIT_CONFIG_VALUE_0='git-lfs smudge --skip -- %f'
export GIT_CONFIG_KEY_1=filter.lfs.process
export GIT_CONFIG_VALUE_1='git-lfs filter-process --skip'

TARGET_SHA="dd6d89c6bc6e4326dad6a348b868578df1b3e4fe"
STATE="$HOME/.local/state/home-center/improper-image-delivery"
SOURCE="$STATE/bootstrap-source"
LEGACY_WORKTREE="$HOME/.cache/fortress/improper-image-${TARGET_SHA:0:8}"
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

# Scrub the half-created worktree left by the first bootstrap attempt. A failed
# LFS checkout can leave Git metadata even when its working files are incomplete.
if git worktree list --porcelain | grep -Fqx "worktree $LEGACY_WORKTREE"; then
  git worktree remove --force "$LEGACY_WORKTREE" 2>/dev/null || true
fi
rm -rf "$LEGACY_WORKTREE"
git worktree prune

# Non-cone sparse patterns select the complete tools tree and exactly one docs
# file required by test_improper_image_delivery_contract.py. Evidence assets are
# not selected, so the broken/missing LFS objects cannot participate.
git sparse-checkout set --no-cone '/tools/' '/docs/IMPROPER_IMAGE_DELIVERY_CAMPAIGN.md'
git checkout --detach --force "$TARGET_SHA"

test -f "$SOURCE/tools/test_improper_image_delivery_contract.py"
test -f "$SOURCE/tools/setup_android_phone_home_center_relay.sh"
test -f "$SOURCE/tools/android_phone_home_center_relay.py"
test -f "$SOURCE/docs/IMPROPER_IMAGE_DELIVERY_CAMPAIGN.md"

python3 "$SOURCE/tools/test_improper_image_delivery_contract.py"
bash "$SOURCE/tools/setup_android_phone_home_center_relay.sh"

cat <<EOF
HOME CENTER PHONE RELAY RETURNED
Pinned source: $TARGET_SHA
Sparse surface: tools/ + docs/IMPROPER_IMAGE_DELIVERY_CAMPAIGN.md
LFS surface: excluded
Queued image canary: phc_improper_image_dd6d89c6_canary_v1
Do not run another repair or image script. Return to ChatGPT/Home Center so the queued canary receipt can be consumed.
EOF
