#!/data/data/com.termux/files/usr/bin/bash
set -u

STATE_DIR="${PHONE_HANDS_STATE_DIR:-$HOME/.local/state/home-center}"
LOG="$STATE_DIR/phone-hands-watchdog.log"
PIDFILE="$STATE_DIR/phone-hands-worker.pid"
WORKER_LOG="$STATE_DIR/phone-hands-worker.log"
LOCKDIR="$STATE_DIR/phone-hands-watchdog.lock"
LAST_NOTICE="$STATE_DIR/phone-hands-last-notice"
SELF="$(cd "$(dirname "$0")" 2>/dev/null && pwd)/$(basename "$0")"
DIAG_ID=6404
STATE_ID=6405
mkdir -p "$STATE_DIR"

log(){ printf '%s %s\n' "$(date '+%Y-%m-%dT%H:%M:%S%z')" "$*" | tee -a "$LOG"; }
action_cmd(){ printf "bash -l -c '%s %s'" "$SELF" "$1"; }

post_diagnostic_button(){
  local summary="${1:-Ready. Tap to diagnose and repair Phone Hands.}"
  command -v termux-notification >/dev/null 2>&1 || return 0
  termux-notification \
    --id "$DIAG_ID" \
    --title 'Home Center diagnostics' \
    --content "$summary" \
    --priority default \
    --ongoing true \
    --button1 'Diagnose & repair' \
    --button1-action "$(action_cmd diagnose)" >/dev/null 2>&1 || true
}

state_notice(){
  local key="$1" title="$2" body="$3" priority="${4:-default}" action="${5:-diagnose}"
  local last=""
  [ -f "$LAST_NOTICE" ] && last="$(cat "$LAST_NOTICE" 2>/dev/null || true)"
  [ "$last" = "$key" ] && return 0
  printf '%s' "$key" > "$LAST_NOTICE"
  command -v termux-notification >/dev/null 2>&1 || return 0
  termux-notification \
    --id "$STATE_ID" \
    --title "$title" \
    --content "$body" \
    --priority "$priority" \
    --button1 'Diagnose & repair' \
    --button1-action "$(action_cmd "$action")" >/dev/null 2>&1 || true
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

network_ok(){ ip route 2>/dev/null | grep -q '^default '; }

shizuku_ok(){
  if command -v rish >/dev/null 2>&1 && rish -c 'id' >/dev/null 2>&1; then return 0; fi
  [ -x "$PREFIX/tmp/shizuku-recover.sh" ] && "$PREFIX/tmp/shizuku-recover.sh" >/dev/null 2>&1 || true
  command -v rish >/dev/null 2>&1 && rish -c 'id' >/dev/null 2>&1
}

run_once(){
  mkdir "$LOCKDIR" 2>/dev/null || return 0
  termux-wake-lock >/dev/null 2>&1 || true
  local worker

  if ! network_ok; then
    log 'DEGRADED no default network route'
    post_diagnostic_button 'DEGRADED — no network route. Tap Diagnose & repair.'
    state_notice 'no-network' 'Home Center degraded' 'No network route. Automatic recovery will keep retrying.' high
    return 10
  fi

  if ! shizuku_ok; then
    log 'HUMAN_REQUIRED Shizuku/rish unavailable'
    post_diagnostic_button 'ACTION NEEDED — Android authority unavailable.'
    state_notice 'shizuku-required' 'Phone Hands needs Android authority' 'Tap Diagnose & repair. If Android still blocks it, Wireless Debugging is the remaining operator step.' max
    return 20
  fi

  if worker_alive; then
    log 'HEALTHY worker already alive'
    post_diagnostic_button 'HEALTHY — Phone Hands is online.'
    state_notice 'healthy' 'Phone Hands online' 'Control lane healthy.' low
    return 0
  fi

  worker="$(find_worker || true)"
  if [ -z "$worker" ]; then
    log 'DEGRADED worker executable not found'
    post_diagnostic_button 'DEGRADED — worker missing. Tap Diagnose & repair.'
    state_notice 'worker-missing' 'Phone Hands degraded' 'Worker executable not found.' high
    return 30
  fi

  if start_worker "$worker"; then
    log "RECOVERED worker=$worker pid=$(cat "$PIDFILE")"
    post_diagnostic_button 'RECOVERED — Phone Hands restarted itself.'
    state_notice 'recovered' 'Phone Hands recovered' 'Worker restarted automatically. No terminal paste required.' default
    return 0
  fi

  log "DEGRADED failed to start worker=$worker"
  post_diagnostic_button 'DEGRADED — restart failed. Tap Diagnose & repair.'
  state_notice 'start-failed' 'Phone Hands restart failed' 'Recovery failed; logs preserved for inspection.' high
  return 40
}

diagnose(){
  # One-button path: attempt every safe repair first, then surface only the irreducible state.
  rm -f "$LAST_NOTICE" 2>/dev/null || true
  run_once || true
  if ! shizuku_ok; then
    am start -a android.settings.WIRELESS_DEBUGGING_SETTINGS >/dev/null 2>&1 \
      || am start -a android.settings.WIRELESS_SETTINGS >/dev/null 2>&1 \
      || true
  fi
}

post_diagnostic_button

case "${1:-once}" in
  once) run_once ;;
  diagnose) diagnose ;;
  loop)
    while :; do
      run_once || true
      sleep "${PHONE_HANDS_WATCHDOG_INTERVAL:-30}"
    done
    ;;
  *) printf 'usage: %s [once|diagnose|loop]\n' "$0" >&2; exit 64 ;;
esac
