#!/usr/bin/env bash
set -euo pipefail

# Terminal DMC campaign.
#
# One operator script installs a persistent, commit-bound game worktree and
# leaves a stable `terminal-dmc` command with install/run/resume/status/follow/
# stop/prove/play/turn/receipts/update/doctor controls.
#
# The campaign never switches or resets Drew's working checkout. Every accepted
# revision is installed as a detached Git worktree under campaign-owned storage.
# Mechanical proof is commit-bound. Human feel remains human-owned.

SCHEMA="terminal-dmc-campaign.v1"
PR_NUMBER="362"
EXPECTED_BRANCH="codex/terminal-dmc-vertical-slice"

STATE_ROOT="${HC_STATE_DIR:-$HOME/.local/state/home-center}/terminal-dmc-campaign"
DATA_ROOT="${HC_DATA_DIR:-$HOME/.local/share/home-center}/terminal-dmc"
REVISIONS="$DATA_ROOT/revisions"
CURRENT="$DATA_ROOT/current"

if [ -n "${PREFIX:-}" ] && [ -d "${PREFIX}/bin" ]; then
  BIN_DIR="${PREFIX}/bin"
else
  BIN_DIR="${HOME}/.local/bin"
fi
BIN="$BIN_DIR/terminal-dmc"

LATEST="$STATE_ROOT/latest.json"
HISTORY="$STATE_ROOT/history.jsonl"
CHECKPOINT="$STATE_ROOT/checkpoint.json"
SOURCE_META="$STATE_ROOT/source.json"
PROOF_RECEIPT="$STATE_ROOT/proof-receipt.json"
PROOF_STDERR="$STATE_ROOT/proof-stderr.log"
WORKER_LOG="$STATE_ROOT/worker.log"
WORKER_PID="$STATE_ROOT/worker.pid"
WORKER_HEARTBEAT="$STATE_ROOT/worker-heartbeat"
PLAY_PID="$STATE_ROOT/play.pid"
CANARY_RECEIPT="$STATE_ROOT/canary.json"
LOCK_DIR="$STATE_ROOT/proof.lock"

SELF_PATH="${BASH_SOURCE[0]}"
SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$SELF_PATH")" && pwd)"
SCRIPT_ROOT="$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)"

mkdir -p "$STATE_ROOT" "$REVISIONS" "$BIN_DIR"

iso_now() {
  python3 - <<'PY'
from datetime import datetime, timezone
print(datetime.now(timezone.utc).isoformat())
PY
}

epoch_now() {
  python3 - <<'PY'
import time
print(int(time.time()))
PY
}

json_receipt() {
  local stage="$1"
  local status="$2"
  local detail="$3"
  local source_commit="${4:-}"
  local pid="${5:-}"
  python3 - "$HISTORY" "$LATEST" "$SCHEMA" "$stage" "$status" "$detail" "$source_commit" "$pid" <<'PY'
import json, os, sys, time
history, latest, schema, stage, status, detail, source_commit, pid = sys.argv[1:]
obj = {
    "schema": schema,
    "at_epoch": int(time.time()),
    "stage": stage,
    "status": status,
    "detail": detail,
}
if source_commit:
    obj["source_commit"] = source_commit
if pid:
    try:
        obj["pid"] = int(pid)
    except ValueError:
        obj["pid"] = pid
os.makedirs(os.path.dirname(history), exist_ok=True)
with open(history, "a", encoding="utf-8") as f:
    f.write(json.dumps(obj, sort_keys=True) + "\n")
tmp = latest + ".tmp"
with open(tmp, "w", encoding="utf-8") as f:
    json.dump(obj, f, indent=2, sort_keys=True)
    f.write("\n")
os.replace(tmp, latest)
print(json.dumps(obj, sort_keys=True))
PY
}

