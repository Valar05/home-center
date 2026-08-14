#!/data/data/com.termux/files/usr/bin/bash
set -u

ROLE="${1:-}"
REPO="${FORTRESS_HOME_CENTER:-/storage/emulated/0/Documents/GodotProjects/home-center}"
STATE="$HOME/.local/state/home-center/fortress-campaign"
mkdir -p "$STATE"

case "$ROLE" in
  kernel) CMD=(python "$REPO/tools/fortress_phone_kernel.py" daemon) ;;
  throne) CMD=(python "$REPO/tools/fortress_throne_adapter.py" serve) ;;
  campaign) CMD=(python "$REPO/tools/fortress_campaign.py" daemon) ;;
  *) echo "usage: fortress_supervise.sh kernel|throne|campaign" >&2; exit 2 ;;
esac

LOG="$STATE/supervisor-$ROLE.log"
DELAY=2
MAX_DELAY=120

while true; do
  started="$(date +%s)"
  printf '%s role=%s event=start command=%q\n' "$(date -Iseconds)" "$ROLE" "${CMD[*]}" >>"$LOG"
  "${CMD[@]}" >>"$LOG" 2>&1
  rc=$?
  ended="$(date +%s)"
  lived=$((ended-started))
  printf '%s role=%s event=exit code=%s lived=%ss backoff=%ss\n' "$(date -Iseconds)" "$ROLE" "$rc" "$lived" "$DELAY" >>"$LOG"
  # A process that remained healthy for a while earns a reset; crash loops back off.
  if [ "$lived" -ge 120 ]; then DELAY=2; else DELAY=$((DELAY*2)); [ "$DELAY" -gt "$MAX_DELAY" ] && DELAY="$MAX_DELAY"; fi
  sleep "$DELAY"
done
