#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

TARGET_SHA="dd6d89c6bc6e4326dad6a348b868578df1b3e4fe"
STATE="$HOME/.local/state/home-center/improper-image-delivery"
SOURCE="$STATE/bootstrap-source"
WORKTREE="$HOME/.cache/fortress/improper-image-${TARGET_SHA:0:8}"
mkdir -p "$STATE" "$(dirname "$WORKTREE")"

[ -f "$HOME/.config/home-center/codex-hub.json" ] || {
  echo 'BLOCKED: Home Center pairing config is missing; do not attempt image repair.' >&2
  exit 2
}

if [ ! -d "$SOURCE/.git" ]; then
  rm -rf "$SOURCE"
  GIT_LFS_SKIP_SMUDGE=1 gh repo clone Valar05/home-center "$SOURCE" -- --filter=blob:none
fi
cd "$SOURCE"
GIT_LFS_SKIP_SMUDGE=1 git fetch --no-tags origin "$TARGET_SHA"
git cat-file -e "$TARGET_SHA^{commit}"

if [ -e "$WORKTREE/.git" ]; then
  test "$(git -C "$WORKTREE" rev-parse HEAD)" = "$TARGET_SHA" || {
    echo "BLOCKED: pinned worktree exists at the wrong commit: $WORKTREE" >&2
    exit 3
  }
else
  rm -rf "$WORKTREE"
  git worktree add --detach "$WORKTREE" "$TARGET_SHA"
fi

python3 "$WORKTREE/tools/test_improper_image_delivery_contract.py"
bash "$WORKTREE/tools/setup_android_phone_home_center_relay.sh"

cat <<EOF
HOME CENTER PHONE RELAY RETURNED
Pinned source: $TARGET_SHA
Queued image canary: phc_improper_image_dd6d89c6_canary_v1
Do not run another repair or image script. Return to ChatGPT/Home Center so the queued canary receipt can be consumed.
EOF
