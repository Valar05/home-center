#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

REPO_ROOT="${HC_REPO_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}"
STATE_DIR="${HC_SWARM_STATE_DIR:-$HOME/.local/state/home-center/vlad-swarm}"
JAR_CACHE="${HC_JUDGMENT_JARS_CACHE:-$STATE_DIR/judgment-jars.json}"
JAR_CONFIG="${HC_JUDGMENT_JARS_CONFIG:-$REPO_ROOT/config/judgment-jars.v1.json}"
JAR_SYNC_RECEIPT="$STATE_DIR/judgment-jars-initial-sync.json"
JAR_USAGE_STATUS="$STATE_DIR/judgment-jar-usage-status.json"
JAR_TOOL="$REPO_ROOT/tools/judgment_jars.py"
VLAD_TOOL="$REPO_ROOT/tools/vlad.py"
JAR_RECEIPTS="$REPO_ROOT/tools/judgment_jar_receipts.py"
JAR_CLIENT="$REPO_ROOT/tools/home_center_mcp_client.py"
JAR_COMMON="$REPO_ROOT/tools/judgment_jar_common.py"
JAR_CABINET="$REPO_ROOT/tools/judgment_jar_cabinet.py"
JAR_REGISTRY="$REPO_ROOT/tools/judgment_jar_registry.py"
JAR_TEST="$REPO_ROOT/tools/test_judgment_jar_registry.py"
JAR_RECEIPT_TEST="$REPO_ROOT/tools/test_judgment_jar_receipts.py"
BIN_DIR="${HC_ADAM_BIN_DIR:-${PREFIX:-$HOME/.local}/bin}"
JAR_BIN="$BIN_DIR/vlad-jars"
VLAD_BIN="$BIN_DIR/vlad"
SERVICE_DIR="$PREFIX/var/service/vlad-swarm"
LOG_DIR="$PREFIX/var/log/vlad-swarm"
MODE="${1:-ensure}"
RECEIPT="$STATE_DIR/service-receipt.json"
DAEMON="$REPO_ROOT/tools/vlad_swarm_daemon.py"
DAEMON_SHA_FILE="$STATE_DIR/daemon-source.sha256"

mkdir -p "$STATE_DIR" "$LOG_DIR" "$BIN_DIR"
for file in \
  "$DAEMON" "$JAR_TOOL" "$VLAD_TOOL" "$JAR_RECEIPTS" "$JAR_CLIENT" \
  "$JAR_COMMON" "$JAR_CABINET" "$JAR_REGISTRY" "$JAR_TEST" \
  "$JAR_RECEIPT_TEST" "$JAR_CONFIG"; do
  [ -f "$file" ] || { echo "BLOCKED: Vlad component missing: $file" >&2; exit 4; }
done
PYTHON_BIN="$(command -v python3 || true)"
[ -n "$PYTHON_BIN" ] || { echo "BLOCKED: python3 missing." >&2; exit 5; }
chmod +x "$DAEMON" "$JAR_TOOL" "$VLAD_TOOL" "$JAR_CLIENT"

cd "$REPO_ROOT"
python3 "$JAR_TEST"
python3 "$JAR_RECEIPT_TEST"
python3 -m py_compile \
  "$DAEMON" "$JAR_TOOL" "$VLAD_TOOL" "$JAR_RECEIPTS" "$JAR_CLIENT" \
  "$JAR_COMMON" "$JAR_CABINET" "$JAR_REGISTRY"
"$PYTHON_BIN" "$JAR_TOOL" \
  --root "$REPO_ROOT" \
  --cache "$JAR_CACHE" \
  --config "$JAR_CONFIG" \
  sync --force-home-center > "$JAR_SYNC_RECEIPT"
python3 - "$JAR_SYNC_RECEIPT" "$JAR_CACHE" <<'PY'
import json,sys
receipt_path,cache_path=sys.argv[1:]
receipt=json.load(open(receipt_path,encoding='utf-8'))
if receipt.get('ok') is not True:
    raise SystemExit('BLOCKED: Judgment Jar compiler did not produce a usable cache receipt.')
if int(receipt.get('localJarCount') or 0) < 1:
    raise SystemExit('BLOCKED: no repository operational Judgment Jars were compiled.')
json.load(open(cache_path,encoding='utf-8'))
print(json.dumps({
    'ok':True,
    'complete':receipt.get('complete') is True,
    'jarCount':receipt.get('jarCount'),
    'localJarCount':receipt.get('localJarCount'),
    'cabinetJarCount':receipt.get('cabinetJarCount'),
    'unregisteredJarCount':receipt.get('unregisteredJarCount'),
    'homeCenterState':receipt.get('homeCenterState'),
    'homeCenterLastError':receipt.get('homeCenterLastError'),
    'pendingUsageReceipts':(receipt.get('usageReceipts') or {}).get('remaining'),
},sort_keys=True))
PY

