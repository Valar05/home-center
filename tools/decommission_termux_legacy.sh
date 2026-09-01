#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

STATE_ROOT="${HC_STATE_DIR:-$HOME/.local/state/home-center}"
STAMP="$(date '+%Y%m%d-%H%M%S')"
ARCHIVE_ROOT="/sdcard/Fortress-Graveyard/Termux/legacy-decommission-$STAMP"
mkdir -p "$ARCHIVE_ROOT"/{state,boot,receipts}

# Preserve evidence before touching resurrection machinery.
cp -a "$STATE_ROOT/." "$ARCHIVE_ROOT/state/" 2>/dev/null || true
cp -a "$HOME/.termux/boot/." "$ARCHIVE_ROOT/boot/" 2>/dev/null || true
ps -A -o USER,PID,PPID,NAME,ARGS > "$ARCHIVE_ROOT/receipts/processes-before.txt" 2>&1 || true
command -v termux-job-scheduler >/dev/null 2>&1 && termux-job-scheduler --pending > "$ARCHIVE_ROOT/receipts/jobs-before.txt" 2>&1 || true

# Stop Home Center/Phone Hands legacy user-space supervisors. Keep sshd and
# fortress-sshd-guardian: SSH is the break-glass maintenance lane.
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

# Remove only Home Center-owned Termux:Boot resurrection entries.
for f in \
  "$HOME/.termux/boot/20-phone-hands-watchdog" \
  "$HOME/.termux/boot/30-home-center" \
  "$HOME/.termux/boot/40-adam-campaign" \
  "$HOME/.termux/boot/50-home-center-status"; do
  [ -e "$f" ] && rm -f "$f"
done

# Cancel the known persisted watchdog job. Do not blanket-cancel unrelated jobs.
if command -v termux-job-scheduler >/dev/null 2>&1; then
  termux-job-scheduler --cancel --job-id 6405 >/dev/null 2>&1 || true
fi

# Remove Home Center's persistent notifications. Best-effort only.
if command -v termux-notification-remove >/dev/null 2>&1; then
  for id in 6404 6405 6410; do
    termux-notification-remove "$id" >/dev/null 2>&1 || true
  done
fi

# The old watchdog leaked a wake lock on every pass. Release it once after all
# legacy workers have been stopped. sshd does not require Termux's global lock.
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
ssh_guardian=preserved
sshd=preserved
result=CLEAN_SLATE_PENDING_OBSERVATION
EOF

printf 'TERMUX_LEGACY_DECOMMISSIONED archive=%s ssh=preserved\n' "$ARCHIVE_ROOT"
