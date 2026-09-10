#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
umask 077

STARTED_PID=""
KEEP_STARTED=0
PAIR_TMP=""

DEVICE_ID="${HC_RESCUE_DEVICE_ID:-primary-phone-rescue-v1}"
BASE_HOME="${HOME:?HOME is required}"
BASE_STATE="${HC_PHONE_STATE_DIR:-$BASE_HOME/.local/state/home-center}"
MAIN_HEARTBEAT="$BASE_STATE/phone-relay-heartbeat.json"
MAIN_PAIR="$BASE_HOME/.config/home-center/codex-hub.json"
RESCUE_ROOT="$BASE_STATE/rescue-relay/$DEVICE_ID"
RESCUE_HOME="$RESCUE_ROOT/home"
RESCUE_STATE="$RESCUE_HOME/.local/state/home-center"
RESCUE_HEARTBEAT="$RESCUE_STATE/phone-relay-heartbeat.json"
RESCUE_PAIR="$RESCUE_HOME/.config/home-center/codex-hub.json"
PIDFILE="$RESCUE_ROOT/relay.pid"
LOG="$RESCUE_ROOT/relay.log"
LOCK="$RESCUE_ROOT/bootstrap.lock"
MAX_MAIN_AGE_SECONDS="${HC_RESCUE_MAIN_MAX_AGE_SECONDS:-90}"
STARTUP_WAIT_SECONDS="${HC_RESCUE_STARTUP_WAIT_SECONDS:-75}"

mkdir -p "$RESCUE_ROOT"
mkdir "$LOCK" 2>/dev/null || {
  printf 'RESCUE_READY=0\nERROR=bootstrap_already_running\n'
  exit 75
}
cleanup() {
  rmdir "$LOCK" 2>/dev/null || true
  if [ "$KEEP_STARTED" -ne 1 ] && [ -n "$STARTED_PID" ] && kill -0 "$STARTED_PID" 2>/dev/null; then
    kill "$STARTED_PID" 2>/dev/null || true
  fi
  [ -n "$PAIR_TMP" ] && rm -f "$PAIR_TMP" 2>/dev/null || true
  if [ "$KEEP_STARTED" -ne 1 ] && [ -n "$STARTED_PID" ]; then
    rm -f "$RESCUE_PAIR" 2>/dev/null || true
  fi
}
trap cleanup EXIT INT TERM

say() { printf '%s\n' "$*"; }
fail() {
  say 'RESCUE_READY=0'
  say "ERROR=$*"
  exit 1
}

case "$DEVICE_ID" in
  primary-phone-rescue-[a-zA-Z0-9._-]*) ;;
  *) fail "unsafe_rescue_device_id:$DEVICE_ID" ;;
esac

PY="$(command -v python 2>/dev/null || command -v python3 2>/dev/null || true)"
[ -n "$PY" ] || fail 'python_missing'
command -v nohup >/dev/null 2>&1 || fail 'nohup_missing'
[ -r "$MAIN_PAIR" ] || fail "main_pair_unreadable:$MAIN_PAIR"
[ -r "$MAIN_HEARTBEAT" ] || fail "main_heartbeat_unreadable:$MAIN_HEARTBEAT"

MAIN_META="$($PY - "$MAIN_HEARTBEAT" "$MAX_MAIN_AGE_SECONDS" <<'PY'
import hashlib,json,os,sys,time
path,max_age=sys.argv[1],int(sys.argv[2])
try:
    data=json.load(open(path,encoding='utf-8'))
except Exception as exc:
    raise SystemExit(f'heartbeat_parse:{type(exc).__name__}')
if data.get('schema')!='home-center-phone-relay-heartbeat-v1':
    raise SystemExit('heartbeat_schema')
if data.get('deviceId')!='primary-phone':
    raise SystemExit('heartbeat_device')
pid=int(data.get('pid') or 0)
if pid <= 1:
    raise SystemExit('heartbeat_pid')
age=int(time.time())-int(data.get('lastSuccessAtEpoch') or 0)
if age < 0 or age > max_age:
    raise SystemExit(f'heartbeat_stale:{age}')
if data.get('state') not in {'poll_ok','command_completed','command_failed'}:
    raise SystemExit('heartbeat_state')
