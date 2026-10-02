#!/data/data/com.termux/files/usr/bin/bash
set -u

CAMPAIGN_ID="headcrab-home-center-deploy"
PROJECT="${FIREBASE_PROJECT:-home-center-dclar}"
REGION="${GCLOUD_FUNCTIONS_REGION:-us-central1}"
REPO_URL="${HOME_CENTER_REPO_URL:-https://github.com/Valar05/home-center.git}"
STATE_ROOT="${HC_STATE_DIR:-$HOME/.local/state/home-center}/$CAMPAIGN_ID"
RUNTIME_ROOT="${HC_CAMPAIGN_RUNTIME_ROOT:-$HOME/.local/share/home-center-campaigns}/$CAMPAIGN_ID"
WORK="$RUNTIME_ROOT/worktree"
STATE="$STATE_ROOT/state.json"
HISTORY="$STATE_ROOT/history.jsonl"
LOG="$STATE_ROOT/campaign.log"
LATEST="$STATE_ROOT/latest-receipt.json"
PIDFILE="$STATE_ROOT/worker.pid"
STOPFILE="$STATE_ROOT/STOP"
mkdir -p "$STATE_ROOT" "$RUNTIME_ROOT"

clip(){
  local msg="$1"
  if command -v termux-clipboard-set >/dev/null 2>&1; then
    printf '%s' "$msg" | termux-clipboard-set >/dev/null 2>&1 || true
  else
    printf 'HEADCRAB_DEPLOY_CLIPBOARD_UNAVAILABLE\n' >&2
  fi
}

state(){
  local stage="$1" status="$2" detail="$3"
  python3 - "$STATE" "$HISTORY" "$stage" "$status" "$detail" "$PIDFILE" "$WORK" <<'PY'
import json,os,sys,time
state,history,stage,status,detail,pidfile,work=sys.argv[1:]
pid=None
try: pid=int(open(pidfile).read().strip())
except Exception: pass
obj={"schema":"headcrab-home-center-deploy-campaign-v1","stage":stage,"status":status,"detail":detail,"pid":pid,"worktree":work,"updatedAtEpoch":int(time.time())}
tmp=state+".tmp"; open(tmp,"w",encoding="utf-8").write(json.dumps(obj,indent=2,sort_keys=True)+"\n"); os.replace(tmp,state)
with open(history,"a",encoding="utf-8") as f: f.write(json.dumps(obj,sort_keys=True)+"\n")
print(json.dumps(obj,sort_keys=True))
PY
}

need(){ command -v "$1" >/dev/null 2>&1 || { state prerequisites blocked "missing $1"; return 10; }; }

ensure_gcloud(){
  if command -v gcloud >/dev/null 2>&1; then
    state prerequisites running "using native Termux gcloud"
    return 0
  fi

  if ! command -v proot-distro >/dev/null 2>&1; then
    state prerequisites repairing "installing Termux proot-distro for Google Cloud CLI capsule"
    command -v pkg >/dev/null 2>&1 || { state prerequisites blocked "pkg unavailable; cannot install proot-distro"; return 10; }
    pkg install -y proot-distro >>"$LOG" 2>&1 || return 10
  fi

  if ! proot-distro login debian -- true >/dev/null 2>&1; then
    state prerequisites repairing "installing Debian capsule for Google Cloud CLI"
    proot-distro install debian >>"$LOG" 2>&1 || return 10
  fi

  if ! proot-distro login debian -- sh -lc 'command -v gcloud >/dev/null 2>&1'; then
    state prerequisites repairing "installing Google Cloud CLI inside Debian capsule"
    proot-distro login debian -- sh -lc '
      set -eu
      apt-get update
      apt-get install -y ca-certificates curl gnupg
      mkdir -p /usr/share/keyrings
      curl -fsSL https://packages.cloud.google.com/apt/doc/apt-key.gpg | gpg --dearmor --yes -o /usr/share/keyrings/cloud.google.gpg
      printf "%s\\n" "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" > /etc/apt/sources.list.d/google-cloud-sdk.list
      apt-get update
      apt-get install -y google-cloud-cli
    ' >>"$LOG" 2>&1 || return 10
  fi

  local bindir="$STATE_ROOT/bin"
  mkdir -p "$bindir"
  cat >"$bindir/gcloud" <<EOF
#!/data/data/com.termux/files/usr/bin/bash
exec proot-distro login debian --bind "$HOME:$HOME" -- gcloud "\$@"
EOF
  chmod 700 "$bindir/gcloud"
  export PATH="$bindir:$PATH"
  command -v gcloud >/dev/null 2>&1 || return 10
  state prerequisites running "using Debian/proot gcloud capsule"
  return 0
}

