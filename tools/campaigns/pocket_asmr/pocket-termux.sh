#!/usr/bin/env bash
# Phone-side Pocket ASMR operator; Git pulls campaign to Windows through existing SSH.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CAULDRON="${POCKET_CAULDRON_COMMAND:-cauldron}"
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
  "$CAULDRON" "powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $FOLDER/pocket-service.ps1 $1"
}
sync_git() {
  if "$CAULDRON" "git -C $REMOTE rev-parse --is-inside-work-tree" >/dev/null 2>&1; then
    "$CAULDRON" "git -C $REMOTE pull --ff-only origin $BRANCH"
  else
    "$CAULDRON" "git clone --branch $BRANCH --single-branch $REPO $REMOTE"
  fi
}
tunnel_on() {
  echo "BLOCKED: cauldron command is the remote transport; private API forwarding is not yet configured." >&2
  return 2
}
tunnel_off() {
  echo "TUNNEL=not_managed"
}
token_fetch() {
  mkdir -p "$(dirname "$TOKEN")"
  umask 077
  local tmp="$TOKEN.tmp"
  "$CAULDRON" "type C:\\Users\\dclar\\PocketASMR\\gateway-token.txt" > "$tmp"
  [[ -s "$tmp" ]] || { rm -f "$tmp"; echo "Gateway token unavailable" >&2; exit 2; }
  tr -d '\r\n' < "$tmp" > "$TOKEN"
  rm -f "$tmp"
  chmod 600 "$TOKEN"
}
case "${1:-doctor}" in
  install)
    install_dir="${PREFIX:-$HOME/.local}/bin"
    mkdir -p "$install_dir"
    printf '#!/usr/bin/env bash\\nexec bash "%s" "$@"\\n' "$HERE/pocket-termux.sh" > "$install_dir/pocket"
    chmod 700 "$install_dir/pocket"
    echo "INSTALLED $install_dir/pocket"
    ;;
  on)
    command -v "$CAULDRON" >/dev/null || { echo "BLOCKED: cauldron command not installed" >&2; exit 2; }
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
    echo "REMOTE_COMMAND=$CAULDRON"
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
    echo "Usage: pocket {install|on|off|doctor|service-status|asmr [asmr.txt] [--voice whisper]|status JOB|pull JOB}" >&2
    exit 2
    ;;
esac
