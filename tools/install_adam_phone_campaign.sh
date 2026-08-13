#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
SOURCE_ROOT="${HC_REPO_ROOT:-$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)}"
STATE_BASE="${HC_STATE_DIR:-$HOME/.local/state/home-center}"
CAMPAIGN_DIR="$STATE_BASE/adam-campaign"
RUNTIME="$CAMPAIGN_DIR/runtime"
mkdir -p "$CAMPAIGN_DIR"

git -C "$SOURCE_ROOT" rev-parse --is-inside-work-tree >/dev/null 2>&1 || { echo "BLOCKED: not a git worktree: $SOURCE_ROOT" >&2; exit 2; }
git -C "$SOURCE_ROOT" fetch origin main

if [ ! -e "$RUNTIME/.git" ]; then
  rm -rf "$RUNTIME"
  git -C "$SOURCE_ROOT" worktree add --detach "$RUNTIME" origin/main
else
  git -C "$RUNTIME" fetch origin main
  if [ -z "$(git -C "$RUNTIME" status --porcelain)" ]; then
    git -C "$RUNTIME" checkout --detach origin/main
  fi
fi

SCRIPT="$RUNTIME/tools/adam_phone_campaign.sh"
[ -f "$SCRIPT" ] || { echo "BLOCKED: campaign script missing from dedicated runtime: $SCRIPT" >&2; exit 3; }
HC_REPO_ROOT="$RUNTIME" bash "$SCRIPT" install-service
exec env HC_REPO_ROOT="$RUNTIME" "${PREFIX:-$HOME/.local}/bin/adam-campaign" run
