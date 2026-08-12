#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
ROOT="${HC_REPO_ROOT:-$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)}"
STATE="${HC_STATE_DIR:-$HOME/.local/state/home-center}"
CAMPAIGN_STATE="$STATE/adam-campaign/state.json"
PLAN="$STATE/adam-daemon/venice-plan-review-last.json"
STOP="$STATE/adam-daemon/venice-review-last.json"
ID=6410
MODE="${1:-main}"
PROBE=0
[ "$MODE" = "probe" ] && { PROBE=1; MODE=main; }
mkdir -p "$STATE/adam-campaign"

campaign_summary="Home Center ready"
if [ -f "$CAMPAIGN_STATE" ]; then
  campaign_summary="$(python3 - "$CAMPAIGN_STATE" <<'PY'
import json,sys
try:
 d=json.load(open(sys.argv[1],encoding='utf-8'))
 print(f"Adam: {d.get('stage','unknown')} / {d.get('status','unknown')}")
except Exception:
 print('Adam campaign state unreadable')
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

command -v termux-notification >/dev/null 2>&1 || exit 3
q(){ printf "%q" "$1"; }
action(){ printf "bash -l -c '%s'" "$1"; }
SELF="cd $(q "$ROOT") && bash tools/home_center_status_menu.sh"
CAMPAIGN="adam-campaign run >>\"$STATE/adam-campaign/background.log\" 2>&1 &"
OVERLAY="cd $(q "$ROOT") && bash tools/recover_adam_overlay_phone.sh >>\"$STATE/adam-campaign/overlay-recover.log\" 2>&1 && bash tools/home_center_status_menu.sh main"
HANDS="cd $(q "$ROOT") && bash tools/phone_hands_watchdog.sh diagnose >>\"$STATE/phone-hands-watchdog.log\" 2>&1 && bash tools/home_center_status_menu.sh main"

case "$MODE" in
  main)
    title='Home Center'
    content="$campaign_summary — $review_summary"
    b1='Resume Adam'; a1="$(action "$CAMPAIGN")"
    b2='Status'; a2="$(action "$SELF status")"
    b3='Recovery'; a3="$(action "$SELF recovery")"
    ;;
  status)
    title='Home Center status'
    content="$campaign_summary — $review_summary"
    b1='Refresh'; a1="$(action "$SELF status")"
    b2='Receipts'; a2="$(action "$SELF receipts")"
    b3='Back'; a3="$(action "$SELF main")"
    ;;
  receipts)
    title='Home Center receipts'
    content="$review_summary — campaign receipt: $([ -f "$STATE/adam-campaign/latest-receipt.json" ] && echo yes || echo no)"
    b1='Status'; a1="$(action "$SELF status")"
    b2='Recovery'; a2="$(action "$SELF recovery")"
    b3='Back'; a3="$(action "$SELF main")"
    ;;
  recovery)
    title='Home Center recovery'
    content='Persistent recovery controls'
    b1='Overlay on'; a1="$(action "$OVERLAY")"
    b2='Phone Hands'; a2="$(action "$HANDS")"
    b3='Back'; a3="$(action "$SELF main")"
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
