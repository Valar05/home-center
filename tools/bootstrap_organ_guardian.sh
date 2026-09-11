#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
umask 077

WORKSPACE=/storage/emulated/0/Documents/GodotProjects
ORGAN="$WORKSPACE/organ"
ACTIVE="$ORGAN/.organ-runtime/active/organ"
EXPECTED_ACTIVE_SHA=ee40432c8e96eb23a6fa8b5ddb686be6292a4514407bdd0b10a91e876ee88000
STATE="$HOME/.local/state/organ-guardian-bootstrap"
MISSION="$STATE/active-slot-bootstrap.mission.json"
PLAN="$STATE/active-slot-bootstrap.plan.json"
WATCHER="$STATE/guardian-watcher.py"
mkdir -p "$STATE"

notify() {
  if command -v termux-notification >/dev/null 2>&1; then
    termux-notification --id organ-guardian-bootstrap --title "$1" --content "$2" >/dev/null 2>&1 || true
  fi
}
die() {
  printf 'BLOCKED: %s\n' "$*" >&2
  notify 'Organ Guardian BLOCKED' "$*"
  exit 2
}

command -v python3 >/dev/null 2>&1 || die 'python3 missing'
command -v git >/dev/null 2>&1 || die 'git missing'
[ -d "$ORGAN/.git" ] || die "Organ checkout missing: $ORGAN"
[ -f "$ACTIVE" ] || die 'active Organ slot missing'

actual_active_sha="$(sha256sum "$ACTIVE" | awk '{print $1}')"
[ "$actual_active_sha" = "$EXPECTED_ACTIVE_SHA" ] || die "active Organ hash mismatch: $actual_active_sha"
python3 "$ACTIVE" selftest | tee "$STATE/active-selftest.json" | grep -q '"ok": true' || die 'active Organ v3 selftest failed'

cd "$ORGAN"
[ -z "$(git status --porcelain -- change-ui tests/test_change_ui.py)" ] || die 'Organ bootstrap-owned paths are already dirty'

# Reconcile only the safe case automatically: local behind with no unique local commits.
# Local-ahead/diverged history is preserved and used as the phone bootstrap base; it is never reset or force-pushed.
SYNCABLE=0
REMOTE_BASE=''
if git fetch --quiet origin master; then
  LOCAL_HEAD="$(git rev-parse HEAD)"
  REMOTE_HEAD="$(git rev-parse origin/master)"
  counts="$(git rev-list --left-right --count HEAD...origin/master)"
  LOCAL_AHEAD="${counts%%[[:space:]]*}"
  REMOTE_AHEAD="${counts##*[[:space:]]}"
  if [ "$LOCAL_AHEAD" = 0 ] && [ "$REMOTE_AHEAD" -gt 0 ]; then
    git merge --ff-only origin/master || die 'safe fast-forward to origin/master failed'
    LOCAL_HEAD="$(git rev-parse HEAD)"
  fi
  REMOTE_BASE="$(git rev-parse origin/master)"
  if [ "$(git rev-parse HEAD)" = "$REMOTE_BASE" ]; then
    SYNCABLE=1
  fi
  printf '{"local_head":"%s","origin_master":"%s","local_ahead":%s,"remote_ahead":%s,"syncable":%s}\n' \
    "$(git rev-parse HEAD)" "$REMOTE_BASE" "$LOCAL_AHEAD" "$REMOTE_AHEAD" "$SYNCABLE" > "$STATE/git-reconciliation.json"
else
  printf '{"syncable":0,"state":"FETCH_UNAVAILABLE"}\n' > "$STATE/git-reconciliation.json"
fi

# The generated shell currently validates blocked v4 instead of the verified active slot.
# Repair exactly that one bootstrap defect through active v3's own sealed mission/apply path.
if grep -Fq "['python3','organ','selftest']" change-ui; then
  python3 - "$WORKSPACE" "$MISSION" <<'PY'
import base64, hashlib, json, sys
from pathlib import Path
workspace=Path(sys.argv[1])
out=Path(sys.argv[2])
path=workspace/'organ'/'change-ui'
data=path.read_bytes()
old=b"['python3','organ','selftest']"
new=b"['python3','.organ-runtime/active/organ','selftest']"
if data.count(old)!=1:
    raise SystemExit('BOOTSTRAP_REPLACE_COUNT')
