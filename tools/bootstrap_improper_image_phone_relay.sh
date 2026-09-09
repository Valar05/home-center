#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

# This bootstrap must never depend on Git LFS payload availability. The phone only
# needs the deterministic Home Center tools tree to restore the relay; evidence
# images and other LFS assets are deliberately outside the sparse checkout.
export GIT_LFS_SKIP_SMUDGE=1

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

# Scrub the half-created worktree left by the previous bootstrap. A failed LFS
# checkout can leave Git metadata behind even when the files are incomplete.
if git worktree list --porcelain | grep -Fqx "worktree $LEGACY_WORKTREE"; then
  git worktree remove --force "$LEGACY_WORKTREE" 2>/dev/null || true
fi
rm -rf "$LEGACY_WORKTREE"
git worktree prune

# Materialize only deterministic executable source. This prevents unrelated LFS
# evidence assets from participating in relay recovery at all.
git sparse-checkout init --cone
git sparse-checkout set tools
git checkout --detach --force "$TARGET_SHA"

test -f "$SOURCE/tools/test_improper_image_delivery_contract.py"
test -f "$SOURCE/tools/setup_android_phone_home_center_relay.sh"
test -f "$SOURCE/tools/android_phone_home_center_relay.py"

python3 "$SOURCE/tools/test_improper_image_delivery_contract.py"
bash "$SOURCE/tools/setup_android_phone_home_center_relay.sh"

cat <<EOF
HOME CENTER PHONE RELAY RETURNED
Pinned source: $TARGET_SHA
LFS surface: excluded (tools-only sparse checkout)
Queued image canary: phc_improper_image_dd6d89c6_canary_v1
Do not run another repair or image script. Return to ChatGPT/Home Center so the queued canary receipt can be consumed.
EOF