write_checkpoint() {
  local phase="$1"
  local status="$2"
  local next="$3"
  local source_commit="${4:-}"
  python3 - "$CHECKPOINT" "$SCHEMA" "$phase" "$status" "$next" "$source_commit" "$PROOF_RECEIPT" "$BIN" <<'PY'
import json, os, sys, time
path, schema, phase, status, nxt, source_commit, proof, binary = sys.argv[1:]
callable_now = os.path.isfile(binary) and os.access(binary, os.X_OK)
obj = {
    "schema": schema + ".checkpoint",
    "at_epoch": int(time.time()),
    "objective": "Make the ASCII Kinesis / Motion Dungeon learning concrete as a playable original first-person terminal action game.",
    "phase": phase,
    "status": status,
    "next": nxt,
    "capability": {
        "requested": True,
        "implemented": True,
        "tested": status in {"PROOF_PASS", "PLAY_READY", "PLAY_ENDED"},
        "deployed": False,
        "callable": callable_now,
        "delivered": callable_now,
        "accepted": False,
    },
}
if source_commit:
    obj["source_commit"] = source_commit
if os.path.exists(proof):
    obj["proof_receipt"] = proof
tmp = path + ".tmp"
with open(tmp, "w", encoding="utf-8") as f:
    json.dump(obj, f, indent=2, sort_keys=True)
    f.write("\n")
os.replace(tmp, path)
PY
}

need() {
  command -v "$1" >/dev/null 2>&1 || {
    json_receipt "doctor" "BLOCKED" "missing required command: $1"
    echo "BLOCKED: missing required command: $1" >&2
    exit 20
  }
}

source_root() {
  if [ -n "${HC_REPO_ROOT:-}" ] && git -C "$HC_REPO_ROOT" rev-parse --show-toplevel >/dev/null 2>&1; then
    git -C "$HC_REPO_ROOT" rev-parse --show-toplevel
    return
  fi
  if [ -f "$SOURCE_META" ]; then
    local saved
    saved="$(python3 - "$SOURCE_META" <<'PY'
import json, sys
try:
    print(json.load(open(sys.argv[1], encoding="utf-8")).get("operator_repo_root", ""))
except Exception:
    print("")
PY
)"
    if [ -n "$saved" ] && git -C "$saved" rev-parse --show-toplevel >/dev/null 2>&1; then
      git -C "$saved" rev-parse --show-toplevel
      return
    fi
  fi
  if git -C "$SCRIPT_ROOT" rev-parse --show-toplevel >/dev/null 2>&1; then
    git -C "$SCRIPT_ROOT" rev-parse --show-toplevel
    return
  fi
  echo ""
}

required_files_ok() {
  local root="$1"
  local missing=0
  local path
  for path in \
    tools/terminal_dmc.py \
    tools/test_terminal_dmc.py \
    tools/terminal_dmc_prove.py \
    tools/terminal_dmc_campaign.sh \
    docs/TERMINAL_DMC_VERTICAL_SLICE.md
  do
    if [ ! -f "$root/$path" ]; then
      echo "MISSING: $path" >&2
      missing=1
    fi
  done
  [ "$missing" -eq 0 ]
}

current_root() {
  if [ -L "$CURRENT" ] || [ -d "$CURRENT" ]; then
    python3 - "$CURRENT" <<'PY'
import os, sys
print(os.path.realpath(sys.argv[1]))
PY
  fi
}

current_commit() {
  local root
  root="$(current_root)"
  if [ -n "$root" ] && [ -d "$root" ]; then
    git -C "$root" rev-parse HEAD 2>/dev/null || true
  fi
}

proof_status() {
  if [ ! -f "$PROOF_RECEIPT" ]; then
    echo "MISSING"
    return
  fi
  python3 - "$PROOF_RECEIPT" <<'PY'
import json, sys
try:
    print(json.load(open(sys.argv[1], encoding="utf-8")).get("status", "UNKNOWN"))
except Exception:
    print("INVALID")
PY
}

