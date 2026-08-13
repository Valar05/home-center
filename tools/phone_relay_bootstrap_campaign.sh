#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
STATE_DIR="$HOME/.cache/home-center"
LOG="$STATE_DIR/phone-relay.log"
RECEIPT="$STATE_DIR/phone-relay-bootstrap-$STAMP.receipt.txt"
mkdir -p "$STATE_DIR"

say(){ printf '%s\n' "$*" | tee -a "$RECEIPT"; }
fail(){ say "STATUS=FAILED"; say "ERROR=$*"; exit 1; }

say "CAMPAIGN=phone-relay-bootstrap"
say "STARTED_AT=$STAMP"
say "UI_CONTROL_TOUCHED=false"
say "PURPOSE=promote canonical background phone_shell bypass and restart relay only"

command -v git >/dev/null 2>&1 || fail "git not found in Termux"
command -v python >/dev/null 2>&1 || command -v python3 >/dev/null 2>&1 || fail "python not found in Termux"
PY="$(command -v python || command -v python3)"

# Prefer the exact script currently used by the running relay. Fall back only to known
# Home Center checkout locations. Never search or mutate arbitrary shared storage.
PID="$(pgrep -f '[a]ndroid_phone_home_center_relay.py' | head -n1 || true)"
LIVE_SCRIPT=""
if [[ -n "$PID" && -r "/proc/$PID/cmdline" ]]; then
  mapfile -d '' ARGV < "/proc/$PID/cmdline" || true
  for arg in "${ARGV[@]:-}"; do
    if [[ "$arg" == *android_phone_home_center_relay.py ]]; then
      LIVE_SCRIPT="$arg"
      break
    fi
  done
fi

if [[ -z "$LIVE_SCRIPT" ]]; then
  for candidate in \
    "$HOME/home-center/tools/android_phone_home_center_relay.py" \
    "$HOME/src/home-center/tools/android_phone_home_center_relay.py" \
    "/storage/emulated/0/Documents/GodotProjects/home-center/tools/android_phone_home_center_relay.py"
  do
    if [[ -f "$candidate" ]]; then LIVE_SCRIPT="$candidate"; break; fi
  done
fi
[[ -n "$LIVE_SCRIPT" && -f "$LIVE_SCRIPT" ]] || fail "could not locate installed android_phone_home_center_relay.py"

SCRIPT_DIR="$(cd "$(dirname "$LIVE_SCRIPT")" && pwd)"
REPO_ROOT="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel 2>/dev/null || true)"
[[ -n "$REPO_ROOT" ]] || fail "relay file is not inside a git checkout"
say "LIVE_SCRIPT=$LIVE_SCRIPT"
say "REPO_ROOT=$REPO_ROOT"
say "OLD_PID=${PID:-none}"
say "LOCAL_HEAD=$(git -C "$REPO_ROOT" rev-parse HEAD 2>/dev/null || echo unknown)"
say "LOCAL_BRANCH=$(git -C "$REPO_ROOT" branch --show-current 2>/dev/null || echo unknown)"

# Preserve every local branch/worktree change. Refresh only the remote ref, then extract
# exactly one canonical file from origin/main without checkout/reset/pull.
git -C "$REPO_ROOT" fetch --quiet origin main
REMOTE_MAIN="$(git -C "$REPO_ROOT" rev-parse FETCH_HEAD)"
say "FETCHED_ORIGIN_MAIN=$REMOTE_MAIN"

TMP="$STATE_DIR/android_phone_home_center_relay.$STAMP.py"
git -C "$REPO_ROOT" show "$REMOTE_MAIN:tools/android_phone_home_center_relay.py" > "$TMP"

# Refuse to install a source that does not contain the intended background-shell bypass.
grep -q "if k in TERMUX_SHELL_ACTIONS:return termux_shell_execute(a)" "$TMP" \
  || fail "fetched relay does not contain canonical TERMUX_SHELL_ACTIONS bypass"
grep -q "gate=overlay_control_gate()" "$TMP" \
  || fail "fetched relay is missing overlay gate for interactive paths"

NEW_SHA="$(sha256sum "$TMP" | awk '{print $1}')"
OLD_SHA="$(sha256sum "$LIVE_SCRIPT" | awk '{print $1}')"
say "OLD_RELAY_SHA256=$OLD_SHA"
say "NEW_RELAY_SHA256=$NEW_SHA"

BACKUP="$STATE_DIR/android_phone_home_center_relay.before-$STAMP.py"
cp -p "$LIVE_SCRIPT" "$BACKUP"
say "BACKUP=$BACKUP"

# Atomic replacement in the existing checkout. No chmod/exec assumption on shared storage.
INSTALL_TMP="$LIVE_SCRIPT.bootstrap-new"
cat "$TMP" > "$INSTALL_TMP"
mv -f "$INSTALL_TMP" "$LIVE_SCRIPT"

# Restart only the relay process. Do not touch Shizuku, overlay state, Android UI, SSH, or ADB.
if [[ -n "$PID" ]]; then
  kill "$PID" 2>/dev/null || true
  for _ in 1 2 3 4 5; do
    kill -0 "$PID" 2>/dev/null || break
    sleep 1
  done
  kill -0 "$PID" 2>/dev/null && fail "old relay PID $PID did not exit"
fi

nohup "$PY" "$LIVE_SCRIPT" >>"$LOG" 2>&1 </dev/null &
NEW_PID=$!
say "NEW_PID=$NEW_PID"

sleep 4
kill -0 "$NEW_PID" 2>/dev/null || {
  tail -n 40 "$LOG" | tee -a "$RECEIPT" || true
  fail "replacement relay exited during startup"
}

if ! tail -n 80 "$LOG" | grep -q 'Home Center phone relay online: primary-phone'; then
  tail -n 40 "$LOG" | tee -a "$RECEIPT" || true
  fail "relay process is alive but did not report primary-phone online"
fi

INSTALLED_SHA="$(sha256sum "$LIVE_SCRIPT" | awk '{print $1}')"
[[ "$INSTALLED_SHA" == "$NEW_SHA" ]] || fail "installed relay hash does not match fetched canonical source"

say "INSTALLED_RELAY_SHA256=$INSTALLED_SHA"
say "LOG=$LOG"
say "STATUS=BOOTSTRAP_COMPLETE_PENDING_REMOTE_PHONE_SHELL_PROBE"
say "NEXT=Return this receipt path or simply tell Adam 'done'; Adam must retry phone_shell through Home Center without UI control, then continue Thunder Run-One automatically."
printf '\n%s\n' "RECEIPT=$RECEIPT"
