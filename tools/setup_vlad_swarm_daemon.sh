#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

REPO_ROOT="${HC_REPO_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}"
STATE_DIR="${HC_SWARM_STATE_DIR:-$HOME/.local/state/home-center/vlad-swarm}"
SERVICE_DIR="$PREFIX/var/service/vlad-swarm"
LOG_DIR="$PREFIX/var/log/vlad-swarm"
MODE="${1:-ensure}"
RECEIPT="$STATE_DIR/service-receipt.json"

mkdir -p "$STATE_DIR" "$LOG_DIR"
chmod +x "$REPO_ROOT/tools/vlad_swarm_daemon.py"

write_receipt(){
  local ok="$1" manager="$2" detail="$3"
  python3 - "$RECEIPT" "$ok" "$manager" "$detail" "$REPO_ROOT" <<'PY'
import json,os,sys,time
path,ok,manager,detail,root=sys.argv[1:]
obj={'schema':'vlad-swarm-service-v2','ok':ok=='1','manager':manager,'detail':detail,'repoRoot':root,'atEpoch':int(time.time())}
os.makedirs(os.path.dirname(path),exist_ok=True);tmp=path+'.tmp';open(tmp,'w',encoding='utf-8').write(json.dumps(obj,indent=2,sort_keys=True)+'\n');os.replace(tmp,path);print(json.dumps(obj,sort_keys=True))
PY
}

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
  if [ "$MODE" = "restart" ]; then sv restart vlad-swarm >/dev/null 2>&1 || sv up vlad-swarm >/dev/null 2>&1 || true; else sv up vlad-swarm >/dev/null 2>&1 || true; fi
  sleep 1
  if sv status vlad-swarm 2>/dev/null | grep -q '^run:'; then write_receipt 1 runit "vlad-swarm running from canonical repoRoot"; else write_receipt 0 runit "vlad-swarm is not running"; exit 2; fi
else
  PIDFILE="$STATE_DIR/daemon.pid"
  if [ "$MODE" = "restart" ] && [ -f "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then kill "$(cat "$PIDFILE")" 2>/dev/null || true; sleep 1; fi
  if [ -f "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then write_receipt 1 pidfile "vlad-swarm already running pid=$(cat "$PIDFILE")"; exit 0; fi
  nohup env HC_REPO_ROOT="$REPO_ROOT" python3 "$REPO_ROOT/tools/vlad_swarm_daemon.py" >>"$STATE_DIR/daemon.log" 2>&1 </dev/null &
  echo $! > "$PIDFILE"
  sleep 1
  if kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then write_receipt 1 pidfile "vlad-swarm started pid=$(cat "$PIDFILE")"; else write_receipt 0 pidfile "vlad-swarm exited during startup"; exit 3; fi
fi
