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

install_service(){
  local bindir="${PREFIX:-$HOME/.local}/bin" target
  target="$bindir/adam-campaign"
  mkdir -p "$bindir"
  cat >"$target" <<EOF
#!/data/data/com.termux/files/usr/bin/bash
exec bash "$ROOT/tools/adam_phone_campaign.sh" "\$@"
EOF
  chmod 755 "$target"
  bash "$ROOT/tools/home_center_status_menu.sh" >/dev/null 2>&1 || true
}

status(){ [ -f "$STATE" ] && cat "$STATE" || printf '{"schema":"adam-phone-campaign-v1","stage":"never-run","status":"idle"}\n'; }
receipts(){
  status
  [ -f "$LATEST" ] && { echo "===== $LATEST ====="; cat "$LATEST"; }
  for f in "$HOME/.local/state/home-center/adam-cli-install-receipt.json" "$HOME/.local/state/home-center/adam-phone-worker-acceptance.json" "$HOME/.local/state/home-center/adam-daemon/venice-plan-review-last.json" "$HOME/.local/state/home-center/adam-daemon/venice-review-last.json"; do
    [ -f "$f" ] && { echo "===== $f ====="; cat "$f"; }
  done
}
backoff(){ local n="$1"; [ "$n" -gt 6 ] && n=6; local seq=(0 1 2 4 8 15 30); sleep "${seq[$n]}"; }

preserve_workspace(){
  ORIGINAL_REF="$(git -C "$ROOT" symbolic-ref --short -q HEAD || git -C "$ROOT" rev-parse HEAD)" || return 1
  printf '%s\n' "$ORIGINAL_REF" > "$STATE_ROOT/original-ref"
  PRESERVED_STASH=""
  if [ -n "$(git -C "$ROOT" status --porcelain)" ]; then
    local stamp
    stamp="$(date +%Y%m%d-%H%M%S)"
    git -C "$ROOT" stash push -u -m "adam-campaign-preserve-$stamp" >/dev/null || return 1
    PRESERVED_STASH="$(git -C "$ROOT" stash list -1 --format='%gd')"
    printf '%s\n' "$PRESERVED_STASH" > "$STATE_ROOT/preserved-stash"
    json_state preserve-local preserved "phone edits preserved as $PRESERVED_STASH; original ref=$ORIGINAL_REF"
  else
    json_state preserve-local preserved "clean workspace preserved; original ref=$ORIGINAL_REF"
  fi
}
restore_workspace(){
  local original="${ORIGINAL_REF:-}" stash="${PRESERVED_STASH:-}"
  [ -n "$original" ] || [ ! -f "$STATE_ROOT/original-ref" ] || original="$(cat "$STATE_ROOT/original-ref")"
  [ -n "$stash" ] || [ ! -f "$STATE_ROOT/preserved-stash" ] || stash="$(cat "$STATE_ROOT/preserved-stash")"
  if [ -n "$original" ]; then
    json_state restore-ref running "restoring original ref $original"
    if ! git -C "$ROOT" checkout "$original" >>"$LOG" 2>&1; then json_state reconcile-required blocked "could not restore original ref $original"; return 1; fi
  fi
  if [ -n "$stash" ]; then
    json_state restore-local running "restoring $stash"
    if ! git -C "$ROOT" stash pop --index "$stash" >>"$LOG" 2>&1; then json_state reconcile-required blocked "preserved phone edits conflict while restoring $stash; stash/history retained"; return 1; fi
    rm -f "$STATE_ROOT/preserved-stash"; PRESERVED_STASH=""
  fi
  rm -f "$STATE_ROOT/original-ref"; ORIGINAL_REF=""
}

repair_with_adam(){
  local failure_log="$1"
  json_state repair running "planned Adam self-heal repairing failed campaign stage"
  python3 "$ROOT/tools/adam_planned_venice.py" "Repair the Adam phone campaign from the current repository/runtime evidence. This is a continuing-value campaign, not a one-off. Read the failing log at $failure_log, preserve campaign doctrine, fix the smallest root cause, run relevant tests, and obtain Venice plan and completion review. Do not ask Drew to paste another diagnostic chain." >>"$LOG" 2>&1
}

persist_repairs(){
  json_state persist-repair running "persisting campaign state/repairs to canonical main"
  if [ -n "$(git -C "$ROOT" status --porcelain)" ]; then
    git -C "$ROOT" add -A >>"$LOG" 2>&1 || return 1
    if ! git -C "$ROOT" diff --cached --quiet; then git -C "$ROOT" commit -m "Self-heal Adam phone campaign" >>"$LOG" 2>&1 || return 1; fi
  fi
  git -C "$ROOT" fetch origin main >>"$LOG" 2>&1 || return 1
  if ! git -C "$ROOT" rebase origin/main >>"$LOG" 2>&1; then git -C "$ROOT" rebase --abort >>"$LOG" 2>&1 || true; return 1; fi
  git -C "$ROOT" push origin HEAD:main >>"$LOG" 2>&1 || return 1
}

