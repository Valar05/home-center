#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
CFG="$HOME/.config/home-center"
STATE="$HOME/.local/state/home-center"
mkdir -p "$HOME/bin" "$CFG" "$STATE"
chmod 700 "$CFG"
[ -f "$CFG/codex-hub.json" ] || { echo 'BLOCKED: Home Center Termux pairing config missing.' >&2; exit 2; }
cat > "$HOME/bin/home-center-phone-relay" <<EOF
#!/data/data/com.termux/files/usr/bin/bash
exec python '$ROOT/tools/android_phone_home_center_relay.py' "\$@"
EOF
chmod +x "$HOME/bin/home-center-phone-relay"
LOG="$STATE/phone-relay.log"
PID="$STATE/phone-relay.pid"
if [ -f "$PID" ] && kill -0 "$(cat "$PID")" 2>/dev/null; then
  kill "$(cat "$PID")" 2>/dev/null || true
  sleep 1
fi
nohup "$HOME/bin/home-center-phone-relay" >>"$LOG" 2>&1 &
echo $! > "$PID"
sleep 2
kill -0 "$(cat "$PID")" 2>/dev/null || { echo "BLOCKED: relay exited; inspect $LOG" >&2; tail -80 "$LOG" >&2; exit 3; }
echo "PHONE RELAY RUNNING pid=$(cat "$PID") log=$LOG"
