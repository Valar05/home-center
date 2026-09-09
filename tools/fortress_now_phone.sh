#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

ROOT="${HC_REPO_ROOT:-$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)}"
STATE="${HC_STATE_DIR:-$HOME/.local/state/home-center}/fortress-now"
LOG="$STATE/run.log"
RECEIPT="$STATE/latest.json"
SESSION="hc-fortress-now"
mkdir -p "$STATE"

stamp(){ date -Iseconds; }
step(){ printf '%s\t%s\n' "$(stamp)" "$*" | tee -a "$LOG"; }

capture(){
  local name="$1" out="$STATE/$name.png"
  local rish_bin="${RISH:-$(command -v rish 2>/dev/null || true)}"
  [ -n "$rish_bin" ] || rish_bin="$HOME/bin/rish"
  if [ -x "$rish_bin" ]; then
    "$rish_bin" -c "screencap -p /sdcard/$name.png" >/dev/null 2>&1 || true
    cp "/storage/emulated/0/$name.png" "$out" 2>/dev/null || true
  elif command -v screencap >/dev/null 2>&1; then
    screencap -p > "$out" 2>/dev/null || true
  fi
  [ -s "$out" ] && printf '%s\n' "$out" || true
}

run_now(){
  local before after overlay_rc=0 hands_rc=0 hole_rc=0 campaign_rc=0
  step "START observe actual phone before narration"
  before="$(capture fortress-now-before || true)"
  [ -n "$before" ] && step "SCREENSHOT_BEFORE $before" || step "SCREENSHOT_BEFORE unavailable"

  step "RECOVER overlay"
  bash "$ROOT/tools/recover_adam_overlay_phone.sh" >>"$LOG" 2>&1 || overlay_rc=$?

  step "RECOVER Phone Hands"
  bash "$ROOT/tools/phone_hands_watchdog.sh" diagnose >>"$LOG" 2>&1 || hands_rc=$?

  step "START/RESUME Hole coding campaign"
  bash "$ROOT/tools/fortress_script_campaign_hole.sh" >>"$LOG" 2>&1 || hole_rc=$?

  step "START/RESUME Adam phone campaign in tmux"
  if command -v tmux >/dev/null 2>&1; then
    if ! tmux has-session -t hc-adam-phone-campaign 2>/dev/null; then
      tmux new-session -d -s hc-adam-phone-campaign "cd '$ROOT' && bash tools/adam_phone_campaign.sh resume >>'$STATE/adam-phone-campaign.log' 2>&1"
    fi
  else
    campaign_rc=127
  fi

  after="$(capture fortress-now-after || true)"
  [ -n "$after" ] && step "SCREENSHOT_AFTER $after" || step "SCREENSHOT_AFTER unavailable"

  python3 - "$RECEIPT" "$before" "$after" "$overlay_rc" "$hands_rc" "$hole_rc" "$campaign_rc" "$LOG" <<'PY'
import json,sys,time,os
receipt,before,after,overlay,hands,hole,campaign,log=sys.argv[1:]
obj={
 'schema':'fortress-now-v1',
 'verifiedAtEpoch':int(time.time()),
 'beforeScreenshot':before or None,
 'afterScreenshot':after or None,
 'overlayRecoveryRc':int(overlay),
 'phoneHandsRecoveryRc':int(hands),
 'holeCampaignRc':int(hole),
 'adamPhoneCampaignLaunchRc':int(campaign),
 'logPath':log,
 'stateChanged':True,
 'note':'This receipt proves the local recovery/orchestration attempt, not that Home Center is online or the Hole is delivered.'
}
open(receipt,'w',encoding='utf-8').write(json.dumps(obj,indent=2,sort_keys=True)+'\n')
print(json.dumps(obj,indent=2,sort_keys=True))
PY

  bash "$ROOT/tools/adam_failure_daemon.sh" add office-space "talked instead of observing phone and advancing swarm; fortress-now now exists to make that regression executable" >/dev/null 2>&1 || true
  step "END receipt=$RECEIPT"
}

case "${1:-run}" in
  run)
    if command -v tmux >/dev/null 2>&1; then
      if tmux has-session -t "$SESSION" 2>/dev/null; then
        printf '[fortress-now] already running: %s\n' "$SESSION"
      else
        tmux new-session -d -s "$SESSION" "cd '$ROOT' && bash tools/fortress_now_phone.sh foreground"
        printf '[fortress-now] launched: %s\n' "$SESSION"
      fi
    else
      exec "$0" foreground
    fi
    ;;
  foreground) run_now ;;
  status) [ -f "$RECEIPT" ] && cat "$RECEIPT" || echo '{"schema":"fortress-now-v1","status":"never-run"}' ;;
  *) echo "usage: $0 [run|foreground|status]" >&2; exit 64 ;;
esac
