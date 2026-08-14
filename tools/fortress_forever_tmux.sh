#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
SESSION="${HC_FOREVER_SESSION:-fortress-forever}"
LOOP="$ROOT/tools/fortress_forever.sh"
[ -x "$LOOP" ] || chmod +x "$LOOP"
if tmux has-session -t "$SESSION" 2>/dev/null; then exit 0; fi
exec tmux new-session -d -s "$SESSION" "$LOOP"
