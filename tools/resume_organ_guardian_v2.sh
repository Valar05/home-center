#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
umask 077

WORKSPACE=/storage/emulated/0/Documents/GodotProjects
ORGAN="$WORKSPACE/organ"
ACTIVE="$ORGAN/.organ-runtime/active/organ"
EXPECTED_ACTIVE_SHA=ee40432c8e96eb23a6fa8b5ddb686be6292a4514407bdd0b10a91e876ee88000
STATE="$HOME/.local/state/organ-guardian-bootstrap"
WATCHER="$STATE/guardian-watcher-v2.py"
mkdir -p "$STATE"

notify() {
  if command -v termux-notification >/dev/null 2>&1; then
    termux-notification --id organ-guardian-bootstrap --title "$1" --content "$2" >/dev/null 2>&1 || true
  fi
}
die() {
  printf 'BLOCKED: %s\n' "$*" >&2
  notify 'Guardian BLOCKED' "$*"
  exit 2
}

[ -d "$ORGAN/.git" ] || die "checkout missing: $ORGAN"
[ -f "$ACTIVE" ] || die 'active runtime slot missing'
actual="$(sha256sum "$ACTIVE" | awk '{print $1}')"
[ "$actual" = "$EXPECTED_ACTIVE_SHA" ] || die "active slot hash mismatch: $actual"
python3 "$ACTIVE" selftest | grep -q '"ok": true' || die 'active v3 selftest failed'
cd "$ORGAN"

grep -Fq "['python3','.organ-runtime/active/organ','selftest']" change-ui || die 'active-slot bootstrap repair is missing'
[ -z "$(git status --porcelain -- change-ui tests/test_change_ui.py)" ] || die 'commissioned source paths are already dirty'

git fetch --quiet origin master || die 'cannot refresh origin/master'
REMOTE_BASE="$(git rev-parse origin/master)"
if ! git merge-base --is-ancestor "$REMOTE_BASE" HEAD; then
  die 'phone history and origin/master truly diverged; no reset or force-push attempted'
fi

# Clear only stale Guardian-local session state from the earlier failed attempt.
python3 - "$ORGAN" <<'PY'
import json,sys
from pathlib import Path
root=Path(sys.argv[1]); session=root/'.organ-runtime'/'codex-lite-session.json'
if not session.is_file(): raise SystemExit(0)
v=json.loads(session.read_text())
active=v.get('active') or {}; pending=v.get('pending') or {}
items=[x for x in (active,pending) if x]
if not items: raise SystemExit(0)
for item in items:
    if item.get('kind')!='intent':
        raise SystemExit('UNRELATED_WORK_ACTIVE')
    ident=item.get('id')
    p=root/'.organ-runtime'/'intents'/(str(ident)+'.json')
    try:r=json.loads(p.read_text())
    except Exception: raise SystemExit('UNREADABLE_ACTIVE_INTENT')
    if 'Guardian admission controller v1' not in r.get('request',''):
        raise SystemExit('UNRELATED_WORK_ACTIVE')
# session points only at the stale Guardian intent, so clear through the normal UI contract.
PY
session_state="$(python3 - "$ORGAN" <<'PY'
import json,sys
from pathlib import Path
p=Path(sys.argv[1])/'.organ-runtime'/'codex-lite-session.json'
if not p.is_file(): print('CLEAR'); raise SystemExit
v=json.loads(p.read_text()); print('BUSY' if (v.get('active') or v.get('pending')) else 'CLEAR')
PY
)"
if [ "$session_state" = BUSY ]; then
  python3 "$ORGAN/change-ui" --project organ cancel >/dev/null || die 'could not clear stale Guardian intent'
fi

