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
 pair)
  mkdir -p "$HOME/.config/pocket-asmr"
  umask 077
  tmp="$(mktemp)"
  trap 'rm -f "$tmp"' EXIT
  "$CAULDRON" 'cmd /d /c type C:\Users\dclar\PocketASMR\gateway-token.txt' > "$tmp"
  python - "$tmp" "$HOME/.config/pocket-asmr/token" <<'PY'
import pathlib,re,sys,os
data=pathlib.Path(sys.argv[1]).read_text(errors="replace").splitlines()
matches=[line.strip() for line in data if re.fullmatch(r"[A-Za-z0-9_-]{40,60}",line.strip())]
if len(matches)!=1: raise SystemExit("BLOCKED: unexpected credential output, token not saved")
pathlib.Path(sys.argv[2]).write_text(matches[0]+"\n")
os.chmod(sys.argv[2],0o600)
print("TOKEN=stored_privately")
PY
  ;;
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
  echo "API=$POCKET_ASMR_URL"
  python - "$POCKET_ASMR_URL" "$HOME/.config/pocket-asmr/token" <<'PY'
import pathlib,sys,urllib.request,urllib.error
url,path=sys.argv[1:]
headers={}
p=pathlib.Path(path)
if p.is_file(): headers["Authorization"]="Bearer "+p.read_text().strip()
try:
 r=urllib.request.urlopen(urllib.request.Request(url+"/asmr/health",headers=headers),timeout=12)
 print("HTTP_STATUS",r.status,"BODY",r.read(500).decode(errors="replace"))
except urllib.error.HTTPError as e:
 print("HTTP_STATUS",e.code,"BODY",e.read(500).decode(errors="replace"))
 if e.code==401: print("NEXT=pocket_pair")
 sys.exit(2)
PY
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
