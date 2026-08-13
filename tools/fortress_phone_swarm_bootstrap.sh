#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

REPO="${FORTRESS_HOME_CENTER:-/storage/emulated/0/Documents/GodotProjects/home-center}"
BRANCH="${FORTRESS_SWARM_BRANCH:-feat/fortress-phone-swarm-campaign}"
STATE="$HOME/.local/state/home-center/fortress-campaign"
BIN="$HOME/bin"
LOG="$STATE/bootstrap.log"
SESSION="fortress-swarm"
SELF_REL="tools/fortress_phone_swarm_bootstrap.sh"
CAMPAIGN_REL="tools/fortress_campaign.py"
KERNEL_SETUP_REL="tools/setup_fortress_phone_kernel.sh"

mkdir -p "$STATE" "$BIN"
exec > >(tee -a "$LOG") 2>&1

say(){ printf '\n=== %s ===\n' "$*"; }
fail(){ echo "BLOCKED: $*" >&2; exit 2; }
retry(){
  local tries="$1"; shift
  local n=1 delay=2
  until "$@"; do
    if [ "$n" -ge "$tries" ]; then return 1; fi
    echo "retry $n/$tries failed: $*; sleeping ${delay}s" >&2
    sleep "$delay"
    n=$((n+1)); delay=$((delay*2)); [ "$delay" -gt 30 ] && delay=30
  done
}

[ -d "$REPO/.git" ] || fail "$REPO is not a Home Center git worktree"
command -v python >/dev/null || fail "python is required"
command -v git >/dev/null || fail "git is required"
command -v tmux >/dev/null || {
  command -v pkg >/dev/null || fail "tmux missing and pkg unavailable"
  retry 3 pkg install -y tmux || fail "could not install tmux"
}
cd "$REPO"

say "1. Recover dirty tree"
# Fetch only; do not mutate the working tree before rescue.
retry 4 git fetch origin "$BRANCH"
git show "origin/$BRANCH:$CAMPAIGN_REL" > "$STATE/fortress_campaign.py.tmp"
python -m py_compile "$STATE/fortress_campaign.py.tmp"
mv "$STATE/fortress_campaign.py.tmp" "$STATE/fortress_campaign.py"
python "$STATE/fortress_campaign.py" recover-dirty-tree

after="$(git status --porcelain=v2 --branch)"
if printf '%s\n' "$after" | grep -Ev '^# branch\.' | grep -q .; then
  fail "dirty-tree recovery did not produce a clean tracked/untracked tree"
fi

say "2. Enter exact campaign branch without losing rescued work"
# Dirty work is now durably stashed. Move the worktree to the fetched campaign head.
if git show-ref --verify --quiet "refs/heads/$BRANCH"; then
  git checkout "$BRANCH"
  git reset --hard "origin/$BRANCH"
else
  git checkout -b "$BRANCH" --track "origin/$BRANCH"
fi
current="$(git rev-parse HEAD)"
expected="$(git rev-parse "origin/$BRANCH")"
[ "$current" = "$expected" ] || fail "campaign branch head mismatch"
clean="$(git status --porcelain=v2 --branch)"
if printf '%s\n' "$clean" | grep -Ev '^# branch\.' | grep -q .; then
  fail "campaign branch is unexpectedly dirty after rescue/switch"
fi

say "3. Validate campaign runtime"
for rel in \
  "$SELF_REL" \
  "$CAMPAIGN_REL" \
  "$KERNEL_SETUP_REL" \
  tools/fortress_phone_kernel.py \
  tools/fortress_cli.py \
  tools/fortress_prompt.py \
  tools/fortress_read_aloud.py \
  config/fortress-phone-kernel.json \
  config/fortress-prompt.json \
  config/fortress-adam-voice.json; do
  test -s "$REPO/$rel" || fail "campaign branch missing $rel"
done
chmod 700 "$REPO/$SELF_REL" "$REPO/$KERNEL_SETUP_REL" "$REPO/$CAMPAIGN_REL"
python -m py_compile "$REPO/$CAMPAIGN_REL" "$REPO/tools/fortress_phone_kernel.py" "$REPO/tools/fortress_cli.py" "$REPO/tools/fortress_prompt.py"
python -m json.tool "$REPO/config/fortress-phone-kernel.json" >/dev/null

say "4. Install/repair existing Fortress phone kernel"
FORTRESS_PHONE_BRANCH="$BRANCH" retry 3 bash "$REPO/$KERNEL_SETUP_REL"

