#!/data/data/com.termux/files/usr/bin/bash
set -u

STATE_DIR="${PHONE_HANDS_STATE_DIR:-$HOME/.local/state/home-center}"
LOG="$STATE_DIR/phone-hands-watchdog.log"
PIDFILE="$STATE_DIR/phone-hands-worker.pid"
WORKER_LOG="$STATE_DIR/phone-hands-worker.log"
RUN_LOCK="$STATE_DIR/phone-hands-watchdog.run.lock"
LOOP_PIDFILE="$STATE_DIR/phone-hands-watchdog-loop.pid"
SELF="$(cd "$(dirname "$0")" 2>/dev/null && pwd)/$(basename "$0")"
mkdir -p "$STATE_DIR"

log(){ printf '%s %s\n' "$(date '+%Y-%m-%dT%H:%M:%S%z')" "$*" >> "$LOG"; }

# Legacy compatibility only. No notifications, no Termux global wake lock, and
# no Android settings launches. The old versions of this script were capable of
# keeping Termux visibly alive and repeatedly presenting recovery surfaces.
find_worker(){
  local root f
  for root in \
    "/storage/emulated/0/Documents/GodotProjects/home-center" \
    "$HOME/home-center"; do
    [ -d "$root" ] || continue
    f="$(find "$root" -maxdepth 5 -type f \( -iname '*phone*hands*.sh' -o -iname '*phone*hands*.js' -o -iname '*phone*worker*.sh' -o -iname '*phone*worker*.js' \) 2>/dev/null | grep -v 'phone_hands_watchdog.sh' | head -1)"
    [ -n "$f" ] && { printf '%s\n' "$f"; return 0; }
  done
  return 1
}

worker_alive(){
  [ -f "$PIDFILE" ] || return 1
  local pid
  pid="$(cat "$PIDFILE" 2>/dev/null || true)"
  [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null
}

start_worker(){
  local f="$1" pid
  case "$f" in
    *.js) nohup node "$f" >>"$WORKER_LOG" 2>&1 & ;;
    *.sh) nohup bash "$f" >>"$WORKER_LOG" 2>&1 & ;;
    *) nohup "$f" >>"$WORKER_LOG" 2>&1 & ;;
  esac
  pid=$!
  printf '%s\n' "$pid" > "$PIDFILE"
  sleep 2
  kill -0 "$pid" 2>/dev/null
}

run_once(){
  (
    mkdir "$RUN_LOCK" 2>/dev/null || exit 0
    trap 'rmdir "$RUN_LOCK" 2>/dev/null || true' EXIT INT TERM

    if worker_alive; then
      log "HEALTHY worker already alive"
      exit 0
    fi

    worker="$(find_worker || true)"
    if [ -z "$worker" ]; then
      log "DEGRADED worker executable not found"
      exit 30
    fi

    if start_worker "$worker"; then
      log "RECOVERED worker=$worker pid=$(cat "$PIDFILE")"
      exit 0
    fi

    log "DEGRADED failed to start worker=$worker"
    exit 40
  )
}

loop_alive(){
  [ -f "$LOOP_PIDFILE" ] || return 1
  local pid
  pid="$(cat "$LOOP_PIDFILE" 2>/dev/null || true)"
  [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null
}

run_loop(){
  if loop_alive && [ "$(cat "$LOOP_PIDFILE" 2>/dev/null || true)" != "$$" ]; then
    log "LOOP_ALREADY_RUNNING pid=$(cat "$LOOP_PIDFILE")"
    exit 0
  fi
  printf '%s\n' "$$" > "$LOOP_PIDFILE"
  trap 'rm -f "$LOOP_PIDFILE" 2>/dev/null || true' EXIT INT TERM
  while :; do
    run_once || true
    sleep "${PHONE_HANDS_WATCHDOG_INTERVAL:-300}"
  done
}

case "${1:-once}" in
  once|diagnose) run_once ;;
  loop) run_loop ;;
  *) printf 'usage: %s [once|diagnose|loop]\n' "$0" >&2; exit 64 ;;
esac