proof_commit() {
  if [ ! -f "$PROOF_RECEIPT" ]; then
    echo ""
    return
  fi
  python3 - "$PROOF_RECEIPT" <<'PY'
import json, sys
try:
    d = json.load(open(sys.argv[1], encoding="utf-8"))
    print((d.get("repository") or {}).get("head_sha", ""))
except Exception:
    print("")
PY
}

pid_alive() {
  local file="$1"
  [ -f "$file" ] || return 1
  local pid
  pid="$(cat "$file" 2>/dev/null || true)"
  [ -n "$pid" ] || return 1
  kill -0 "$pid" 2>/dev/null
}

install_revision() {
  need git
  need python3
  local root
  root="$(source_root)"
  if [ -z "$root" ]; then
    json_receipt "install" "BLOCKED" "authorized Home Center repository root could not be resolved"
    echo "BLOCKED: Home Center repository root could not be resolved." >&2
    exit 21
  fi
  if ! required_files_ok "$root"; then
    json_receipt "install" "BLOCKED" "Terminal DMC campaign files are incomplete in source checkout"
    exit 22
  fi

  local head branch dirty revdir
  head="$(git -C "$root" rev-parse HEAD)"
  branch="$(git -C "$root" branch --show-current || true)"
  dirty="$(git -C "$root" status --porcelain=v1 --untracked-files=normal || true)"
  revdir="$REVISIONS/$head"

  # Never flip the installed `current` pointer out from under an active proof
  # worker, synchronous proof, or interactive game.
  if [ -L "$CURRENT" ] || [ -d "$CURRENT" ]; then
    if pid_alive "$WORKER_PID" || pid_alive "$PLAY_PID" || [ -d "$LOCK_DIR" ]; then
      json_receipt "install" "BLOCKED" "active proof/play owns the installed revision; stop or wait before update" "$(current_commit)"
      return 25
    fi
  fi

  # We never reset, checkout, stash, or clean the operator's working tree.
  # A dirty source checkout is preserved and simply excluded from the installed
  # commit snapshot.
  if [ ! -d "$revdir" ]; then
    git -C "$root" worktree add --detach "$revdir" "$head" >/dev/null
  fi
  if [ "$(git -C "$revdir" rev-parse HEAD)" != "$head" ]; then
    json_receipt "install" "BLOCKED" "campaign-owned revision directory does not match requested commit" "$head"
    exit 23
  fi
  if [ -n "$(git -C "$revdir" status --porcelain=v1 --untracked-files=normal)" ]; then
    json_receipt "install" "BLOCKED" "campaign-owned revision worktree is dirty; preservation boundary" "$head"
    exit 24
  fi

  ln -sfn "$revdir" "$CURRENT"

  python3 - "$SOURCE_META" "$root" "$head" "$branch" "$dirty" "$PR_NUMBER" "$EXPECTED_BRANCH" <<'PY'
import json, os, sys, time
path, root, head, branch, dirty, pr, expected = sys.argv[1:]
obj = {
    "schema": "terminal-dmc-campaign.source.v1",
    "operator_repo_root": root,
    "source_commit": head,
    "source_branch": branch,
    "source_checkout_dirty_preserved": bool(dirty),
    "pr_number": int(pr),
    "expected_branch": expected,
    "installed_at_epoch": int(time.time()),
}
tmp = path + ".tmp"
with open(tmp, "w", encoding="utf-8") as f:
    json.dump(obj, f, indent=2, sort_keys=True)
    f.write("\n")
os.replace(tmp, path)
PY

  cat > "$BIN" <<EOF
#!/usr/bin/env bash
exec bash $(printf '%q' "$CURRENT/tools/terminal_dmc_campaign.sh") "\$@"
EOF
  chmod 755 "$BIN"

  local dirty_note=""
  if [ -n "$dirty" ]; then
    dirty_note="; operator checkout had preserved local edits not included in installed commit"
  fi
  json_receipt "install" "READY" "installed commit-bound Terminal DMC revision${dirty_note}" "$head"
  write_checkpoint "INSTALL" "IMPLEMENTED" "Run canary and mechanical proof." "$head"
  printf 'terminal-dmc installed: %s\n' "$BIN"
  printf 'source commit: %s\n' "$head"
  if [ -n "$branch" ] && [ "$branch" != "$EXPECTED_BRANCH" ]; then
    printf 'NOTE: source branch is %s; expected campaign branch is %s. Commit identity is authoritative.\n' "$branch" "$EXPECTED_BRANCH"
  fi
}

