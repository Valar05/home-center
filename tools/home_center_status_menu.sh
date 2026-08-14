#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
ROOT="${HC_REPO_ROOT:-$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)}"
STATE="${HC_STATE_DIR:-$HOME/.local/state/home-center}"
CAMPAIGN_STATE="$STATE/fortress-campaign/state.json"
[ -f "$CAMPAIGN_STATE" ] || CAMPAIGN_STATE="$STATE/adam-campaign/state.json"
PLAN="$STATE/adam-daemon/venice-plan-review-last.json"
STOP="$STATE/adam-daemon/venice-review-last.json"
FORGE_STATE="$STATE/forge-campaign/latest.json"
ADAM_STATE="$STATE/adam-do/current.json"
INTAKE_STATE="$STATE/campaign-intake/current.json"
ID=6410
MODE="${1:-main}"
PROBE=0
[ "$MODE" = "probe" ] && { PROBE=1; MODE=main; }
mkdir -p "$STATE/fortress-campaign" "$STATE/adam-do" "$STATE/campaign-intake"

campaign_summary="Fortress ready"
if [ -f "$CAMPAIGN_STATE" ]; then
  campaign_summary="$(python3 - "$CAMPAIGN_STATE" <<'PY'
import json,sys
try:
 d=json.load(open(sys.argv[1],encoding='utf-8'))
 print(f"Fortress: {d.get('phase',d.get('stage','unknown'))} / {d.get('status','unknown')}")
except Exception:
 print('Fortress campaign state unreadable')
PY
)"
fi
review_summary="$(python3 - "$PLAN" "$STOP" <<'PY'
import json,sys
vals=[]
for label,path in [('plan',sys.argv[1]),('stop',sys.argv[2])]:
 try:
  d=json.load(open(path,encoding='utf-8')); vals.append(f"{label}={d.get('directive','?')}")
 except Exception: vals.append(f"{label}=?")
print(' '.join(vals))
PY
)"
ssh_summary="$(python3 - "$STATE/phone-ssh/latest.json" <<'PY'
import json,sys
try:
 d=json.load(open(sys.argv[1],encoding='utf-8')); print('ssh='+str(d.get('state','?')))
except Exception: print('ssh=?')
PY
)"
forge_summary="$(python3 - "$FORGE_STATE" <<'PY'
import json,sys
try:
 d=json.load(open(sys.argv[1],encoding='utf-8')); print('forge='+str(d.get('stage','?'))+'/'+str(d.get('status','?')))
except Exception: print('forge=?')
PY
)"
adam_summary="$(python3 - "$ADAM_STATE" <<'PY'
import json,sys,time
try:
 d=json.load(open(sys.argv[1],encoding='utf-8'))
 hb=int(d.get('heartbeatAtEpoch') or d.get('updatedAtEpoch') or 0)
 age=max(0,int(time.time())-hb) if hb else -1
 print(f"Adam: {d.get('status','?')} / {d.get('phase','?')} / hb {age}s")
except Exception: print('Adam: idle')
PY
)"
intake_summary="$(python3 - "$INTAKE_STATE" <<'PY'
import json,sys
try:
 d=json.load(open(sys.argv[1],encoding='utf-8'))
 idx=int(d.get('index',0)); print(f"Intake: {d.get('status','?')} / q{min(idx+1,6)}/6")
except Exception: print('Intake: idle')
PY
)"

command -v termux-notification >/dev/null 2>&1 || exit 3
q(){ printf "%q" "$1"; }
action(){ printf "bash -l -c '%s'" "$1"; }
SELF="cd $(q "$ROOT") && bash tools/home_center_status_menu.sh"
CAMPAIGN="fortress-campaign run >>\"$STATE/fortress-campaign/background.log\" 2>&1 &"
OVERLAY="fortress-campaign overlay >>\"$STATE/fortress-campaign/overlay-recover.log\" 2>&1; $SELF recovery"
SSH="fortress-campaign ssh >>\"$STATE/fortress-campaign/ssh-recover.log\" 2>&1; $SELF recovery"
HANDS="fortress-campaign phone-hands >>\"$STATE/fortress-campaign/phone-hands.log\" 2>&1; $SELF recovery-more"
REPAIR="fortress-campaign repair >>\"$STATE/fortress-campaign/repair.log\" 2>&1 &"
FORGE="home-center-forge resume >>\"$STATE/forge-campaign/menu.log\" 2>&1 &"
FORGE_STATUS="home-center-forge status >\"$STATE/forge-campaign/menu-status.log\" 2>&1; $SELF forge"
ADAM_STATUS="adam --status >\"$STATE/adam-do/menu-status.log\" 2>&1; $SELF adam"
ADAM_STOP="adam --stop >\"$STATE/adam-do/menu-stop.log\" 2>&1; $SELF adam"
ADAM_RESUME="adam --resume >\"$STATE/adam-do/menu-resume.log\" 2>&1; $SELF adam"
ADAM_RECEIPTS="adam --receipts >\"$STATE/adam-do/menu-receipts.log\" 2>&1; $SELF adam-more"
INTAKE="python3 tools/campaign_intake_shera.py start >\"$STATE/campaign-intake/menu.log\" 2>&1"
INTAKE_STATUS="python3 tools/campaign_intake_shera.py status >\"$STATE/campaign-intake/menu-status.log\" 2>&1; $SELF intake"
INTAKE_CANCEL="python3 tools/campaign_intake_shera.py cancel >\"$STATE/campaign-intake/menu-cancel.log\" 2>&1; $SELF main"

