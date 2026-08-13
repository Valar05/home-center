#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

REPO="${FORTRESS_HOME_CENTER:-/storage/emulated/0/Documents/GodotProjects/home-center}"
BRANCH="${FORTRESS_SWARM_BRANCH:-feat/fortress-phone-swarm-campaign}"
STATE="$HOME/.local/state/home-center/fortress-campaign"
BIN="$HOME/bin"
BOOT="$HOME/.termux/boot"
LOG="$STATE/bootstrap.log"
SELF_REL="tools/fortress_phone_swarm_bootstrap.sh"
CAMPAIGN_REL="tools/fortress_campaign.py"
KERNEL_SETUP_REL="tools/setup_fortress_phone_kernel.sh"

mkdir -p "$STATE" "$BIN" "$BOOT"
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
cd "$REPO"

say "1. Recover dirty tree"
# Pull the campaign implementation without checking out/changing branches first. The recovery
# program itself is copied through git-show into state so it can safely stash the dirty tree.
retry 4 git fetch origin "$BRANCH"
git show "origin/$BRANCH:$CAMPAIGN_REL" > "$STATE/fortress_campaign.py.tmp"
python -m py_compile "$STATE/fortress_campaign.py.tmp"
mv "$STATE/fortress_campaign.py.tmp" "$STATE/fortress_campaign.py"
python "$STATE/fortress_campaign.py" recover-dirty-tree

after="$(git status --porcelain=v2 --branch)"
if printf '%s\n' "$after" | grep -Ev '^# branch\.' | grep -q .; then
  fail "dirty-tree recovery did not produce a clean tracked/untracked tree"
fi

say "2. Materialize campaign runtime from durable branch"
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
  mkdir -p "$(dirname "$REPO/$rel")"
  git show "origin/$BRANCH:$rel" > "$REPO/$rel" || fail "branch missing $rel"
done
chmod 700 "$REPO/$SELF_REL" "$REPO/$KERNEL_SETUP_REL" "$REPO/$CAMPAIGN_REL"
python -m py_compile "$REPO/$CAMPAIGN_REL" "$REPO/tools/fortress_phone_kernel.py" "$REPO/tools/fortress_cli.py" "$REPO/tools/fortress_prompt.py"
python -m json.tool "$REPO/config/fortress-phone-kernel.json" >/dev/null

say "3. Install/repair existing Fortress phone kernel"
# Reuse the existing kernel/setup organ. It is itself idempotent and preserves the commissioned
# Termux/SQLite/Boot architecture.
FORTRESS_PHONE_BRANCH="$BRANCH" retry 3 bash "$REPO/$KERNEL_SETUP_REL"

say "4. Install campaign command surface"
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
chmod 700 "$BIN/fortress-campaign" "$BIN/fortress-code" "$BIN/fortress-swarm-repair"

say "5. Install persistent campaign daemon"
cat > "$BOOT/35-fortress-campaign" <<EOF
#!/data/data/com.termux/files/usr/bin/bash
set -eu
STATE="\$HOME/.local/state/home-center/fortress-campaign"
mkdir -p "\$STATE"
PID="\$STATE/daemon.pid"
if [ -s "\$PID" ] && kill -0 "\$(cat "\$PID")" 2>/dev/null; then exit 0; fi
nohup python "$REPO/$CAMPAIGN_REL" daemon >>"\$STATE/daemon.log" 2>&1 < /dev/null &
echo \$! > "\$PID"
EOF
chmod 700 "$BOOT/35-fortress-campaign"
"$BOOT/35-fortress-campaign"
sleep 1

say "6. Diagnostics and self-repair proof"
# Kernel and campaign must both be alive. If not, retry their existing bootstrap/boot scripts.
if ! "$BIN/fortress" --status >/tmp/fortress-kernel-status.$$ 2>&1; then
  cat /tmp/fortress-kernel-status.$$ >&2 || true
  FORTRESS_PHONE_BRANCH="$BRANCH" retry 2 bash "$REPO/$KERNEL_SETUP_REL" || fail "phone kernel recovery failed"
fi
rm -f /tmp/fortress-kernel-status.$$

campaign_status="$($BIN/fortress-campaign status)" || {
  "$BOOT/35-fortress-campaign"
  sleep 1
  campaign_status="$($BIN/fortress-campaign status)" || fail "campaign status unavailable after daemon restart"
}
echo "$campaign_status"

pid="$(python - "$campaign_status" <<'PY'
import json,sys
print(json.loads(sys.argv[1]).get('daemonPid') or '')
PY
)"
[ -n "$pid" ] || fail "campaign did not publish daemon PID"
kill -0 "$pid" 2>/dev/null || {
  "$BOOT/35-fortress-campaign"
  sleep 1
  pid="$(cat "$STATE/daemon.pid" 2>/dev/null || true)"
  [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null || fail "campaign daemon is not alive"
}

say "7. Ready"
echo "Campaign daemon PID: $pid"
echo "Prompt entrypoint: fortress-code \"your coding commission\""
echo "Status: fortress-campaign status"
echo "Repair/rebootstrap: fortress-swarm-repair"
echo "Dirty-tree rescue receipt: $STATE/campaign.sqlite3 + $STATE/campaign.jsonl"
echo "Venice/Judgment jars: consumes VLAD_JUDGMENT_JARS or discovered Vlad local cache when available; missing adapter can never self-authorize STOP."
echo "FORTRESS_PHONE_SWARM_READY"
