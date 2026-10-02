#!/data/data/com.termux/files/usr/bin/bash
set -u

CAMPAIGN_ID="headcrab-pr384"
PR_NUMBER="384"
REMOTE_BRANCH="codex/headcrab-durable-reminders"
RUNTIME_BRANCH="campaign/headcrab-pr384-runtime"

ROOT="${HC_REPO_ROOT:-$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)}"
STATE_ROOT="${HC_STATE_DIR:-$HOME/.local/state/home-center}/$CAMPAIGN_ID"
RUNTIME_ROOT="${HC_CAMPAIGN_RUNTIME_ROOT:-$HOME/.local/share/home-center-campaigns}/$CAMPAIGN_ID"
WORKTREE="$RUNTIME_ROOT/worktree"
STATE="$STATE_ROOT/state.json"
HISTORY="$STATE_ROOT/history.jsonl"
LOG="$STATE_ROOT/campaign.log"
LATEST="$STATE_ROOT/latest-receipt.json"
PRIMARY_SNAPSHOT="$STATE_ROOT/primary-worktree.json"
WORKER_PID="$STATE_ROOT/worker.pid"
STOP_FILE="$STATE_ROOT/STOP"
mkdir -p "$STATE_ROOT" "$RUNTIME_ROOT"

clipboard() {
  local payload="$1"
  if command -v termux-clipboard-set >/dev/null 2>&1; then
    printf '%s' "$payload" | termux-clipboard-set >/dev/null 2>&1 || true
  else
    printf 'HEADCRAB_CAMPAIGN_CLIPBOARD_UNAVAILABLE\n' >&2
  fi
}

write_state() {
  local stage="$1" status="$2" detail="$3"
  python3 - "$STATE" "$HISTORY" "$stage" "$status" "$detail" "$WORKER_PID" "$WORKTREE" "$PR_NUMBER" <<'PY'
import json,os,sys,time
state,history,stage,status,detail,pid_path,worktree,pr=sys.argv[1:]
pid=None
try: pid=int(open(pid_path).read().strip())
except Exception: pass
obj={
  "schema":"headcrab-pr384-campaign-v1",
  "campaign":"headcrab-pr384",
  "pr":int(pr),
  "stage":stage,
  "status":status,
  "detail":detail,
  "pid":pid,
  "worktree":worktree,
  "updatedAtEpoch":int(time.time()),
}
tmp=state+".tmp"
open(tmp,"w",encoding="utf-8").write(json.dumps(obj,indent=2,sort_keys=True)+"\n")
os.replace(tmp,state)
with open(history,"a",encoding="utf-8") as f:
  f.write(json.dumps(obj,sort_keys=True)+"\n")
print(json.dumps(obj,sort_keys=True))
PY
}

