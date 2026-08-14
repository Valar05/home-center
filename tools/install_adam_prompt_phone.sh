#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
BIN="$HOME/bin"
STATE="$HOME/.local/state/home-center/adam-do"
mkdir -p "$BIN" "$STATE"
[ -f "$ROOT/tools/adam_prompt.py" ] || { echo "BLOCKED: missing $ROOT/tools/adam_prompt.py" >&2; exit 2; }
[ -f "$ROOT/tools/adam.py" ] || { echo "BLOCKED: missing $ROOT/tools/adam.py" >&2; exit 2; }
cat > "$BIN/adam-do" <<EOF
#!/data/data/com.termux/files/usr/bin/bash
export ADAM_DO_REPO=$(printf '%q' "$ROOT")
exec python3 $(printf '%q' "$ROOT/tools/adam_prompt.py") "\$@"
EOF
chmod 700 "$BIN/adam-do"
cat > "$BIN/adam-router" <<EOF
#!/data/data/com.termux/files/usr/bin/bash
exec python3 $(printf '%q' "$ROOT/tools/adam.py") "\$@"
EOF
chmod 700 "$BIN/adam-router"
cat > "$BIN/adam" <<'EOF'
#!/data/data/com.termux/files/usr/bin/bash
exec "$HOME/bin/adam-do" "$@"
EOF
chmod 700 "$BIN/adam"

"$BIN/adam-do" --help >/dev/null
"$BIN/adam-do" --canary >"$STATE/install-canary.json"
python3 - "$STATE/install-canary.json" <<'PY'
import json,sys
p=sys.argv[1]
d=json.load(open(p,encoding='utf-8'))
assert d.get('ok') is True, d
assert d.get('operatorShellBlocked') is False, d
assert d.get('killPath') == 'process-group TERM->KILL', d
PY
printf '{"schema":"adam-do-install-v2","ok":true,"repo":"%s","command":"%s","router":"%s","canary":"%s"}\n' "$ROOT" "$BIN/adam" "$BIN/adam-router" "$STATE/install-canary.json" | tee "$STATE/install.json"
printf '\nREADY\n  adam "what you want done"   # returns shell immediately\n  adam --status\n  adam --follow\n  adam --stop\n  adam --resume\n  adam --receipts\n'
