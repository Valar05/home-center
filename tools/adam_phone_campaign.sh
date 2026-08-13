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
exec env HC_REPO_ROOT="$ROOT" bash "$ROOT/tools/adam_phone_campaign.sh" "\$@"
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

sync_runtime(){
  json_state sync running "syncing dedicated detached campaign runtime to canonical main"
  git -C "$ROOT" fetch origin main >>"$LOG" 2>&1 || return 1
  if [ -z "$(git -C "$ROOT" status --porcelain)" ]; then
    git -C "$ROOT" checkout --detach origin/main >>"$LOG" 2>&1 || return 1
  else
    json_state sync-preserved preserved "campaign runtime has governed repair changes; preserving them for resume/persistence"
  fi
}

venice_plan_gate(){
  json_state venice-plan running "Judgment Jars selected and Venice plan review required before substantive campaign mutation"
  python3 - "$ROOT" "$STATE_ROOT/venice-startup-gate.json" <<'PY'
import json,sys
from pathlib import Path
root=Path(sys.argv[1]).resolve(); out=Path(sys.argv[2])
sys.path.insert(0,str(root/'tools'))
import adam_planned_venice as av
mission=(
 "Continue the durable Adam phone-control campaign. Preserve the user's active worktree and all unrelated work. "
 "Use the existing operator-campaign skill, active Judgment Jars, Home Center operator overlay, Phone Hands relay, watchdog, receipts, and persistent control surface. "
 "The campaign must install itself into its own detached runtime, recover rather than drip-feed diagnostics, prove callable phone control with a harmless canary when available, and leave durable self-heal/status/recovery value after installation. "
 "Do not make Tailscale a prerequisite unless runtime evidence proves the commissioned route requires it. Do not stop without Venice STOP_ALLOWED."
)
gate=av.preflight(mission,root,stop_after_steps=8)
review=gate.get('review') or {}
obj={'schema':'adam-campaign-venice-startup-v1','directive':review.get('directive'),'verdict':review.get('verdict'),'planPermissionGranted':review.get('planPermissionGranted') is True,'receipt':review.get('receipt'),'selectedJars':(gate.get('packet') or {}).get('selectedJars') or [],'plan':(gate.get('packet') or {}).get('plan') or []}
out.write_text(json.dumps(obj,indent=2,sort_keys=True)+'\n',encoding='utf-8')
print(json.dumps(obj,sort_keys=True))
raise SystemExit(0 if obj['planPermissionGranted'] else 7)
PY
}

repair_with_adam(){
  local failure_log="$1"
  json_state repair running "planned Adam self-heal repairing failed campaign stage"
  python3 "$ROOT/tools/adam_planned_venice.py" "Repair the Adam phone campaign from current repository/runtime evidence. This is a continuing-value campaign, not a one-off. Read the failing log at $failure_log, preserve campaign doctrine, fix the smallest root cause, run relevant tests, and obtain Venice plan and completion review. Do not ask Drew to paste another diagnostic chain." >>"$LOG" 2>&1
}

