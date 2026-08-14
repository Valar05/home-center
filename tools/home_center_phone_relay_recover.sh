#!/system/bin/sh
set -eu

ROOT="${HC_PHONE_REPO:-/storage/emulated/0/Documents/GodotProjects/home-center-phone-hands}"
STATE_DIR="${HC_PHONE_STATE_DIR:-$HOME/.local/state/home-center}"
LOG="$STATE_DIR/phone-relay.log"
PIDFILE="$STATE_DIR/phone-relay.pid"
HEARTBEAT="${HC_PHONE_RELAY_HEARTBEAT:-$STATE_DIR/phone-relay-heartbeat.json}"
MAX_HEARTBEAT_AGE="${HC_PHONE_RELAY_HEALTH_MAX_AGE_SECONDS:-15}"
PYTHON="${HC_PHONE_PYTHON:-python}"
RELAY="$ROOT/tools/android_phone_home_center_relay.py"

mkdir -p "$STATE_DIR"

say() { printf '[phone-relay-recover] %s\n' "$*"; }

relay_pids() {
  pgrep -f '[p]ython.*android_phone_home_center_relay.py' || true
}

relay_alive() {
  pids="$(relay_pids)"
  [ -n "$pids" ]
}

heartbeat_ok() {
  wanted_pid="$1"
  [ -f "$HEARTBEAT" ] || return 1
  "$PYTHON" - "$HEARTBEAT" "$wanted_pid" "$MAX_HEARTBEAT_AGE" <<'PY' >/dev/null 2>&1
import json,os,sys,time
path,pid,max_age=sys.argv[1],int(sys.argv[2]),int(sys.argv[3])
try:
    data=json.load(open(path,encoding='utf-8'))
except Exception:
    raise SystemExit(2)
if data.get('schema')!='home-center-phone-relay-heartbeat-v1':
    raise SystemExit(3)
if data.get('deviceId')!='primary-phone':
    raise SystemExit(4)
if int(data.get('pid') or 0)!=pid:
    raise SystemExit(5)
age=int(time.time())-int(data.get('lastSuccessAtEpoch') or 0)
if age < 0 or age > max_age:
    raise SystemExit(6)
if data.get('state') not in {'poll_ok','command_completed','command_failed'}:
    raise SystemExit(7)
PY
}

wait_for_heartbeat() {
  wanted_pid="$1"
  tries="${2:-10}"
  i=0
  while [ "$i" -lt "$tries" ]; do
    kill -0 "$wanted_pid" 2>/dev/null || return 1
    heartbeat_ok "$wanted_pid" && return 0
    i=$((i+1))
    sleep 1
  done
  return 1
}

print_receipt() {
  status="$1"
  pids="$(relay_pids | tr '\n' ' ' | sed 's/[[:space:]]*$//')"
  hb_state="missing"
  hb_age=""
  if [ -f "$HEARTBEAT" ]; then
    hb_state="$($PYTHON - "$HEARTBEAT" <<'PY' 2>/dev/null || printf invalid
import json,sys,time
try:d=json.load(open(sys.argv[1],encoding='utf-8'))
except Exception:raise SystemExit(1)
print(str(d.get('state') or 'unknown'))
PY
)"
    hb_age="$($PYTHON - "$HEARTBEAT" <<'PY' 2>/dev/null || true
import json,sys,time
try:d=json.load(open(sys.argv[1],encoding='utf-8'))
except Exception:raise SystemExit(1)
print(max(0,int(time.time())-int(d.get('lastSuccessAtEpoch') or 0)))
PY
)"
  fi
  printf '{"status":"%s","repo":"%s","relay":"%s","pids":"%s","heartbeat":"%s","heartbeatState":"%s","heartbeatAgeSeconds":"%s","log":"%s","checkedAt":"%s"}\n' \
    "$status" "$ROOT" "$RELAY" "$pids" "$HEARTBEAT" "$hb_state" "$hb_age" "$LOG" "$(date -Iseconds)"
}

if [ ! -f "$RELAY" ]; then
  say "BLOCKED: relay script missing: $RELAY"
  print_receipt "blocked_missing_relay"
  exit 2
fi

if relay_alive; then
  existing_pid="$(relay_pids | head -n1)"
  if heartbeat_ok "$existing_pid"; then
    say "relay process has a fresh Home Center poll heartbeat"
    printf '%s\n' "$existing_pid" > "$PIDFILE"
    print_receipt "healthy"
    exit 0
  fi
  say "relay process exists but Home Center liveness is not proven; attempting bounded recovery"
  for pid in $(relay_pids); do kill "$pid" 2>/dev/null || true; done
  sleep 1
fi

say "starting one fresh relay instance"
cd "$ROOT"
rm -f "$HEARTBEAT"
nohup "$PYTHON" "$RELAY" >> "$LOG" 2>&1 < /dev/null &
pid=$!
printf '%s\n' "$pid" > "$PIDFILE"

if wait_for_heartbeat "$pid" 15; then
  say "relay started and completed a fresh Home Center poll"
  print_receipt "recovered"
  exit 0
fi

if kill -0 "$pid" 2>/dev/null; then
  say "relay is alive but did not prove Home Center liveness"
  tail -n 30 "$LOG" || true
  print_receipt "running_unconfirmed"
  exit 1
fi

say "relay exited before proving Home Center liveness"
tail -n 40 "$LOG" || true
print_receipt "failed"
exit 1