ensure_installed() {
  if [ ! -L "$CURRENT" ] || [ ! -f "$CURRENT/tools/terminal_dmc.py" ]; then
    install_revision
  fi
}

kill_process_group() {
  local pid="$1"
  local grace="${2:-3}"
  python3 - "$pid" "$grace" <<'PY'
import os, signal, sys, time
pid = int(sys.argv[1]); grace = float(sys.argv[2])
try:
    pgid = os.getpgid(pid)
except ProcessLookupError:
    raise SystemExit(0)
try:
    os.killpg(pgid, signal.SIGTERM)
except ProcessLookupError:
    raise SystemExit(0)
deadline = time.time() + grace
while time.time() < deadline:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        raise SystemExit(0)
    time.sleep(0.1)
try:
    os.killpg(pgid, signal.SIGKILL)
except ProcessLookupError:
    pass
PY
}

canary() {
  ensure_installed
  need python3

  local pid
  pid="$(
    python3 - "$STATE_ROOT/canary-worker.log" <<'PY'
import subprocess, sys
log = open(sys.argv[1], "ab", buffering=0)
p = subprocess.Popen(
    [sys.executable, "-c", "import time; time.sleep(120)"],
    stdin=subprocess.DEVNULL,
    stdout=log,
    stderr=log,
    start_new_session=True,
)
print(p.pid)
PY
  )"
  echo "$pid" > "$STATE_ROOT/canary.pid"
  sleep 0.2
  if ! kill -0 "$pid" 2>/dev/null; then
    json_receipt "canary" "FAIL" "isolated canary process did not remain alive" "$(current_commit)"
    return 1
  fi

  # Invoke the stop helper through a fresh script process, proving that a second
  # shell/process can kill the isolated process group.
  bash "$CURRENT/tools/terminal_dmc_campaign.sh" _stop-canary "$pid"
  sleep 0.2
  if kill -0 "$pid" 2>/dev/null; then
    json_receipt "canary" "FAIL" "out-of-band canary stop did not terminate process group" "$(current_commit)"
    return 1
  fi

  # Prove the stable entrypoint can execute independently of the bootstrap shell.
  if ! "$BIN" status --quiet >/dev/null 2>&1; then
    json_receipt "canary" "FAIL" "stable terminal-dmc entrypoint failed status probe" "$(current_commit)"
    return 1
  fi

  python3 - "$CANARY_RECEIPT" "$(current_commit)" "$BIN" <<'PY'
import json, os, sys, time
path, commit, binary = sys.argv[1:]
obj = {
    "schema": "terminal-dmc-campaign.canary.v1",
    "status": "PASS",
    "at_epoch": int(time.time()),
    "source_commit": commit,
    "checks": {
        "stable_entrypoint": True,
        "isolated_process_group": True,
        "out_of_band_stop": True,
        "prompt_transport": "NOT_APPLICABLE_NO_PROSE_PAYLOAD",
    },
    "entrypoint": binary,
}
tmp = path + ".tmp"
with open(tmp, "w", encoding="utf-8") as f:
    json.dump(obj, f, indent=2, sort_keys=True)
    f.write("\n")
os.replace(tmp, path)
PY
  rm -f "$STATE_ROOT/canary.pid"
  json_receipt "canary" "PASS" "stable entrypoint, process isolation, and out-of-band stop proved" "$(current_commit)"
}

