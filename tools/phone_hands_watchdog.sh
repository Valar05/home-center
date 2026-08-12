#!/data/data/com.termux/files/usr/bin/bash
set -u

STATE_DIR="${PHONE_HANDS_STATE_DIR:-$HOME/.local/state/home-center}"
LOG="$STATE_DIR/phone-hands-watchdog.log"
PIDFILE="$STATE_DIR/phone-hands-worker.pid"
WORKER_LOG="$STATE_DIR/phone-hands-worker.log"
LOCKDIR="$STATE_DIR/phone-hands-watchdog.lock"
LAST_NOTICE="$STATE_DIR/phone-hands-last-notice"
SELF="$(cd "$(dirname "$0")" 2>/dev/null && pwd)/$(basename "$0")"
mkdir -p "$STATE_DIR"

log(){ printf '%s %s\n' "$(date '+%Y-%m-%dT%H:%M:%S%z')" "$*" | tee -a "$LOG"; }

action_cmd(){
  printf "bash -l -c '%s %s'" "$SELF" "$1"
}

notify(){
  local key="$1" title="$2" body="$3" priority="${4:-default}" mode="${5:-retry}"
  local last=""
  [ -f "$LAST_NOTICE" ] && last="$(cat "$LAST_NOTICE" 2>/dev/null || true)"
  [ "$last" = "$key" ] && return 0
  printf '%s' "$key" > "$LAST_NOTICE"
  command -v termux-notification >/dev/null 2>&1 || return 0

  case "$mode" in
    authority)
      termux-notification --id 6405 --title "$title" --content "$body" --priority "$priority" \
        --button1 'Open wireless debugging' --button1-action "am start -a android.settings.WIRELESS_DEBUGGING_SETTINGS >/dev/null 2>&1 || am start -a android.settings.WIRELESS_SETTINGS >/dev/null 2>&1" \
        --button2 'Retry now' --button2-action "$(action_cmd once)" \
        --button3 'Show log' --button3-action "tail -80 '$LOG' | termux-toast -b black -c white" >/dev/null 2>&1 || true
      ;;
    missing)
      termux-notification --id 6405 --title "$title" --content "$body" --priority "$priority" \
        --button1 'Retry now' --button1-action "$(action_cmd once)" \
        --button2 'Show log' --button2-action "tail -80 '$LOG' | termux-toast -b black -c white" >/dev/null 2>&1 || true
      ;;
    healthy)
      termux-notification --id 6405 --title "$title" --content "$body" --priority "$priority" \
        --button1 'Health check' --button1-action "$(action_cmd once)" >/dev/null 2>&1 || true
      ;;
    *)
      termux-notification --id 6405 --title "$title" --content "$body" --priority "$priority" \
        --button1 'Retry now' --button1-action "$(action_cmd once)" \
        --button2 'Show log' --button2-action "tail -80 '$LOG' | termux-toast -b black -c white" >/dev/null 2>&1 || true
      ;;
  esac
}

finish(){ rmdir "$LOCKDIR" 2>/dev/null || true; }
trap finish EXIT INT TERM

find_worker(){
  local root f
  for root in \
    "/storage/emulated/0/Documents/GodotProjects/home-center" \
    "$HOME/home-center" \
    "$HOME"; do
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
    *) chmod +x "$f" 2>/dev/null || true; nohup "$f" >>"$WORKER_LOG" 2>&1 & ;;
  esac
  pid=$!
  printf '%s\n' "$pid" > "$PIDFILE"
  sleep 2
  kill -0 "$pid" 2>/dev/null
}

shizuku_ok(){
  if command -v rish >/dev/null 2>&1; then
    rish -c 'id' >/dev/null 2>&1 && return 0
  fi
  [ -x "$PREFIX/tmp/shizuku-recover.sh" ] && "$PREFIX/tmp/shizuku-recover.sh" >/dev/null 2>&1 || true
  if command -v rish >/dev/null 2>&1; then
    rish -c 'id' >/dev/null 2>&1 && return 0
  fi
  return 1
}

network_ok(){ ip route 2>/dev/null | grep -q '^default '; }

run_once(){
  mkdir "$LOCKDIR" 2>/dev/null || exit 0
  termux-wake-lock >/dev/null 2>&1 || true
  local worker

  if ! network_ok; then
    log 'DEGRADED no default network route'
    notify 'no-network' 'Home Center degraded' 'Phone Hands has no network route. Recovery will retry automatically.' high retry
    return 10
  fi

  if ! shizuku_ok; then
    log 'HUMAN_REQUIRED Shizuku/rish unavailable'
    notify 'shizuku-required' 'Phone Hands needs Android authority' 'Tap to open Wireless debugging, then Retry now. No terminal paste required.' max authority
    return 20
  fi

  if worker_alive; then
    log 'HEALTHY worker already alive'
    notify 'healthy' 'Phone Hands online' 'The phone control lane is healthy.' low healthy
    return 0
  fi

  worker="$(find_worker || true)"
  if [ -z "$worker" ]; then
    log 'DEGRADED worker executable not found'
    notify 'worker-missing' 'Phone Hands degraded' 'Worker executable not found. Tap Show log or Retry now.' high missing
    return 30
  fi

  if start_worker "$worker"; then
    log "RECOVERED worker=$worker pid=$(cat "$PIDFILE")"
    notify 'recovered' 'Phone Hands recovered' 'The phone worker restarted itself. No paste command required.' default healthy
    return 0
  fi

  log "DEGRADED failed to start worker=$worker"
  notify 'start-failed' 'Phone Hands restart failed' 'Tap Retry now or Show log. Adam can inspect the same preserved log remotely.' high retry
  return 40
}

case "${1:-once}" in
  once) run_once ;;
  loop)
    while :; do
      run_once || true
      sleep "${PHONE_HANDS_WATCHDOG_INTERVAL:-30}"
    done
    ;;
  *) printf 'usage: %s [once|loop]\n' "$0" >&2; exit 64 ;;
esac
