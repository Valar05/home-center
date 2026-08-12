#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
STATE="$HOME/.local/state/home-center"
CFG="$HOME/.config/home-center"
BIN="$HOME/bin"
BOOT="$HOME/.termux/boot"
mkdir -p "$STATE" "$CFG" "$BIN" "$BOOT"
chmod 700 "$CFG"

PY="$ROOT/tools/eve_humane_session_daemon.py"
[ -f "$PY" ] || { echo "BLOCKED: missing $PY" >&2; exit 2; }
command -v python >/dev/null 2>&1 || { echo "BLOCKED: python missing in Termux" >&2; exit 2; }

cat > "$BIN/eve-session" <<EOF
#!/data/data/com.termux/files/usr/bin/bash
exec python '$PY' "\$@"
EOF
chmod +x "$BIN/eve-session"

# First run writes a conservative, editable config if none exists.
"$BIN/eve-session" init >/dev/null

cat > "$BOOT/40-eve-humane-session" <<EOF
#!/data/data/com.termux/files/usr/bin/bash
STATE='${STATE}'
BIN='${BIN}'
mkdir -p "\$STATE"
PID="\$STATE/eve-humane-session.pid"
LOG="\$STATE/eve-humane-session-supervisor.log"
if [ -f "\$PID" ] && kill -0 "\$(cat "\$PID")" 2>/dev/null; then
  exit 0
fi
nohup "\$BIN/eve-session" daemon >>"\$LOG" 2>&1 < /dev/null &
echo \$! > "\$PID"
EOF
chmod +x "$BOOT/40-eve-humane-session"

PID="$STATE/eve-humane-session.pid"
LOG="$STATE/eve-humane-session-supervisor.log"
if [ -f "$PID" ] && kill -0 "$(cat "$PID")" 2>/dev/null; then
  kill "$(cat "$PID")" 2>/dev/null || true
  sleep 1
fi
nohup "$BIN/eve-session" daemon >>"$LOG" 2>&1 < /dev/null &
echo $! > "$PID"
sleep 2
kill -0 "$(cat "$PID")" 2>/dev/null || {
  echo "BLOCKED: Eve daemon exited; inspect $LOG" >&2
  tail -80 "$LOG" >&2 || true
  exit 3
}

cat <<EOF
EVE SESSION DAEMON RUNNING pid=$(cat "$PID")
config=$CFG/eve-humane-session.json
status: $BIN/eve-session status
begin:  $BIN/eve-session begin
end:    $BIN/eve-session end
skip:   $BIN/eve-session skip
boot_script=$BOOT/40-eve-humane-session
NOTE: reboot persistence requires the Termux:Boot companion app to be installed and launched once.
NOTE: Android notifications/TTS require the Termux:API companion app plus the termux-api package; daemon still works without them.
EOF
