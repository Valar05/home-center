#!/data/data/com.termux/files/usr/bin/bash
set -u
ROOT="${HC_REPO_ROOT:-$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)}"
STATE_ROOT="${HC_STATE_DIR:-$HOME/.local/state/home-center}/adam-campaign"
STATE="$STATE_ROOT/state.json"
HISTORY="$STATE_ROOT/history.jsonl"
LOG="$STATE_ROOT/campaign.log"
LATEST="$STATE_ROOT/latest-receipt.json"
LOCK="$STATE_ROOT/run.lock"
mkdir -p "$STATE_ROOT"

json_state(){
  local stage="$1" status="$2" detail="$3"
  python3 - "$STATE" "$HISTORY" "$stage" "$status" "$detail" <<'PY'
import json,sys,time,os
state,history,stage,status,detail=sys.argv[1:]
obj={'schema':'adam-phone-campaign-v1','stage':stage,'status':status,'detail':detail,'updatedAtEpoch':int(time.time())}
tmp=state+'.tmp';open(tmp,'w',encoding='utf-8').write(json.dumps(obj,indent=2,sort_keys=True)+'\n');os.replace(tmp,state)
with open(history,'a',encoding='utf-8') as f:f.write(json.dumps(obj,sort_keys=True)+'\n')
print(json.dumps(obj,sort_keys=True))
PY
  bash "$ROOT/tools/home_center_status_menu.sh" >/dev/null 2>&1 || true
}

status(){
  [ -f "$STATE" ] && cat "$STATE" || printf '{"schema":"adam-phone-campaign-v1","stage":"never-run","status":"idle"}\n'
}
receipts(){
  status
  for f in \
    "$HOME/.local/state/home-center/adam-cli-install-receipt.json" \
    "$HOME/.local/state/home-center/adam-phone-worker-acceptance.json" \
    "$HOME/.local/state/home-center/adam-daemon/venice-plan-review-last.json" \
    "$HOME/.local/state/home-center/adam-daemon/venice-review-last.json"; do
    [ -f "$f" ] && { echo "===== $f ====="; cat "$f"; }
  done
}
backoff(){ local n="$1"; [ "$n" -gt 6 ] && n=6; local seq=(0 1 2 4 8 15 30); sleep "${seq[$n]}"; }

preserve_local(){
  PRESERVED_STASH=""
  if [ -n "$(git -C "$ROOT" status --porcelain)" ]; then
    local stamp
    stamp="$(date +%Y%m%d-%H%M%S)"
    git -C "$ROOT" stash push -u -m "adam-campaign-preserve-$stamp" >/dev/null || return 1
    PRESERVED_STASH="$(git -C "$ROOT" stash list -1 --format='%gd')"
    printf '%s\n' "$PRESERVED_STASH" > "$STATE_ROOT/preserved-stash"
    json_state preserve-local preserved "phone edits preserved as $PRESERVED_STASH"
  fi
}
restore_local(){
  local stash="${PRESERVED_STASH:-}"
  [ -n "$stash" ] || [ ! -f "$STATE_ROOT/preserved-stash" ] || stash="$(cat "$STATE_ROOT/preserved-stash")"
  [ -n "$stash" ] || return 0
  json_state restore-local running "restoring $stash"
  if git -C "$ROOT" stash pop --index "$stash"; then rm -f "$STATE_ROOT/preserved-stash"; PRESERVED_STASH=""; return 0; fi
  json_state reconcile-required blocked "preserved phone edits conflict while restoring $stash; stash/history retained"
  return 1
}

repair_with_adam(){
  local failure_log="$1"
  json_state repair running "planned Adam self-heal repairing failed campaign stage"
  python3 "$ROOT/tools/adam_planned_venice.py" \
    "Repair the Adam phone campaign from the current repository/runtime evidence. This is a continuing-value campaign, not a one-off. Read the failing log at $failure_log, preserve campaign doctrine, fix the smallest root cause, run relevant tests, and obtain Venice plan and completion review. Do not ask Drew to paste another diagnostic chain." \
    >>"$LOG" 2>&1
}