# Deliberately avoid the project basename in request prose because the current router
# treats that basename as ambiguous with tracked runtime slot files.
REQUEST=$(cat <<'EOF'
Change exactly change-ui and tests/test_change_ui.py. Implement Guardian admission controller v1 as a resident deterministic admission boundary. Consume typed machine facts only. Free-form prose, metaphor, persuasion, emotion, model confidence, and plain yes or go-ahead text must never create permission. Add strict deterministic decisions ALLOW, REQUIRE_PHYSICAL, REQUIRE_SCREENSHOT, COOLDOWN, and DENY. Consequential classes include external communication, purchase or spending, destructive deletion, account or security changes, permission changes, substance-sensitive actions, irreversible actions, and unknown external side effects. Reversible local work may remain ALLOW. Physical approval must be a device-local artifact bound to the exact canonical action hash, exact target, mandatory before-screenshot SHA-256, nonce, and expiry. Missing, stale, corrupt, broad, replayed, expired, or mismatched approval must fail closed. Consequential screen actions require a real BEFORE screenshot before approval and a real AFTER screenshot before successful receipt; screenshot failure must fail closed. Use local device mechanisms only; rish or Shizuku may provide Android screenshot privilege when genuinely required but must never become authority. Store Guardian runtime state owner-private under Termux internal storage. Add machine-readable --guardian-status and --guardian-selftest entry points. --guardian-status emits one JSON object with schema organ-guardian-status-v1 and ok=true only when the deterministic runtime is ready. --guardian-selftest executes negative controls for prose authorization, replay, action/target/screenshot mismatch, missing evidence, expiry, and identical-facts determinism, and emits schema organ-guardian-selftest-v1 with ok=true only when all controls pass. Add regression tests for those guarantees. Preserve the blocked v4 authority-key rotation exactly; do not fabricate or weaken its key requirement.
EOF
)
CLARIFICATION=$(cat <<'EOF'
Existing planning, confirmation, memory, web, supervisor, recovery, promotion, and fail-closed behavior must remain unchanged unless an operation explicitly enters the new typed Guardian boundary. Keep the verified active v3 slot as bootstrap authority and leave candidate v4 blocked. Device evidence and typed action facts are the only permission inputs. No cloud dependency and no parallel agent framework. Success is visible only when --guardian-status and --guardian-selftest both return ok=true on this phone after promotion.
EOF
)

python3 "$ORGAN/change-ui" --project organ "$REQUEST"
python3 "$ORGAN/change-ui" --project organ "$CLARIFICATION"
python3 "$ORGAN/change-ui" --project organ apply

JOB="$(cat "$ORGAN/.organ-runtime/latest-change-job" 2>/dev/null || true)"
[ -n "$JOB" ] || die 'no Guardian change job was created'

