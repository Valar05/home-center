#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

REPO="${FORTRESS_HOME_CENTER:-/storage/emulated/0/Documents/GodotProjects/home-center}"
BRANCH="${FORTRESS_SWARM_BRANCH:-feat/fortress-phone-swarm-campaign}"
STATE="$HOME/.local/state/home-center/fortress-campaign"
KERNEL_STATE="$HOME/.local/state/home-center/fortress-phone-kernel"
BIN="$HOME/bin"
BOOT="$HOME/.termux/boot"
CONFIG="$HOME/.config/home-center"
LOG="$STATE/bootstrap.log"
SESSION="fortress-swarm"
SELF_REL="tools/fortress_phone_swarm_bootstrap.sh"
CAMPAIGN_REL="tools/fortress_campaign.py"
THRONE_ADAPTER_REL="tools/fortress_throne_adapter.py"
SUPERVISOR_REL="tools/fortress_supervise.sh"
KERNEL_SETUP_REL="tools/setup_fortress_phone_kernel.sh"

mkdir -p "$STATE" "$KERNEL_STATE" "$BIN" "$BOOT" "$CONFIG"
exec > >(tee -a "$LOG") 2>&1

say(){ printf '\n=== %s ===\n' "$*"; }
fail(){ echo "BLOCKED: $*" >&2; exit 2; }
retry(){ local tries="$1"; shift; local n=1 delay=2; until "$@"; do [ "$n" -ge "$tries" ] && return 1; echo "retry $n/$tries failed: $*; sleeping ${delay}s" >&2; sleep "$delay"; n=$((n+1)); delay=$((delay*2)); [ "$delay" -gt 30 ] && delay=30; done; }

[ -d "$REPO/.git" ] || fail "$REPO is not a Home Center git worktree"
command -v python >/dev/null || fail "python is required"
command -v git >/dev/null || fail "git is required"
command -v ssh >/dev/null || fail "OpenSSH client is required for SSH Axis"
command -v tmux >/dev/null || { command -v pkg >/dev/null || fail "tmux missing and pkg unavailable"; retry 3 pkg install -y tmux || fail "could not install tmux"; }
cd "$REPO"

say "1. Recover dirty tree"
retry 4 git fetch origin "$BRANCH"
git show "origin/$BRANCH:$CAMPAIGN_REL" > "$STATE/fortress_campaign.py.tmp"
python -m py_compile "$STATE/fortress_campaign.py.tmp"
mv "$STATE/fortress_campaign.py.tmp" "$STATE/fortress_campaign.py"
python "$STATE/fortress_campaign.py" recover-dirty-tree

after="$(git status --porcelain=v2 --branch)"
if printf '%s\n' "$after" | grep -Ev '^# branch\.' | grep -q .; then fail "dirty-tree recovery did not produce a clean tracked/untracked tree"; fi

say "2. Enter exact campaign branch without losing rescued work"
if git show-ref --verify --quiet "refs/heads/$BRANCH"; then git checkout "$BRANCH"; git reset --hard "origin/$BRANCH"; else git checkout -b "$BRANCH" --track "origin/$BRANCH"; fi
current="$(git rev-parse HEAD)"; expected="$(git rev-parse "origin/$BRANCH")"; [ "$current" = "$expected" ] || fail "campaign branch head mismatch"
clean="$(git status --porcelain=v2 --branch)"; if printf '%s\n' "$clean" | grep -Ev '^# branch\.' | grep -q .; then fail "campaign branch is unexpectedly dirty after rescue/switch"; fi

say "3. Validate campaign runtime"
for rel in "$SELF_REL" "$CAMPAIGN_REL" "$THRONE_ADAPTER_REL" "$SUPERVISOR_REL" "$KERNEL_SETUP_REL" tools/fortress_phone_kernel.py tools/fortress_cli.py tools/fortress_prompt.py config/fortress-phone-kernel.json config/fortress-prompt.json; do test -s "$REPO/$rel" || fail "campaign branch missing $rel"; done
chmod 700 "$REPO/$SELF_REL" "$REPO/$KERNEL_SETUP_REL" "$REPO/$CAMPAIGN_REL" "$REPO/$THRONE_ADAPTER_REL" "$REPO/$SUPERVISOR_REL"
python -m py_compile "$REPO/$CAMPAIGN_REL" "$REPO/$THRONE_ADAPTER_REL" "$REPO/tools/fortress_phone_kernel.py" "$REPO/tools/fortress_cli.py" "$REPO/tools/fortress_prompt.py"
python -m json.tool "$REPO/config/fortress-phone-kernel.json" >/dev/null

say "4. Install/repair existing Fortress phone kernel"
FORTRESS_PHONE_BRANCH="$BRANCH" retry 3 bash "$REPO/$KERNEL_SETUP_REL"

