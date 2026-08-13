#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
ROOT="${HC_REPO_ROOT:-$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)}"
STATE="${HC_STATE_DIR:-$HOME/.local/state/home-center}"
CAMPAIGN_STATE="$STATE/fortress-campaign/state.json"
[ -f "$CAMPAIGN_STATE" ] || CAMPAIGN_STATE="$STATE/adam-campaign/state.json"
PLAN="$STATE/adam-daemon/venice-plan-review-last.json"
STOP="$STATE/adam-daemon/venice-review-last.json"
ID=6410
MODE="${1:-main}"
PROBE=0
[ "$MODE" = "probe" ] && { PROBE=1; MODE=main; }
mkdir -p "$STATE/fortress-campaign"

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

command -v termux-notification >/dev/null 2>&1 || exit 3
q(){ printf "%q" "$1"; }
action(){ printf "bash -l -c '%s'" "$1"; }
SELF="cd $(q "$ROOT") && bash tools/home_center_status_menu.sh"
CAMPAIGN="fortress-campaign run >>\"$STATE/fortress-campaign/background.log\" 2>&1 &"
OVERLAY="fortress-campaign overlay >>\"$STATE/fortress-campaign/overlay-recover.log\" 2>&1; $SELF recovery"
SSH="fortress-campaign ssh >>\"$STATE/fortress-campaign/ssh-recover.log\" 2>&1; $SELF recovery"
HANDS="fortress-campaign phone-hands >>\"$STATE/fortress-campaign/phone-hands.log\" 2>&1; $SELF recovery-more"
REPAIR="fortress-campaign repair >>\"$STATE/fortress-campaign/repair.log\" 2>&1 &"

case "$MODE" in
  main)
    title='Fortress'
    content="$campaign_summary — $ssh_summary — $review_summary"
    b1='Resume'; a1="$(action "$CAMPAIGN")"
    b2='Status'; a2="$(action "$SELF status")"
    b3='Recovery'; a3="$(action "$SELF recovery")"
    ;;
  status)
    title='Fortress status'
    content="$campaign_summary — $ssh_summary — $review_summary"
    b1='Refresh'; a1="$(action "$SELF status")"
    b2='Receipts'; a2="$(action "$SELF receipts")"
    b3='Back'; a3="$(action "$SELF main")"
    ;;
  receipts)
    title='Fortress receipts'
    content="campaign=$([ -f "$STATE/fortress-campaign/latest.json" ] && echo yes || echo no) ssh=$([ -f "$STATE/phone-ssh/latest.json" ] && echo yes || echo no) — $review_summary"
    b1='Status'; a1="$(action "$SELF status")"
    b2='Recovery'; a2="$(action "$SELF recovery")"
    b3='Back'; a3="$(action "$SELF main")"
    ;;
  recovery)
    title='Fortress recovery'
    content="Persistent body recovery — $ssh_summary"
    b1='SSH repair'; a1="$(action "$SSH")"
    b2='Overlay on'; a2="$(action "$OVERLAY")"
    b3='More'; a3="$(action "$SELF recovery-more")"
    ;;
  recovery-more)
    title='Fortress recovery · more'
    content='Phone Hands and full deterministic repair'
    b1='Phone Hands'; a1="$(action "$HANDS")"
    b2='Repair all'; a2="$(action "$REPAIR")"
    b3='Back'; a3="$(action "$SELF recovery")"
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