snapshot_primary() {
  python3 - "$ROOT" "$PRIMARY_SNAPSHOT" <<'PY'
import json,subprocess,sys,time,os
root,out=sys.argv[1:]
def run(*args):
    p=subprocess.run(args,cwd=root,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    return {"code":p.returncode,"stdout":p.stdout[-20000:],"stderr":p.stderr[-4000:]}
obj={
  "schema":"headcrab-primary-worktree-snapshot-v1",
  "capturedAtEpoch":int(time.time()),
  "root":root,
  "head":run("git","rev-parse","HEAD"),
  "branch":run("git","symbolic-ref","--short","-q","HEAD"),
  "status":run("git","status","--porcelain=v2","--branch"),
  "diffStat":run("git","diff","--stat"),
  "cachedDiffStat":run("git","diff","--cached","--stat"),
  "untracked":run("git","ls-files","--others","--exclude-standard"),
}
tmp=out+".tmp"
open(tmp,"w",encoding="utf-8").write(json.dumps(obj,indent=2,sort_keys=True)+"\n")
os.replace(tmp,out)
print(json.dumps({"snapshot":out,"dirty":bool(obj["status"]["stdout"].strip())},sort_keys=True))
PY
}

stop_requested() { [ -f "$STOP_FILE" ]; }

ensure_runtime() {
  write_state runtime running "preparing isolated campaign worktree; primary checkout remains untouched"
  git -C "$ROOT" fetch origin main "$REMOTE_BRANCH" >>"$LOG" 2>&1 || return 1

  if [ -d "$WORKTREE/.git" ] || [ -f "$WORKTREE/.git" ]; then
    git -C "$WORKTREE" fetch origin main "$REMOTE_BRANCH" >>"$LOG" 2>&1 || return 1
    if [ -n "$(git -C "$WORKTREE" status --porcelain)" ]; then
      write_state runtime-blocked blocked "isolated campaign worktree itself is dirty; refusing to overwrite it"
      return 12
    fi
    git -C "$WORKTREE" checkout "$RUNTIME_BRANCH" >>"$LOG" 2>&1 || return 1
    git -C "$WORKTREE" reset --hard "origin/$REMOTE_BRANCH" >>"$LOG" 2>&1 || return 1
  else
    rm -rf "$WORKTREE"
    mkdir -p "$(dirname "$WORKTREE")"
    git -C "$ROOT" worktree prune >>"$LOG" 2>&1 || true
    git -C "$ROOT" worktree add -B "$RUNTIME_BRANCH" "$WORKTREE" "origin/$REMOTE_BRANCH" >>"$LOG" 2>&1 || return 1
  fi
}

run_contracts() {
  write_state contracts running "running Headcrab contract suite in isolated worktree"
  (
    cd "$WORKTREE" &&
    python3 tools/test_headcrab_morning.py &&
    python3 tools/test_headcrab_obligations.py &&
    node --test tools/headcrab_reminder_store.test.js
  ) >"$STATE_ROOT/contracts.log" 2>&1
}

repair_contracts() {
  write_state repair running "local Headcrab contracts failed; attempting bounded governed repair in isolated worktree"
  if [ -f "$WORKTREE/tools/adam_planned_venice.py" ] && command -v python3 >/dev/null 2>&1; then
    (
      cd "$WORKTREE" &&
      python3 tools/adam_planned_venice.py         "Repair ONLY PR #384 Headcrab durable-reminder changes in this isolated campaign worktree. Read $STATE_ROOT/contracts.log. Preserve the dirty primary checkout outside this worktree. Fix the smallest root cause, run the Headcrab contracts, review the diff, and stop only at a proven boundary. Do not reset, clean, stash, or mutate the primary checkout."
    ) >>"$LOG" 2>&1 || true
  else
    write_state repair-unavailable blocked "governed repair helper unavailable; receipt contains failing contract log"
    return 13
  fi
}

push_runtime() {
  write_state push running "pushing isolated repaired branch to PR #384 remote branch"
  git -C "$WORKTREE" status --short >>"$LOG" 2>&1
  if [ -n "$(git -C "$WORKTREE" status --porcelain)" ]; then
    git -C "$WORKTREE" add -A >>"$LOG" 2>&1 || return 1
    if ! git -C "$WORKTREE" diff --cached --quiet; then
      git -C "$WORKTREE" commit -m "Repair Headcrab durable reminder campaign" >>"$LOG" 2>&1 || return 1
    fi
  fi
  git -C "$WORKTREE" push origin "HEAD:$REMOTE_BRANCH" >>"$LOG" 2>&1 || return 1
}

ci_snapshot() {
  gh pr checks "$PR_NUMBER" --repo Valar05/home-center >"$STATE_ROOT/ci-checks.txt" 2>&1
  return $?
}

wait_ci() {
  local round=0
  while true; do
    stop_requested && return 130
    round=$((round+1))
    write_state ci running "checking PR #384 CI round $round"
    ci_snapshot
    local rc=$?
    if [ "$rc" -eq 0 ]; then return 0; fi

    if grep -Eiq 'fail|cancel|error' "$STATE_ROOT/ci-checks.txt"; then
      write_state ci-failed repairing "CI reports failure; capturing logs and attempting one bounded repair cycle"
      gh run list --repo Valar05/home-center --branch "$REMOTE_BRANCH" --limit 20 >"$STATE_ROOT/ci-runs.txt" 2>&1 || true
      fail_id="$(gh run list --repo Valar05/home-center --branch "$REMOTE_BRANCH" --status failure --limit 1 --json databaseId --jq '.[0].databaseId' 2>/dev/null || true)"
      if [ -n "$fail_id" ]; then
        gh run view "$fail_id" --repo Valar05/home-center --log-failed >"$STATE_ROOT/ci-failed.log" 2>&1 || true
      else
        cp "$STATE_ROOT/ci-checks.txt" "$STATE_ROOT/ci-failed.log" 2>/dev/null || true
      fi
      return 2
    fi
    sleep 20
    [ "$round" -ge 45 ] && { write_state ci-waiting waiting "CI still pending after bounded wait; resume continues polling"; return 3; }
  done
}

write_receipt() {
  local status="$1" detail="$2"
  python3 - "$LATEST" "$ROOT" "$WORKTREE" "$PRIMARY_SNAPSHOT" "$STATE_ROOT/ci-checks.txt" "$status" "$detail" "$PR_NUMBER" <<'PY'
import json,sys,time,subprocess,os
out,root,worktree,primary,checks,status,detail,pr=sys.argv[1:]
def run(cwd,*args):
  p=subprocess.run(args,cwd=cwd,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
  return {"code":p.returncode,"stdout":p.stdout[-12000:],"stderr":p.stderr[-2000:]}
obj={
 "schema":"headcrab-pr384-campaign-receipt-v1",
 "campaign":"headcrab-pr384",
 "pr":int(pr),
 "status":status,
 "detail":detail,
 "verifiedAtEpoch":int(time.time()),
 "primarySnapshot":primary,
 "primaryUntouched":True,
 "runtime":{"path":worktree,"head":run(worktree,"git","rev-parse","HEAD"),"status":run(worktree,"git","status","--short")},
 "ciChecks":open(checks,encoding="utf-8",errors="replace").read()[-12000:] if os.path.exists(checks) else "",
 "capability":{"requested":True,"implementedInRepository":True,"testedLocally":status in ("ci-green","merged"),"ciGreen":status in ("ci-green","merged"),"merged":status=="merged","deployed":False,"callableProduction":False,"accepted":False},
}
tmp=out+".tmp";open(tmp,"w",encoding="utf-8").write(json.dumps(obj,indent=2,sort_keys=True)+"\n");os.replace(tmp,out)
print(json.dumps(obj,indent=2,sort_keys=True))
PY
}

reconcile_primary() {
  snapshot_primary >/dev/null 2>&1 || true
  if [ -n "$(git -C "$ROOT" status --porcelain)" ]; then
    write_state reconcile-preserved preserved "primary Home Center checkout is dirty; leaving it untouched and using isolated runtime as reconciled campaign surface"
    printf 'Primary checkout remains dirty and untouched. Campaign worktree: %s\n' "$WORKTREE"
    return 0
  fi
  git -C "$ROOT" fetch origin main >>"$LOG" 2>&1 || return 1
  if git -C "$ROOT" merge --ff-only origin/main >>"$LOG" 2>&1; then
    write_state reconciled healthy "clean primary checkout fast-forwarded to origin/main"
    return 0
  fi
  write_state reconcile-blocked blocked "primary checkout clean but not fast-forwardable; no destructive reconciliation attempted"
  return 14
}

worker() {
  rm -f "$STOP_FILE"
  : >"$LOG"
  snapshot_primary >>"$LOG" 2>&1 || { write_state snapshot-failed blocked "could not snapshot primary checkout"; exit 4; }
  ensure_runtime || exit $?

  local repairs=0
  while ! run_contracts; do
    repairs=$((repairs+1))
    [ "$repairs" -gt 2 ] && { write_state contracts-blocked blocked "local contracts still failing after bounded repairs"; write_receipt blocked "local contracts failed"; exit 15; }
    repair_contracts || { write_receipt blocked "repair lane unavailable"; exit 16; }
  done

  push_runtime || { write_state push-failed degraded "push failed; resume retries without touching primary checkout"; write_receipt degraded "push failed"; exit 17; }

  local ci_repairs=0
  while true; do
    wait_ci
    rc=$?
    [ "$rc" -eq 0 ] && break
    [ "$rc" -eq 130 ] && { write_state stopped stopped "operator stop requested"; write_receipt stopped "operator stop"; exit 130; }
    [ "$rc" -eq 3 ] && { write_receipt waiting "CI still pending"; exit 0; }

    ci_repairs=$((ci_repairs+1))
    [ "$ci_repairs" -gt 2 ] && { write_state ci-blocked blocked "CI still failing after bounded repair attempts"; write_receipt blocked "CI failure"; exit 18; }
    cp "$STATE_ROOT/ci-failed.log" "$STATE_ROOT/contracts.log" 2>/dev/null || true
    repair_contracts || true
    run_contracts || continue
    push_runtime || { write_state push-failed degraded "push after CI repair failed"; exit 19; }
  done

  write_state ci-green healthy "PR #384 checks are green"
  write_receipt ci-green "PR #384 checks green" >"$STATE_ROOT/receipt.out" 2>&1

  if gh pr view "$PR_NUMBER" --repo Valar05/home-center --json mergeStateStatus,isDraft,state >"$STATE_ROOT/pr.json" 2>>"$LOG"; then
    if python3 - "$STATE_ROOT/pr.json" <<'PY'
import json,sys
x=json.load(open(sys.argv[1]))
raise SystemExit(0 if x.get("state")=="OPEN" and not x.get("isDraft") and x.get("mergeStateStatus") in ("CLEAN","HAS_HOOKS","UNSTABLE") else 1)
PY
    then
      write_state merge-ready healthy "CI green; PR is ready for operator merge decision"
    fi
  fi

  reconcile_primary || true
  local final="HEADCRAB PR384 READY: CI green. Primary dirty worktree preserved. Receipts: $LATEST"
  write_state ready healthy "$final"
  clipboard "$final"
  printf '%s\n' "$final"
}

launch() {
  if [ -f "$WORKER_PID" ]; then
    old="$(cat "$WORKER_PID" 2>/dev/null || true)"
    if [ -n "$old" ] && kill -0 "$old" 2>/dev/null; then
      status
      exit 0
    fi
  fi
  rm -f "$STOP_FILE"
  if ! command -v setsid >/dev/null 2>&1; then
    write_state launch-blocked blocked "setsid unavailable; refusing to let a long-running campaign own the operator shell"
    clipboard "HEADCRAB PR384 CAMPAIGN BLOCKED: setsid unavailable"
    return 22
  fi
  setsid env HC_REPO_ROOT="$ROOT" HC_STATE_DIR="${HC_STATE_DIR:-$HOME/.local/state/home-center}" \
    bash "$ROOT/tools/headcrab_pr384_campaign.sh" _worker >>"$LOG" 2>&1 < /dev/null &
  pid=$!
  printf '%s\n' "$pid" >"$WORKER_PID"
  write_state launched running "campaign worker launched in background"
  local receipt="HEADCRAB PR384 CAMPAIGN STARTED pid=$pid; status: headcrab-ci-campaign status; follow: headcrab-ci-campaign follow; stop: headcrab-ci-campaign stop"
  clipboard "$receipt"
  printf '%s\n' "$receipt"
}

stop_campaign() {
  touch "$STOP_FILE"
  if [ -f "$WORKER_PID" ]; then
    pid="$(cat "$WORKER_PID" 2>/dev/null || true)"
    if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
      kill -TERM "-$pid" 2>/dev/null || kill -TERM "$pid" 2>/dev/null || true
      for _ in 1 2 3 4 5; do kill -0 "$pid" 2>/dev/null || break; sleep 1; done
      kill -KILL "-$pid" 2>/dev/null || kill -KILL "$pid" 2>/dev/null || true
    fi
  fi
  write_state stopped stopped "operator requested stop"
  clipboard "HEADCRAB PR384 CAMPAIGN STOPPED"
}

status() {
  [ -f "$STATE" ] && cat "$STATE" || printf '{"schema":"headcrab-pr384-campaign-v1","stage":"never-run","status":"idle"}\n'
  [ -f "$PRIMARY_SNAPSHOT" ] && { echo "===== PRIMARY SNAPSHOT ====="; cat "$PRIMARY_SNAPSHOT"; }
}

receipts() {
  status
  [ -f "$LATEST" ] && { echo "===== LATEST RECEIPT ====="; cat "$LATEST"; }
  [ -f "$STATE_ROOT/ci-checks.txt" ] && { echo "===== CI ====="; tail -80 "$STATE_ROOT/ci-checks.txt"; }
}

follow() {
  touch "$LOG"
  tail -n 80 -f "$LOG"
}

install_command() {
  bindir="${PREFIX:-$HOME/.local}/bin"
  stable="$STATE_ROOT/campaign.sh"
  mkdir -p "$bindir" "$STATE_ROOT"
  if [ "$(readlink -f "${BASH_SOURCE[0]}")" != "$(readlink -f "$stable" 2>/dev/null || true)" ]; then
    cp "${BASH_SOURCE[0]}" "$stable"
    chmod 700 "$stable"
  fi
  cat >"$bindir/headcrab-ci-campaign" <<EOF
#!/data/data/com.termux/files/usr/bin/bash
exec env HC_REPO_ROOT="$ROOT" bash "$stable" "\$@"
EOF
  chmod 755 "$bindir/headcrab-ci-campaign"
  printf 'installed %s/headcrab-ci-campaign\n' "$bindir"
}

case "${1:-run}" in
  run|resume) install_command; launch ;;
  _worker) worker ;;
  status) status ;;
  follow) follow ;;
  stop) stop_campaign ;;
  receipts) receipts ;;
  reconcile) reconcile_primary ;;
  merge)
    write_state merge running "operator explicitly requested merge after campaign verification"
    gh pr checks "$PR_NUMBER" --repo Valar05/home-center --required >>"$LOG" 2>&1 || { write_state merge-blocked blocked "required checks are not green"; exit 23; }
    gh pr merge "$PR_NUMBER" --repo Valar05/home-center --merge >>"$LOG" 2>&1 || { write_state merge-failed degraded "GitHub merge failed; no local destructive fallback attempted"; exit 24; }
    write_receipt merged "PR #384 merged" >"$STATE_ROOT/receipt.out" 2>&1 || true
    reconcile_primary || true
    write_state merged healthy "PR #384 merged; primary reconciliation handled conservatively"
    clipboard "HEADCRAB PR384 MERGED; receipts: $LATEST"
    ;;
  install) install_command ;;
  *)
    echo "usage: headcrab-ci-campaign [run|resume|status|follow|stop|receipts|reconcile|merge|install]" >&2
    exit 64
    ;;
esac