run_proof_sync() {
  ensure_installed
  need python3

  local commit run_root
  run_root="$(current_root)"
  commit="$(git -C "$run_root" rev-parse HEAD 2>/dev/null || true)"
  if [ -z "$commit" ]; then
    json_receipt "proof" "BLOCKED" "installed revision has no Git commit identity"
    return 30
  fi

  if ! mkdir "$LOCK_DIR" 2>/dev/null; then
    if pid_alive "$WORKER_PID"; then
      json_receipt "proof" "ALREADY_RUNNING" "proof worker is already active" "$commit" "$(cat "$WORKER_PID")"
      return 0
    fi
    rmdir "$LOCK_DIR" 2>/dev/null || true
    mkdir "$LOCK_DIR"
  fi
  json_receipt "proof" "RUNNING" "executing commit-bound mechanical proof" "$commit"
  write_checkpoint "PROOF" "RUNNING" "Wait for proof completion; do not infer human feel." "$commit"

  local tmp rc
  tmp="$STATE_ROOT/proof-receipt.tmp.$$"
  : > "$PROOF_STDERR"
  set +e
  (
    cd "$run_root"
    PYTHONDONTWRITEBYTECODE=1 python3 -B tools/terminal_dmc_prove.py > "$tmp" 2> "$PROOF_STDERR"
  )
  rc=$?
  set -e

  if ! python3 -m json.tool "$tmp" >/dev/null 2>&1; then
    python3 - "$tmp" "$rc" "$commit" <<'PY'
import json, sys, time
path, rc, commit = sys.argv[1:]
obj = {
    "schema": "terminal-dmc-proof.v1",
    "status": "FAIL",
    "generated_at_epoch": int(time.time()),
    "repository": {"head_sha": commit},
    "blockers": ["PROOF_OUTPUT_NOT_JSON"],
    "runner_exit_code": int(rc),
}
with open(path, "w", encoding="utf-8") as f:
    json.dump(obj, f, indent=2, sort_keys=True)
    f.write("\n")
PY
  fi
  mv "$tmp" "$PROOF_RECEIPT"

  local status receipt_commit
  status="$(proof_status)"
  receipt_commit="$(proof_commit)"
  if [ "$status" = "PASS" ] && [ "$receipt_commit" = "$commit" ] && [ "$rc" -eq 0 ]; then
    json_receipt "proof" "PASS" "mechanical proof passed on installed commit" "$commit"
    write_checkpoint "PROOF" "PROOF_PASS" "Launch interactive play; human feel remains pending." "$commit"
    rmdir "$LOCK_DIR" 2>/dev/null || true
    return 0
  fi

  json_receipt "proof" "FAIL" "mechanical proof failed or receipt commit did not match installed commit" "$commit"
  write_checkpoint "PROOF" "BLOCKED" "Inspect proof receipt and stderr; repair code before claiming runtime proof." "$commit"
  rmdir "$LOCK_DIR" 2>/dev/null || true
  return 31
}

worker_main() {
  ensure_installed
  echo "$$" > "$WORKER_PID"
  trap 'rm -f "$WORKER_PID" "$WORKER_HEARTBEAT"' EXIT INT TERM
  epoch_now > "$WORKER_HEARTBEAT"
  json_receipt "worker" "RUNNING" "background proof worker started" "$(current_commit)" "$$"
  set +e
  run_proof_sync >> "$WORKER_LOG" 2>&1
  local rc=$?
  set -e
  epoch_now > "$WORKER_HEARTBEAT"
  if [ "$rc" -eq 0 ]; then
    json_receipt "worker" "DONE" "background proof worker completed successfully" "$(current_commit)" "$$"
  else
    json_receipt "worker" "BLOCKED" "background proof worker completed with failure" "$(current_commit)" "$$"
  fi
  return "$rc"
}