say "5. Install campaign command surface"
cat > "$BIN/fortress-campaign" <<EOF
#!/data/data/com.termux/files/usr/bin/bash
exec python "$REPO/$CAMPAIGN_REL" "\$@"
EOF
cat > "$BIN/fortress-code" <<EOF
#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
[ "\$#" -gt 0 ] || { echo 'usage: fortress-code <prompt>' >&2; exit 2; }
exec python "$REPO/$CAMPAIGN_REL" prompt "\$*"
EOF
cat > "$BIN/fortress-swarm-repair" <<EOF
#!/data/data/com.termux/files/usr/bin/bash
exec bash "$REPO/$SELF_REL"
EOF
cat > "$BIN/fortress-swarm-attach" <<EOF
#!/data/data/com.termux/files/usr/bin/bash
exec tmux attach-session -t "$SESSION"
EOF
cat > "$BIN/fortress-swarm-status" <<EOF
#!/data/data/com.termux/files/usr/bin/bash
set -e
tmux list-windows -t "$SESSION" -F '#{window_index}:#{window_name} pane=#{pane_pid} dead=#{pane_dead}' 2>/dev/null || true
exec "$BIN/fortress-campaign" status
EOF
chmod 700 "$BIN/fortress-campaign" "$BIN/fortress-code" "$BIN/fortress-swarm-repair" "$BIN/fortress-swarm-attach" "$BIN/fortress-swarm-status"

say "6. Start persistent tmux swarm"
# tmux is the process supervisor. Re-running this bootstrap repairs missing/dead windows in place.
if ! tmux has-session -t "$SESSION" 2>/dev/null; then
  tmux new-session -d -s "$SESSION" -n kernel "cd '$REPO' && exec python '$REPO/tools/fortress_phone_kernel.py' daemon"
  tmux new-window -t "$SESSION" -n campaign "cd '$REPO' && exec python '$REPO/$CAMPAIGN_REL' daemon"
else
  if ! tmux list-windows -t "$SESSION" -F '#{window_name}' | grep -qx kernel; then
    tmux new-window -t "$SESSION" -n kernel "cd '$REPO' && exec python '$REPO/tools/fortress_phone_kernel.py' daemon"
  fi
  if ! tmux list-windows -t "$SESSION" -F '#{window_name}' | grep -qx campaign; then
    tmux new-window -t "$SESSION" -n campaign "cd '$REPO' && exec python '$REPO/$CAMPAIGN_REL' daemon"
  fi
fi
sleep 1

say "7. Diagnostics and self-repair proof"
# A tmux window whose pane died is repaired once here; later re-running fortress-swarm-repair does the same.
repair_window(){
  local name="$1" cmd="$2"
  if ! tmux list-windows -t "$SESSION" -F '#{window_name}:#{pane_dead}' | grep -qx "$name:0"; then
    tmux kill-window -t "$SESSION:$name" 2>/dev/null || true
    tmux new-window -t "$SESSION" -n "$name" "$cmd"
    sleep 1
  fi
  tmux list-windows -t "$SESSION" -F '#{window_name}:#{pane_dead}' | grep -qx "$name:0"
}
repair_window kernel "cd '$REPO' && exec python '$REPO/tools/fortress_phone_kernel.py' daemon" || fail "kernel tmux window is not alive"
repair_window campaign "cd '$REPO' && exec python '$REPO/$CAMPAIGN_REL' daemon" || fail "campaign tmux window is not alive"

"$BIN/fortress" --status >/dev/null || {
  tmux respawn-pane -k -t "$SESSION:kernel" "cd '$REPO' && exec python '$REPO/tools/fortress_phone_kernel.py' daemon"
  sleep 1
  "$BIN/fortress" --status >/dev/null || fail "phone kernel remains unhealthy after tmux respawn"
}

campaign_status="$($BIN/fortress-campaign status)" || {
  tmux respawn-pane -k -t "$SESSION:campaign" "cd '$REPO' && exec python '$REPO/$CAMPAIGN_REL' daemon"
  sleep 1
  campaign_status="$($BIN/fortress-campaign status)" || fail "campaign remains unhealthy after tmux respawn"
}
echo "$campaign_status"

tmux list-windows -t "$SESSION" -F 'window=#{window_name} pid=#{pane_pid} dead=#{pane_dead}'

say "8. Ready"
echo "One prompt: fortress-code \"your coding commission\""
echo "Attach live daemon: fortress-swarm-attach"
echo "Status: fortress-swarm-status"
echo "Repair/rebootstrap: fortress-swarm-repair"
echo "tmux session: $SESSION"
echo "Dirty-tree rescue is reversible and recorded in $STATE/campaign.sqlite3 + $STATE/campaign.jsonl"
echo "Vlad jar cache is consumed when available; this bootstrap never relocates or rebuilds it."
echo "No Venice adapter/cache may ever fabricate STOP_ALLOWED."
echo "FORTRESS_PHONE_SWARM_READY"
