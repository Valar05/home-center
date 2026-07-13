#!/data/data/com.termux/files/usr/bin/sh
set -eu

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
cd "$ROOT"

SESSION="${HOME_CENTER_SCHEDULER_TMUX_SESSION:-home-center-scheduler}"
LOG_FILE="${HOME_CENTER_SCHEDULER_LOG:-generated/home_center_scheduler/scheduler.log}"
COMMAND="python3 tools/home_center_scheduler.py --loop"

usage() {
  cat <<USAGE
Usage: sh tools/home_center_scheduler_tmux.sh start|stop|status|attach|logs|once|list [job-id]

Durable session: $SESSION
Scheduler log: $LOG_FILE
USAGE
}

need_tmux() {
  if ! command -v tmux >/dev/null 2>&1; then
    echo "tmux is not installed. Install it with: pkg install tmux" >&2
    exit 1
  fi
}

case "${1:-status}" in
  start)
    need_tmux
    mkdir -p "$(dirname -- "$LOG_FILE")"
    if tmux has-session -t "$SESSION" 2>/dev/null; then
      echo "already running: $SESSION"
      exit 0
    fi
    tmux new-session -d -s "$SESSION" -c "$ROOT" "$COMMAND >>'$LOG_FILE' 2>&1"
    echo "started: $SESSION"
    ;;
  stop)
    need_tmux
    if tmux has-session -t "$SESSION" 2>/dev/null; then
      tmux kill-session -t "$SESSION"
      echo "stopped: $SESSION"
    else
      echo "not running: $SESSION"
    fi
    ;;
  status)
    need_tmux
    if tmux has-session -t "$SESSION" 2>/dev/null; then
      echo "running: $SESSION"
    else
      echo "not running: $SESSION"
    fi
    python3 tools/home_center_scheduler.py --status
    ;;
  attach)
    need_tmux
    exec tmux attach-session -t "$SESSION"
    ;;
  logs)
    if [ -f "$LOG_FILE" ]; then
      tail -80 "$LOG_FILE"
    else
      echo "no scheduler log yet: $LOG_FILE"
    fi
    ;;
  once)
    if [ -n "${2:-}" ]; then
      python3 tools/home_center_scheduler.py --once --job "$2"
    else
      python3 tools/home_center_scheduler.py --once --force
    fi
    ;;
  list)
    python3 tools/home_center_scheduler.py --list
    ;;
  --help|-h|help)
    usage
    ;;
  *)
    usage >&2
    exit 2
    ;;
esac
