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

# Friendly alias: `adam "prompt"` now means do the work. Existing explicit
# router modes remain available as `adam-router` for scripts and diagnostics.
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
printf '{"schema":"adam-do-install-v1","ok":true,"repo":"%s","command":"%s","router":"%s"}\n' "$ROOT" "$BIN/adam" "$BIN/adam-router" | tee "$STATE/install.json"
printf '\nREADY\n  adam "what you want done"\n  adam-do "what you want done"\n  adam-router continue "what you want done"\n'
