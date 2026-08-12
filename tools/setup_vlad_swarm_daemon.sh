#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

REPO_ROOT="${HC_REPO_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}"
STATE_DIR="${HC_SWARM_STATE_DIR:-$HOME/.local/state/home-center/vlad-swarm}"
SERVICE_DIR="$PREFIX/var/service/vlad-swarm"
LOG_DIR="$PREFIX/var/log/vlad-swarm"

mkdir -p "$STATE_DIR" "$LOG_DIR"
chmod +x "$REPO_ROOT/tools/vlad_swarm_daemon.py"

if command -v sv >/dev/null 2>&1 && [ -d "$PREFIX/var/service" ]; then
  mkdir -p "$SERVICE_DIR/log"
  cat > "$SERVICE_DIR/run" <<EOF
#!/data/data/com.termux/files/usr/bin/bash
exec env HC_REPO_ROOT=$(printf '%q' "$REPO_ROOT") python3 $(printf '%q' "$REPO_ROOT/tools/vlad_swarm_daemon.py") 2>&1
EOF
  cat > "$SERVICE_DIR/log/run" <<EOF
#!/data/data/com.termux/files/usr/bin/bash
exec svlogd -tt $(printf '%q' "$LOG_DIR")
EOF
  chmod +x "$SERVICE_DIR/run" "$SERVICE_DIR/log/run"
  sv up vlad-swarm || true
  echo "vlad-swarm service installed via runit"
  sv status vlad-swarm || true
else
  PIDFILE="$STATE_DIR/daemon.pid"
  if [ -f "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
    echo "vlad-swarm already running pid=$(cat "$PIDFILE")"
    exit 0
  fi
  nohup env HC_REPO_ROOT="$REPO_ROOT" python3 "$REPO_ROOT/tools/vlad_swarm_daemon.py" >>"$STATE_DIR/daemon.log" 2>&1 </dev/null &
  echo $! > "$PIDFILE"
  echo "vlad-swarm started pid=$!"
fi

sleep 1
if [ -f "$STATE_DIR/last.json" ]; then
  cat "$STATE_DIR/last.json"
fi
