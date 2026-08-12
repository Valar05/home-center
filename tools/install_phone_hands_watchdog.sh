#!/data/data/com.termux/files/usr/bin/bash
set -eu

REPO_ROOT="${1:-/storage/emulated/0/Documents/GodotProjects/home-center}"
SRC="$REPO_ROOT/tools/phone_hands_watchdog.sh"
BIN="$HOME/bin/phone-hands-watchdog"
BOOT_DIR="$HOME/.termux/boot"
BOOT="$BOOT_DIR/20-phone-hands-watchdog"
STATE_DIR="$HOME/.local/state/home-center"
LOOP_PIDFILE="$STATE_DIR/phone-hands-watchdog-loop.pid"
JOB_ID="6405"

[ -f "$SRC" ] || { echo "missing watchdog source: $SRC" >&2; exit 2; }
mkdir -p "$HOME/bin" "$BOOT_DIR" "$STATE_DIR"
cp "$SRC" "$BIN"
chmod 700 "$BIN"

cat > "$BOOT" <<EOF
#!/data/data/com.termux/files/usr/bin/bash
termux-wake-lock >/dev/null 2>&1 || true
nohup "$BIN" loop >"$STATE_DIR/phone-hands-watchdog-boot.log" 2>&1 &
EOF
chmod 700 "$BOOT"

if command -v termux-job-scheduler >/dev/null 2>&1; then
  termux-job-scheduler --script "$BIN" --job-id "$JOB_ID" --period-ms 900000 \
    --network none --battery-not-low false --storage-not-low false --charging false --persisted true >/dev/null 2>&1 || true
fi

alive=0
if [ -f "$LOOP_PIDFILE" ]; then
  pid="$(cat "$LOOP_PIDFILE" 2>/dev/null || true)"
  [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null && alive=1 || true
fi

if [ "$alive" -eq 0 ]; then
  rm -f "$LOOP_PIDFILE" 2>/dev/null || true
  nohup "$BIN" loop >"$STATE_DIR/phone-hands-watchdog-install.log" 2>&1 &
fi

"$BIN" once >/dev/null 2>&1 || true
printf 'PHONE_HANDS_WATCHDOG_INSTALLED bin=%s boot=%s job_id=%s loop_already_alive=%s\n' "$BIN" "$BOOT" "$JOB_ID" "$alive"
