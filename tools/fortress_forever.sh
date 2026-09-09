#!/data/data/com.termux/files/usr/bin/bash
set -uo pipefail

# FORTRESS FOREVER — SAINT ANDREW CUSTODY
# One supervisor. Every ordinary exit is treated as a failure and reincarnated.
# Only an explicit operator RETIRE file or an unrecoverable safety/authority boundary may stop mutation.

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
STATE="${HC_FOREVER_STATE:-$HOME/.local/state/home-center/forever}"
STOP="$STATE/RETIRE"
LOG="$STATE/forever.log"
RECEIPT="$STATE/receipt.json"
LOCK="$STATE/lock"
SLEEP_MIN="${HC_FOREVER_SLEEP_MIN:-20}"
SLEEP_MAX="${HC_FOREVER_SLEEP_MAX:-300}"
FAIL_DAEMON="$ROOT/tools/adam_failure_daemon.sh"
EVOLVE="$ROOT/tools/failure_evolution_campaign.py"
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

mandatory_failure_ritual(){
  [ -x "$FAIL_DAEMON" ] || { record "FATAL failure-memory-missing"; return 91; }
  [ -f "$EVOLVE" ] || { record "FATAL failure-evolution-missing"; return 92; }
  event="cycle:$(date +%s):$(git -C "$ROOT" rev-parse --short HEAD 2>/dev/null || echo nogit)"
  selection="$(python3 "$EVOLVE" select "$event" 2>>"$LOG")" || return 93
  trait="$(printf '%s' "$selection" | python3 -c 'import json,sys; print(json.load(sys.stdin)["trait"])' 2>>"$LOG")" || return 94
  text="$(printf '%s' "$selection" | python3 -c 'import json,sys; print(json.load(sys.stdin)["text"])' 2>>"$LOG")" || return 95
  "$FAIL_DAEMON" add "evolved:$trait" "$text" >>"$LOG" 2>&1 || return 96
  "$FAIL_DAEMON" current >>"$LOG" 2>&1 || return 97
  printf '%s\n' "$selection" > "$STATE/last-failure-selection.json"
  record "MANDATORY_FAILURE_RITUAL trait=$trait"
}

cycle(){
  progressed=0
  mandatory_failure_ritual || return $?

  if [ -x "$ROOT/tools/demotivational_poster_os_tmux.sh" ]; then
    run poster-os "$ROOT/tools/demotivational_poster_os_tmux.sh" start && progressed=1 || true
  fi
  if [ -x "$ROOT/tools/fortress_script_campaign_hole.sh" ]; then
    run hole-campaign "$ROOT/tools/fortress_script_campaign_hole.sh" && progressed=1 || true
  fi

  sms="$ROOT/app/src/main/java/com/dclar/homecenter/SmsCalendarNotificationListener.java"
  [ -f "$sms" ] && sms_state=IMPLEMENTED_IN_REPO || sms_state=MISSING
  call_state=NOT_PROVEN_ON_PHONE

  python3 - "$RECEIPT" "$progressed" "$sms_state" "$call_state" "$STATE/last-failure-selection.json" <<'PY'
import json,sys,time,os
p,progressed,sms,call,sel=sys.argv[1:]
selection={}
try: selection=json.load(open(sel))
except Exception: pass
obj={'schema':'fortress-forever-v3','timestamp':int(time.time()),
     'saintAndrewCustody':True,'normalStopAllowed':False,
     'cycleProgressAttempted':progressed=='1','failureRitualMandatory':True,
     'failureRitualPlayed':bool(selection),'failureSelection':selection,
     'textIngestion':sms,'callCapture':call,'terminal':False,
     'retireFile':os.path.join(os.path.dirname(p),'RETIRE')}
tmp=p+'.tmp'; open(tmp,'w').write(json.dumps(obj,indent=2,sort_keys=True)+'\n'); os.replace(tmp,p)
PY
}

backoff="$SLEEP_MIN"
record "BOOT SAINT_ANDREW_CUSTODY pid=$$ root=$ROOT"
while :; do
  if [ -e "$STOP" ]; then
    record "RETIRED explicit_operator_file=$STOP"
    exit 0
  fi
  before="$(date +%s)"
  if cycle; then
    after="$(date +%s)"
    if [ $((after-before)) -gt 5 ]; then backoff="$SLEEP_MIN"; else
      backoff=$((backoff*2)); [ "$backoff" -gt "$SLEEP_MAX" ] && backoff="$SLEEP_MAX"
    fi
  else
    rc=$?
    record "CYCLE_FAILED rc=$rc SAINT_ANDREW_REINCARNATES"
    backoff="$SLEEP_MIN"
  fi
  sleep "$backoff"
done