sha=str(data.get('sourceSha256') or '').lower()
if len(sha)!=64 or any(c not in '0123456789abcdef' for c in sha):
    raise SystemExit('heartbeat_source_sha')
print(f'{pid}|{sha}|{age}')
PY
)" || fail "main_relay_not_proven:$MAIN_META"
IFS='|' read -r MAIN_PID MAIN_SHA MAIN_AGE <<EOF_META
$MAIN_META
EOF_META
kill -0 "$MAIN_PID" 2>/dev/null || fail "main_relay_pid_dead:$MAIN_PID"

LIVE_SCRIPT="$($PY - "$MAIN_PID" <<'PY'
from pathlib import Path
import sys
pid=sys.argv[1]
raw=Path(f'/proc/{pid}/cmdline').read_bytes().split(b'\0')
for part in raw:
    text=part.decode('utf-8','replace')
    if text.endswith('android_phone_home_center_relay.py'):
        print(text)
        raise SystemExit(0)
raise SystemExit(2)
PY
)" || fail 'main_relay_script_not_found_in_proc'
[ -r "$LIVE_SCRIPT" ] || fail "main_relay_script_unreadable:$LIVE_SCRIPT"

SCRIPT_SHA="$($PY - "$LIVE_SCRIPT" <<'PY'
import hashlib,sys
print(hashlib.sha256(open(sys.argv[1],'rb').read()).hexdigest())
PY
)"
[ "$SCRIPT_SHA" = "$MAIN_SHA" ] || fail "main_source_hash_mismatch:heartbeat=$MAIN_SHA disk=$SCRIPT_SHA"

TOOLS_DIR="$(cd "$(dirname "$LIVE_SCRIPT")" && pwd)"
TERMUX_SHELL="$TOOLS_DIR/android_phone_termux_shell.py"
[ -r "$TERMUX_SHELL" ] || fail "termux_shell_module_missing:$TERMUX_SHELL"
"$PY" - "$LIVE_SCRIPT" "$TERMUX_SHELL" <<'PY' >/dev/null 2>&1 || fail 'relay_python_syntax_invalid'
import sys
for path in sys.argv[1:]:
    source=open(path,encoding='utf-8').read()
    compile(source,path,'exec')
PY
"$PY" - "$LIVE_SCRIPT" <<'PY' || fail 'shizuku_independence_invariant_missing'
import sys
text=open(sys.argv[1],encoding='utf-8').read()
needle="if kind in TERMUX_SHELL_ACTIONS:\n        return termux_shell_execute(action)"
gate='from android_operator_overlay import ('
if needle not in text or gate not in text or text.index(needle) > text.index(gate):
    raise SystemExit(1)
PY

RESCUE_NODE="$RESCUE_HOME/.config/home-center/phone-relay.json"
if [ -r "$RESCUE_NODE" ]; then
  "$PY" - "$RESCUE_NODE" "$DEVICE_ID" <<'PY' >/dev/null 2>&1 || fail 'rescue_node_identity_mismatch'
import json,sys
d=json.load(open(sys.argv[1],encoding='utf-8'))
assert d.get('deviceId')==sys.argv[2]
assert isinstance(d.get('deviceToken'),str) and len(d.get('deviceToken')) >= 32
PY
fi

existing_pid=""
[ -f "$PIDFILE" ] && existing_pid="$(cat "$PIDFILE" 2>/dev/null || true)"
if [ -n "$existing_pid" ] && kill -0 "$existing_pid" 2>/dev/null; then
  [ "$existing_pid" != "$MAIN_PID" ] || fail 'rescue_pidfile_points_to_primary_relay'
  if "$PY" - "$RESCUE_HEARTBEAT" "$existing_pid" "$DEVICE_ID" "$SCRIPT_SHA" <<'PY' >/dev/null 2>&1