cat > "$WATCHER" <<'PY'
#!/usr/bin/env python3
import json, shutil, subprocess, sys, time
from pathlib import Path
repo=Path(sys.argv[1]); job=sys.argv[2]; remote_base=sys.argv[3]
record_path=repo/'.organ-runtime'/'change-jobs'/(job+'.json')
state_dir=Path.home()/'.local/state'/'organ-guardian-bootstrap'
result_path=state_dir/'durable-result.json'
terminal={'BLOCKED_HUMAN_REQUIRED','BLOCKED_MALFORMED_RESULT','BLOCKED_HOST_UNREACHABLE','CHECKPOINTED','FAILED','CANCELLED','BLOCKED','REJECT'}
def notify(title,content):
    if shutil.which('termux-notification'):
        subprocess.run(['termux-notification','--id','organ-guardian-bootstrap','--title',title,'--content',content],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
def finish(obj,code):
    state_dir.mkdir(parents=True,exist_ok=True)
    result_path.write_text(json.dumps(obj,indent=2,sort_keys=True)+'\n')
    raise SystemExit(code)
def json_cmd(*argv):
    p=subprocess.run(list(argv),cwd=repo,text=True,capture_output=True,timeout=180)
    if p.returncode:
        raise RuntimeError((p.stderr or p.stdout)[-2000:] or 'command failed')
    value=json.loads(p.stdout.strip())
    if value.get('ok') is not True:
        raise RuntimeError(json.dumps(value,sort_keys=True))
    return value
for _ in range(12*60*60//5):
    try:r=json.loads(record_path.read_text())
    except Exception:
        time.sleep(5); continue
    state=r.get('state','UNKNOWN')
    if state=='PROMOTED':
        candidate=r.get('candidate_commit','')
        if not candidate:
            notify('Guardian BLOCKED','promoted record lacks candidate commit')
            finish({'ok':False,'state':'BLOCKED_NO_COMMIT','job':job},2)
        try:
            status=json_cmd('python3','change-ui','--guardian-status')
            selftest=json_cmd('python3','change-ui','--guardian-selftest')
        except Exception as exc:
            notify('Guardian BLOCKED','runtime acceptance failed')
            finish({'ok':False,'state':'BLOCKED_RUNTIME_ACCEPTANCE','job':job,'commit':candidate,'error':str(exc)},2)
        fetch=subprocess.run(['git','fetch','--quiet','origin','master'],cwd=repo,text=True,capture_output=True)
        if fetch.returncode:
            notify('Guardian BLOCKED','phone accepted, but remote refresh failed')
            finish({'ok':False,'state':'BLOCKED_REMOTE_FETCH','job':job,'commit':candidate,'guardian_status':status,'guardian_selftest':selftest},2)
        current_remote=subprocess.run(['git','rev-parse','origin/master'],cwd=repo,text=True,capture_output=True,check=True).stdout.strip()
        if current_remote!=remote_base:
            notify('Guardian BLOCKED','phone accepted; remote advanced; no force-push attempted')
            finish({'ok':False,'state':'BLOCKED_REMOTE_ADVANCED','job':job,'commit':candidate,'remote':current_remote,'guardian_status':status,'guardian_selftest':selftest},2)
        ancestor=subprocess.run(['git','merge-base','--is-ancestor',current_remote,candidate],cwd=repo)
        if ancestor.returncode:
            notify('Guardian BLOCKED','candidate is not a fast-forward of origin/master')
            finish({'ok':False,'state':'BLOCKED_NOT_FAST_FORWARD','job':job,'commit':candidate},2)
        push=subprocess.run(['git','push','origin',candidate+':refs/heads/master'],cwd=repo,text=True,capture_output=True)
        if push.returncode:
            notify('Guardian BLOCKED','phone accepted; durable push failed')
            finish({'ok':False,'state':'BLOCKED_PUSH','job':job,'commit':candidate,'error':push.stderr[-1200:],'guardian_status':status,'guardian_selftest':selftest},2)
        obj={'ok':True,'state':'DURABLE','job':job,'commit':candidate,'guardian_status':status,'guardian_selftest':selftest,'remote_state':'SYNCED_MASTER'}
        notify('Guardian READY','Phone accepted and synced to master')
        finish(obj,0)
    if state in terminal:
        notify('Guardian '+state,job)
        finish({'ok':False,'state':state,'job':job,'error':r.get('error') or r.get('remote',{}).get('error')},2)
    time.sleep(5)
notify('Guardian BLOCKED','watcher timeout')
finish({'ok':False,'state':'WATCH_TIMEOUT','job':job},2)
PY
chmod 700 "$WATCHER"
nohup python3 "$WATCHER" "$ORGAN" "$JOB" "$REMOTE_BASE" >"$STATE/watcher-v2.log" 2>&1 </dev/null &

for _ in $(seq 1 20); do
  record="$ORGAN/.organ-runtime/change-jobs/$JOB.json"
  supervisor="$ORGAN/.organ-runtime/supervisors/$JOB.json"
  if [ -f "$supervisor" ]; then
    pid="$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["pid"])' "$supervisor" 2>/dev/null || true)"
    if [ -n "$pid" ] && [ -d "/proc/$pid" ]; then
      state="$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1])).get("state","UNKNOWN"))' "$record" 2>/dev/null || true)"
      printf 'WIGGLING: Guardian job %s state=%s supervisor=%s\n' "$JOB" "$state" "$pid"
      printf 'You may leave Termux. Completion or a real blocker will notify you.\n'
      notify 'Guardian WIGGLING' "$JOB $state"
      exit 0
    fi
  fi
  sleep 1
done

die "job $JOB exists but detached supervision did not become observable"
