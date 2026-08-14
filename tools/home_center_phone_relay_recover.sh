#!/system/bin/sh
set -eu

ROOT="${HC_PHONE_REPO:-/storage/emulated/0/Documents/GodotProjects/home-center-phone-hands}"
STATE_DIR="${HC_PHONE_STATE_DIR:-$HOME/.local/state/home-center}"
LOG="$STATE_DIR/phone-relay.log"
PIDFILE="$STATE_DIR/phone-relay.pid"
HEARTBEAT="${HC_PHONE_RELAY_HEARTBEAT:-$STATE_DIR/phone-relay-heartbeat.json}"
RECEIPTS="$STATE_DIR/phone-relay-recovery-receipts.jsonl"
LATEST="$STATE_DIR/phone-relay-recovery-latest.json"
# The relay's Home Center requests may legitimately block for up to 45 seconds.
# Health therefore allows a bounded margin beyond one request, while first boot
# gets enough time for token refresh + registration + the first successful pull.
MAX_HEARTBEAT_AGE="${HC_PHONE_RELAY_HEALTH_MAX_AGE_SECONDS:-90}"
STARTUP_WAIT_SECONDS="${HC_PHONE_RELAY_STARTUP_WAIT_SECONDS:-120}"
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

heartbeat_ok() {
  wanted_pid="$1"
  [ -f "$HEARTBEAT" ] || return 1
  "$PYTHON" - "$HEARTBEAT" "$wanted_pid" "$MAX_HEARTBEAT_AGE" <<'PY' >/dev/null 2>&1
import json,sys,time
path,pid,max_age=sys.argv[1],int(sys.argv[2]),int(sys.argv[3])
try:
    data=json.load(open(path,encoding='utf-8'))
except Exception:
    raise SystemExit(2)
if data.get('schema')!='home-center-phone-relay-heartbeat-v1':
    raise SystemExit(3)
if data.get('deviceId')!='primary-phone':
    raise SystemExit(4)
if int(data.get('pid') or 0)!=pid:
    raise SystemExit(5)
age=int(time.time())-int(data.get('lastSuccessAtEpoch') or 0)
if age < 0 or age > max_age:
    raise SystemExit(6)
if data.get('state') not in {'poll_ok','command_completed','command_failed'}:
    raise SystemExit(7)
PY
}

wait_for_heartbeat() {
  wanted_pid="$1"
  tries="${2:-$STARTUP_WAIT_SECONDS}"
  i=0
  while [ "$i" -lt "$tries" ]; do
    kill -0 "$wanted_pid" 2>/dev/null || return 1
    heartbeat_ok "$wanted_pid" && return 0
    i=$((i+1))
    sleep 1
  done
  return 1
}

print_receipt() {
  status="$1"
  pids="$(relay_pids | tr '\n' ' ' | sed 's/[[:space:]]*$//')"
  "$PYTHON" - "$status" "$ROOT" "$RELAY" "$pids" "$HEARTBEAT" "$LOG" "$RECEIPTS" "$LATEST" <<'PY'
import json,os,sys,time
status,root,relay,pids,heartbeat,log,receipts,latest=sys.argv[1:]
now=int(time.time())
hb={'present':False}
if os.path.isfile(heartbeat):
    hb['present']=True
    try:
        raw=json.load(open(heartbeat,encoding='utf-8'))
        hb.update({
            'schema':raw.get('schema'),
            'deviceId':raw.get('deviceId'),
            'pid':raw.get('pid'),
            'state':raw.get('state'),
            'lastSuccessAtEpoch':raw.get('lastSuccessAtEpoch'),
            'ageSeconds':max(0,now-int(raw.get('lastSuccessAtEpoch') or 0)),
        })
    except Exception as exc:
        hb['parseError']=type(exc).__name__
obj={
    'schema':'home-center-phone-relay-recovery-v1',
    'checkedAtEpoch':now,
    'status':status,
    'deviceId':'primary-phone',
    'repo':root,
    'relay':relay,
    'pids':pids.split() if pids else [],
    'heartbeatPath':heartbeat,
    'heartbeat':hb,
    'log':log,
}
os.makedirs(os.path.dirname(receipts),exist_ok=True)
with open(receipts,'a',encoding='utf-8') as f:
    f.write(json.dumps(obj,sort_keys=True)+'\n')
if os.path.getsize(receipts)>512*1024:
    lines=open(receipts,encoding='utf-8').read().splitlines()[-1000:]
    tmp=receipts+'.tmp';open(tmp,'w',encoding='utf-8').write('\n'.join(lines)+'\n');os.replace(tmp,receipts)
tmp=latest+'.tmp';open(tmp,'w',encoding='utf-8').write(json.dumps(obj,indent=2,sort_keys=True)+'\n');os.replace(tmp,latest)
print(json.dumps(obj,sort_keys=True))
PY
}

if [ ! -f "$RELAY" ]; then
  say "BLOCKED: relay script missing: $RELAY"
  print_receipt "blocked_missing_relay"
  exit 2
fi

if relay_alive; then
  existing_pid="$(relay_pids | head -n1)"
  if heartbeat_ok "$existing_pid"; then
    say "relay process has a fresh Home Center poll heartbeat"
    printf '%s\n' "$existing_pid" > "$PIDFILE"
    print_receipt "healthy"
    exit 0
  fi
  say "relay process exists but Home Center liveness is not proven; attempting bounded recovery"
  for pid in $(relay_pids); do kill "$pid" 2>/dev/null || true; done
  sleep 1
fi

say "starting one fresh relay instance"
cd "$ROOT"
rm -f "$HEARTBEAT"
nohup "$PYTHON" "$RELAY" >> "$LOG" 2>&1 < /dev/null &
pid=$!
printf '%s\n' "$pid" > "$PIDFILE"

if wait_for_heartbeat "$pid" "$STARTUP_WAIT_SECONDS"; then
  say "relay started and completed a fresh Home Center poll"
  print_receipt "recovered"
  exit 0
fi

if kill -0 "$pid" 2>/dev/null; then
  say "relay is alive but did not prove Home Center liveness"
  tail -n 30 "$LOG" || true
  print_receipt "running_unconfirmed"
  exit 1
fi

say "relay exited before proving Home Center liveness"
tail -n 40 "$LOG" || true
print_receipt "failed"
exit 1
