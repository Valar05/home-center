#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

LIVE_REPO="${HC_LIVE_REPO:-/storage/emulated/0/Documents/GodotProjects/home-center-phone-hands}"
STATE_ROOT="${HC_STATE_DIR:-$HOME/.local/state/home-center}/fortress-campaign"
RUNTIME_ROOT="${HC_FORTRESS_RUNTIME:-${PREFIX:-$HOME/.local}/var/lib/fortress-campaign/runtime}"
STATE="$STATE_ROOT/state.json"
HISTORY="$STATE_ROOT/history.jsonl"
LATEST="$STATE_ROOT/latest.json"
LOCK="$STATE_ROOT/run.lock"
LOG="$STATE_ROOT/campaign.log"
BIN="${PREFIX:-$HOME/.local}/bin/fortress-campaign"
mkdir -p "$STATE_ROOT" "$(dirname "$RUNTIME_ROOT")" "$(dirname "$BIN")"

record(){
  local phase="$1" status="$2" detail="$3"
  python3 - "$STATE" "$HISTORY" "$LATEST" "$phase" "$status" "$detail" <<'PY'
import json,os,sys,time
state,history,latest,phase,status,detail=sys.argv[1:]
obj={'schema':'fortress-phone-campaign-v1','phase':phase,'status':status,'detail':detail,'updatedAtEpoch':int(time.time())}
for path in (state,latest):
 os.makedirs(os.path.dirname(path),exist_ok=True);tmp=path+'.tmp';open(tmp,'w',encoding='utf-8').write(json.dumps(obj,indent=2,sort_keys=True)+'\n');os.replace(tmp,path)
with open(history,'a',encoding='utf-8') as f:f.write(json.dumps(obj,sort_keys=True)+'\n')
print(json.dumps(obj,sort_keys=True))
PY
}

install_command(){
  cat >"$BIN" <<EOF
#!/data/data/com.termux/files/usr/bin/bash
exec bash "$RUNTIME_ROOT/tools/fortress_phone_campaign.sh" "\$@"
EOF
  chmod 755 "$BIN"
}

sync_runtime(){
  record runtime-sync running "refreshing isolated canonical runtime; live phone worktree is untouched"
  [ -d "$LIVE_REPO/.git" ] || { record runtime-sync blocked "live repository metadata not found at $LIVE_REPO"; return 2; }
  git -C "$LIVE_REPO" fetch origin main >>"$LOG" 2>&1 || { record runtime-sync degraded "fetch origin/main failed; existing runtime will be used if present"; [ -d "$RUNTIME_ROOT/.git" ] && return 0 || return 3; }
  if [ ! -d "$RUNTIME_ROOT/.git" ]; then
    git -C "$LIVE_REPO" worktree prune >>"$LOG" 2>&1 || true
    git -C "$LIVE_REPO" worktree add --detach "$RUNTIME_ROOT" origin/main >>"$LOG" 2>&1 || { record runtime-sync blocked "could not create isolated runtime worktree"; return 4; }
  else
    git -C "$RUNTIME_ROOT" fetch origin main >>"$LOG" 2>&1 || true
    git -C "$RUNTIME_ROOT" reset --hard origin/main >>"$LOG" 2>&1 || { record runtime-sync blocked "could not reset isolated runtime to origin/main"; return 5; }
    git -C "$RUNTIME_ROOT" clean -fd >>"$LOG" 2>&1 || true
  fi
  record runtime-sync healthy "isolated runtime tracks origin/main; live phone worktree untouched"
}