start_worker() {
  ensure_installed
  if pid_alive "$WORKER_PID"; then
    local pid
    pid="$(cat "$WORKER_PID")"
    json_receipt "worker" "ALREADY_RUNNING" "proof worker already active" "$(current_commit)" "$pid"
    status
    return 0
  fi

  : > "$WORKER_LOG"
  local pid
  pid="$(
    python3 - "$CURRENT/tools/terminal_dmc_campaign.sh" "$WORKER_LOG" <<'PY'
import subprocess, sys
script, log_path = sys.argv[1:]
log = open(log_path, "ab", buffering=0)
p = subprocess.Popen(
    ["bash", script, "_proof-worker"],
    stdin=subprocess.DEVNULL,
    stdout=log,
    stderr=log,
    start_new_session=True,
)
print(p.pid)
PY
  )"
  echo "$pid" > "$WORKER_PID"
  epoch_now > "$WORKER_HEARTBEAT"
  json_receipt "worker" "STARTED" "proof worker launched in isolated process group; operator shell released" "$(current_commit)" "$pid"
  printf 'run=%s phase=proof pid=%s\n' "$(basename "$STATE_ROOT")" "$pid"
  printf 'status: %s status\n' "$BIN"
  printf 'follow: %s follow\n' "$BIN"
  printf 'stop:   %s stop\n' "$BIN"
}

stop_worker() {
  local stopped=0
  if pid_alive "$WORKER_PID"; then
    local pid
    pid="$(cat "$WORKER_PID")"
    kill_process_group "$pid" 3 || true
    stopped=1
    rm -f "$WORKER_PID" "$WORKER_HEARTBEAT"
    json_receipt "stop" "STOPPED" "background worker process group terminated" "$(current_commit)" "$pid"
  fi

  if pid_alive "$PLAY_PID"; then
    local ppid
    ppid="$(cat "$PLAY_PID")"
    kill "$ppid" 2>/dev/null || true
    sleep 0.3
    if kill -0 "$ppid" 2>/dev/null; then
      kill -KILL "$ppid" 2>/dev/null || true
    fi
    stopped=1
    rm -f "$PLAY_PID"
    json_receipt "stop" "STOPPED" "interactive game process terminated" "$(current_commit)" "$ppid"
  fi

  if [ "$stopped" -eq 0 ]; then
    json_receipt "stop" "IDLE" "no campaign worker or game process was active" "$(current_commit)"
  fi
}

proof_current_or_run() {
  ensure_installed
  local commit status receipt_commit
  commit="$(current_commit)"
  status="$(proof_status)"
  receipt_commit="$(proof_commit)"
  if [ "$status" = "PASS" ] && [ "$receipt_commit" = "$commit" ]; then
    return 0
  fi
  run_proof_sync
}

play_game() {
  local mode="${1:-raw}"
  ensure_installed
  if ! proof_current_or_run; then
    echo "BLOCKED: mechanical proof did not pass; refusing to launder failure into play-ready." >&2
    return 40
  fi

  local commit run_root
  run_root="$(current_root)"
  commit="$(git -C "$run_root" rev-parse HEAD 2>/dev/null || true)"
  write_checkpoint "PLAY" "PLAY_READY" "Drew plays; first feel defect becomes the next concrete campaign slice." "$commit"
  json_receipt "play" "STARTING" "interactive game launch; human acceptance remains pending" "$commit"

  if command -v termux-notification >/dev/null 2>&1; then
    termux-notification \
      --id terminal-dmc-campaign \
      --title "Terminal DMC" \
      --content "Proof PASS. Q quits. terminal-dmc status / stop from another shell." \
      --priority high >/dev/null 2>&1 || true
  fi

  local rc
  set +e
  if [ -r /dev/tty ] && [ -w /dev/tty ]; then
    if [ "$mode" = "turn" ]; then
      python3 -B "$run_root/tools/terminal_dmc.py" --turn </dev/tty >/dev/tty 2>/dev/tty &
    else
      python3 -B "$run_root/tools/terminal_dmc.py" </dev/tty >/dev/tty 2>/dev/tty &
    fi
    local game_pid=$!
    echo "$game_pid" > "$PLAY_PID"
    wait "$game_pid"
    rc=$?
    rm -f "$PLAY_PID"
  else
    if [ "$mode" = "turn" ]; then
      python3 -B "$run_root/tools/terminal_dmc.py" --turn
    else
      python3 -B "$run_root/tools/terminal_dmc.py"
    fi
    rc=$?
  fi
  set -e

  json_receipt "play" "ENDED" "interactive game exited; this does not imply human acceptance" "$commit"
  write_checkpoint "PLAY" "PLAY_ENDED" "Capture Drew's concrete feel defect or acceptance; mutate gameplay, not ontology." "$commit"
  return "$rc"
}

