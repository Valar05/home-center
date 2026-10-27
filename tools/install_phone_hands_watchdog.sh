#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

REPO_ROOT="${1:-/storage/emulated/0/Documents/GodotProjects/home-center}"
SRC="$REPO_ROOT/tools/phone_hands_watchdog.sh"
BIN="$HOME/bin/phone-hands-watchdog"
BOOT_DIR="$HOME/.termux/boot"
BOOT="$BOOT_DIR/20-phone-hands-watchdog"
STATE_DIR="$HOME/.local/state/home-center"
LOOP_PIDFILE="$STATE_DIR/phone-hands-watchdog-loop.pid"
JOB_ID="6405"

[ -f "$SRC" ] || { echo "missing watchdog source: $SRC" >&2; exit 2; }
[ -f "$REPO_ROOT/tools/home_center_phone_relay_recover.sh" ] || { echo "missing relay recovery source" >&2; exit 3; }

mkdir -p "$HOME/bin" "$BOOT_DIR" "$STATE_DIR"
cp "$SRC" "$BIN"
chmod 700 "$BIN"

cat > "$BOOT" <<EOF
#!/data/data/com.termux/files/usr/bin/bash
export PHONE_HANDS_REPO_ROOT="$REPO_ROOT"
export PHONE_HANDS_WATCHDOG_INTERVAL=60
nohup "$BIN" loop >>"$STATE_DIR/phone-hands-watchdog-boot.log" 2>&1 &
EOF
chmod 700 "$BOOT"

# One watchdog implementation, two launch triggers:
# - the boot hook owns the 60s resident loop;
# - JobScheduler is only a persisted 15-minute backstop if Android kills the loop.
# Both paths use the same run lock and the same canonical recovery primitive.
if command -v termux-job-scheduler >/dev/null 2>&1; then
  termux-job-scheduler --cancel --job-id "$JOB_ID" >/dev/null 2>&1 || true
  PHONE_HANDS_REPO_ROOT="$REPO_ROOT" termux-job-scheduler     --script "$BIN"     --job-id "$JOB_ID"     --period-ms 900000     --network none     --battery-not-low false     --storage-not-low false     --charging false     --persisted true >/dev/null 2>&1 || true
fi

alive=0
if [ -f "$LOOP_PIDFILE" ]; then
  pid="$(cat "$LOOP_PIDFILE" 2>/dev/null || true)"
  [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null && alive=1 || true
fi

if [ "$alive" -eq 0 ]; then
  rm -f "$LOOP_PIDFILE" 2>/dev/null || true
  PHONE_HANDS_REPO_ROOT="$REPO_ROOT" nohup "$BIN" loop >>"$STATE_DIR/phone-hands-watchdog-install.log" 2>&1 &
fi

PHONE_HANDS_REPO_ROOT="$REPO_ROOT" "$BIN" once >/dev/null 2>&1 || true

sleep 1
pid="$(cat "$LOOP_PIDFILE" 2>/dev/null || true)"
if [ -z "$pid" ] || ! kill -0 "$pid" 2>/dev/null; then
  printf 'PHONE_HANDS_WATCHDOG_INSTALL_FAILED loop_not_alive\n' >&2
  exit 4
fi

printf 'PHONE_HANDS_WATCHDOG_ACTIVE bin=%s boot=%s loop_pid=%s job_id=%s no_wakelock=1 no_notification=1 canonical_recovery=1\n'   "$BIN" "$BOOT" "$pid" "$JOB_ID"