run_campaign(){
  mkdir "$LOCK" 2>/dev/null || { json_state already-running healthy "campaign already active"; return 0; }
  trap 'rmdir "$LOCK" 2>/dev/null || true' EXIT INT TERM
  cd "$ROOT" || return 2
  PRESERVED_STASH=""
  json_state bootstrap running "starting/resuming Adam phone campaign"
  preserve_local || { json_state preserve-failed blocked "could not preserve local phone work"; return 3; }

  json_state sync running "syncing canonical main"
  git fetch origin main >>"$LOG" 2>&1 || { restore_local || true; json_state sync-failed degraded "git fetch failed; future run will retry"; return 4; }
  git checkout main >>"$LOG" 2>&1 || { restore_local || true; json_state sync-failed blocked "cannot checkout main"; return 5; }
  git pull --ff-only origin main >>"$LOG" 2>&1 || { restore_local || true; json_state sync-failed degraded "fast-forward pull failed; preserved state retained"; return 6; }

  local round=0
  while true; do
    round=$((round+1))
    json_state contracts running "local deterministic contract round $round"
    if bash tools/run_fortress_local_contracts.sh >"$STATE_ROOT/contracts.log" 2>&1; then break; fi
    json_state contracts-failed repairing "contract round $round failed; invoking governed repair"
    repair_with_adam "$STATE_ROOT/contracts.log" || true
    backoff "$round"
  done

  round=0
  while true; do
    round=$((round+1))
    json_state install running "Adam install/runtime acceptance round $round"
    if bash tools/install_adam_cli.sh >"$STATE_ROOT/install.log" 2>&1; then break; fi
    json_state install-failed repairing "install/runtime round $round failed; invoking governed repair"
    repair_with_adam "$STATE_ROOT/install.log" || true
    backoff "$round"
  done

  json_state verify running "verifying plan and completion receipts"
  python3 - "$LATEST" <<'PY'
import json,os,sys,time,hashlib
home=os.path.expanduser('~/.local/state/home-center')
paths={
 'install':home+'/adam-cli-install-receipt.json',
 'plan':home+'/adam-daemon/venice-plan-review-last.json',
 'stop':home+'/adam-daemon/venice-review-last.json'}
data={k:json.load(open(v,encoding='utf-8')) for k,v in paths.items()}
ok=(data['install'].get('ok') is True and data['plan'].get('directive')=='PLAN_ALLOWED' and data['plan'].get('planPermissionGranted') is True and data['stop'].get('directive')=='STOP_ALLOWED' and data['stop'].get('externalReviewGateSatisfied') is True)
obj={'schema':'adam-phone-campaign-receipt-v1','ok':ok,'paths':paths,'verifiedAtEpoch':int(time.time()),'continuingValue':{'stableCommand':'adam-campaign','state':home+'/adam-campaign/state.json','history':home+'/adam-campaign/history.jsonl','notificationMenu':True,'overlayRecovery':True,'phoneHandsRecovery':True}}
open(sys.argv[1],'w',encoding='utf-8').write(json.dumps(obj,indent=2,sort_keys=True)+'\n')
print(json.dumps(obj,indent=2,sort_keys=True))
raise SystemExit(0 if ok else 2)
PY
  local verify_rc=$?
  if [ "$verify_rc" -ne 0 ]; then json_state verify-failed repairing "receipts did not prove PLAN_ALLOWED + STOP_ALLOWED"; restore_local || true; return "$verify_rc"; fi

  json_state service running "installing continuing campaign command and notification menu"
  local bindir="${PREFIX:-$HOME/.local}/bin"
  mkdir -p "$bindir"
  cat >"$bindir/adam-campaign" <<EOF
#!/data/data/com.termux/files/usr/bin/bash
exec bash "$ROOT/tools/adam_phone_campaign.sh" "\$@"
EOF
  chmod 755 "$bindir/adam-campaign"
  bash "$ROOT/tools/home_center_status_menu.sh" >/dev/null 2>&1 || true

  restore_local || return 20
  json_state healthy healthy "Adam campaign accepted; continuing service/menu installed"
  cat "$LATEST"
}

case "${1:-run}" in
  run|resume) run_campaign ;;
  status) status ;;
  receipts) receipts ;;
  menu) bash "$ROOT/tools/home_center_status_menu.sh" ;;
  overlay) bash "$ROOT/tools/recover_adam_overlay_phone.sh" ;;
  phone-hands) bash "$ROOT/tools/phone_hands_watchdog.sh" diagnose ;;
  *) echo 'usage: adam-campaign [run|resume|status|receipts|menu|overlay|phone-hands]' >&2; exit 64 ;;
esac