stopped(){ [ -f "$STOPFILE" ]; }

prepare_clean_main(){
  state prepare running "creating sparse isolated main checkout for deployment/test surfaces; dirty primary checkout is not touched"
  rm -rf "$WORK"
  GIT_LFS_SKIP_SMUDGE=1 git clone --depth 1 --no-checkout --branch main "$REPO_URL" "$WORK" >>"$LOG" 2>&1 || return 11
  git -C "$WORK" sparse-checkout init --cone >>"$LOG" 2>&1 || return 12
  git -C "$WORK" sparse-checkout set functions tools contracts .github >>"$LOG" 2>&1 || return 13
  GIT_LFS_SKIP_SMUDGE=1 git -C "$WORK" checkout main >>"$LOG" 2>&1 || return 14
  git -C "$WORK" remote get-url origin >>"$LOG" 2>&1 || return 15
  dirty="$(git -C "$WORK" status --porcelain --untracked-files=all)"
  if [ -n "$dirty" ]; then
    printf '%s\n' "$dirty" >>"$LOG"
    state prepare-dirty blocked "sparse deployment checkout is unexpectedly dirty"
    return 16
  fi
}

install_dependencies(){
  state deps running "installing locked Functions dependencies in isolated checkout"
  npm ci --prefix "$WORK/functions" --ignore-scripts >>"$LOG" 2>&1 || return 20
}

run_headcrab_tests(){
  state test running "running focused Headcrab unit and syntax tests locally"
  (
    cd "$WORK" &&
    node --check functions/headcrab_reminder_store.js &&
    node --test tools/headcrab_reminder_store.test.js &&
    python3 tools/test_headcrab_morning.py &&
    python3 tools/test_headcrab_obligations.py &&
    node --check functions/home_center_mcp.js &&
    if [ -f tools/headcrab_pr384_campaign.sh ]; then bash -n tools/headcrab_pr384_campaign.sh; fi
  ) >>"$LOG" 2>&1
}

refresh_manifest(){
  state manifest running "refreshing Home Center public tool manifest from exact local source"
  (
    cd "$WORK" &&
    node tools/generate_home_center_public_manifest.mjs &&
    node tools/generate_home_center_public_manifest.mjs --check &&
    grep -q '"name": "headcrab_remember"' contracts/home-center-public-tool-manifest.v1.json &&
    grep -q '"name": "headcrab_reminders"' contracts/home-center-public-tool-manifest.v1.json &&
    grep -q '"name": "headcrab_attention_pulse"' contracts/home-center-public-tool-manifest.v1.json &&
    grep -q '"name": "headcrab_mine_email"' contracts/home-center-public-tool-manifest.v1.json
  ) >>"$LOG" 2>&1 || return 30

  if ! git -C "$WORK" diff --quiet -- contracts/home-center-top-level-mcp.v1.json contracts/home-center-public-tool-manifest.v1.json; then
    state manifest-commit running "committing refreshed Headcrab tool manifest directly to main"
    if ! git -C "$WORK" config user.name >/dev/null 2>&1; then git -C "$WORK" config user.name "Drew Clarke"; fi
    if ! git -C "$WORK" config user.email >/dev/null 2>&1; then git -C "$WORK" config user.email "dclarke1005@gmail.com"; fi
    git -C "$WORK" add contracts/home-center-top-level-mcp.v1.json contracts/home-center-public-tool-manifest.v1.json
    git -C "$WORK" commit -m "Refresh Home Center manifest for Headcrab reminders [skip ci]" >>"$LOG" 2>&1 || return 31
    if ! git -C "$WORK" push origin HEAD:main >>"$LOG" 2>&1; then
      state manifest-push-retry retrying "main advanced while manifest was generated; rebuilding once from newest main"
      prepare_clean_main || return 32
      install_dependencies || return 33
      run_headcrab_tests || return 34
      (cd "$WORK" && node tools/generate_home_center_public_manifest.mjs && node tools/generate_home_center_public_manifest.mjs --check) >>"$LOG" 2>&1 || return 35
      git -C "$WORK" add contracts/home-center-top-level-mcp.v1.json contracts/home-center-public-tool-manifest.v1.json
      if ! git -C "$WORK" diff --cached --quiet; then
        git -C "$WORK" config user.name "Drew Clarke"
        git -C "$WORK" config user.email "dclarke1005@gmail.com"
        git -C "$WORK" commit -m "Refresh Home Center manifest for Headcrab reminders [skip ci]" >>"$LOG" 2>&1 || return 36
        git -C "$WORK" push origin HEAD:main >>"$LOG" 2>&1 || return 37
      fi
    fi
  fi
}

