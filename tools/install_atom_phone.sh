#!/data/data/com.termux/files/usr/bin/sh
set -eu
ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
SRC="$ROOT/atom"
DEST="$HOME/.local/share/atom"
BIN="$HOME/bin"
BOOT="$HOME/.termux/boot"
STATE="$HOME/.local/state/atom"
[ -f "$SRC/server.mjs" ] || { echo "BLOCKED: Atom source missing at $SRC" >&2; exit 2; }
mkdir -p "$DEST" "$BIN" "$BOOT" "$STATE"
rm -rf "$DEST.new"
mkdir -p "$DEST.new"
cp -R "$SRC/." "$DEST.new/"
rm -rf "$DEST.old"
[ ! -d "$DEST" ] || mv "$DEST" "$DEST.old"
mv "$DEST.new" "$DEST"
cat > "$BIN/atom" <<'EOF'
#!/data/data/com.termux/files/usr/bin/sh
exec node "$HOME/.local/share/atom/server.mjs" "$@"
EOF
chmod 700 "$BIN/atom"
cat > "$BIN/atom-open" <<'EOF'
#!/data/data/com.termux/files/usr/bin/sh
URL='http://127.0.0.1:8788/'
if command -v termux-open-url >/dev/null 2>&1; then exec termux-open-url "$URL"; fi
exec am start -a android.intent.action.VIEW -d "$URL"
EOF
chmod 700 "$BIN/atom-open"
cat > "$BOOT/15-atom" <<'EOF'
#!/data/data/com.termux/files/usr/bin/sh
STATE="$HOME/.local/state/atom"
mkdir -p "$STATE"
if [ -f "$STATE/server.pid" ] && kill -0 "$(cat "$STATE/server.pid" 2>/dev/null)" 2>/dev/null; then exit 0; fi
nohup "$HOME/bin/atom" >>"$STATE/server.log" 2>&1 &
echo $! > "$STATE/server.pid"
EOF
chmod 700 "$BOOT/15-atom"
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
    --content 'Command the Fortress from the phone. Chromium Throne is inside.' \
    --button1 'Open Atom' \
    --button1-action "bash -l -c '$HOME/bin/atom-open'" \
    --button2 'Diagnose & repair' \
    --button2-action "bash -l -c '$HOME/bin/phone-hands-watchdog diagnose'" >/dev/null 2>&1 || true
fi
printf 'ATOM_PHONE_INSTALLED root=%s ui=http://127.0.0.1:8788 notification=6500\n' "$DEST"
