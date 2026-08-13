#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

BRANCH="${HC_SPOTIFY_RADIO_BRANCH:-feature/spotify-overlay-radio-20260813}"
EXPECTED_COMMIT="${HC_SPOTIFY_RADIO_EXPECTED_COMMIT:-}"
DEST="${HC_SPOTIFY_RADIO_SOURCE_ROOT:-$HOME/.local/share/home-center/spotify-overlay-radio-src}"
REPO="${HC_SPOTIFY_RADIO_REPO:-Valar05/home-center}"
PARENT="$(dirname "$DEST")"

mkdir -p "$PARENT"
export GIT_LFS_SKIP_SMUDGE=1

if command -v gh >/dev/null 2>&1; then
  gh auth setup-git >/dev/null 2>&1 || true
fi

if [ ! -d "$DEST/.git" ]; then
  rm -rf "$DEST"
  git clone --filter=blob:none --no-checkout --single-branch --branch "$BRANCH" "https://github.com/$REPO.git" "$DEST"
  git -C "$DEST" config core.autocrlf false
  git -C "$DEST" config core.eol lf
  git -C "$DEST" sparse-checkout init --cone
  git -C "$DEST" sparse-checkout set android/operator-overlay tools skills config .continue
else
  current_origin="$(git -C "$DEST" remote get-url origin)"
  case "$current_origin" in
    *"github.com/$REPO.git"|*"github.com:$REPO.git") ;;
    *) echo "BLOCKED: dedicated Spotify radio clone has unexpected origin: $current_origin" >&2; exit 2 ;;
  esac
fi

git -C "$DEST" fetch --prune origin "$BRANCH"
git -C "$DEST" checkout -B "$BRANCH" "origin/$BRANCH"
git -C "$DEST" reset --hard "origin/$BRANCH"
git -C "$DEST" clean -fdx

SOURCE_COMMIT="$(git -C "$DEST" rev-parse HEAD)"
if [ -n "$EXPECTED_COMMIT" ] && [ "$SOURCE_COMMIT" != "$EXPECTED_COMMIT" ]; then
  echo "BLOCKED: Spotify radio source commit mismatch expected=$EXPECTED_COMMIT actual=$SOURCE_COMMIT" >&2
  exit 3
fi

[ -z "$(git -C "$DEST" status --porcelain=v1)" ] || { echo 'BLOCKED: dedicated Spotify radio clone is not clean.' >&2; exit 4; }

python - "$DEST" "$BRANCH" "$SOURCE_COMMIT" <<'PY'
import json,sys
root,branch,commit=sys.argv[1:]
print(json.dumps({
  'schema':'home-center.spotify-overlay-radio.bootstrap.v1',
  'ok':True,
  'dedicatedGeneratedClone':True,
  'dirtySharedCheckoutUsed':False,
  'sourceRoot':root,
  'sourceBranch':branch,
  'sourceCommit':commit,
},sort_keys=True))
PY

exec bash "$DEST/tools/deploy_spotify_overlay_radio_phone.sh"