status() {
  local quiet=0
  if [ "${1:-}" = "--quiet" ]; then quiet=1; fi

  local worker_active=false play_active=false
  pid_alive "$WORKER_PID" && worker_active=true || true
  pid_alive "$PLAY_PID" && play_active=true || true

  local commit
  commit="$(current_commit)"
  python3 - "$LATEST" "$CHECKPOINT" "$PROOF_RECEIPT" "$WORKER_HEARTBEAT" "$WORKER_PID" "$PLAY_PID" "$commit" "$worker_active" "$play_active" "$BIN" "$STATE_ROOT" "$WORKER_LOG" "$quiet" <<'PY'
import json, os, sys, time
(latest_path, checkpoint_path, proof_path, hb_path, worker_pid_path, play_pid_path,
 commit, worker_active, play_active, binary, state_root, log_path, quiet) = sys.argv[1:]

def load(path):
    try:
        return json.load(open(path, encoding="utf-8"))
    except Exception:
        return None

def read_int(path):
    try:
        return int(open(path, encoding="utf-8").read().strip())
    except Exception:
        return None

latest = load(latest_path)
checkpoint = load(checkpoint_path)
proof = load(proof_path)
hb = read_int(hb_path)
now = int(time.time())
obj = {
    "schema": "terminal-dmc-campaign.status.v1",
    "source_commit": commit or None,
    "worker_active": worker_active == "true",
    "worker_pid": read_int(worker_pid_path),
    "heartbeat_age_seconds": (now - hb) if hb else None,
    "play_active": play_active == "true",
    "play_pid": read_int(play_pid_path),
    "proof_status": (proof or {}).get("status"),
    "proof_commit": ((proof or {}).get("repository") or {}).get("head_sha"),
    "latest": latest,
    "checkpoint": checkpoint,
    "entrypoint": binary,
    "state_root": state_root,
    "log": log_path,
    "capability_boundary": {
        "implemented": True,
        "runtime_mechanical_proof": (proof or {}).get("status") == "PASS"
            and ((proof or {}).get("repository") or {}).get("head_sha") == commit,
        "interactive_human_acceptance": False,
        "merged_or_deployed": False,
    },
}
if quiet != "1":
    print(json.dumps(obj, indent=2, sort_keys=True))
PY
}

receipts() {
  local n="${1:-40}"
  if [ ! -f "$HISTORY" ]; then
    echo "No receipts yet."
    return 0
  fi
  tail -n "$n" "$HISTORY"
}

follow_log() {
  if [ ! -f "$WORKER_LOG" ]; then
    echo "No worker log yet."
    return 0
  fi
  echo "Following $WORKER_LOG"
  echo "Ctrl-C detaches this viewer; it does not stop the campaign."
  tail -n 120 -F "$WORKER_LOG"
}

