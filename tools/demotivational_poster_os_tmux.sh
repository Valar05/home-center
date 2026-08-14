#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
SESSION="${HC_POSTER_OS_TMUX_SESSION:-hc-poster-os}"
INBOX="${HC_POSTER_OS_INBOX:-$HOME/.local/state/home-center/poster-events.jsonl}"
LOG="${HC_POSTER_OS_LOG:-$HOME/.local/state/home-center/poster-os.log}"
mkdir -p "$(dirname "$INBOX")" "$(dirname "$LOG")"

runner="while true; do if [ -s '$INBOX' ]; then line=\$(head -n1 '$INBOX'); tail -n +2 '$INBOX' > '$INBOX.tmp' || true; mv '$INBOX.tmp' '$INBOX'; text=\$(python3 -c 'import json,sys; d=json.loads(sys.argv[1]); print(d.get(\"text\",\"\"))' \"\$line\"); importance=\$(python3 -c 'import json,sys; d=json.loads(sys.argv[1]); print(d.get(\"importance\",5))' \"\$line\"); tags=\$(python3 -c 'import json,sys; d=json.loads(sys.argv[1]); print(d.get(\"tags\",\"\"))' \"\$line\"); python3 '$ROOT/tools/demotivational_poster_os.py' ingest \"\$text\" --importance \"\$importance\" --tags \"\$tags\" >> '$LOG' 2>&1; else sleep 5; fi; done"

case "${1:-status}" in
  start)
    command -v tmux >/dev/null || { echo 'BLOCKED: tmux missing' >&2; exit 2; }
    if tmux has-session -t "$SESSION" 2>/dev/null; then echo "already running: $SESSION"; exit 0; fi
    tmux new-session -d -s "$SESSION" "$runner"
    echo "started: $SESSION"
    ;;
  stop)
    tmux has-session -t "$SESSION" 2>/dev/null && tmux kill-session -t "$SESSION" || true
    echo "stopped: $SESSION"
    ;;
  status)
    if tmux has-session -t "$SESSION" 2>/dev/null; then echo "running: $SESSION"; else echo "not running: $SESSION"; fi
    python3 "$ROOT/tools/demotivational_poster_os.py" status
    ;;
  logs) tail -80 "$LOG" 2>/dev/null || true ;;
  *) echo "usage: $0 start|stop|status|logs" >&2; exit 64 ;;
esac