persist_repairs(){
  json_state persist-repair running "persisting governed campaign repairs to canonical main"
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
  python3 - "$LATEST" "$menu_ok" "$ROOT" <<'PY'
import json,os,sys,time
home=os.path.expanduser('~/.local/state/home-center'); menu_ok=sys.argv[2]=='1'; root=sys.argv[3]
paths={'install':home+'/adam-cli-install-receipt.json','plan':home+'/adam-daemon/venice-plan-review-last.json','stop':home+'/adam-daemon/venice-review-last.json','startupGate':home+'/adam-campaign/venice-startup-gate.json'}
try:data={k:json.load(open(v,encoding='utf-8')) for k,v in paths.items()}
except Exception as e: print(json.dumps({'ok':False,'error':str(e),'paths':paths}));raise SystemExit(2)
ok=(data['install'].get('ok') is True and data['plan'].get('directive')=='PLAN_ALLOWED' and data['plan'].get('planPermissionGranted') is True and data['startupGate'].get('directive')=='PLAN_ALLOWED' and data['startupGate'].get('planPermissionGranted') is True and data['stop'].get('directive')=='STOP_ALLOWED' and data['stop'].get('externalReviewGateSatisfied') is True and menu_ok)
obj={'schema':'adam-phone-campaign-receipt-v4','ok':ok,'paths':paths,'verifiedAtEpoch':int(time.time()),'continuingValue':{'stableCommand':'adam-campaign','commands':['run','resume','status','receipts','menu','overlay','phone-hands'],'runtimeWorktree':root,'state':home+'/adam-campaign/state.json','history':home+'/adam-campaign/history.jsonl','notificationMenu':menu_ok,'notificationMenuProbe':home+'/adam-campaign/menu-probe.log','overlayRecovery':True,'phoneHandsRecovery':True,'selfHeal':True,'daemonBackoff':True,'activeWorktreeUntouched':True,'veniceStartupGate':True,'judgmentJarsRequired':True}}
open(sys.argv[1],'w',encoding='utf-8').write(json.dumps(obj,indent=2,sort_keys=True)+'\n');print(json.dumps(obj,indent=2,sort_keys=True));raise SystemExit(0 if ok else 2)
PY
}

run_campaign(){
  install_service
  mkdir "$LOCK" 2>/dev/null || { json_state already-running healthy "campaign already active; stable command/menu remain callable"; return 0; }
  trap 'rmdir "$LOCK" 2>/dev/null || true' EXIT INT TERM
  cd "$ROOT" || return 2
  json_state bootstrap running "starting/resuming dedicated Adam campaign runtime"
  sync_runtime || { json_state sync-failed degraded "canonical fetch/detached sync failed; adam-campaign resume will retry"; return 4; }
  venice_plan_gate >>"$LOG" 2>&1 || { json_state venice-plan-blocked blocked "Venice did not grant PLAN_ALLOWED; durable review receipt retained"; return 7; }

  local round=0
  while true; do
    round=$((round+1));json_state contracts running "local deterministic contract round $round"
    if bash "$ROOT/tools/run_fortress_local_contracts.sh" >"$STATE_ROOT/contracts.log" 2>&1; then break; fi
    json_state contracts-failed repairing "contract round $round failed; invoking governed repair"; repair_with_adam "$STATE_ROOT/contracts.log" || true; backoff "$round"
  done

  round=0
  while true; do
    round=$((round+1));json_state install running "Adam install/runtime acceptance round $round"
    if bash "$ROOT/tools/install_adam_cli.sh" >"$STATE_ROOT/install.log" 2>&1; then break; fi
    json_state install-failed repairing "install/runtime round $round failed; invoking governed repair"; repair_with_adam "$STATE_ROOT/install.log" || true; backoff "$round"
  done

  round=0
  while true; do
    round=$((round+1));json_state verify running "continuing-value acceptance round $round"
    if bash "$ROOT/tools/home_center_status_menu.sh" probe >"$STATE_ROOT/menu-probe.log" 2>&1; then MENU_OK=1; else MENU_OK=0; fi
    if write_acceptance "$MENU_OK" >"$STATE_ROOT/verify.log" 2>&1; then break; fi
    json_state verify-failed repairing "Venice plan/stop receipts or persistent control surface not proven; invoking governed repair"
    repair_with_adam "$STATE_ROOT/verify.log" || true
    backoff "$round"
    bash "$ROOT/tools/run_fortress_local_contracts.sh" >"$STATE_ROOT/contracts.log" 2>&1 || true
    bash "$ROOT/tools/install_adam_cli.sh" >"$STATE_ROOT/install.log" 2>&1 || true
  done

  persist_repairs || { json_state persist-failed degraded "accepted locally but canonical persistence failed; adam-campaign resume will retry"; return 21; }
  install_service
  json_state healthy healthy "Adam campaign accepted; persistent self-heal/status/menu remain installed in dedicated runtime"
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
