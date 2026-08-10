#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
mkdir -p "$HOME/bin" "$HOME/.local/state/home-center/coding-dungeon" "$HOME/.config/home-center/dungeons"
pkg install -y python git >/dev/null
PYTHON_BIN="$(command -v python)"
[ -x "$PYTHON_BIN" ] || { echo "BLOCKED: Termux Python is not executable: $PYTHON_BIN" >&2; exit 2; }
cat > "$HOME/bin/dungeon" <<EOF
#!/data/data/com.termux/files/usr/bin/bash
exec '$PYTHON_BIN' '$ROOT/tools/mobile_coding_dungeon.py' "\$@"
EOF
chmod +x "$HOME/bin/dungeon"
cat > "$HOME/.config/home-center/dungeons/example-repair.json" <<EOF
{
  "name": "example-repair",
  "owner": "Drew",
  "principal": "Adam",
  "workspace": "$ROOT",
  "objective": "Run a bounded verification loop and stop green or blocked.",
  "steps": [
    {"type":"verify","name":"python syntax","run":"'$PYTHON_BIN' -m py_compile tools/mobile_coding_dungeon.py"},
    {"type":"verify","name":"git diff check","run":"git diff --check"}
  ],
  "scars": [],
  "stop": {"max_cycles":2,"same_failure_limit":2,"command_timeout_seconds":120}
}
EOF
"$PYTHON_BIN" "$ROOT/tools/mobile_coding_dungeon.py" run "$HOME/.config/home-center/dungeons/example-repair.json"
echo 'MOBILE CODING DUNGEON READY.'
echo 'Run: dungeon run ~/.config/home-center/dungeons/example-repair.json'
echo 'Ledger: ~/.local/state/home-center/coding-dungeon/<run>/ledger.jsonl'
