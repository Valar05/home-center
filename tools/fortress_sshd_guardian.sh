#!/data/data/com.termux/files/usr/bin/bash
set -u
STATE="$HOME/.local/state/home-center/sshd-guardian"
LOG="$STATE/guardian.log"
PIDFILE="$STATE/guardian.pid"
mkdir -p "$STATE"
listener_up() {
  python - <<'PY'
import socket
s=socket.socket(); s.settimeout(1.5)
try:
    s.connect(("127.0.0.1",8022))
except OSError:
    raise SystemExit(1)
finally:
    s.close()
raise SystemExit(0)
PY
}
start_sshd() {
  if listener_up; then return 0; fi
  "$PREFIX/bin/sshd" >>"$LOG" 2>&1 || true
  sleep 1
  listener_up
}
start_guardian() {
  if [ -s "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then return 0; fi
  nohup bash "$0" daemon >>"$STATE/boot.log" 2>&1 &
  echo $! > "$PIDFILE"
}
case "${1:-ensure}" in
  check)
    if listener_up; then echo 'SSH_LISTENER=UP PORT=8022'; exit 0; fi
    echo 'SSH_LISTENER=DOWN PORT=8022'; exit 1 ;;
  repair)
    if start_sshd; then echo 'SSH_REPAIR=OK PORT=8022'; exit 0; fi
    echo 'SSH_REPAIR=FAILED PORT=8022'; tail -40 "$LOG" 2>/dev/null || true; exit 1 ;;
  ensure)
    start_sshd || { echo 'SSH_ENSURE=FAILED PORT=8022'; exit 1; }
    start_guardian
    echo "SSH_ENSURE=OK PORT=8022 GUARDIAN_PID=$(cat "$PIDFILE")" ;;
  daemon)
    echo $$ > "$PIDFILE"
    while :; do
      if ! listener_up; then
        printf '%s listener_down; repairing\n' "$(date -u +%FT%TZ)" >>"$LOG"
        if start_sshd; then printf '%s repair_ok\n' "$(date -u +%FT%TZ)" >>"$LOG"; else printf '%s repair_failed\n' "$(date -u +%FT%TZ)" >>"$LOG"; fi
      fi
      sleep 20
    done ;;
  *) echo 'usage: fortress_sshd_guardian.sh [check|repair|ensure|daemon]' >&2; exit 2 ;;
esac