probe_atom(){ curl -fsS http://127.0.0.1:8788/v1/atom/status; }
probe_overlay(){ command -v rish >/dev/null 2>&1 && rish -c 'content query --uri content://com.homecenter.operatoroverlay.state/state' 2>/dev/null | grep -q 'control_enabled='; }
probe_menu(){ bash "$RUNTIME_ROOT/tools/home_center_status_menu.sh" probe >/dev/null 2>&1; }
probe_vlad(){ pgrep -f 'vlad_swarm_daemon.py' >/dev/null 2>&1; }
probe_hands(){ bash "$RUNTIME_ROOT/tools/phone_hands_watchdog.sh" diagnose >/dev/null 2>&1; }
probe_ssh(){ bash "$RUNTIME_ROOT/tools/phone_ssh_service.sh" status >/dev/null 2>&1; }

triage(){
  record triage running "probing Atom, Vlad daemon, SSH, overlay, Phone Hands, notification menu, and SSH Axis"
  local atom=0 vlad=0 ssh=0 overlay=0 hands=0 menu=0
  probe_atom >/dev/null 2>&1 && atom=1 || true
  probe_vlad && vlad=1 || true
  probe_ssh && ssh=1 || true
  probe_overlay && overlay=1 || true
  probe_hands && hands=1 || true
  probe_menu && menu=1 || true
  python3 - "$STATE_ROOT/triage.json" "$atom" "$vlad" "$ssh" "$overlay" "$hands" "$menu" <<'PY'
import json,sys,time,os
p=sys.argv[1];vals=list(map(int,sys.argv[2:]));names=['atom','vladDaemon','sshLocal','overlay','phoneHands','notificationMenu']
obj={'schema':'fortress-phone-triage-v1','atEpoch':int(time.time()),'checks':dict(zip(names,[bool(x) for x in vals]))}
os.makedirs(os.path.dirname(p),exist_ok=True);open(p,'w',encoding='utf-8').write(json.dumps(obj,indent=2,sort_keys=True)+'\n');print(json.dumps(obj,sort_keys=True))
PY
  record triage healthy "fresh subsystem triage receipt written"
}

repair_core(){
  record repair-core running "repairing only failed existing organs"
  if ! probe_atom >/dev/null 2>&1 || ! probe_vlad; then HC_REPO_ROOT="$RUNTIME_ROOT" bash "$RUNTIME_ROOT/tools/install_atom_vlad_phone.sh" >>"$LOG" 2>&1 || { record repair-core blocked "Atom/Vlad install or daemon recovery failed"; return 10; }; fi
  if ! probe_ssh; then bash "$RUNTIME_ROOT/tools/phone_ssh_service.sh" repair >>"$LOG" 2>&1 || { record repair-core degraded "SSH local repair failed"; return 11; }; fi
  if ! probe_overlay; then bash "$RUNTIME_ROOT/tools/recover_adam_overlay_phone.sh" >>"$LOG" 2>&1 || { record repair-core degraded "overlay recovery failed"; return 12; }; fi
  if ! probe_hands; then
    if [ -x "$RUNTIME_ROOT/tools/home_center_phone_relay_recover.sh" ] || [ -f "$RUNTIME_ROOT/tools/home_center_phone_relay_recover.sh" ]; then bash "$RUNTIME_ROOT/tools/home_center_phone_relay_recover.sh" >>"$LOG" 2>&1 || true; fi
    probe_hands || { record repair-core degraded "Phone Hands still unhealthy after bounded recovery"; return 13; }
  fi
  bash "$RUNTIME_ROOT/tools/home_center_status_menu.sh" main >/dev/null 2>&1 || { record repair-core degraded "notification/status surface unavailable"; return 14; }
  record repair-core healthy "existing phone organs recovered without touching live worktree"
}

verify_phone(){
  record verify-phone running "fresh local verification after repairs"
  local atom_json
  atom_json="$(probe_atom 2>/dev/null)" || { record verify-phone blocked "Atom status unavailable"; return 20; }
  python3 - "$atom_json" <<'PY' || { record verify-phone blocked "Atom does not report loaded deterministic Vlad contract"; return 21; }
import json,sys
x=json.loads(sys.argv[1]);v=x.get('vlad') or {}
assert x.get('ok') is True and x.get('service')=='Atom' and v.get('loaded') is True and v.get('defaultMode')=='deterministic' and v.get('ollamaDefault')=='disabled'
PY
  probe_vlad || { record verify-phone blocked "Vlad persistent daemon unavailable"; return 22; }
  probe_ssh || { record verify-phone blocked "local SSH listener unavailable"; return 23; }
  probe_overlay || { record verify-phone blocked "operator overlay/status provider unavailable"; return 24; }
  probe_hands || { record verify-phone blocked "Phone Hands diagnose failed"; return 25; }
  probe_menu || { record verify-phone blocked "notification menu probe failed"; return 26; }
  python3 "$RUNTIME_ROOT/tools/ssh_axis.py" check --target cauldron --json >"$STATE_ROOT/ssh-axis-cauldron.json" 2>&1 || true
  record verify-phone healthy "phone-local acceptance passed; external phone SSH callability remains separate evidence"
}

write_review_packet(){
  record review-packet running "writing bounded evidence packet for Vlad, Venice, and Tetsuya"
  python3 - "$STATE_ROOT/review-packet.json" "$STATE_ROOT" "$RUNTIME_ROOT" <<'PY'
import json,os,sys,time
out,state,root=sys.argv[1:]
def load(name):
 p=os.path.join(state,name)
 try:return json.load(open(p,encoding='utf-8'))
 except Exception:return None
obj={'schema':'fortress-phone-review-packet-v1','createdAtEpoch':int(time.time()),'runtimeRoot':root,'evidence':{'triage':load('triage.json'),'phoneSsh':load('../phone-ssh/latest.json'),'sshAxisCauldron':load('ssh-axis-cauldron.json')},'requiredGates':{'vlad':'GO or GO-WITH-SCAR','venice':'STOP_ALLOWED with externalReviewGateSatisfied=true','tetsuya':'RELEASE_ALLOWED'},'accepted':False}
open(out,'w',encoding='utf-8').write(json.dumps(obj,indent=2,sort_keys=True)+'\n');print(json.dumps(obj,sort_keys=True))
PY
  record review-packet awaiting-review "campaign is operational but cannot self-release; Vlad + Venice + Tetsuya gates remain"
}

run_campaign(){
  mkdir "$LOCK" 2>/dev/null || { record lock healthy "campaign already running"; return 0; }
  trap 'rmdir "$LOCK" 2>/dev/null || true' EXIT INT TERM
  sync_runtime
  install_command
  triage
  repair_core
  triage
  verify_phone
  write_review_packet
}

status(){ [ -f "$STATE" ] && cat "$STATE" || printf '{"schema":"fortress-phone-campaign-v1","phase":"never-run","status":"idle"}\n'; }
receipts(){ status; [ -f "$STATE_ROOT/triage.json" ] && cat "$STATE_ROOT/triage.json"; [ -f "$STATE_ROOT/review-packet.json" ] && cat "$STATE_ROOT/review-packet.json"; [ -f "${HC_STATE_DIR:-$HOME/.local/state/home-center}/phone-ssh/latest.json" ] && cat "${HC_STATE_DIR:-$HOME/.local/state/home-center}/phone-ssh/latest.json"; }

case "${1:-run}" in
  run|resume) run_campaign ;;
  triage) sync_runtime; triage ;;
  repair) sync_runtime; repair_core; triage; verify_phone ;;
  ssh) sync_runtime; bash "$RUNTIME_ROOT/tools/phone_ssh_service.sh" repair; bash "$RUNTIME_ROOT/tools/home_center_status_menu.sh" main >/dev/null 2>&1 || true ;;
  overlay) sync_runtime; bash "$RUNTIME_ROOT/tools/recover_adam_overlay_phone.sh" ;;
  phone-hands) sync_runtime; bash "$RUNTIME_ROOT/tools/phone_hands_watchdog.sh" diagnose ;;
  status) status ;;
  receipts) receipts ;;
  *) echo 'usage: fortress-campaign [run|resume|triage|repair|ssh|overlay|phone-hands|status|receipts]' >&2; exit 64 ;;
esac