digest=hashlib.sha256(data).hexdigest()
mission={
  'schema':'organ-mission-v1',
  'id':'organ-active-slot-selftest-bootstrap-v1',
  'workspace_root':str(workspace),
  'state_root':'organ/.organ-state',
  'authority':{
    'plan_hash':'dc568497be7f525663e41ffe86f8fcf6b0b8adf697e7d459e1ebbfbce233d1a1',
    'amendment_hash':'5e4953f1945dc783ef50c117d1c62afd8436ee39304c43ce836e09e368d295cf',
    'seed_hash':'902a0fa836b8a3dc6a73ab8fcdd2aea7d84dabd9a65013b282072361aad19354',
  },
  'files':[{
    'path':'organ/change-ui',
    'expected_before':digest,
    'source':{'kind':'file','path':'organ/change-ui','sha256':digest},
    'transforms':[{
      'kind':'replace-exact',
      'old_b64':base64.b64encode(old).decode(),
      'new_b64':base64.b64encode(new).decode(),
      'count':1,
    }],
  }],
  'performance':{
    'predicted_elapsed_ms':20,
    'predicted_input_tokens':None,
    'predicted_output_tokens':None,
    'soundness':{'active_slot':5,'fail_closed':5,'sealed_apply':5},
  },
}
out.write_text(json.dumps(mission,indent=2,sort_keys=True)+'\n')
PY
  python3 "$ACTIVE" plan "$MISSION" --out "$PLAN" | tee "$STATE/bootstrap-plan-result.json"
  python3 "$ACTIVE" apply "$PLAN" | tee "$STATE/bootstrap-apply-result.json"
fi

grep -Fq "['python3','.organ-runtime/active/organ','selftest']" change-ui || die 'active-slot validation repair did not land'
python3 -c "from pathlib import Path; compile(Path('change-ui').read_text(),'change-ui','exec')" || die 'change-ui compile failed after bootstrap repair'
python3 "$ACTIVE" selftest | grep -q '"ok": true' || die 'active slot failed after bootstrap repair'
git diff --check || die 'bootstrap repair has whitespace errors'

# Commit only the exact bootstrap code mutation. Runtime receipts remain runtime evidence, not swept into source history.
git add -- change-ui
if ! git diff --cached --quiet; then
  git -c user.name='Organ Bootstrap' -c user.email='organ-bootstrap@localhost' commit -m 'bootstrap: validate active Organ slot' >/dev/null
fi

# Do not trample another live Organ commission.
python3 - "$ORGAN" <<'PY'
import json,sys
from pathlib import Path
p=Path(sys.argv[1])/'.organ-runtime'/'codex-lite-session.json'
if p.is_file():
    v=json.loads(p.read_text())
    if v.get('active') or v.get('pending'):
        raise SystemExit('EXISTING_ORGAN_WORK')
PY

REQUEST=$(cat <<'EOF'
Change exactly change-ui and tests/test_change_ui.py. Build Guardian admission controller v1 as a resident deterministic Organ boundary. This is not a mania detector and not a conversational safety prompt. It consumes typed machine facts and must be impossible to authorize by metaphor, sentiment, persuasion, or free-form AI prose. Add a strict typed guardian action contract and deterministic decisions ALLOW, REQUIRE_PHYSICAL, REQUIRE_SCREENSHOT, COOLDOWN, or DENY. High-impact classes include external communication, purchase/spending, destructive deletion, account/security changes, permission changes, substance-sensitive actions, irreversible actions, and unknown external side effects. Low-impact reversible local work may remain ALLOW. Physical approval must be a device-local artifact, never synthesized from chat text, and must bind to the exact canonical action hash, target, mandatory before-screenshot SHA-256, nonce, and expiry. Missing, stale, corrupt, overly broad, replayed, or mismatched approval must fail closed. Important/high-impact screen actions require a real BEFORE screenshot before approval and a real AFTER screenshot before successful receipt; screenshot capture failure must fail closed. Use local device mechanisms only; rish/Shizuku may be used narrowly for Android screenshot privilege when required, but must not become authority. Store runtime guardian state owner-private under Termux internal storage, not shared storage. Add machine-readable --guardian-status and --guardian-selftest entry points for future ChatGPT/Home Center callers while keeping AI text non-authoritative. --guardian-status must emit one JSON object with schema organ-guardian-status-v1 and ok=true only when the deterministic Guardian runtime is ready. --guardian-selftest must execute deterministic negative controls for prose authorization, replay, target/action/screenshot mismatch, missing evidence, expiry, and identical-facts determinism, and emit one JSON object with schema organ-guardian-selftest-v1 and ok=true only when all controls pass. Add regression tests proving identical typed facts produce identical decisions regardless of surrounding metaphor, that plain yes/go ahead text cannot create physical approval, that approval cannot be replayed for another target/action/screenshot, and that missing evidence fails closed. Preserve the blocked v4 authority-key rotation; do not fabricate or weaken its key requirement. When done, existing Organ behavior must still pass its project-native tests and the Guardian contract tests must pass.
EOF
)
CLARIFICATION=$(cat <<'EOF'
All existing Organ planning, confirmation, memory, image, web, supervisor, recovery, promotion, and fail-closed behavior must remain unchanged unless an operation explicitly enters the new typed Guardian boundary. Keep the verified active v3 slot as bootstrap authority and do not promote, rewrite, bypass, or weaken candidate v4. Guardian decisions come only from typed action facts plus local device evidence. Free-form prose, character roleplay, emotional state, model confidence, and inferred mania are never permission inputs. No cloud dependency and no parallel agent framework. Success is visible when --guardian-status and --guardian-selftest both return ok=true on this phone after promotion.
EOF
)

python3 "$ORGAN/change-ui" --project organ "$REQUEST"
python3 "$ORGAN/change-ui" --project organ "$CLARIFICATION"
python3 "$ORGAN/change-ui" --project organ yes

