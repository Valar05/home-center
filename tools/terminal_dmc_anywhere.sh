#!/usr/bin/env bash
set -euo pipefail

# Terminal DMC anywhere bootstrap.
#
# Launchable from any directory. This bootstrap owns a sparse Home Center source
# checkout and a sparse immutable revision worktree containing only the text
# files Terminal DMC needs. Unrelated LFS/media files never enter the checkout.
# The operator's current repository is never mutated.

export GIT_LFS_SKIP_SMUDGE=1

REPO="Valar05/home-center"
BRANCH="codex/terminal-dmc-vertical-slice"
HTTPS_URL="https://github.com/Valar05/home-center.git"
SSH_URL="git@github.com:Valar05/home-center.git"

BOOT_ROOT="${HC_DATA_DIR:-$HOME/.local/share/home-center}/terminal-dmc-bootstrap"
# v2 intentionally abandons the earlier broad checkout in place. It may be
# dirty because historical LFS attributes classify ordinary MP4 blobs as LFS.
SOURCE="$BOOT_ROOT/source-sparse-v2"
LOCK="$BOOT_ROOT/bootstrap-v2.lock"
LOCK_OWNER="$LOCK/pid"
DATA_ROOT="${HC_DATA_DIR:-$HOME/.local/share/home-center}/terminal-dmc"
REVISIONS="$DATA_ROOT/revisions"

CAMPAIGN_PATHS=(
  tools/terminal_dmc_campaign.sh
  tools/terminal_dmc_anywhere.sh
  tools/terminal_dmc.py
  tools/test_terminal_dmc.py
  tools/terminal_dmc_prove.py
  tools/terminal_dmc_anticipation.py
  tools/test_terminal_dmc_anticipation.py
  docs/TERMINAL_DMC_VERTICAL_SLICE.md
)

need() {
  command -v "$1" >/dev/null 2>&1 || {
    printf 'BLOCKED: missing required command: %s\n' "$1" >&2
    exit 20
  }
}

release_lock() {
  rm -rf "$LOCK" 2>/dev/null || true
}

acquire_lock() {
  if mkdir "$LOCK" 2>/dev/null; then
    printf '%s\n' "$$" > "$LOCK_OWNER"
    return 0
  fi

  local owner=""
  owner="$(cat "$LOCK_OWNER" 2>/dev/null || true)"
  if [ -n "$owner" ] && kill -0 "$owner" 2>/dev/null; then
    echo "BLOCKED: another Terminal DMC sparse bootstrap is active: $LOCK (pid $owner)" >&2
    exit 21
  fi

  # v2 originally exec'd into the campaign while still holding this mkdir lock,
  # which guaranteed a stale directory after the bootstrap shell disappeared.
  # A missing/dead owner therefore means stale bootstrap state, not an active
  # campaign. Reclaim it deterministically instead of asking the operator to
  # perform manual cleanup.
  echo "RECOVER: removing stale Terminal DMC bootstrap lock: $LOCK" >&2
  rm -rf "$LOCK"
  mkdir "$LOCK"
  printf '%s\n' "$$" > "$LOCK_OWNER"
}

need bash
need git
need python3
mkdir -p "$BOOT_ROOT" "$REVISIONS"
acquire_lock
trap release_lock EXIT INT TERM

clone_source() {
  if [ -e "$SOURCE" ]; then
    echo "BLOCKED: sparse bootstrap source exists but is not a Git checkout: $SOURCE" >&2
    exit 22
  fi

  mkdir -p "$(dirname "$SOURCE")"

  if command -v gh >/dev/null 2>&1 && gh auth status >/dev/null 2>&1; then
    if gh repo clone "$REPO" "$SOURCE" -- --filter=blob:none --no-checkout; then
      return 0
    fi
    rm -rf "$SOURCE"
  fi

  if command -v ssh >/dev/null 2>&1; then
    if GIT_SSH_COMMAND="ssh -o BatchMode=yes -o ConnectTimeout=8" \
      git clone --filter=blob:none --no-checkout "$SSH_URL" "$SOURCE"; then
      return 0
    fi
    rm -rf "$SOURCE"
  fi

  if git clone --filter=blob:none --no-checkout "$HTTPS_URL" "$SOURCE"; then
    return 0
  fi

  rm -rf "$SOURCE"
  echo "BLOCKED: could not authenticate a clean clone of $REPO" >&2
  echo "Authenticate GitHub with gh or git/ssh, then rerun this same bootstrap." >&2
  exit 23
}