deploy(){
  state deploy running "deploying only homeCenterMcp from exact clean main checkout"
  cd "$WORK" || return 40
  git fetch origin main >>"$LOG" 2>&1 || return 41
  [ "$(git rev-parse HEAD)" = "$(git rev-parse origin/main)" ] || { state deploy-blocked blocked "isolated checkout is no longer exact origin/main"; return 42; }
  [ -z "$(git status --porcelain)" ] || { state deploy-blocked blocked "isolated checkout became dirty before deploy"; return 43; }

  GCLOUD_FUNCTIONS_REGION="$REGION" sh tools/deploy_functions_termux.sh "$PROJECT" homeCenterMcp >>"$LOG" 2>&1 || return 44
}

verify(){
  state verify running "verifying deployed release identity and live Headcrab tool surface"
  local commit ready
  commit="$(git -C "$WORK" rev-parse HEAD)"
  ready="$(curl --fail --silent --show-error "https://${REGION}-${PROJECT}.cloudfunctions.net/homeCenterMcp/ready")" || return 50
  READY_JSON="$ready" EXPECTED="$commit" node -e '
const p=JSON.parse(process.env.READY_JSON), i=p.releaseIdentity||{};
if(!p.ready) throw new Error("readiness false");
if(i.sourceCommit!==process.env.EXPECTED) throw new Error("sourceCommit mismatch "+i.sourceCommit+" != "+process.env.EXPECTED);
if(i.sourceRef!=="refs/heads/main") throw new Error("sourceRef mismatch "+i.sourceRef);
console.log(JSON.stringify({ready:p.ready,releaseIdentity:i}));
' >>"$LOG" 2>&1 || return 51

  HOME_CENTER_EXPECTED_SOURCE_COMMIT="$commit" \
  HOME_CENTER_MCP_URL="https://${REGION}-${PROJECT}.cloudfunctions.net/homeCenterMcp/mcp" \
    node "$WORK/tools/home_center_production_catalog_test.mjs" >>"$LOG" 2>&1 || return 52

  node - "$WORK/contracts/home-center-public-tool-manifest.v1.json" <<'NODE' >>"$LOG" 2>&1
const fs=require('fs');
const m=JSON.parse(fs.readFileSync(process.argv[2],'utf8'));
const names=new Set((m.entries||[]).map(x=>x.name));
for(const n of ['headcrab_remember','headcrab_reminders','headcrab_close_reminder','headcrab_reschedule_reminder','headcrab_attention_pulse','headcrab_mark_checked','headcrab_mine_email']){
  if(!names.has(n)) throw new Error('missing Headcrab tool '+n);
}
console.log(JSON.stringify({headcrabTools:[...names].filter(x=>x.startsWith('headcrab_')).sort()}));
NODE
}

