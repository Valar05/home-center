#!/system/bin/sh
set -eu

ROOT="${HC_PHONE_REPO:-/storage/emulated/0/Documents/GodotProjects/home-center-phone-hands}"
STATE_DIR="${HC_PHONE_STATE_DIR:-$HOME/.local/state/home-center}"
LOG="$STATE_DIR/phone-relay.log"
PIDFILE="$STATE_DIR/phone-relay.pid"
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

print_receipt() {
  status="$1"
  pids="$(relay_pids | tr '\n' ' ' | sed 's/[[:space:]]*$//')"
  printf '{"status":"%s","repo":"%s","relay":"%s","pids":"%s","log":"%s","checkedAt":"%s"}\n' \
    "$status" "$ROOT" "$RELAY" "$pids" "$LOG" "$(date -Iseconds)"
}

if [ ! -f "$RELAY" ]; then
  say "BLOCKED: relay script missing: $RELAY"
  print_receipt "blocked_missing_relay"
  exit 2
fi

if relay_alive; then
  say "relay process already alive"
  relay_pids | head -n1 > "$PIDFILE" || true
  print_receipt "already_running"
  exit 0
fi

say "relay process absent; starting one fresh instance"
cd "$ROOT"
nohup "$PYTHON" "$RELAY" >> "$LOG" 2>&1 < /dev/null &
pid=$!
printf '%s\n' "$pid" > "$PIDFILE"

for _ in 1 2 3 4 5 6 7 8 9 10; do
  if kill -0 "$pid" 2>/dev/null; then
    if grep -q 'Home Center phone relay online:' "$LOG" 2>/dev/null; then
      say "relay started and announced online"
      print_receipt "recovered"
      exit 0
    fi
  else
    say "relay exited during startup"
    tail -n 40 "$LOG" || true
    print_receipt "failed_startup"
    exit 1
  fi
  sleep 1
done

if kill -0 "$pid" 2>/dev/null; then
  say "relay is alive; startup announcement not yet observed"
  tail -n 20 "$LOG" || true
  print_receipt "running_unconfirmed"
  exit 0
fi

say "relay failed to remain alive"
tail -n 40 "$LOG" || true
print_receipt "failed"
exit 1
