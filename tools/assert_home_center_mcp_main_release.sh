#!/data/data/com.termux/files/usr/bin/sh
set -eu

ROOT="${1:-$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)}"

fail() {
  echo "homeCenterMcp publish gate: $1" >&2
  exit 23
}

git -C "$ROOT" rev-parse --is-inside-work-tree >/dev/null 2>&1 || fail "source is not a Git working tree"
git -C "$ROOT" remote get-url origin >/dev/null 2>&1 || fail "origin remote is required"
git -C "$ROOT" fetch --quiet origin refs/heads/main:refs/remotes/origin/main || fail "could not refresh origin/main"

HEAD_SHA="$(git -C "$ROOT" rev-parse HEAD)"
MAIN_SHA="$(git -C "$ROOT" rev-parse refs/remotes/origin/main)"
BRANCH="$(git -C "$ROOT" symbolic-ref --quiet --short HEAD 2>/dev/null || true)"
RELEASE_MODE=""

if [ "$BRANCH" = "main" ]; then
  RELEASE_MODE="current-main"
elif [ "${GITHUB_ACTIONS:-}" = "true" ] && [ "${GITHUB_REF:-}" = "refs/heads/main" ] && [ "${GITHUB_SHA:-}" = "$HEAD_SHA" ]; then
  RELEASE_MODE="github-main-pin"
else
  fail "source must be branch main (or the immutable GitHub Actions refs/heads/main checkout); got ${BRANCH:-detached}"
fi

if [ "$RELEASE_MODE" = "github-main-pin" ]; then
  git -C "$ROOT" merge-base --is-ancestor "$HEAD_SHA" "$MAIN_SHA" || fail "pinned GitHub Actions main commit $HEAD_SHA is no longer an ancestor of current origin/main $MAIN_SHA"
else
  [ "$HEAD_SHA" = "$MAIN_SHA" ] || fail "HEAD $HEAD_SHA is not the current origin/main commit $MAIN_SHA"
fi

[ -z "$(git -C "$ROOT" status --porcelain --untracked-files=all)" ] || fail "working tree is not clean"

if [ "$RELEASE_MODE" = "github-main-pin" ] && [ "$HEAD_SHA" != "$MAIN_SHA" ]; then
  printf '%s\n' "homeCenterMcp publish gate: verified pinned main release $HEAD_SHA; current origin/main advanced safely to descendant $MAIN_SHA"
else
  printf '%s\n' "homeCenterMcp publish gate: verified origin/main $MAIN_SHA"
fi