receipt(){
  local status="$1" detail="$2"
  python3 - "$LATEST" "$WORK" "$status" "$detail" "$PROJECT" "$REGION" <<'PY'
import json,subprocess,sys,time,os
out,work,status,detail,project,region=sys.argv[1:]
def run(*args):
    p=subprocess.run(args,cwd=work,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    return {"code":p.returncode,"stdout":p.stdout[-8000:],"stderr":p.stderr[-2000:]}
obj={
 "schema":"headcrab-home-center-deploy-receipt-v1",
 "status":status,
 "detail":detail,
 "project":project,
 "region":region,
 "verifiedAtEpoch":int(time.time()),
 "source":{"head":run("git","rev-parse","HEAD"),"branch":run("git","symbolic-ref","--short","-q","HEAD"),"status":run("git","status","--short")},
 "capability":{"requested":True,"implemented":True,"testedLocally":status=="healthy","deployed":status=="healthy","liveVerified":status=="healthy","accepted":False},
 "primaryDirtyCheckoutTouched":False,
}
tmp=out+".tmp";open(tmp,"w",encoding="utf-8").write(json.dumps(obj,indent=2,sort_keys=True)+"\n");os.replace(tmp,out)
print(json.dumps(obj,indent=2,sort_keys=True))
PY
}

worker_once(){
  rm -f "$STOPFILE"
  : >"$LOG"
  need git || return $?
  need node || return $?
  need npm || return $?
  need python3 || return $?
  ensure_gcloud || return $?
  need curl || return $?
  stopped && return 130

  prepare_clean_main || { rc=$?; state prepare-failed retrying "clean checkout failed rc=$rc"; receipt degraded "prepare failed"; return "$rc"; }
  install_dependencies || { rc=$?; state deps-failed retrying "npm ci failed rc=$rc"; receipt degraded "dependency install failed"; return "$rc"; }
  run_headcrab_tests || { rc=$?; state test-failed retrying "focused Headcrab tests failed rc=$rc"; receipt degraded "tests failed"; return "$rc"; }
  refresh_manifest || { rc=$?; state manifest-failed retrying "manifest refresh failed rc=$rc"; receipt degraded "manifest refresh failed"; return "$rc"; }

  prepare_clean_main || { rc=$?; state prepare-deploy-failed retrying "could not refresh exact main rc=$rc"; return "$rc"; }
  install_dependencies || { rc=$?; state deps-deploy-failed retrying "npm ci before deploy failed rc=$rc"; return "$rc"; }
  run_headcrab_tests || { rc=$?; state final-test-failed retrying "Headcrab tests failed on exact deploy commit rc=$rc"; return "$rc"; }
  (cd "$WORK" && node tools/generate_home_center_public_manifest.mjs --check) >>"$LOG" 2>&1 || { state manifest-check-failed retrying "manifest stale on exact deploy commit"; return 60; }

  acct="$(gcloud auth list --filter=status:ACTIVE --format='value(account)' 2>/dev/null | head -n 1 || true)"
  if [ -z "$acct" ]; then
    state auth-needed waiting "Google Cloud CLI is installed but no active account is authenticated. Run gcloud auth login in the same Termux/Proot environment, then leave this campaign running; it will continue automatically."
    return 75
  fi

  deploy || { rc=$?; state deploy-failed retrying "homeCenterMcp deploy failed rc=$rc"; receipt degraded "deploy failed"; return "$rc"; }
  verify || { rc=$?; state verify-failed retrying "deployment completed but live verification failed rc=$rc"; receipt degraded "live verification failed"; return "$rc"; }

  receipt healthy "Headcrab Home Center deployment verified live" >>"$LOG" 2>&1
  state healthy healthy "Headcrab reminder tools are deployed and verified on live Home Center"
  msg="HEADCRAB HOME CENTER DEPLOYED + VERIFIED. Receipt: $LATEST"
  clip "$msg"
  printf '%s\n' "$msg"
  return 0
}

self_update(){
  local root="/storage/emulated/0/Documents/GodotProjects/home-center"
  local latest="$STATE_ROOT/latest-campaign.sh"
  if [ -e "$root/.git" ]; then
    git -C "$root" fetch origin main >>"$LOG" 2>&1 || return 1
    git -C "$root" show origin/main:tools/headcrab_home_center_deploy_campaign.sh >"$latest" 2>>"$LOG" || return 1
    chmod 700 "$latest"
    if ! cmp -s "$latest" "$0"; then
      state self-update restarting "newer campaign script found on origin/main; restarting supervisor with latest code"
      exec bash "$latest" _supervise
    fi
  fi
}

supervise(){
  rm -f "$STOPFILE"
  local round=0 rc=0 delay=0
  while true; do
    stopped && { state stopped stopped "operator stop requested"; return 130; }
    round=$((round+1))
    state supervise running "completion supervisor round $round"
    self_update || true
    worker_once
    rc=$?
    if [ "$rc" -eq 0 ]; then return 0; fi
    if [ "$rc" -eq 130 ]; then return 130; fi
    if [ "$rc" -eq 75 ]; then
      sleep 30
      continue
    fi
    if [ "$round" -lt 6 ]; then delay=$((2 ** round)); else delay=60; fi
    [ "$delay" -gt 60 ] && delay=60
    state supervise retrying "round $round ended rc=$rc; retrying in ${delay}s"
    sleep "$delay"
  done
}

launch(){
  if [ -f "$PIDFILE" ]; then
    old="$(cat "$PIDFILE" 2>/dev/null || true)"
    if [ -n "$old" ] && kill -0 "$old" 2>/dev/null; then
      state attached running "campaign already active; attaching to existing worker"
      return 0
    fi
  fi
  rm -f "$STOPFILE"
  command -v setsid >/dev/null 2>&1 || { echo "NEED: setsid" >&2; return 70; }
  setsid bash "$0" _supervise >>"$LOG" 2>&1 < /dev/null &
  pid=$!
  printf '%s\n' "$pid" >"$PIDFILE"
  state launched running "background deployment campaign launched"
  msg="HEADCRAB DEPLOY CAMPAIGN STARTED pid=$pid"
  clip "$msg"; printf '%s\n' "$msg"
}

run_and_follow(){
  install
  launch || return $?
  printf '\nFollowing campaign log. Ctrl-C detaches the viewer; it does NOT stop the campaign.\n'
  follow
}

stop_campaign(){
  touch "$STOPFILE"
  if [ -f "$PIDFILE" ]; then
    pid="$(cat "$PIDFILE" 2>/dev/null || true)"
    if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
      kill -TERM "-$pid" 2>/dev/null || kill -TERM "$pid" 2>/dev/null || true
      sleep 2
      kill -KILL "-$pid" 2>/dev/null || kill -KILL "$pid" 2>/dev/null || true
    fi
  fi
  state stopped stopped "operator stop requested"
  clip "HEADCRAB DEPLOY CAMPAIGN STOPPED"
}

status(){ [ -f "$STATE" ] && cat "$STATE" || printf '{"schema":"headcrab-home-center-deploy-campaign-v1","stage":"never-run","status":"idle"}\n'; }
follow(){ touch "$LOG"; tail -n 120 -f "$LOG"; }
receipts(){ status; [ -f "$LATEST" ] && { echo "===== RECEIPT ====="; cat "$LATEST"; }; echo "===== LOG TAIL ====="; tail -n 120 "$LOG" 2>/dev/null || true; }

install(){
  local bin="${PREFIX:-$HOME/.local}/bin/headcrab-deploy-campaign"
  local stable="$STATE_ROOT/campaign.sh"
  mkdir -p "$(dirname "$bin")" "$STATE_ROOT"
  cp "$0" "$stable"
  chmod 700 "$stable"
  cat >"$bin" <<EOF
#!/data/data/com.termux/files/usr/bin/bash
exec bash "$stable" "\$@"
EOF
  chmod 755 "$bin"
  printf 'installed %s\n' "$bin"
}

case "${1:-run}" in
  run) run_and_follow ;;
  start|resume) install; launch ;;
  _supervise) supervise ;;
  status) status ;;
  follow) follow ;;
  receipts) receipts ;;
  stop) stop_campaign ;;
  install) install ;;
  *) echo "usage: headcrab-deploy-campaign [run|start|resume|status|follow|receipts|stop|install]" >&2; exit 64 ;;
esac
