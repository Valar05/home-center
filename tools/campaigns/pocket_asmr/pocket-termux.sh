#!/usr/bin/env bash
# Termux entrypoint. Runs exclusively on the phone. Git is the source of scripts and transcripts.
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export POCKET_ASMR_URL="${POCKET_ASMR_URL:-http://127.0.0.1:10215}"
client="$here/pocket-api-client.py"
case "${1:-doctor}" in
  doctor)
    command -v python >/dev/null || { echo "BLOCKED: install python in Termux"; exit 2; }
    test -f "$client" || { echo "BLOCKED: client missing"; exit 2; }
    test -f "$here/asmr.txt" || { echo "BLOCKED: transcript missing"; exit 2; }
    echo "SOURCE=present"
    echo "CLIENT=present"
    echo "TRANSCRIPT=present"
    echo "API=$POCKET_ASMR_URL"
    echo "TOKEN=${POCKET_ASMR_TOKEN:-$HOME/.config/pocket-asmr/token}"
    echo "Audio API must be independently deployed and reachable; this doctor does not imply it is."
    ;;
  asmr)
    shift
    if [[ "${1:-}" == "" ]]; then set -- "$here/asmr.txt"; fi
    exec python "$client" asmr "$@"
    ;;
  status|pull) exec python "$client" "$@" ;;
  *) echo 'Usage: bash pocket-termux.sh doctor|asmr [transcript] [--voice whisper]|status JOB_ID|pull JOB_ID'; exit 2 ;;
esac
