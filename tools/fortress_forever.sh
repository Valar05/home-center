#!/data/data/com.termux/files/usr/bin/bash
set -uo pipefail

# FORTRESS FOREVER
# One supervisor. No prose. No terminal success condition except explicit retirement.
# Existing organs remain authoritative; this loop wakes them, records truth, and retries.

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
STATE="${HC_FOREVER_STATE:-$HOME/.local/state/home-center/forever}"
STOP="$STATE/RETIRE"
LOG="$STATE/forever.log"
RECEIPT="$STATE/receipt.json"
LOCK="$STATE/lock"
SLEEP_MIN="${HC_FOREVER_SLEEP_MIN:-20}"
SLEEP_MAX="${HC_FOREVER_SLEEP_MAX:-300}"
mkdir -p "$STATE"

exec 9>"$LOCK"
flock -n 9 || exit 0

stamp(){ date -Iseconds; }
record(){ printf '%s\t%s\n' "$(stamp)" "$*" >> "$LOG"; }
run(){
  name="$1"; shift
  start="$(date +%s)"
  record "START $name"
  if timeout 900 "$@" >>"$LOG" 2>&1; then rc=0; else rc=$?; fi
  end="$(date +%s)"
  record "END $name rc=$rc seconds=$((end-start))"
  return "$rc"
}

# Wake existing machinery; absence is a visible gap, not an excuse to invent a substitute.
cycle(){
  progressed=0

  if [ -x "$ROOT/tools/adam_failure_daemon.sh" ]; then
    run failure-memory "$ROOT/tools/adam_failure_daemon.sh" render && progressed=1 || true
  fi

  if [ -x "$ROOT/tools/demotivational_poster_os_tmux.sh" ]; then
    run poster-os "$ROOT/tools/demotivational_poster_os_tmux.sh" start && progressed=1 || true
  fi

  if [ -x "$ROOT/tools/fortress_script_campaign_hole.sh" ]; then
    run hole-campaign "$ROOT/tools/fortress_script_campaign_hole.sh" && progressed=1 || true
  fi

  # Text ingestion lives in the Android app notification listener. This supervisor
  # does not counterfeit deployment; it records whether repository support exists.
  sms="$ROOT/app/src/main/java/com/dclar/homecenter/SmsCalendarNotificationListener.java"
  [ -f "$sms" ] && sms_state=IMPLEMENTED_IN_REPO || sms_state=MISSING

  # Call capture is not claimed until phone runtime evidence exists.
  call_state=NOT_PROVEN_ON_PHONE

  python3 - "$RECEIPT" "$progressed" "$sms_state" "$call_state" <<'PY'
import json,sys,time,os
p,progressed,sms,call=sys.argv[1:]
obj={
 'schema':'fortress-forever-v1',
 'timestamp':int(time.time()),
 'cycleProgressAttempted':progressed=='1',
 'textIngestion':sms,
 'callCapture':call,
 'terminal':False,
 'retireFile':os.path.join(os.path.dirname(p),'RETIRE')
}
tmp=p+'.tmp'
open(tmp,'w').write(json.dumps(obj,indent=2,sort_keys=True)+'\n')
os.replace(tmp,p)
PY
}

backoff="$SLEEP_MIN"
record "BOOT pid=$$ root=$ROOT"
while [ ! -e "$STOP" ]; do
  before="$(date +%s)"
  cycle
  after="$(date +%s)"
  if [ $((after-before)) -gt 5 ]; then backoff="$SLEEP_MIN"; else
    backoff=$((backoff*2)); [ "$backoff" -gt "$SLEEP_MAX" ] && backoff="$SLEEP_MAX"
  fi
  sleep "$backoff"
done
record "RETIRED explicit_file=$STOP"