doctor() {
  local blocked=0
  local cmd
  for cmd in bash git python3; do
    if command -v "$cmd" >/dev/null 2>&1; then
      printf 'PASS command %s -> %s\n' "$cmd" "$(command -v "$cmd")"
    else
      printf 'FAIL command %s missing\n' "$cmd"
      blocked=1
    fi
  done

  local root
  root="$(source_root)"
  if [ -n "$root" ]; then
    printf 'PASS repo %s\n' "$root"
    required_files_ok "$root" || blocked=1
    printf 'HEAD %s\n' "$(git -C "$root" rev-parse HEAD 2>/dev/null || echo UNKNOWN)"
    printf 'BRANCH %s\n' "$(git -C "$root" branch --show-current 2>/dev/null || echo DETACHED)"
  else
    echo "FAIL repo root unresolved"
    blocked=1
  fi

  if [ -x "$BIN" ]; then
    printf 'PASS stable entrypoint %s\n' "$BIN"
  else
    printf 'WARN stable entrypoint not installed yet: %s\n' "$BIN"
  fi

  if [ -f "$CANARY_RECEIPT" ]; then
    printf 'CANARY %s\n' "$(python3 - "$CANARY_RECEIPT" <<'PY'
import json, sys
try:
    print(json.load(open(sys.argv[1], encoding="utf-8")).get("status", "UNKNOWN"))
except Exception:
    print("INVALID")
PY
)"
  else
    echo "CANARY MISSING"
  fi

  if [ "$blocked" -ne 0 ]; then
    json_receipt "doctor" "BLOCKED" "campaign doctor found required failures" "$(current_commit)"
    return 50
  fi
  json_receipt "doctor" "PASS" "campaign dependencies and repository surface are present" "$(current_commit)"
}

update_campaign() {
  # Update means install the operator checkout's *current committed HEAD* as a
  # new immutable revision. It never fetches, switches branches, resets, stashes,
  # cleans, or overwrites Drew's working tree.
  install_revision
  canary
  run_proof_sync
}

bootstrap() {
  install_revision
  canary
  if ! run_proof_sync; then
    status
    return 60
  fi
  status
  if [ -t 0 ] && [ -t 1 ]; then
    play_game raw
  else
    printf '\nREADY FOR HUMAN PLAY\n%s play\n' "$BIN"
  fi
}

usage() {
  cat <<EOF
Terminal DMC campaign

One-time from the authorized Home Center checkout:
  bash tools/terminal_dmc_campaign.sh

Stable controls left behind:
  terminal-dmc play        # raw-key game
  terminal-dmc turn        # line-input fallback
  terminal-dmc prove       # synchronous commit-bound proof
  terminal-dmc run         # isolated background proof; returns shell immediately
  terminal-dmc resume      # same as run, idempotent
  terminal-dmc status
  terminal-dmc follow      # Ctrl-C detaches viewer only
  terminal-dmc stop        # TERM -> KILL background proof; stops active game PID
  terminal-dmc receipts [N]
  terminal-dmc update      # install current committed operator checkout, then prove
  terminal-dmc doctor
  terminal-dmc canary
  terminal-dmc install

Capability law:
  GitHub/repository presence = IMPLEMENTED only.
  proof PASS on the authorized body = runtime mechanical proof only.
  Drew playing and judging feel = human acceptance.
EOF
}

cmd="${1:-bootstrap}"
case "$cmd" in
  bootstrap)
    shift || true
    bootstrap "$@"
    ;;
  install)
    shift
    install_revision "$@"
    ;;
  update)
    shift
    update_campaign "$@"
    ;;
  canary)
    shift
    canary "$@"
    ;;
  prove)
    shift
    run_proof_sync "$@"
    ;;
  run|resume)
    shift
    start_worker "$@"
    ;;
  play)
    shift
    play_game raw "$@"
    ;;
  turn)
    shift
    play_game turn "$@"
    ;;
  status)
    shift
    status "$@"
    ;;
  follow)
    shift
    follow_log "$@"
    ;;
  stop)
    shift
    stop_worker "$@"
    ;;
  receipts)
    shift
    receipts "$@"
    ;;
  doctor)
    shift
    doctor "$@"
    ;;
  _proof-worker)
    shift
    worker_main "$@"
    ;;
  _stop-canary)
    shift
    kill_process_group "${1:?canary pid required}" 1
    ;;
  help|-h|--help)
    usage
    ;;
  *)
    usage >&2
    exit 2
    ;;
esac
