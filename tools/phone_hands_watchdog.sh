#!/data/data/com.termux/files/usr/bin/bash
set -u

STATE_DIR="${PHONE_HANDS_STATE_DIR:-$HOME/.local/state/home-center}"
LOG="$STATE_DIR/phone-hands-watchdog.log"
RUN_LOCK="$STATE_DIR/phone-hands-watchdog.run.lock"
LOOP_PIDFILE="$STATE_DIR/phone-hands-watchdog-loop.pid"
HEARTBEAT="${HC_PHONE_RELAY_HEARTBEAT:-$STATE_DIR/phone-relay-heartbeat.json}"
INTERVAL="${PHONE_HANDS_WATCHDOG_INTERVAL:-60}"
HEALTHY_AGE="${PHONE_HANDS_WATCHDOG_HEALTHY_AGE_SECONDS:-120}"
BUSY_GRACE="${PHONE_HANDS_WATCHDOG_BUSY_GRACE_SECONDS:-1200}"
STARTUP_GRACE="${PHONE_HANDS_WATCHDOG_STARTUP_GRACE_SECONDS:-180}"
mkdir -p "$STATE_DIR"

log(){ printf '%s %s\n' "$(date '+%Y-%m-%dT%H:%M:%S%z')" "$*" >> "$LOG"; }

find_repo(){
  local root
  for root in     "${PHONE_HANDS_REPO_ROOT:-}"     "/storage/emulated/0/Documents/GodotProjects/home-center"     "/storage/emulated/0/Documents/GodotProjects/home-center-phone-hands"     "$HOME/home-center"; do
    [ -n "$root" ] || continue
    [ -f "$root/tools/android_phone_home_center_relay.py" ] || continue
    [ -f "$root/tools/home_center_phone_relay_recover.sh" ] || continue
    printf '%s\n' "$root"
    return 0
  done
  return 1
}

relay_pids(){ pgrep -f '[p]ython.*android_phone_home_center_relay.py' || true; }

pid_age_seconds(){
  local pid="$1" value
  value="$(ps -o etimes= -p "$pid" 2>/dev/null | tr -d ' ' || true)"
  case "$value" in ''|*[!0-9]*) printf '999999\n' ;; *) printf '%s\n' "$value" ;; esac
}

source_sha(){
  python - "$1/tools/android_phone_home_center_relay.py" <<'PY'
import hashlib,sys
print(hashlib.sha256(open(sys.argv[1],'rb').read()).hexdigest())
PY
}

heartbeat_snapshot(){
  python - "$HEARTBEAT" <<'PY'
import json,sys,time
path=sys.argv[1]
try:
    d=json.load(open(path,encoding='utf-8'))
except Exception:
    raise SystemExit(1)
age=max(0,int(time.time())-int(d.get('lastSuccessAtEpoch') or 0))
print("\t".join([
    str(age),
    str(int(d.get('pid') or 0)),
    str(d.get('sourceSha256') or ''),
    str(d.get('commandId') or ''),
    str(d.get('state') or ''),
]))
PY
}

recover(){
  local repo="$1" reason="$2" recover="$repo/tools/home_center_phone_relay_recover.sh"
  log "RECOVERY_REQUEST reason=$reason repo=$repo"
  if env \
    -u PHONE_HANDS_WATCHDOG_INTERVAL \
    -u PHONE_HANDS_WATCHDOG_HEALTHY_AGE_SECONDS \
    -u PHONE_HANDS_WATCHDOG_BUSY_GRACE_SECONDS \
    -u PHONE_HANDS_WATCHDOG_STARTUP_GRACE_SECONDS \
    -u PHONE_HANDS_STATE_DIR \
    -u PHONE_HANDS_REPO_ROOT \
    HC_PHONE_REPO="$repo" sh "$recover" >>"$LOG" 2>&1; then
    log "RECOVERED reason=$reason"
    return 0
  else
    rc=$?
    log "DEGRADED recovery_failed reason=$reason rc=$rc"
    return "$rc"
  fi
}

run_once(){
  (
    mkdir "$RUN_LOCK" 2>/dev/null || exit 0
    trap 'rmdir "$RUN_LOCK" 2>/dev/null || true' EXIT INT TERM

    repo="$(find_repo || true)"
    if [ -z "$repo" ]; then
      log "DEGRADED canonical_repo_not_found"
      exit 30
    fi

    pids="$(relay_pids)"
    count="$(printf '%s\n' "$pids" | sed '/^$/d' | wc -l | tr -d ' ')"
    if [ "$count" -eq 0 ]; then
      recover "$repo" "relay_absent"
      exit $?
    fi
    if [ "$count" -gt 1 ]; then
      log "DEGRADED duplicate_relays count=$count pids=$(printf '%s' "$pids" | tr '\n' ',')"
      exit 31
    fi

    pid="$pids"
    snap="$(heartbeat_snapshot 2>/dev/null || true)"
    if [ -z "$snap" ]; then
      age="$(pid_age_seconds "$pid")"
      if [ "$age" -le "$STARTUP_GRACE" ]; then
        log "STARTING pid=$pid process_age=$age heartbeat=missing"
        exit 0
      fi
      recover "$repo" "heartbeat_missing"
      exit $?
    fi

    IFS="$(printf '\t')" read -r hb_age hb_pid hb_source command_id hb_state <<EOF
$snap
EOF
    wanted_source="$(source_sha "$repo" 2>/dev/null || true)"

    if [ "$hb_state" = "poll_ok" ] && [ -n "$command_id" ] && [ "$hb_age" -le "$BUSY_GRACE" ]; then
      log "BUSY_PROTECTED pid=$pid heartbeat_age=$hb_age command=$command_id state=$hb_state"
      exit 0
    fi

    if [ "$hb_pid" != "$pid" ]; then
      recover "$repo" "heartbeat_pid_mismatch"
      exit $?
    fi
    if [ -n "$wanted_source" ] && [ "$hb_source" != "$wanted_source" ]; then
      recover "$repo" "source_hash_mismatch"
      exit $?
    fi
    if [ "$hb_age" -le "$HEALTHY_AGE" ]; then
      log "HEALTHY pid=$pid heartbeat_age=$hb_age state=$hb_state"
      exit 0
    fi

    recover "$repo" "idle_heartbeat_stale"
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
  log "LOOP_START pid=$$ interval=$INTERVAL"
  while :; do
    run_once || true
    sleep "$INTERVAL"
  done
}

case "${1:-once}" in
  once|diagnose) run_once ;;
  loop) run_loop ;;
  *) printf 'usage: %s [once|diagnose|loop]\n' "$0" >&2; exit 64 ;;
esac
