#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
CFG="$HOME/.config/home-center"
FISHCFG="$HOME/.config/fish/conf.d"
mkdir -p "$HOME/bin" "$CFG" "$FISHCFG"
command -v fish >/dev/null 2>&1 || pkg install -y fish
install -m 755 "$ROOT/tools/fortress_prompt.py" "$HOME/bin/fortress-prompt"
cat > "$HOME/bin/fortress" <<'EOF'
#!/data/data/com.termux/files/usr/bin/bash
exec "$HOME/bin/fortress-prompt" "$@"
EOF
chmod +x "$HOME/bin/fortress"
if [ ! -f "$CFG/fortress-prompt.json" ]; then
  cp "$ROOT/config/fortress-prompt.json" "$CFG/fortress-prompt.json"
fi
cat > "$FISHCFG/fortress.fish" <<'EOF'
function fortress
    command $HOME/bin/fortress-prompt $argv
end
abbr --add f fortress
abbr --add fs 'fortress status'
abbr --add fg 'fortress git status'
EOF
printf 'FORTRESS FISH INSTALLED\nengine=%s\nconfig=%s\n' "$HOME/bin/fortress-prompt" "$CFG/fortress-prompt.json"
printf 'Behavior updates are config-only. Runtime redeploy is only needed when the compiler itself changes.\n'