write_acceptance(){
  local menu_ok="$1"
  python3 - "$LATEST" "$menu_ok" <<'PY'
import json,os,sys,time
home=os.path.expanduser('~/.local/state/home-center'); menu_ok=sys.argv[2]=='1'
paths={'install':home+'/adam-cli-install-receipt.json','plan':home+'/adam-daemon/venice-plan-review-last.json','stop':home+'/adam-daemon/venice-review-last.json'}
try:data={k:json.load(open(v,encoding='utf-8')) for k,v in paths.items()}
except Exception as e: print(json.dumps({'ok':False,'error':str(e),'paths':paths}));raise SystemExit(2)
ok=(data['install'].get('ok') is True and data['plan'].get('directive')=='PLAN_ALLOWED' and data['plan'].get('planPermissionGranted') is True and data['stop'].get('directive')=='STOP_ALLOWED' and data['stop'].get('externalReviewGateSatisfied') is True and menu_ok)
obj={'schema':'adam-phone-campaign-receipt-v2','ok':ok,'paths':paths,'verifiedAtEpoch':int(time.time()),'continuingValue':{'stableCommand':'adam-campaign','commands':['run','resume','status','receipts','menu','overlay','phone-hands'],'state':home+'/adam-campaign/state.json','history':home+'/adam-campaign/history.jsonl','notificationMenu':menu_ok,'notificationMenuProbe':home+'/adam-campaign/menu-probe.log','overlayRecovery':True,'phoneHandsRecovery':True,'selfHeal':True,'daemonBackoff':True,'workspacePreservation':True}}
open(sys.argv[1],'w',encoding='utf-8').write(json.dumps(obj,indent=2,sort_keys=True)+'\n');print(json.dumps(obj,indent=2,sort_keys=True));raise SystemExit(0 if ok else 2)
PY
}

run_campaign(){
  install_service
  mkdir "$LOCK" 2>/dev/null || { json_state already-running healthy "campaign already active; stable command/menu remain callable"; return 0; }
  trap 'rmdir "$LOCK" 2>/dev/null || true' EXIT INT TERM
  cd "$ROOT" || return 2
  PRESERVED_STASH=""; ORIGINAL_REF=""
  json_state bootstrap running "starting/resuming Adam phone campaign; continuing service already installed"
  preserve_workspace || { json_state preserve-failed blocked "could not preserve original branch/worktree"; return 3; }
  json_state sync running "syncing canonical main"
  git fetch origin main >>"$LOG" 2>&1 || { restore_workspace || true; json_state sync-failed degraded "git fetch failed; adam-campaign resume will retry"; return 4; }
  git checkout main >>"$LOG" 2>&1 || { restore_workspace || true; json_state sync-failed blocked "cannot checkout main"; return 5; }
  git pull --ff-only origin main >>"$LOG" 2>&1 || { restore_workspace || true; json_state sync-failed degraded "fast-forward pull failed; preserved state retained for resume"; return 6; }

  local round=0
  while true; do
    round=$((round+1));json_state contracts running "local deterministic contract round $round"
    if bash tools/run_fortress_local_contracts.sh >"$STATE_ROOT/contracts.log" 2>&1; then break; fi
    json_state contracts-failed repairing "contract round $round failed; invoking governed repair";repair_with_adam "$STATE_ROOT/contracts.log" || true;backoff "$round"
  done

  round=0
  while true; do
    round=$((round+1));json_state install running "Adam install/runtime acceptance round $round"
    if bash tools/install_adam_cli.sh >"$STATE_ROOT/install.log" 2>&1; then break; fi
    json_state install-failed repairing "install/runtime round $round failed; invoking governed repair";repair_with_adam "$STATE_ROOT/install.log" || true;backoff "$round"
  done

  round=0
  while true; do
    round=$((round+1));json_state verify running "continuing-value acceptance round $round"
    if bash "$ROOT/tools/home_center_status_menu.sh" probe >"$STATE_ROOT/menu-probe.log" 2>&1; then MENU_OK=1; else MENU_OK=0; fi
    if write_acceptance "$MENU_OK" >"$STATE_ROOT/verify.log" 2>&1; then break; fi
    json_state verify-failed repairing "plan/stop receipts or notification control surface not proven; invoking governed repair"
    repair_with_adam "$STATE_ROOT/verify.log" || true
    backoff "$round"
    bash tools/run_fortress_local_contracts.sh >"$STATE_ROOT/contracts.log" 2>&1 || true
    bash tools/install_adam_cli.sh >"$STATE_ROOT/install.log" 2>&1 || true
  done

  persist_repairs || { json_state persist-failed degraded "accepted locally but canonical persistence failed; adam-campaign resume will retry"; restore_workspace || true; return 21; }
  restore_workspace || return 20
  install_service
  json_state healthy healthy "Adam campaign accepted; persistent self-heal/status/menu remain installed"
  cat "$LATEST"
}

case "${1:-run}" in
  run|resume) run_campaign ;;
  status) status ;;
  receipts) receipts ;;
  menu) install_service; bash "$ROOT/tools/home_center_status_menu.sh" ;;
  overlay) bash "$ROOT/tools/recover_adam_overlay_phone.sh" ;;
  phone-hands) bash "$ROOT/tools/phone_hands_watchdog.sh" diagnose ;;
  install-service) install_service; json_state service-installed healthy "stable command and notification menu installed" ;;
  *) echo 'usage: adam-campaign [run|resume|status|receipts|menu|overlay|phone-hands|install-service]' >&2; exit 64 ;;
esac
