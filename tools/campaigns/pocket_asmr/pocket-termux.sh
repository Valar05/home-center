#!/usr/bin/env bash
# Phone-side Pocket ASMR operator; Git pulls campaign to Windows through existing SSH.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HOST="${POCKET_SSH_HOST:-thecauldron}"
REMOTE="C:/Users/dclar/PocketASMRGit"
FOLDER="$REMOTE/tools/campaigns/pocket_asmr"
REPO="https://github.com/Valar05/home-center.git"
BRANCH="campaign/pocket-asmr-queue-20261026"
TOKEN="${POCKET_ASMR_TOKEN:-$HOME/.config/pocket-asmr/token}"
SOCKET="$HOME/.local/state/pocket-asmr/ssh-control"
export POCKET_ASMR_URL="http://127.0.0.1:10215"
export POCKET_ASMR_TOKEN="$TOKEN"
mkdir -p "$(dirname "$SOCKET")"

service() {
  ssh -o BatchMode=yes "$HOST" "powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $FOLDER/pocket-service.ps1 $1"
}
sync_git() {
  if ssh -o BatchMode=yes "$HOST" "git -C $REMOTE rev-parse --is-inside-work-tree" >/dev/null 2>&1; then
    ssh -o BatchMode=yes "$HOST" "git -C $REMOTE pull --ff-only origin $BRANCH"
  else
    ssh -o BatchMode=yes "$HOST" "git clone --branch $BRANCH --single-branch $REPO $REMOTE"
  fi
}
tunnel_on() {
  if ssh -S "$SOCKET" -O check "$HOST" >/dev/null 2>&1; then return 0; fi
  ssh -o BatchMode=yes -o ExitOnForwardFailure=yes -M -S "$SOCKET" -fN \
    -L 127.0.0.1:10215:127.0.0.1:10215 "$HOST"
}
tunnel_off() {
  ssh -S "$SOCKET" -O exit "$HOST" >/dev/null 2>&1 || true
}
token_fetch() {
  mkdir -p "$(dirname "$TOKEN")"
  umask 077
  local tmp="$TOKEN.tmp"
  ssh -o BatchMode=yes "$HOST" "type C:\\Users\\dclar\\PocketASMR\\gateway-token.txt" > "$tmp"
  [[ -s "$tmp" ]] || { rm -f "$tmp"; echo "Gateway token unavailable" >&2; exit 2; }
  tr -d '\r\n' < "$tmp" > "$TOKEN"
  rm -f "$tmp"
  chmod 600 "$TOKEN"
}
case "${1:-doctor}" in
  on)
    sync_git
    service install
    service on
    token_fetch
    tunnel_on
    echo "ASMR_GATEWAY=started; TUNNEL=ready; TOKEN=stored_privately"
    ;;
  off)
    tunnel_off
    service off
    ;;
  service-status)
    service status
    ;;
  doctor)
    command -v python >/dev/null || { echo "BLOCKED: Termux python missing"; exit 2; }
    [[ -f "$HERE/pocket-api-client.py" && -f "$HERE/asmr.txt" ]] || { echo "BLOCKED: Git campaign missing files"; exit 2; }
    echo "FILES=present"
    service status
    python -c 'import json,urllib.request,os,pathlib; t=pathlib.Path(os.environ["POCKET_ASMR_TOKEN"]).read_text().strip();r=urllib.request.Request(os.environ["POCKET_ASMR_URL"]+"/asmr/health",headers={"Authorization":"Bearer "+t});print(json.load(urllib.request.urlopen(r,timeout=8)))'
    ;;
  asmr)
    shift
    if [[ ${1:-} == "" || ${1:-} == --voice ]]; then
      set -- "$HERE/asmr.txt" "$@"
    fi
    exec python "$HERE/pocket-api-client.py" asmr "$@"
    ;;
  status|pull)
    exec python "$HERE/pocket-api-client.py" "$@"
    ;;
  *)
    echo "Usage: pocket {on|off|doctor|service-status|asmr [asmr.txt] [--voice whisper]|status JOB|pull JOB}" >&2
    exit 2
    ;;
esac
