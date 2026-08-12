#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
ROOT="${HC_REPO_ROOT:-$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)}"
STATE="${HC_STATE_DIR:-$HOME/.local/state/home-center}"
CAMPAIGN_STATE="$STATE/adam-campaign/state.json"
ID=6410
mkdir -p "$STATE/adam-campaign"

summary="Home Center ready"
if [ -f "$CAMPAIGN_STATE" ]; then
  summary="$(python3 - "$CAMPAIGN_STATE" <<'PY'
import json,sys
try:
 d=json.load(open(sys.argv[1],encoding='utf-8'))
 print(f"Adam campaign: {d.get('stage','unknown')} / {d.get('status','unknown')}")
except Exception:
 print('Adam campaign state unreadable')
PY
)"
fi

command -v termux-notification >/dev/null 2>&1 || exit 0
q(){ printf "%q" "$1"; }
CAMPAIGN="bash -l -c 'adam-campaign run >>\"$STATE/adam-campaign/background.log\" 2>&1 &'"
OVERLAY="bash -l -c 'cd $(q "$ROOT") && bash tools/recover_adam_overlay_phone.sh >>\"$STATE/adam-campaign/overlay-recover.log\" 2>&1'"
HANDS="bash -l -c 'cd $(q "$ROOT") && bash tools/phone_hands_watchdog.sh diagnose >>\"$STATE/phone-hands-watchdog.log\" 2>&1'"
termux-notification \
  --id "$ID" \
  --title 'Home Center' \
  --content "$summary" \
  --priority default \
  --ongoing true \
  --button1 'Resume Adam' \
  --button1-action "$CAMPAIGN" \
  --button2 'Overlay on' \
  --button2-action "$OVERLAY" \
  --button3 'Repair Phone Hands' \
  --button3-action "$HANDS" >/dev/null 2>&1 || true