TMP_JAR_BIN="$JAR_BIN.tmp.$$"
cat > "$TMP_JAR_BIN" <<EOF2
#!/data/data/com.termux/files/usr/bin/bash
exec env \
  HC_REPO_ROOT=$(printf '%q' "$REPO_ROOT") \
  HC_JUDGMENT_JARS_CACHE=$(printf '%q' "$JAR_CACHE") \
  HC_JUDGMENT_JARS_CONFIG=$(printf '%q' "$JAR_CONFIG") \
  "$PYTHON_BIN" "$JAR_TOOL" "\$@"
EOF2
chmod 755 "$TMP_JAR_BIN"
mv -f "$TMP_JAR_BIN" "$JAR_BIN"

TMP_VLAD_BIN="$VLAD_BIN.tmp.$$"
cat > "$TMP_VLAD_BIN" <<EOF2
#!/data/data/com.termux/files/usr/bin/bash
exec env \
  HC_REPO_ROOT=$(printf '%q' "$REPO_ROOT") \
  HC_JUDGMENT_JARS_CACHE=$(printf '%q' "$JAR_CACHE") \
  HC_JUDGMENT_JARS_CONFIG=$(printf '%q' "$JAR_CONFIG") \
  "$PYTHON_BIN" "$VLAD_TOOL" "\$@"
EOF2
chmod 755 "$TMP_VLAD_BIN"
mv -f "$TMP_VLAD_BIN" "$VLAD_BIN"
hash -r 2>/dev/null || true

"$JAR_BIN" status >/dev/null
"$VLAD_BIN" jars usage-status > "$JAR_USAGE_STATUS"
python3 - "$JAR_USAGE_STATUS" <<'PY'
import json,sys
value=json.load(open(sys.argv[1],encoding='utf-8'))
assert value.get('ok') is True, value
assert value.get('outputKinds'), value
assert value.get('historyPath'), value
assert value.get('pendingOutboxPath'), value
print(json.dumps({'ok':True,'outputKinds':value['outputKinds'],'pendingUsageReceipts':value.get('pendingUsageReceipts')},sort_keys=True))
PY

DAEMON_SHA="$(sha256sum "$DAEMON" | awk '{print $1}')"
INSTALLED_DAEMON_SHA="$(cat "$DAEMON_SHA_FILE" 2>/dev/null || true)"
SOURCE_CHANGED=0
[ "$DAEMON_SHA" = "$INSTALLED_DAEMON_SHA" ] || SOURCE_CHANGED=1

write_receipt(){
  local ok="$1" manager="$2" detail="$3"
  python3 - "$RECEIPT" "$ok" "$manager" "$detail" "$REPO_ROOT" "$JAR_CACHE" "$JAR_CONFIG" "$JAR_SYNC_RECEIPT" "$JAR_USAGE_STATUS" "$JAR_BIN" "$VLAD_BIN" "$DAEMON_SHA" <<'PY'
import json,os,sys,time
(path,ok,manager,detail,root,jar_cache,jar_config,jar_sync_path,
 usage_path,jar_bin,vlad_bin,daemon_sha)=sys.argv[1:]
try:
    jar_sync=json.load(open(jar_sync_path,encoding='utf-8'))
except Exception as exc:
    jar_sync={'ok':False,'complete':False,'error':f'{type(exc).__name__}: {exc}'}
try:
    usage=json.load(open(usage_path,encoding='utf-8'))
except Exception as exc:
    usage={'ok':False,'error':f'{type(exc).__name__}: {exc}'}
obj={
  'schema':'vlad-swarm-service-v5-home-center-judgment-jar-usage-receipts',
  'ok':ok=='1' and jar_sync.get('ok') is True and usage.get('ok') is True,
  'manager':manager,
  'detail':detail,
  'repoRoot':root,
  'daemonSha256':daemon_sha,
  'atEpoch':int(time.time()),
  'judgmentJars':{
    'schema':'home-center.judgment-jars.registry.v2',
    'cachePath':jar_cache,
    'configPath':jar_config,
    'cli':jar_bin,
    'vladCli':vlad_bin,
    'complete':jar_sync.get('complete') is True,
    'jarCount':jar_sync.get('jarCount'),
    'localJarCount':jar_sync.get('localJarCount'),
    'cabinetJarCount':jar_sync.get('cabinetJarCount'),
    'unregisteredJarCount':jar_sync.get('unregisteredJarCount'),
    'registryDigest':jar_sync.get('registryDigest'),
    'sourceCommit':jar_sync.get('sourceCommit'),
    'homeCenterState':jar_sync.get('homeCenterState'),
    'homeCenterLastError':jar_sync.get('homeCenterLastError'),
    'initialSyncCacheVerified':jar_sync.get('ok') is True,
  },
  'judgmentJarUsageReceipts':{
    'schema':'home-center.judgment-jar-usage-receipt.v1',
    'required':True,
    'outputKindRequired':True,
    'outputKinds':usage.get('outputKinds') or [],
    'historyPath':usage.get('historyPath'),
    'ackPath':usage.get('ackPath'),
    'pendingOutboxPath':usage.get('pendingOutboxPath'),
    'pendingUsageReceipts':usage.get('pendingUsageReceipts'),
    'oldestPendingFirst':True,
    'atomBaseUrl':usage.get('atomBaseUrl'),
    'sameDaemonSync':True,
  },
}
os.makedirs(os.path.dirname(path),exist_ok=True)
tmp=path+'.tmp'
open(tmp,'w',encoding='utf-8').write(json.dumps(obj,indent=2,sort_keys=True)+'\n')
os.replace(tmp,path)
print(json.dumps(obj,sort_keys=True))
PY
}

