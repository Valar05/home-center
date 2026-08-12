#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
STATE="${HC_STATE_DIR:-$HOME/.local/state/home-center}"
HEALTH="${HC_PHONE_LLM_HEALTH:-http://127.0.0.1:8790/health}"
BRAIN="${HC_PHONE_BRAIN_CMD:-$HOME/bin/home-center-phone-brain}"
LOG="$STATE/phone-brain.log"
PIDFILE="$STATE/phone-brain.pid"
mkdir -p "$STATE"

healthy() { curl -fsS --max-time 2 "$HEALTH" >/dev/null 2>&1; }

if healthy; then
  printf '{"schema":"adam-phone-brain-v1","ok":true,"status":"already_running","health":"%s"}\n' "$HEALTH"
  exit 0
fi

[ -x "$BRAIN" ] || {
  printf 'BLOCKED: local Adam brain is not running and launcher is missing: %s\n' "$BRAIN" >&2
  printf 'Canonical bootstrap: bash tools/setup_android_phone_autonomous_node.sh\n' >&2
  exit 2
}

# Kill only the pid previously recorded for this brain launcher, if stale-but-live.
if [ -f "$PIDFILE" ]; then
  old="$(cat "$PIDFILE" 2>/dev/null || true)"
  if [ -n "$old" ] && kill -0 "$old" 2>/dev/null; then
    kill "$old" 2>/dev/null || true
    sleep 1
  fi
fi

nohup "$BRAIN" >"$LOG" 2>&1 < /dev/null &
echo $! > "$PIDFILE"

for _ in $(seq 1 30); do
  if healthy; then
    printf '{"schema":"adam-phone-brain-v1","ok":true,"status":"started","pid":%s,"health":"%s","log":"%s"}\n' "$(cat "$PIDFILE")" "$HEALTH" "$LOG"
    exit 0
  fi
  sleep 1
done

echo "BLOCKED: Adam phone brain failed to become healthy; log=$LOG" >&2
tail -n 40 "$LOG" >&2 || true
exit 3