case "$MODE" in
  main)
    title='Fortress'
    content="$campaign_summary — $adam_summary — $intake_summary"
    b1='New campaign'; a1="$(action "$INTAKE")"
    b2='Adam'; a2="$(action "$SELF adam")"
    b3='Recovery'; a3="$(action "$SELF recovery")"
    ;;
  status)
    title='Fortress status'
    content="$campaign_summary — $adam_summary — $intake_summary — $ssh_summary — $forge_summary — $review_summary"
    b1='Refresh'; a1="$(action "$SELF status")"
    b2='Intake'; a2="$(action "$SELF intake")"
    b3='Back'; a3="$(action "$SELF main")"
    ;;
  intake)
    title='She-Ra campaign intake'
    content="$intake_summary — she interrogates until the real commission is exposed"
    b1='Continue'; a1="$(action "$INTAKE")"
    b2='Status'; a2="$(action "$INTAKE_STATUS")"
    b3='Cancel'; a3="$(action "$INTAKE_CANCEL")"
    ;;
  adam)
    title='Adam operator'
    content="$adam_summary"
    b1='Status'; a1="$(action "$ADAM_STATUS")"
    b2='STOP'; a2="$(action "$ADAM_STOP")"
    b3='More'; a3="$(action "$SELF adam-more")"
    ;;
  adam-more)
    title='Adam operator · more'
    content="$adam_summary"
    b1='Resume'; a1="$(action "$ADAM_RESUME")"
    b2='Receipts'; a2="$(action "$ADAM_RECEIPTS")"
    b3='Back'; a3="$(action "$SELF adam")"
    ;;
  forge)
    title='Home Center forge'
    content="$forge_summary — always-online free-tier body"
    b1='Resume forge'; a1="$(action "$FORGE")"
    b2='Refresh'; a2="$(action "$FORGE_STATUS")"
    b3='Back'; a3="$(action "$SELF status")"
    ;;
  receipts)
    title='Fortress receipts'
    content="campaign=$([ -f "$STATE/fortress-campaign/latest.json" ] && echo yes || echo no) adam=$([ -f "$STATE/adam-do/last.json" ] && echo yes || echo no) intake=$([ -f "$INTAKE_STATE" ] && echo yes || echo no)"
    b1='Adam'; a1="$(action "$SELF adam")"
    b2='Intake'; a2="$(action "$SELF intake")"
    b3='Back'; a3="$(action "$SELF main")"
    ;;
  recovery)
    title='Fortress recovery'
    content="Persistent body recovery — $ssh_summary — $forge_summary"
    b1='SSH repair'; a1="$(action "$SSH")"
    b2='Forge repair'; a2="$(action "$FORGE")"
    b3='More'; a3="$(action "$SELF recovery-more")"
    ;;
  recovery-more)
    title='Fortress recovery · more'
    content='Phone Hands, overlay, and full deterministic repair'
    b1='Phone Hands'; a1="$(action "$HANDS")"
    b2='Overlay on'; a2="$(action "$OVERLAY")"
    b3='Repair all'; a3="$(action "$REPAIR")"
    ;;
  *) exec bash "$0" main ;;
esac

set +e
termux-notification \
  --id "$ID" \
  --title "$title" \
  --content "$content" \
  --priority default \
  --ongoing true \
  --button1 "$b1" --button1-action "$a1" \
  --button2 "$b2" --button2-action "$a2" \
  --button3 "$b3" --button3-action "$a3" >/dev/null 2>&1
rc=$?
set -e
[ "$PROBE" -eq 1 ] && exit "$rc"
exit 0