if [ ! -d "$SOURCE/.git" ]; then
  clone_source
fi

origin="$(git -C "$SOURCE" remote get-url origin 2>/dev/null || true)"
case "$origin" in
  *Valar05/home-center.git|*Valar05/home-center) ;;
  *)
    echo "BLOCKED: campaign-owned sparse source has unexpected origin: ${origin:-NONE}" >&2
    exit 24
    ;;
esac

# Fetch metadata/blobs for the campaign branch without checking out the broad
# repository tree.
git -C "$SOURCE" fetch --prune origin \
  "+refs/heads/$BRANCH:refs/remotes/origin/$BRANCH"

# Configure exact-file sparse checkout before materializing any branch content.
# This is intentionally non-cone because one required file lives under docs/
# while docs/evidence contains unrelated LFS payloads.
git -C "$SOURCE" sparse-checkout init --no-cone >/dev/null 2>&1 || true
git -C "$SOURCE" sparse-checkout set --no-cone "${CAMPAIGN_PATHS[@]}"
git -C "$SOURCE" checkout --detach "refs/remotes/origin/$BRANCH" >/dev/null

head="$(git -C "$SOURCE" rev-parse HEAD)"
remote_head="$(git -C "$SOURCE" rev-parse "refs/remotes/origin/$BRANCH")"
if [ "$head" != "$remote_head" ]; then
  echo "BLOCKED: fetched branch identity does not match sparse source" >&2
  exit 26
fi

if [ -n "$(git -C "$SOURCE" status --porcelain=v1 --untracked-files=normal)" ]; then
  echo "BLOCKED: sparse campaign source is unexpectedly dirty." >&2
  git -C "$SOURCE" status --short >&2 || true
  echo "Path: $SOURCE" >&2
  exit 25
fi

missing=0
for path in "${CAMPAIGN_PATHS[@]}"; do
  if [ ! -f "$SOURCE/$path" ]; then
    printf 'MISSING: %s\n' "$path" >&2
    missing=1
  fi
done
if [ "$missing" -ne 0 ]; then
  echo "BLOCKED: fetched campaign branch is incomplete" >&2
  exit 27
fi

# Pre-create the exact immutable revision worktree that terminal_dmc_campaign.sh
# expects. The campaign therefore never needs to make a broad worktree checkout.
revdir="$REVISIONS/$head"
if [ ! -d "$revdir" ]; then
  git -C "$SOURCE" worktree add --detach --no-checkout "$revdir" "$head" >/dev/null
  git -C "$revdir" sparse-checkout init --no-cone >/dev/null 2>&1 || true
  git -C "$revdir" sparse-checkout set --no-cone "${CAMPAIGN_PATHS[@]}"
  git -C "$revdir" checkout --detach "$head" >/dev/null
fi

if [ "$(git -C "$revdir" rev-parse HEAD 2>/dev/null || true)" != "$head" ]; then
  echo "BLOCKED: sparse revision worktree commit mismatch: $revdir" >&2
  exit 28
fi
if [ -n "$(git -C "$revdir" status --porcelain=v1 --untracked-files=normal)" ]; then
  echo "BLOCKED: sparse revision worktree is unexpectedly dirty." >&2
  git -C "$revdir" status --short >&2 || true
  exit 29
fi

printf 'Terminal DMC sparse anywhere bootstrap\n'
printf 'source: %s\n' "$SOURCE"
printf 'revision: %s\n' "$revdir"
printf 'commit: %s\n' "$head"
printf 'caller cwd preserved: %s\n' "$PWD"
printf 'LFS/media checkout: bypassed\n'

export HC_REPO_ROOT="$SOURCE"

# The bootstrap lock protects only source/revision preparation. Release it
# explicitly before replacing this process with the long-lived campaign. The
# earlier implementation relied on an EXIT trap across exec, which does not run
# after the shell is replaced and therefore left a permanent stale lock.
release_lock
trap - EXIT INT TERM
exec bash "$SOURCE/tools/terminal_dmc_campaign.sh" "$@"
