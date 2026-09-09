#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

# FORTRESS SCRIPT CAMPAIGN 01 — THE HOLE
# One invocation starts or resumes a persistent phone-local coding campaign.
# Saint Andrew is load-bearing: mine every useful delta, preserve it, and keep the
# campaign alive until the phone artifact is actually delivered or a real boundary exists.

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
STATE_ROOT="${HC_CAMPAIGN_STATE_ROOT:-$HOME/.local/state/home-center/script-campaigns}"
CAMPAIGN="hole-button"
STATE="$STATE_ROOT/$CAMPAIGN"
WORKTREE="${HC_HOLE_WORKTREE:-$HOME/.local/share/home-center/script-campaigns/$CAMPAIGN/worktree}"
SESSION="hc-hole-campaign"
REMOTE_BRANCH="fortress/hole-button"
MISSION="$STATE/mission.txt"
LOG="$STATE/campaign.log"
RECEIPT="$STATE/receipt.json"
EXIT_FILE="$STATE/worker.exit"
RUNNER="$STATE/runner.sh"

mkdir -p "$STATE" "$(dirname "$WORKTREE")"

say() { printf '[hole] %s\n' "$*"; }
fail() { printf '[hole] BLOCKED: %s\n' "$*" >&2; exit 2; }
need() { command -v "$1" >/dev/null 2>&1 || fail "$1 missing; no substitute lane selected"; }

need git
need python3
need tmux

git -C "$ROOT" rev-parse --is-inside-work-tree >/dev/null 2>&1 || fail "$ROOT is not a git checkout"
[ -n "$(git -C "$ROOT" remote get-url origin 2>/dev/null || true)" ] || fail "origin remote missing"

git -C "$ROOT" fetch origin "$REMOTE_BRANCH" --quiet || fail "cannot fetch origin/$REMOTE_BRANCH"

if [ ! -e "$WORKTREE/.git" ]; then
  if [ -e "$WORKTREE" ] && [ -n "$(find "$WORKTREE" -mindepth 1 -maxdepth 1 -print -quit 2>/dev/null)" ]; then
    fail "campaign worktree path exists and is not an attached git worktree: $WORKTREE"
  fi
  rm -rf "$WORKTREE"
  git -C "$ROOT" worktree add --detach "$WORKTREE" "origin/$REMOTE_BRANCH"
else
  git -C "$WORKTREE" fetch origin "$REMOTE_BRANCH" --quiet || true
  if [ -z "$(git -C "$WORKTREE" status --porcelain)" ]; then
    git -C "$WORKTREE" reset --hard "origin/$REMOTE_BRANCH" >/dev/null
  fi
fi

cat > "$MISSION" <<'MISSION_EOF'
FORTRESS SCRIPT CAMPAIGN 01 — THE HOLE

COMMISSION
Deliver exactly one visible Hole button in the existing Home Center Android phone overlay. Pressing it must immediately produce bounded accessible delight. Repeated presses must remain worth pressing. It must survive restart. It must never become homework.

AUTHORIZED LANE
Work only in the existing Valar05/home-center repository/worktree and the existing phone-local Adam/Codex-shaped worker/runtime. Do not substitute another app, dashboard, desktop-only surface, web mockup, scheduler, or chat-only artifact.

EXECUTION LAW
You are not here to explain what you might do. Inspect, edit, build, test, and when authority exists deploy and canary. Keep working through recoverable failures. If blocked, exhaust authorized existing routes first. Only stop at a genuine external/authority/safety boundary or after evidence-backed delivery.

SAINT ANDREW — LOAD-BEARING
After every material discovery/change/test/failure, mine the delta for reusable value. Preserve useful findings in repository-backed docs/receipts/tests/code rather than transient narration. Merge duplicates. Convert repeated failure classes into deterministic checks. Do not let mining delay the primary artifact.

JOY LAW
Every campaign pass must produce both useful progress and at least one bounded joy mutation causally tied to the Hole. Noodle Queen rejects stale/generic/consolation garbage. She-Ra attacks assumptions that threaten the commission. Ares destroys mediocrity when spectacle helps. Punnett preserves traits that survive user feedback. Hatred for waste and love for the artifact are both load-bearing.

CURRENT PREY
1. Inspect android/operator-overlay/app/src/main/java/com/homecenter/operatoroverlay/OperatorOverlayService.java and related state/provider/tests.
2. Add one Hole affordance without creating a new operator-facing mode tree.
3. Implement a deterministic local delight source first; it must work offline and have accessible text/announcement. Variation/state must prevent immediate staleness.
4. Add/extend tests for Hole selection/state/persistence where project-native testing allows.
5. Build using existing phone build tooling, preferring tools/build_operator_overlay_termux.sh where appropriate.
6. If the existing Shizuku/rish install lane is available, deploy through existing recovery/deploy tooling and verify on the actual phone. Never uninstall a working package merely to bypass signer mismatch.
7. Record exact evidence and exact boundary. Repository existence is not delivery.