JOB="$(cat "$ORGAN/.organ-runtime/latest-change-job" 2>/dev/null || true)"
[ -n "$JOB" ] || die 'Guardian work did not create a change job'

cat > "$WATCHER" <<'PY'
#!/usr/bin/env python3
import json, subprocess, sys, time
from pathlib import Path
repo=Path(sys.argv[1]); job=sys.argv[2]; syncable=sys.argv[3]=='1'; remote_base=sys.argv[4]
record_path=repo/'.organ-runtime'/'change-jobs'/(job+'.json')
state_dir=Path.home()/'.local/state'/'organ-guardian-bootstrap'
result_path=state_dir/'durable-result.json'
terminal={'BLOCKED_HUMAN_REQUIRED','BLOCKED_MALFORMED_RESULT','BLOCKED_HOST_UNREACHABLE','CHECKPOINTED','FAILED','CANCELLED','BLOCKED','REJECT'}
def notify(title,content):
    subprocess.run(['termux-notification','--id','organ-guardian-bootstrap','--title',title,'--content',content],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
def finish(obj,code):
    state_dir.mkdir(parents=True,exist_ok=True)
    result_path.write_text(json.dumps(obj,indent=2,sort_keys=True)+'\n')
    raise SystemExit(code)
def json_cmd(*argv):
    p=subprocess.run(list(argv),cwd=repo,text=True,capture_output=True,timeout=120)
    if p.returncode: raise RuntimeError((p.stderr or p.stdout)[-2000:] or 'command failed')
    value=json.loads(p.stdout.strip())
    if value.get('ok') is not True: raise RuntimeError(json.dumps(value,sort_keys=True))
    return value
for _ in range(12*60*60//5):
    try:r=json.loads(record_path.read_text())
    except Exception:
        time.sleep(5); continue
    state=r.get('state','UNKNOWN')
    if state=='PROMOTED':
        candidate=r.get('candidate_commit','')
        if not candidate:
            notify('Organ Guardian BLOCKED','promoted record lacks candidate commit');finish({'ok':False,'state':'BLOCKED_NO_COMMIT','job':job},2)
        try:
            status=json_cmd('python3','change-ui','--guardian-status')
            selftest=json_cmd('python3','change-ui','--guardian-selftest')
        except Exception as exc:
            notify('Organ Guardian BLOCKED','runtime acceptance failed')
            finish({'ok':False,'state':'BLOCKED_RUNTIME_ACCEPTANCE','job':job,'commit':candidate,'error':str(exc)},2)
        remote_state='NOT_REQUESTED_DIVERGED_BASE'
        if syncable:
            fetch=subprocess.run(['git','fetch','--quiet','origin','master'],cwd=repo,text=True,capture_output=True)
            if fetch.returncode==0:
                current_remote=subprocess.run(['git','rev-parse','origin/master'],cwd=repo,text=True,capture_output=True,check=True).stdout.strip()
                if current_remote==remote_base:
                    push=subprocess.run(['git','push','origin',candidate+':refs/heads/master'],cwd=repo,text=True,capture_output=True)
                    remote_state='SYNCED_MASTER' if push.returncode==0 else 'PUSH_FAILED'
                else:
                    remote_state='REMOTE_ADVANCED_NO_FORCE_PUSH'
            else:
                remote_state='FETCH_FAILED'
        obj={'ok':True,'state':'PHONE_DURABLE','job':job,'commit':candidate,'guardian_status':status,'guardian_selftest':selftest,'remote_state':remote_state}
        notify('Organ Guardian READY','Phone runtime accepted. '+remote_state)
        finish(obj,0)
    if state in terminal:
        notify('Organ Guardian '+state,job)
        finish({'ok':False,'state':state,'job':job,'error':r.get('error') or r.get('remote',{}).get('error')},2)
    time.sleep(5)
notify('Organ Guardian BLOCKED','watcher timeout')
finish({'ok':False,'state':'WATCH_TIMEOUT','job':job},2)
PY
chmod 700 "$WATCHER"
nohup python3 "$WATCHER" "$ORGAN" "$JOB" "$SYNCABLE" "$REMOTE_BASE" >"$STATE/watcher.log" 2>&1 </dev/null &

for _ in $(seq 1 20); do
  record="$ORGAN/.organ-runtime/change-jobs/$JOB.json"
  supervisor="$ORGAN/.organ-runtime/supervisors/$JOB.json"
  if [ -f "$supervisor" ]; then
    pid="$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["pid"])' "$supervisor" 2>/dev/null || true)"
    if [ -n "$pid" ] && [ -d "/proc/$pid" ]; then
      state="$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1])).get("state","UNKNOWN"))' "$record" 2>/dev/null || true)"
      printf 'WIGGLING: Guardian job %s state=%s supervisor=%s\n' "$JOB" "$state" "$pid"
      printf 'You may leave Termux. Completion or a real blocker will produce a notification.\n'
      notify 'Organ Guardian WIGGLING' "$JOB $state"
      exit 0
    fi
  fi
  sleep 1
done

die "Guardian job $JOB exists but its detached supervisor did not become observable"
