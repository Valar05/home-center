#!/data/data/com.termux/files/usr/bin/bash
set -Eeuo pipefail

STATE_ROOT="${HC_STATE_DIR:-$HOME/.local/state/home-center}/headcrab-home-center-deploy"
CAMPAIGN="$STATE_ROOT/campaign.sh"
mkdir -p "$STATE_ROOT"

clip(){
  local msg="$1"
  if command -v termux-clipboard-set >/dev/null 2>&1; then
    printf '%s' "$msg" | termux-clipboard-set >/dev/null 2>&1 || true
  fi
}
fail(){
  local rc=$?
  local msg="HEADCRAB DEPLOY BOOTSTRAP FAILED rc=$rc"
  printf '%s\n' "$msg" >&2
  clip "$msg"
  exit "$rc"
}
trap fail ERR

find_repo(){
  local r u
  for r in     "${HC_REPO_ROOT:-}"     "/storage/emulated/0/Documents/GodotProjects/home-center"     "/storage/emulated/0/Documents/GodotProjects/home-center-phone-hands"     "$HOME/home-center"; do
    [ -n "$r" ] || continue
    [ -e "$r/.git" ] || continue
    u="$(git -C "$r" remote get-url origin 2>/dev/null || true)"
    case "$u" in
      *Valar05/home-center*|*valar05/home-center*) printf '%s\n' "$r"; return 0 ;;
    esac
  done
  return 1
}

ROOT="$(find_repo)"
git -C "$ROOT" fetch origin main
git -C "$ROOT" show origin/main:tools/headcrab_home_center_deploy_campaign.sh >"$CAMPAIGN"
chmod 700 "$CAMPAIGN"

printf 'HEADCRAB DEPLOY: loaded latest campaign from origin/main.\n'
printf 'Primary dirty checkout is transport only; deployment uses a clean isolated clone.\n'
exec bash "$CAMPAIGN" run
