#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

STATE_ROOT="${HC_STATE_DIR:-$HOME/.local/state/home-center}"
STAMP="$(date '+%Y%m%d-%H%M%S')"
ARCHIVE_ROOT="/sdcard/Fortress-Graveyard/Termux/legacy-decommission-$STAMP"
OVERLAY_PACKAGE="com.homecenter.operatoroverlay"
mkdir -p "$ARCHIVE_ROOT"/{state,boot,receipts}

cp -a "$STATE_ROOT/." "$ARCHIVE_ROOT/state/" 2>/dev/null || true
cp -a "$HOME/.termux/boot/." "$ARCHIVE_ROOT/boot/" 2>/dev/null || true
ps -A -o USER,PID,PPID,NAME,ARGS > "$ARCHIVE_ROOT/receipts/processes-before.txt" 2>&1 || true
command -v termux-job-scheduler >/dev/null 2>&1 && termux-job-scheduler --pending > "$ARCHIVE_ROOT/receipts/jobs-before.txt" 2>&1 || true

for pattern in \
  'phone-hands-watchdog' \
  'fortress_status_relay.py' \
  'home_center_status_menu.sh' \
  'adam_phone_campaign.sh' \
  'recover_adam_overlay_phone.sh' \
  'home-center-forge' \
  'adam --resume' \
  'adam --daemon'; do
  pgrep -f "$pattern" 2>/dev/null | while read -r pid; do
    [ "$pid" = "$$" ] && continue
    [ "$pid" = "$PPID" ] && continue
    cmd="$(tr '\0' ' ' < "/proc/$pid/cmdline" 2>/dev/null || true)"
    case "$cmd" in
      *decommission_termux_legacy.sh*|*fortress-sshd-guardian*|*sshd*) continue ;;
    esac
    kill "$pid" 2>/dev/null || true
    sleep 0.1
    kill -9 "$pid" 2>/dev/null || true
  done
done

for f in \
  "$HOME/.termux/boot/20-phone-hands-watchdog" \
  "$HOME/.termux/boot/30-home-center" \
  "$HOME/.termux/boot/40-adam-campaign" \
  "$HOME/.termux/boot/50-home-center-status"; do
  [ -e "$f" ] && rm -f "$f"
done

if command -v termux-job-scheduler >/dev/null 2>&1; then
  termux-job-scheduler --cancel --job-id 6405 >/dev/null 2>&1 || true
fi

if command -v termux-notification-remove >/dev/null 2>&1; then
  for id in 6404 6405 6410; do
    termux-notification-remove "$id" >/dev/null 2>&1 || true
  done
fi

# Disable the Android overlay without uninstalling it. The APK remains on the
# device for archaeology, but it cannot draw over apps or restart its service.
RISH_BIN="${RISH:-$(command -v rish 2>/dev/null || true)}"
if [ -n "$RISH_BIN" ] && [ -x "$RISH_BIN" ]; then
  "$RISH_BIN" -c "pm list packages $OVERLAY_PACKAGE; appops get $OVERLAY_PACKAGE SYSTEM_ALERT_WINDOW 2>/dev/null || true" \
    > "$ARCHIVE_ROOT/receipts/operator-overlay-before.txt" 2>&1 || true
  "$RISH_BIN" -c "am force-stop $OVERLAY_PACKAGE 2>/dev/null || true; cmd appops set $OVERLAY_PACKAGE SYSTEM_ALERT_WINDOW deny 2>/dev/null || true; pm disable-user --user 0 $OVERLAY_PACKAGE 2>/dev/null || true" \
    > "$ARCHIVE_ROOT/receipts/operator-overlay-disable.txt" 2>&1 || true
  "$RISH_BIN" -c "pm list packages -d $OVERLAY_PACKAGE; appops get $OVERLAY_PACKAGE SYSTEM_ALERT_WINDOW 2>/dev/null || true" \
    > "$ARCHIVE_ROOT/receipts/operator-overlay-after.txt" 2>&1 || true
fi

command -v termux-wake-unlock >/dev/null 2>&1 && termux-wake-unlock >/dev/null 2>&1 || true

rm -f \
  "$STATE_ROOT/phone-hands-watchdog-loop.pid" \
  "$STATE_ROOT/phone-hands-worker.pid" \
  "$STATE_ROOT/phone-hands-last-notice" 2>/dev/null || true

ps -A -o USER,PID,PPID,NAME,ARGS > "$ARCHIVE_ROOT/receipts/processes-after.txt" 2>&1 || true
command -v termux-job-scheduler >/dev/null 2>&1 && termux-job-scheduler --pending > "$ARCHIVE_ROOT/receipts/jobs-after.txt" 2>&1 || true

cat > "$ARCHIVE_ROOT/receipts/DECOMMISSIONED.txt" <<EOF
FORTRESS ONLINE — TERMUX LEGACY DECOMMISSION
archive=$ARCHIVE_ROOT
legacy_watchdog=disabled
legacy_persisted_job_6405=cancelled
legacy_notifications=removed
legacy_global_wakelock=released
operator_overlay=disabled_if_rish_available
ssh_guardian=preserved
sshd=preserved
result=CLEAN_SLATE_PENDING_OBSERVATION
EOF

printf 'TERMUX_LEGACY_DECOMMISSIONED archive=%s ssh=preserved overlay=disabled_if_authorized\n' "$ARCHIVE_ROOT"