mark_daemon_sha(){
  printf '%s\n' "$DAEMON_SHA" > "$DAEMON_SHA_FILE.tmp"
  mv -f "$DAEMON_SHA_FILE.tmp" "$DAEMON_SHA_FILE"
}

if command -v sv >/dev/null 2>&1 && [ -d "$PREFIX/var/service" ]; then
  mkdir -p "$SERVICE_DIR/log"
  cat > "$SERVICE_DIR/run" <<EOF2
#!/data/data/com.termux/files/usr/bin/bash
exec env \
  HC_REPO_ROOT=$(printf '%q' "$REPO_ROOT") \
  HC_JUDGMENT_JARS_CACHE=$(printf '%q' "$JAR_CACHE") \
  HC_JUDGMENT_JARS_CONFIG=$(printf '%q' "$JAR_CONFIG") \
  python3 $(printf '%q' "$DAEMON") 2>&1
EOF2
  cat > "$SERVICE_DIR/log/run" <<EOF2
#!/data/data/com.termux/files/usr/bin/bash
exec svlogd -tt $(printf '%q' "$LOG_DIR")
EOF2
  chmod +x "$SERVICE_DIR/run" "$SERVICE_DIR/log/run"
  if [ "$MODE" = "restart" ] || [ "$SOURCE_CHANGED" -eq 1 ]; then
    sv restart vlad-swarm >/dev/null 2>&1 || sv up vlad-swarm >/dev/null 2>&1 || true
  else
    sv up vlad-swarm >/dev/null 2>&1 || true
  fi
  sleep 1
  if sv status vlad-swarm 2>/dev/null | grep -q '^run:'; then
    mark_daemon_sha
    write_receipt 1 runit "vlad-swarm running with Judgment Jar registry and usage-receipt sync"
  else
    write_receipt 0 runit "vlad-swarm is not running"
    exit 2
  fi
else
  PIDFILE="$STATE_DIR/daemon.pid"
  NEED_RESTART=0
  [ "$MODE" = "restart" ] && NEED_RESTART=1
  [ "$SOURCE_CHANGED" -eq 1 ] && NEED_RESTART=1
  if [ "$NEED_RESTART" -eq 1 ] && [ -f "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
    kill "$(cat "$PIDFILE")" 2>/dev/null || true
    sleep 1
  fi
  if [ -f "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
    write_receipt 1 pidfile "vlad-swarm already running pid=$(cat "$PIDFILE") with current Judgment Jar cache and receipt outbox"
    exit 0
  fi
  nohup env \
    HC_REPO_ROOT="$REPO_ROOT" \
    HC_JUDGMENT_JARS_CACHE="$JAR_CACHE" \
    HC_JUDGMENT_JARS_CONFIG="$JAR_CONFIG" \
    python3 "$DAEMON" >>"$STATE_DIR/daemon.log" 2>&1 </dev/null &
  echo $! > "$PIDFILE"
  sleep 1
  if kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
    mark_daemon_sha
    write_receipt 1 pidfile "vlad-swarm started pid=$(cat "$PIDFILE") with Judgment Jar registry and usage-receipt sync"
  else
    write_receipt 0 pidfile "vlad-swarm exited during startup"
    exit 3
  fi
fi