import json,sys,time
path,pid,device,sha=sys.argv[1:]
d=json.load(open(path,encoding='utf-8'))
assert d.get('schema')=='home-center-phone-relay-heartbeat-v1'
assert d.get('deviceId')==device
assert int(d.get('pid') or 0)==int(pid)
assert d.get('sourceSha256')==sha
assert d.get('baselineTransport')=='termux-no-shizuku'
assert d.get('state') in {'poll_ok','command_completed','command_failed'}
age=int(time.time())-int(d.get('lastSuccessAtEpoch') or 0)
assert 0 <= age <= 90
PY
  then
    say 'RESCUE_READY=1'
    say "DEVICE_ID=$DEVICE_ID"
    say "PID=$existing_pid"
    say "SOURCE_SHA256=$SCRIPT_SHA"
    say 'NORMAL_RUNTIME_MUTATED=0'
    say 'SHIZUKU_REQUIRED=0'
    exit 0
  fi
  if tr '\0' ' ' < "/proc/$existing_pid/cmdline" 2>/dev/null | grep -Fq "$LIVE_SCRIPT" \
     && tr '\0' '\n' < "/proc/$existing_pid/environ" 2>/dev/null | grep -Fxq "HOME=$RESCUE_HOME"; then
    kill "$existing_pid" 2>/dev/null || true
    for _ in 1 2 3 4 5; do
      kill -0 "$existing_pid" 2>/dev/null || break
      sleep 1
    done
    kill -0 "$existing_pid" 2>/dev/null && fail "stale_rescue_pid_would_not_exit:$existing_pid"
  else
    fail "pidfile_points_to_unrelated_process:$existing_pid"
  fi
fi

mkdir -p "$(dirname "$RESCUE_PAIR")" "$RESCUE_STATE"
PAIR_TMP="$RESCUE_PAIR.tmp.$$"
cp "$MAIN_PAIR" "$PAIR_TMP" || fail 'pair_copy_failed'
chmod 600 "$PAIR_TMP" || fail 'pair_chmod_failed'
mv -f "$PAIR_TMP" "$RESCUE_PAIR" || fail 'pair_install_failed'
PAIR_TMP=""

rm -f "$RESCUE_HEARTBEAT"
nohup env \
  HOME="$RESCUE_HOME" \
  HC_PHONE_DEVICE_ID="$DEVICE_ID" \
  HC_PHONE_STATE_DIR="$RESCUE_STATE" \
  HC_PHONE_RELAY_BASE="https://us-central1-home-center-dclar.cloudfunctions.net/phoneHandsRelay" \
  "$PY" "$LIVE_SCRIPT" >>"$LOG" 2>&1 </dev/null &
NEW_PID=$!
STARTED_PID="$NEW_PID"
printf '%s\n' "$NEW_PID" > "$PIDFILE"

ready=0
i=0
while [ "$i" -lt "$STARTUP_WAIT_SECONDS" ]; do
  kill -0 "$NEW_PID" 2>/dev/null || break
  if "$PY" - "$RESCUE_HEARTBEAT" "$NEW_PID" "$DEVICE_ID" "$SCRIPT_SHA" <<'PY' >/dev/null 2>&1
import json,sys,time
path,pid,device,sha=sys.argv[1:]
d=json.load(open(path,encoding='utf-8'))
assert d.get('schema')=='home-center-phone-relay-heartbeat-v1'
assert d.get('deviceId')==device
assert int(d.get('pid') or 0)==int(pid)
assert d.get('sourceSha256')==sha
assert d.get('baselineTransport')=='termux-no-shizuku'
assert d.get('state') in {'poll_ok','command_completed','command_failed'}
age=int(time.time())-int(d.get('lastSuccessAtEpoch') or 0)
assert 0 <= age <= 15
PY
  then
    ready=1
    break
  fi
  i=$((i+1))
  sleep 1
done

if [ "$ready" -ne 1 ]; then
  if kill -0 "$NEW_PID" 2>/dev/null; then
    kill "$NEW_PID" 2>/dev/null || true
  fi
  tail -n 30 "$LOG" 2>/dev/null || true
  fail 'rescue_relay_failed_to_prove_fresh_home_center_poll'
fi

KEEP_STARTED=1
say 'RESCUE_READY=1'
say "DEVICE_ID=$DEVICE_ID"
say "PID=$NEW_PID"
say "SOURCE_SHA256=$SCRIPT_SHA"
say "MAIN_RELAY_PID=$MAIN_PID"
say "MAIN_HEARTBEAT_AGE_SECONDS=$MAIN_AGE"
say 'NORMAL_RUNTIME_MUTATED=0'
say 'SHIZUKU_REQUIRED=0'
say "RESCUE_STATE=$RESCUE_ROOT"
