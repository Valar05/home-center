#!/data/data/com.termux/files/usr/bin/bash
set -u

STATE_DIR="${PHONE_HANDS_STATE_DIR:-$HOME/.local/state/home-center}"
LOG="$STATE_DIR/phone-hands-watchdog.log"
PIDFILE="$STATE_DIR/phone-hands-worker.pid"
WORKER_LOG="$STATE_DIR/phone-hands-worker.log"
RUN_LOCK="$STATE_DIR/phone-hands-watchdog.run.lock"
LOOP_PIDFILE="$STATE_DIR/phone-hands-watchdog-loop.pid"
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
  local key="$1" title="$2" body="$3" priority="${4:-default}"
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
    --button1-action "$(action_cmd diagnose)" >/dev/null 2>&1 || true
}

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
    *.sh) nohup bash "$f" >>"$WORKER_LOG" 2>&1 & ;;
    *) nohup "$f" >>"$WORKER_LOG" 2>&1 & ;;
  esac
  pid=$!
  printf '%s\n' "$pid" > "$PIDFILE"
  sleep 2
  kill -0 "$pid" 2>/dev/null
}

network_probe(){
  # Android/Termux may hide routing details from `ip route`; treat network as advisory.
  # Return success when any cheap direct signal works. Failure must never block worker start.
  if command -v curl >/dev/null 2>&1 && curl -fsSIL --max-time 4 https://www.google.com/generate_204 >/dev/null 2>&1; then return 0; fi
  if command -v getent >/dev/null 2>&1 && getent hosts github.com >/dev/null 2>&1; then return 0; fi
  if command -v ping >/dev/null 2>&1 && ping -c 1 -W 2 1.1.1.1 >/dev/null 2>&1; then return 0; fi
  return 1
}

shizuku_ok(){
  if command -v rish >/dev/null 2>&1 && rish -c 'id' >/dev/null 2>&1; then return 0; fi
  [ -x "$PREFIX/tmp/shizuku-recover.sh" ] && "$PREFIX/tmp/shizuku-recover.sh" >/dev/null 2>&1 || true
  command -v rish >/dev/null 2>&1 && rish -c 'id' >/dev/null 2>&1
}

run_once(){
  (
    mkdir "$RUN_LOCK" 2>/dev/null || exit 0
    trap 'rmdir "$RUN_LOCK" 2>/dev/null || true' EXIT INT TERM
    termux-wake-lock >/dev/null 2>&1 || true
    local worker network_state='unknown'

    if network_probe; then network_state='reachable'; else network_state='unverified'; fi

    if ! shizuku_ok; then
      log "HUMAN_REQUIRED Shizuku/rish unavailable network=$network_state"
      post_diagnostic_button 'ACTION NEEDED — Android authority unavailable.'
      state_notice 'shizuku-required' 'Phone Hands needs Android authority' 'Tap Diagnose & repair. If Android still blocks it, Wireless Debugging is the remaining operator step.' max
      exit 20
    fi

    if worker_alive; then
      log "HEALTHY worker already alive network=$network_state"
      post_diagnostic_button "HEALTHY — Phone Hands is online. Network $network_state."
      state_notice 'healthy' 'Phone Hands online' 'Control lane healthy.' low
      exit 0
    fi

    worker="$(find_worker || true)"
    if [ -z "$worker" ]; then
      log "DEGRADED worker executable not found network=$network_state"
      post_diagnostic_button 'DEGRADED — worker missing. Tap Diagnose & repair.'
      state_notice 'worker-missing' 'Phone Hands degraded' 'Worker executable not found.' high
      exit 30
    fi

    if start_worker "$worker"; then
      log "RECOVERED worker=$worker pid=$(cat "$PIDFILE") network=$network_state"
      post_diagnostic_button "RECOVERED — Phone Hands restarted itself. Network $network_state."
      state_notice 'recovered' 'Phone Hands recovered' 'Worker restarted automatically. No terminal paste required.' default
      exit 0
    fi

    log "DEGRADED failed to start worker=$worker network=$network_state"
    post_diagnostic_button 'DEGRADED — restart failed. Tap Diagnose & repair.'
    state_notice 'start-failed' 'Phone Hands restart failed' 'Recovery failed; logs preserved for inspection.' high
    exit 40
  )
}

diagnose(){
  rm -f "$LAST_NOTICE" 2>/dev/null || true
  run_once || true
  if ! shizuku_ok; then
    am start -a android.settings.WIRELESS_DEBUGGING_SETTINGS >/dev/null 2>&1 \
      || am start -a android.settings.WIRELESS_SETTINGS >/dev/null 2>&1 \
      || true
  fi
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
  post_diagnostic_button
  while :; do
    run_once || true
    sleep "${PHONE_HANDS_WATCHDOG_INTERVAL:-30}"
  done
}

post_diagnostic_button

case "${1:-once}" in
  once) run_once ;;
  diagnose) diagnose ;;
  loop) run_loop ;;
  *) printf 'usage: %s [once|diagnose|loop]\n' "$0" >&2; exit 64 ;;
esac
