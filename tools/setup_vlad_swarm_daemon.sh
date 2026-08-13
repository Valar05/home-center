#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

REPO_ROOT="${HC_REPO_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}"
STATE_DIR="${HC_SWARM_STATE_DIR:-$HOME/.local/state/home-center/vlad-swarm}"
BIN_DIR="${HC_VLAD_BIN_DIR:-${PREFIX:-$HOME/.local}/bin}"
VLAD_TARGET="$BIN_DIR/vlad"
DAEMON="$REPO_ROOT/tools/vlad_swarm_daemon_receipted.py"
SERVICE_DIR="$PREFIX/var/service/vlad-swarm"
LOG_DIR="$PREFIX/var/log/vlad-swarm"
MODE="${1:-ensure}"
RECEIPT="$STATE_DIR/service-receipt.json"
JAR_RECEIPT="$STATE_DIR/judgement-jar-bootstrap.json"

mkdir -p "$STATE_DIR" "$LOG_DIR" "$BIN_DIR"
for file in \
  "$REPO_ROOT/tools/vlad_swarm_daemon.py" \
  "$DAEMON" \
  "$REPO_ROOT/tools/vlad_jars.py" \
  "$REPO_ROOT/tools/judgement_jar_runtime.py" \
  "$REPO_ROOT/config/judgement-jar-runtime.v1.json"; do
  [ -f "$file" ] || { echo "BLOCKED: required Vlad/Jar component missing: $file" >&2; exit 2; }
done
chmod +x "$REPO_ROOT/tools/vlad_swarm_daemon.py" "$DAEMON" "$REPO_ROOT/tools/vlad_jars.py"

TMP_VLAD="$VLAD_TARGET.tmp.$$"
cat > "$TMP_VLAD" <<EOF
#!/data/data/com.termux/files/usr/bin/bash
exec python3 $(printf '%q' "$REPO_ROOT/tools/vlad_jars.py") "\$@"
EOF
chmod 755 "$TMP_VLAD"
mv -f "$TMP_VLAD" "$VLAD_TARGET"
hash -r 2>/dev/null || true

"$VLAD_TARGET" jars list --json > "$JAR_RECEIPT"
python3 - "$JAR_RECEIPT" <<'PY'
import json,sys
obj=json.load(open(sys.argv[1],encoding='utf-8'))
assert obj.get('ok') is True, obj
assert obj.get('count') == 8, obj
assert len(obj.get('jars') or []) == 8, obj
assert all(j.get('path','').startswith('.continue/rules/') for j in obj['jars']), obj
print(json.dumps({'ok':True,'jarCount':8,'catalogSync':obj.get('catalogSync',{}).get('state'),'receipt':sys.argv[1]},sort_keys=True))
PY

write_receipt(){
  local ok="$1" manager="$2" detail="$3"
  python3 - "$RECEIPT" "$ok" "$manager" "$detail" "$REPO_ROOT" "$VLAD_TARGET" "$JAR_RECEIPT" "$DAEMON" <<'PY'
import json,os,sys,time
path,ok,manager,detail,root,vlad_target,jar_receipt,daemon=sys.argv[1:]
jar=json.load(open(jar_receipt,encoding='utf-8'))
obj={
  'schema':'vlad-swarm-service-v4-judgement-jar-heartbeat-sync',
  'ok':ok=='1',
  'manager':manager,
  'detail':detail,
  'repoRoot':root,
  'daemonEntrypoint':daemon,
  'vladTarget':vlad_target,
  'jarCount':jar.get('count'),
  'jarCatalogSyncState':jar.get('catalogSync',{}).get('state'),
  'jarUsageReceiptsRequired':True,
  'jarOutputKindRequired':True,
  'jarPendingOutboxOldestFirst':True,
  'jarSyncUsesExistingDaemonHeartbeat':True,
  'jarBootstrapReceipt':jar_receipt,
  'atEpoch':int(time.time()),
}
os.makedirs(os.path.dirname(path),exist_ok=True)
tmp=path+'.tmp'
open(tmp,'w',encoding='utf-8').write(json.dumps(obj,indent=2,sort_keys=True)+'\n')
os.replace(tmp,path)
print(json.dumps(obj,sort_keys=True))
PY
}

if command -v sv >/dev/null 2>&1 && [ -d "$PREFIX/var/service" ]; then
  mkdir -p "$SERVICE_DIR/log"
  cat > "$SERVICE_DIR/run" <<EOF
#!/data/data/com.termux/files/usr/bin/bash
exec env HC_REPO_ROOT=$(printf '%q' "$REPO_ROOT") python3 $(printf '%q' "$DAEMON") 2>&1
EOF
  cat > "$SERVICE_DIR/log/run" <<EOF
#!/data/data/com.termux/files/usr/bin/bash
exec svlogd -tt $(printf '%q' "$LOG_DIR")
EOF
  chmod +x "$SERVICE_DIR/run" "$SERVICE_DIR/log/run"
  if [ "$MODE" = "restart" ]; then
    sv restart vlad-swarm >/dev/null 2>&1 || sv up vlad-swarm >/dev/null 2>&1 || true
  else
    sv up vlad-swarm >/dev/null 2>&1 || true
  fi
  sleep 1
  if sv status vlad-swarm 2>/dev/null | grep -q '^run:'; then
    write_receipt 1 runit "vlad-swarm running; fast Jar access and heartbeat sync installed"
  else
    write_receipt 0 runit "vlad-swarm is not running"
    exit 2
  fi
else
  PIDFILE="$STATE_DIR/daemon.pid"
  if [ "$MODE" = "restart" ] && [ -f "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
    kill "$(cat "$PIDFILE")" 2>/dev/null || true
    sleep 1
  fi
  if [ -f "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
    write_receipt 1 pidfile "vlad-swarm already running pid=$(cat "$PIDFILE"); fast Jar access installed"
    exit 0
  fi
  nohup env HC_REPO_ROOT="$REPO_ROOT" python3 "$DAEMON" >>"$STATE_DIR/daemon.log" 2>&1 </dev/null &
  echo $! > "$PIDFILE"
  sleep 1
  if kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
    write_receipt 1 pidfile "vlad-swarm started pid=$(cat "$PIDFILE"); fast Jar access and heartbeat sync installed"
  else
    write_receipt 0 pidfile "vlad-swarm exited during startup"
    exit 3
  fi
fi