say "5. Remove legacy split-brain supervisors"
if [ -s "$KERNEL_STATE/kernel.pid" ]; then oldpid="$(cat "$KERNEL_STATE/kernel.pid" 2>/dev/null || true)"; if [ -n "$oldpid" ] && kill -0 "$oldpid" 2>/dev/null; then kill "$oldpid" 2>/dev/null || true; for _ in 1 2 3 4 5; do kill -0 "$oldpid" 2>/dev/null || break; sleep 1; done; fi; rm -f "$KERNEL_STATE/kernel.pid"; fi
rm -f "$BOOT/30-fortress-phone-kernel" "$BOOT/35-fortress-campaign"

say "6. Bind campaign to the phone-local Throne relay adapter"
cat > "$CONFIG/chromium-throne-peer.json" <<EOF
{
  "url": "http://127.0.0.1:17373",
  "token": "",
  "repoRoot": "operator-selected desktop workspace resolved from commission and durable evidence",
  "transport": "SSH Axis -> THECAULDRON -> existing Chromium Throne relay"
}
EOF
chmod 600 "$CONFIG/chromium-throne-peer.json"

say "7. Install campaign command surface"
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
cat > "$BIN/fortress-throne" <<EOF
#!/data/data/com.termux/files/usr/bin/bash
exec python "$REPO/$THRONE_ADAPTER_REL" "\$@"
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
cat > "$BIN/fortress-swarm-diagnose" <<EOF
#!/data/data/com.termux/files/usr/bin/bash
set -e
"$BIN/fortress-throne" diagnose
exec "$BIN/fortress-campaign" diagnose --repair
EOF
chmod 700 "$BIN/fortress-campaign" "$BIN/fortress-code" "$BIN/fortress-throne" "$BIN/fortress-swarm-repair" "$BIN/fortress-swarm-attach" "$BIN/fortress-swarm-status" "$BIN/fortress-swarm-diagnose"

say "8. Install one Termux:Boot tmux supervisor"
cat > "$BOOT/30-fortress-swarm" <<EOF
#!/data/data/com.termux/files/usr/bin/bash
set -eu
export FORTRESS_HOME_CENTER='$REPO'
SESSION='$SESSION'
SUP='$REPO/$SUPERVISOR_REL'
if ! command -v tmux >/dev/null 2>&1; then exit 0; fi
start_role(){ name="\$1"; if tmux list-windows -t "\$SESSION" -F '#{window_name}:#{pane_dead}' 2>/dev/null | grep -qx "\$name:0"; then return 0; fi; tmux kill-window -t "\$SESSION:\$name" 2>/dev/null || true; tmux new-window -t "\$SESSION" -n "\$name" "cd '$REPO' && exec bash '\$SUP' '\$name'"; }
if ! tmux has-session -t "\$SESSION" 2>/dev/null; then
  tmux new-session -d -s "\$SESSION" -n kernel "cd '$REPO' && exec bash '\$SUP' kernel"
fi
start_role throne
start_role campaign
EOF
chmod 700 "$BOOT/30-fortress-swarm"
"$BOOT/30-fortress-swarm"
sleep 2

say "9. Diagnostics and self-repair proof"
for role in kernel throne campaign; do tmux list-windows -t "$SESSION" -F '#{window_name}:#{pane_dead}' | grep -qx "$role:0" || fail "$role tmux supervisor is not alive"; done
"$BIN/fortress" --status >/dev/null || fail "phone kernel status unavailable under supervisor"
python - <<'PY'
import json,urllib.request
with urllib.request.urlopen('http://127.0.0.1:17373/health',timeout=4) as r:x=json.load(r)
if x.get('contract')!='home-center.chromium-throne.v1' or not x.get('adapter'):raise SystemExit('Throne adapter health contract mismatch')
print(json.dumps(x))
PY
campaign_status="$($BIN/fortress-campaign status)" || fail "campaign status unavailable under supervisor"; echo "$campaign_status"

say "10. Recover/prove THECAULDRON relay through SSH Axis"
"$BIN/fortress-throne" diagnose || true

tmux list-windows -t "$SESSION" -F 'window=#{window_name} pid=#{pane_pid} dead=#{pane_dead}'

say "11. Ready"
echo "One prompt: fortress-code \"your coding commission\""
echo "Attach live daemon: fortress-swarm-attach"
echo "Status: fortress-swarm-status"
echo "Diagnostics/repair: fortress-swarm-diagnose"
echo "Repair/rebootstrap: fortress-swarm-repair"
echo "tmux session: $SESSION (kernel + throne + campaign; each role self-restarts with backoff)"
echo "Dirty-tree rescue is reversible and recorded in $STATE/campaign.sqlite3 + $STATE/campaign.jsonl"
echo "Vlad jar cache is consumed when available; this bootstrap never relocates or rebuilds it."
echo "Chromium Throne transport is the existing relay, reached through SSH Axis; no obsolete bare-metal API is required."
echo "No Venice adapter/cache may ever fabricate STOP_ALLOWED."
echo "FORTRESS_PHONE_SWARM_READY"
