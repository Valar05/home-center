#!/usr/bin/env bash
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REMOTE="C:/Users/dclar/PocketASMRGit"
CAMPAIGN="$REMOTE/tools/campaigns/pocket_asmr"
BRANCH="campaign/pocket-asmr-queue-20261026"
CAULDRON="${POCKET_CAULDRON_COMMAND:-cauldron}"
command -v "$CAULDRON" >/dev/null || { echo "BLOCKED: cauldron command not found" >&2; exit 2; }
export POCKET_ASMR_URL="https://thecauldron-2.tail574fdf.ts.net:8443"
export POCKET_ASMR_TOKEN="${POCKET_ASMR_TOKEN:-$HOME/.config/pocket-asmr/token}"
run_remote() { "$CAULDRON" cmd /d /s /c "$1"; }
case "${1:-doctor}" in
 install)
  mkdir -p "${PREFIX:-$HOME/.local}/bin"
  printf '#!/bin/sh\nexec bash "%s/pocket-termux.sh" "$@"\n' "$HERE" > "${PREFIX:-$HOME/.local}/bin/pocket"
  chmod 700 "${PREFIX:-$HOME/.local}/bin/pocket"
  echo "INSTALLED=pocket"
  ;;
 sync)
  run_remote "if exist $REMOTE\\.git (git -C $REMOTE fetch origin $BRANCH && git -C $REMOTE checkout $BRANCH && git -C $REMOTE pull --ff-only origin $BRANCH) else git clone -b $BRANCH --single-branch https://github.com/Valar05/home-center.git $REMOTE"
  ;;
 on|off|service-status)
  mode="$1"; [[ "$mode" == service-status ]] && mode=status
  run_remote "call $CAMPAIGN/pocket-service.cmd $mode"
  ;;
 doctor)
  [[ -f "$HERE/pocket-api-client.py" && -f "$HERE/asmr.txt" ]] || { echo "FILES=missing"; exit 2; }
  echo "FILES=present"
  echo "REMOTE_LAUNCHER=$CAULDRON"
  run_remote "call $CAMPAIGN/pocket-service.cmd status"
  echo "API_TRANSPORT=Tailscale_Serve_HTTPS_8443"
  ;;
 asmr)
  shift
  [[ "${1:-}" == "" || "${1:-}" == --voice ]] && set -- "$HERE/asmr.txt" "$@"
  exec python "$HERE/pocket-api-client.py" asmr "$@"
  ;;
 status|pull)
  command="$1"; shift
  exec python "$HERE/pocket-api-client.py" "$command" "$@"
  ;;
 *) echo 'Usage: pocket install|sync|on|off|doctor|asmr|status JOB|pull JOB'; exit 2 ;;
esac
