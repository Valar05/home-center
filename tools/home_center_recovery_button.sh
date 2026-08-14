#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

ROOT="${HC_REPO_ROOT:-/storage/emulated/0/Documents/GodotProjects/home-center}"
STATE="${HC_STATE_DIR:-$HOME/.local/state/home-center}"
ID="${HC_RECOVERY_NOTIFICATION_ID:-6422}"
RECEIPT="$STATE/home-center-recovery-button-latest.json"
LOG="$STATE/home-center-recovery-button.log"
mkdir -p "$STATE"

q(){ printf '%q' "$1"; }
action(){ printf "bash -l -c '%s'" "$1"; }
SELF="cd $(q "$ROOT") && bash tools/home_center_recovery_button.sh"

write_receipt(){
  local phase="$1" ok="$2" detail="$3"
  python3 - "$RECEIPT" "$phase" "$ok" "$detail" <<'PY'
import json,os,sys,time
path,phase,ok,detail=sys.argv[1:]
obj={
  'schema':'home-center-recovery-button-v1',
  'phase':phase,
  'ok':ok=='1',
  'detail':detail,
  'device':'primary-phone',
  'verifiedAtEpoch':int(time.time()),
  'truth':{
    'buttonExistsInNotification':phase in {'posted','healthy','degraded','blocked','failed'},
    'homeCenterRecovered':phase=='healthy' and ok=='1',
    'phoneEvidenceRequired':True,
  }
}
os.makedirs(os.path.dirname(path),exist_ok=True)
tmp=path+'.tmp';open(tmp,'w',encoding='utf-8').write(json.dumps(obj,indent=2,sort_keys=True)+'\n');os.replace(tmp,path)
print(json.dumps(obj,sort_keys=True))
PY
}

post(){
  local title="$1" content="$2" priority="${3:-high}"
  command -v termux-notification >/dev/null 2>&1 || return 3
  termux-notification \
    --id "$ID" \
    --title "$title" \
    --content "$content" \
    --priority "$priority" \
    --ongoing true \
    --button1 'TURN HOME CENTER ON' \
    --button1-action "$(action "$SELF recover")" \
    --button2 'STATUS' \
    --button2-action "$(action "$SELF status")" >/dev/null
}

relay_health(){
  [ -f "$STATE/phone-relay-heartbeat.json" ] || return 1
  python3 - "$STATE/phone-relay-heartbeat.json" <<'PY' >/dev/null 2>&1
import json,sys,time
p=sys.argv[1]
d=json.load(open(p,encoding='utf-8'))
if d.get('schema')!='home-center-phone-relay-heartbeat-v1': raise SystemExit(2)
if d.get('deviceId')!='primary-phone': raise SystemExit(3)
age=int(time.time())-int(d.get('lastSuccessAtEpoch') or 0)
if age < 0 or age > 90: raise SystemExit(4)
if d.get('state') not in {'poll_ok','command_completed','command_failed'}: raise SystemExit(5)
PY
}

recover(){
  termux-wake-lock >/dev/null 2>&1 || true
  post 'Home Center recovery' 'Working… actual relay heartbeat will decide success.' max || true
  write_receipt posted 0 'Recovery button pressed; recovery in progress.' >>"$LOG" 2>&1 || true

  local rc=0 detail=''
  if [ -x "$ROOT/tools/home_center_phone_relay_recover.sh" ]; then
    if HC_PHONE_REPO="$ROOT" sh "$ROOT/tools/home_center_phone_relay_recover.sh" >>"$LOG" 2>&1; then
      :
    else
      rc=$?
      detail="relay recovery exited $rc"
    fi
  else
    rc=20
    detail='home_center_phone_relay_recover.sh missing'
  fi

  if [ "$rc" -eq 0 ] && [ -x "$ROOT/tools/phone_hands_watchdog.sh" ]; then
    bash "$ROOT/tools/phone_hands_watchdog.sh" diagnose >>"$LOG" 2>&1 || true
  fi

  if [ "$rc" -eq 0 ] && relay_health; then
    write_receipt healthy 1 'Fresh primary-phone Home Center relay heartbeat proven.' >>"$LOG"
    post 'HOME CENTER • ON' 'Recovered. Fresh phone relay heartbeat proven.' default
    command -v termux-toast >/dev/null 2>&1 && termux-toast 'Home Center is back online.' >/dev/null 2>&1 || true
    exit 0
  fi

  if [ "$rc" -eq 20 ]; then
    write_receipt blocked 0 "$detail" >>"$LOG"
    post 'Home Center recovery blocked' "$detail" max
    exit "$rc"
  fi

  write_receipt degraded 0 "${detail:-relay did not produce a fresh heartbeat}" >>"$LOG"
  post 'HOME CENTER • STILL OFFLINE' 'Tap again after checking the recovery status; no false green was emitted.' max
  exit 1
}

status(){
  if relay_health; then
    write_receipt healthy 1 'Status check found fresh primary-phone Home Center relay heartbeat.'
    post 'HOME CENTER • ON' 'Fresh phone relay heartbeat proven.' default
  else
    write_receipt degraded 0 'Status check found no fresh primary-phone Home Center relay heartbeat.'
    post 'HOME CENTER • OFFLINE' 'Tap TURN HOME CENTER ON.' max
  fi
}

case "${1:-install}" in
  install)
    post 'HOME CENTER • RECOVERY' 'Persistent one-tap recovery control.' high
    write_receipt posted 0 'Persistent recovery button posted; Home Center state not inferred.'
    ;;
  recover) recover ;;
  status) status ;;
  receipt) cat "$RECEIPT" 2>/dev/null || printf '{"schema":"home-center-recovery-button-v1","phase":"never-run","ok":false}\n' ;;
  *) printf 'usage: %s [install|recover|status|receipt]\n' "$0" >&2; exit 64 ;;
esac
