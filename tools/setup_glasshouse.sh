#!/usr/bin/env sh
set -eu

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
STATE="$HOME/.local/state/home-center/glasshouse"
mkdir -p "$STATE" "$HOME/bin"

cat > "$HOME/bin/glasshouse" <<EOF
#!/usr/bin/env sh
exec python3 '$ROOT/tools/glasshouse.py' "\$@"
EOF
chmod +x "$HOME/bin/glasshouse"

PID="$STATE/server.pid"
LOG="$STATE/server.log"

if [ -f "$PID" ] && kill -0 "$(cat "$PID")" 2>/dev/null; then
  kill "$(cat "$PID")" 2>/dev/null || true
  sleep 1
fi

nohup "$HOME/bin/glasshouse" serve --host 127.0.0.1 --port 8765 --workspace "$ROOT" --allow-command >>"$LOG" 2>&1 &
echo $! > "$PID"
sleep 1
kill -0 "$(cat "$PID")" 2>/dev/null || {
  echo "BLOCKED: Glasshouse exited; inspect $LOG" >&2
  tail -80 "$LOG" >&2
  exit 3
}

"$HOME/bin/glasshouse" emit system --pane timeline --title "Glasshouse ready" --text "workspace=$ROOT" --no-focus >/dev/null

echo "GLASSHOUSE RUNNING pid=$(cat "$PID")"
echo "http://127.0.0.1:8765"
echo "log=$LOG"

if command -v termux-open-url >/dev/null 2>&1; then
  termux-open-url http://127.0.0.1:8765 >/dev/null 2>&1 || true
fi
