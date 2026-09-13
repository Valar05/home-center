#!/usr/bin/env bash
set -euo pipefail

# Terminal DMC anywhere bootstrap.
#
# This is the only script that must tolerate being launched from an unrelated
# working directory. It owns a clean source checkout, fetches the exact campaign
# branch, verifies the campaign surface, then hands off to the durable campaign.
# It never mutates the operator's current repository.
#
# Terminal DMC is text-only. Home Center contains unrelated Git LFS evidence,
# including historical objects that may no longer exist on the LFS server. Do
# not let those unrelated payloads block this campaign. Keeping this exported
# also protects the campaign's later detached worktree checkout.
export GIT_LFS_SKIP_SMUDGE=1

REPO="Valar05/home-center"
BRANCH="codex/terminal-dmc-vertical-slice"
HTTPS_URL="https://github.com/Valar05/home-center.git"
SSH_URL="git@github.com:Valar05/home-center.git"

BOOT_ROOT="${HC_DATA_DIR:-$HOME/.local/share/home-center}/terminal-dmc-bootstrap"
SOURCE="$BOOT_ROOT/source"
LOCK="$BOOT_ROOT/bootstrap.lock"

need() {
  command -v "$1" >/dev/null 2>&1 || {
    printf 'BLOCKED: missing required command: %s\n' "$1" >&2
    exit 20
  }
}

need bash
need git
need python3
mkdir -p "$BOOT_ROOT"

if ! mkdir "$LOCK" 2>/dev/null; then
  echo "BLOCKED: another Terminal DMC bootstrap is active: $LOCK" >&2
  exit 21
fi
trap 'rmdir "$LOCK" 2>/dev/null || true' EXIT INT TERM

clone_source() {
  if [ -e "$SOURCE" ]; then
    echo "BLOCKED: bootstrap source exists but is not a Git checkout: $SOURCE" >&2
    exit 22
  fi

  mkdir -p "$(dirname "$SOURCE")"

  # Prefer GitHub CLI because this repository is private and gh can reuse the
  # operator's existing authenticated GitHub session without embedding secrets.
  if command -v gh >/dev/null 2>&1 && gh auth status >/dev/null 2>&1; then
    if gh repo clone "$REPO" "$SOURCE" -- --filter=blob:none --no-checkout; then
      return 0
    fi
    rm -rf "$SOURCE"
  fi

  # Next try a non-interactive SSH clone. Fail quickly instead of hanging on an
  # unavailable key or host prompt.
  if command -v ssh >/dev/null 2>&1; then
    if GIT_SSH_COMMAND="ssh -o BatchMode=yes -o ConnectTimeout=8" \
      git clone --filter=blob:none --no-checkout "$SSH_URL" "$SOURCE"; then
      return 0
    fi
    rm -rf "$SOURCE"
  fi

  # Last resort: HTTPS. Existing Git credential helpers may satisfy auth. Git is
  # allowed to prompt if the operator has configured interactive credentials.
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
    echo "BLOCKED: campaign-owned source has unexpected origin: ${origin:-NONE}" >&2
    exit 24
    ;;
esac

if [ -n "$(git -C "$SOURCE" status --porcelain=v1 --untracked-files=normal)" ]; then
  echo "BLOCKED: campaign-owned bootstrap checkout is dirty; refusing destructive cleanup." >&2
  echo "Path: $SOURCE" >&2
  exit 25
fi

# Fetch the campaign branch directly. No dependence on the caller's current
# directory, current branch, or existence of a Home Center checkout elsewhere.
git -C "$SOURCE" fetch --prune origin \
  "+refs/heads/$BRANCH:refs/remotes/origin/$BRANCH"

# GIT_LFS_SKIP_SMUDGE is deliberately inherited here. The campaign requires
# only normal Git text files, so missing unrelated LFS objects are irrelevant.
git -C "$SOURCE" checkout --detach "refs/remotes/origin/$BRANCH" >/dev/null

head="$(git -C "$SOURCE" rev-parse HEAD)"
remote_head="$(git -C "$SOURCE" rev-parse "refs/remotes/origin/$BRANCH")"
if [ "$head" != "$remote_head" ]; then
  echo "BLOCKED: fetched branch identity does not match checked-out source" >&2
  exit 26
fi

missing=0
for path in \
  tools/terminal_dmc_campaign.sh \
  tools/terminal_dmc.py \
  tools/test_terminal_dmc.py \
  tools/terminal_dmc_prove.py \
  tools/terminal_dmc_anticipation.py \
  tools/test_terminal_dmc_anticipation.py \
  docs/TERMINAL_DMC_VERTICAL_SLICE.md
do
  if [ ! -f "$SOURCE/$path" ]; then
    printf 'MISSING: %s\n' "$path" >&2
    missing=1
  fi
done
if [ "$missing" -ne 0 ]; then
  echo "BLOCKED: fetched campaign branch is incomplete" >&2
  exit 27
fi

printf 'Terminal DMC anywhere bootstrap\n'
printf 'source: %s\n' "$SOURCE"
printf 'commit: %s\n' "$head"
printf 'caller cwd preserved: %s\n' "$PWD"
printf 'LFS smudge: skipped (campaign is text-only)\n'

# The durable campaign uses HC_REPO_ROOT as its source authority. The caller's
# working directory and working repository remain untouched. The LFS skip env
# remains exported so campaign-owned worktree creation cannot re-trigger the
# unrelated missing LFS object.
export HC_REPO_ROOT="$SOURCE"
exec bash "$SOURCE/tools/terminal_dmc_campaign.sh" "$@"
