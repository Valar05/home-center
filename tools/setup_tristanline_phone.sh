#!/data/data/com.termux/files/usr/bin/bash
set -eu

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
CFG_DIR="$HOME/.config/tristanline"
STATE_DIR="$HOME/.local/state/tristanline"
BIN_DIR="$HOME/bin"
CONFIG="$CFG_DIR/config.json"
PIDFILE="$STATE_DIR/daemon.pid"
LOG="$STATE_DIR/daemon.log"

mkdir -p "$CFG_DIR" "$STATE_DIR" "$BIN_DIR"
chmod 700 "$CFG_DIR" "$STATE_DIR"

command -v python >/dev/null 2>&1 || {
  echo 'BLOCKED: python missing in Termux. Install only python, then rerun.' >&2
  exit 2
}

RISH_BIN="${RISH:-$(command -v rish 2>/dev/null || true)}"
[ -n "$RISH_BIN" ] || RISH_BIN="$HOME/bin/rish"
[ -f "$RISH_BIN" ] || {
  echo 'BLOCKED: rish missing. Tristanline will not fake device authority.' >&2
  exit 3
}

if [ ! -f "$CONFIG" ]; then
  cp "$ROOT/config/tristanline/user0.json" "$CONFIG"
  chmod 600 "$CONFIG"
fi

cat > "$BIN_DIR/tristanline" <<EOF
#!/data/data/com.termux/files/usr/bin/bash
exec python '$ROOT/tools/tristanline.py' --config '$CONFIG' --state '$STATE_DIR' "\$@"
EOF
chmod +x "$BIN_DIR/tristanline"

cat > "$BIN_DIR/tristanline-tick" <<EOF
#!/data/data/com.termux/files/usr/bin/bash
exec '$BIN_DIR/tristanline' tick
EOF
chmod +x "$BIN_DIR/tristanline-tick"

"$BIN_DIR/tristanline" doctor | tee "$STATE_DIR/doctor.json"

if [ -f "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
  kill "$(cat "$PIDFILE")" 2>/dev/null || true
  sleep 1
fi
nohup "$BIN_DIR/tristanline" daemon >>"$LOG" 2>&1 </dev/null &
echo $! > "$PIDFILE"

# Optional Android JobScheduler safety net. The daemon remains the fast path;
# this periodic tick restores policy after process death without adding cron.
if command -v termux-job-scheduler >/dev/null 2>&1; then
  termux-job-scheduler \
    --job-id 8711 \
    --period-ms 900000 \
    --persisted true \
    --script "$BIN_DIR/tristanline-tick" >/dev/null 2>&1 || true
fi

sleep 1
"$BIN_DIR/tristanline" status | tee "$STATE_DIR/bootstrap-status.json"
echo "TRISTANLINE BEACHHEAD READY pid=$(cat "$PIDFILE")"