ACCEPTANCE
NOT DELIVERED until the physical phone overlay contains the Hole button and a real press produces an accessible delight. Repeated presses produce non-identical/non-stale output. Restart preserves availability. Failures are visible and do not break the Hole. Ordinary use requires no shell transport.

DO NOT STOP BECAUSE
- code exists
- tests pass
- an APK exists
- a branch exists
- a plan exists
- a receipt exists
- you are tired of the task
MISSION_EOF

cat > "$RUNNER" <<'RUNNER_EOF'
#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
WORKTREE="$1"
MISSION="$2"
LOG="$3"
RECEIPT="$4"
EXIT_FILE="$5"
ROOT="$6"
cd "$WORKTREE"
start="$(date +%s)"
rm -f "$EXIT_FILE"
{
  echo "=== HOLE CAMPAIGN START $(date -Iseconds) ==="
  echo "worktree=$WORKTREE"
  echo "head=$(git rev-parse HEAD)"
  echo "mission=$MISSION"
} >> "$LOG"

set +e
if command -v adam >/dev/null 2>&1; then
  adam "$(cat "$MISSION")" >> "$LOG" 2>&1
  rc=$?
elif [ -f "$ROOT/tools/adam_venice_reviewed.py" ]; then
  python3 "$ROOT/tools/adam_venice_reviewed.py" "$(cat "$MISSION")" >> "$LOG" 2>&1
  rc=$?
else
  echo "BLOCKED: no phone-local Adam entrypoint found" >> "$LOG"
  rc=127
fi
set -e
printf '%s\n' "$rc" > "$EXIT_FILE"
end="$(date +%s)"
python3 - "$RECEIPT" "$WORKTREE" "$MISSION" "$LOG" "$rc" "$start" "$end" <<'PY'
import json,sys,time,subprocess,hashlib
receipt,worktree,mission,log,rc,start,end=sys.argv[1:]
def run(*args):
    p=subprocess.run(args,cwd=worktree,text=True,capture_output=True)
    return p.returncode,(p.stdout+p.stderr).strip()
_,head=run('git','rev-parse','HEAD')
_,status=run('git','status','--short')
_,diff=run('git','diff','--no-ext-diff')
obj={
  'schema':'fortress-script-campaign-v1',
  'campaign':'hole-button',
  'worker':'phone-local-adam-venice-reviewed',
  'startedAtEpoch':int(start),
  'endedAtEpoch':int(end),
  'exitCode':int(rc),
  'worktree':worktree,
  'missionPath':mission,
  'logPath':log,
  'headCommit':head,
  'gitStatus':status[-12000:],
  'diffSha256':hashlib.sha256(diff.encode()).hexdigest(),
  'diffBytes':len(diff.encode()),
  'terminalState':'worker_exited',
  'delivered':False,
  'note':'Worker exit is not acceptance. Physical phone Hole evidence is still required.'
}
open(receipt,'w',encoding='utf-8').write(json.dumps(obj,indent=2,sort_keys=True)+'\n')
print(json.dumps(obj,indent=2,sort_keys=True))
PY
RUNNER_EOF
chmod +x "$RUNNER"

if tmux has-session -t "$SESSION" 2>/dev/null; then
  say "campaign already alive session=$SESSION"
else
  tmux new-session -d -s "$SESSION" "$RUNNER '$WORKTREE' '$MISSION' '$LOG' '$RECEIPT' '$EXIT_FILE' '$ROOT'"
  say "campaign launched session=$SESSION"
fi

python3 - "$STATE" "$WORKTREE" "$SESSION" "$MISSION" "$LOG" "$RECEIPT" <<'PY'
import json,sys,subprocess,time,os
state,worktree,session,mission,log,receipt=sys.argv[1:]
p=subprocess.run(['tmux','has-session','-t',session],capture_output=True)
status=subprocess.run(['git','status','-sb'],cwd=worktree,text=True,capture_output=True)
obj={
 'schema':'fortress-script-campaign-launch-v1',
 'campaign':'hole-button',
 'launchedAtEpoch':int(time.time()),
 'tmuxSession':session,
 'tmuxAlive':p.returncode==0,
 'worktree':worktree,
 'missionPath':mission,
 'logPath':log,
 'receiptPath':receipt,
 'gitStatus':(status.stdout+status.stderr).strip(),
 'joy':'The Hole is now hunting its own implementation.',
 'nextHumanAction':'none; inspect log/receipt only when desired'
}
path=os.path.join(state,'launch.json')
open(path,'w',encoding='utf-8').write(json.dumps(obj,indent=2,sort_keys=True)+'\n')
print(json.dumps(obj,indent=2,sort_keys=True))
PY

say "tail: tmux attach -t $SESSION"
say "receipt: $RECEIPT"
say "log: $LOG"
