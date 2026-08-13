#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
ROOT="${HC_REPO_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}"
BIN="${PREFIX:-$HOME/.local}/bin/home-center-ssh"
CFG="$HOME/.config/home-center/ssh-targets.json"
mkdir -p "$(dirname "$BIN")" "$(dirname "$CFG")"
cat > "$BIN" <<EOF
#!/data/data/com.termux/files/usr/bin/bash
exec python3 $(printf '%q' "$ROOT/tools/home_center_ssh.py") "\$@"
EOF
chmod 755 "$BIN"
if [ ! -f "$CFG" ]; then
  cp "$ROOT/config/ssh-targets.example.json" "$CFG"
  chmod 600 "$CFG"
fi
python3 "$ROOT/tools/home_center_ssh.py" targets
