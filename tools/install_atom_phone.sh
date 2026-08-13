#!/data/data/com.termux/files/usr/bin/sh
set -eu
ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
SRC="$ROOT/atom"
DEST="$HOME/.local/share/atom"
BIN="$HOME/bin"
BOOT="$HOME/.termux/boot"
STATE="$HOME/.local/state/atom"
[ -f "$SRC/server.mjs" ] || { echo "BLOCKED: Atom source missing at $SRC" >&2; exit 2; }
[ -f "$ROOT/config/judgment-jars.v1.json" ] || { echo "BLOCKED: Judgment Jar config missing" >&2; exit 2; }
[ -f "$ROOT/tools/setup_vlad_swarm_daemon.sh" ] || { echo "BLOCKED: Vlad daemon setup missing" >&2; exit 2; }
[ -f "$ROOT/tools/venice_fleshpunk_phone.sh" ] || { echo "BLOCKED: Fleshpunk phone generator missing" >&2; exit 2; }
mkdir -p "$DEST" "$BIN" "$BOOT" "$STATE"
rm -rf "$DEST.new"
mkdir -p "$DEST.new"
cp -R "$SRC/." "$DEST.new/"
mkdir -p "$DEST.new/config"
cp "$ROOT/config/judgment-jars.v1.json" "$DEST.new/config/"
mkdir -p "$DEST.new/tools"
cp "$ROOT/tools/venice_fleshpunk_phone.sh" "$DEST.new/tools/"
cp "$ROOT/tools/ssh_axis.py" "$DEST.new/tools/"
cp "$ROOT/tools/resolve_cauldron_ssh.py" "$DEST.new/tools/"
rm -rf "$DEST.old"
[ ! -d "$DEST" ] || mv "$DEST" "$DEST.old"
mv "$DEST.new" "$DEST"
cat > "$BIN/atom" <<'ATOM_WRAPPER'
#!/data/data/com.termux/files/usr/bin/sh
export HC_JUDGMENT_JARS_CONFIG="${HC_JUDGMENT_JARS_CONFIG:-$HOME/.local/share/atom/config/judgment-jars.v1.json}"
exec node "$HOME/.local/share/atom/server.mjs" "$@"
ATOM_WRAPPER
chmod 700 "$BIN/atom"
cat > "$BIN/atom-open" <<'EOF'
#!/data/data/com.termux/files/usr/bin/sh
URL='http://127.0.0.1:8788/'
if command -v termux-open-url >/dev/null 2>&1; then exec termux-open-url "$URL"; fi
exec am start -a android.intent.action.VIEW -d "$URL"
EOF
chmod 700 "$BIN/atom-open"
cat > "$BIN/venice-image" <<'EOF'
#!/data/data/com.termux/files/usr/bin/sh
exec bash "$HOME/.local/share/atom/tools/venice_fleshpunk_phone.sh" "$@"
EOF
chmod 700 "$BIN/venice-image"
cat > "$BIN/venice-image-ui" <<'EOF'
#!/data/data/com.termux/files/usr/bin/sh
set -eu
STATE="${HC_STATE_DIR:-$HOME/.local/state/home-center}/venice-fleshpunk-image"
if ! command -v termux-dialog >/dev/null 2>&1; then
  echo 'BLOCKED: Termux:API termux-dialog is unavailable. Use: venice-image generate "prompt"' >&2
  exit 2
fi
RAW="$(termux-dialog text -t 'Fleshpunk image' -i 'Describe the image to generate on THECAULDRON')"
PROMPT="$(printf '%s' "$RAW" | python -c 'import json,sys; d=json.load(sys.stdin); print(d.get("text","") if int(d.get("code",-2)) in (-1,0) else "")')"
[ -n "$PROMPT" ] || exit 0
if "$HOME/bin/venice-image" generate "$PROMPT"; then
  [ ! -f "$STATE/latest.json" ] || cat "$STATE/latest.json"
  if command -v termux-toast >/dev/null 2>&1; then termux-toast 'Fleshpunk image generated and returned to phone' >/dev/null 2>&1 || true; fi
  if command -v termux-open >/dev/null 2>&1 && [ -f "$STATE/latest.png" ]; then termux-open "$STATE/latest.png" >/dev/null 2>&1 || true; fi
else
  rc=$?
  if command -v termux-toast >/dev/null 2>&1; then termux-toast "Fleshpunk image generation failed. Exit $rc. Open receipts for details." >/dev/null 2>&1 || true; fi
  exit "$rc"
fi
EOF
chmod 700 "$BIN/venice-image-ui"
cat > "$BOOT/15-atom" <<'EOF'
#!/data/data/com.termux/files/usr/bin/sh
STATE="$HOME/.local/state/atom"
mkdir -p "$STATE"
if [ -f "$STATE/server.pid" ] && kill -0 "$(cat "$STATE/server.pid" 2>/dev/null)" 2>/dev/null; then exit 0; fi
nohup "$HOME/bin/atom" >>"$STATE/server.log" 2>&1 &
echo $! > "$STATE/server.pid"
EOF
chmod 700 "$BOOT/15-atom"
bash "$ROOT/tools/setup_vlad_swarm_daemon.sh" ensure
"$BOOT/15-atom"
sleep 1
if command -v curl >/dev/null 2>&1; then
  curl -fsS http://127.0.0.1:8788/v1/atom/status >/dev/null || { echo "BLOCKED: Atom did not answer local health" >&2; exit 3; }
fi
if command -v termux-notification >/dev/null 2>&1; then
  termux-notification \
    --id 6500 \
    --ongoing true \
    --priority high \
    --title 'Atom Command Center' \
    --content 'Command the Fortress from the phone. Chromium Throne, Judgment Jars, and Fleshpunk image generation are ready here.' \
    --button1 'Open Atom' \
    --button1-action "bash -l -c '$HOME/bin/atom-open'" \
    --button2 'Diagnose & repair' \
    --button2-action "bash -l -c '$HOME/bin/phone-hands-watchdog diagnose'" \
    --button3 'Fleshpunk Image' \
    --button3-action "bash -l -c '$HOME/bin/venice-image-ui'" >/dev/null 2>&1 || true
fi
printf 'ATOM_PHONE_INSTALLED root=%s ui=http://127.0.0.1:8788 notification=6500 judgment_jars=%s image_command=%s image_ui=%s\n' "$DEST" "$HOME/.local/state/home-center/vlad-swarm/judgment-jars.json" "$BIN/venice-image" "$BIN/venice-image-ui"
