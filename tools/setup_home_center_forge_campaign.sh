#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
ROOT="${HC_REPO_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}"
STATE="${HC_FORGE_CAMPAIGN_STATE:-$HOME/.local/state/home-center/forge-campaign}"
BIN="${PREFIX:-$HOME/.local}/bin/home-center-forge"
mkdir -p "$STATE" "$(dirname "$BIN")"
cat > "$BIN" <<EOF
#!/data/data/com.termux/files/usr/bin/bash
exec python3 "$ROOT/tools/home_center_forge_campaign.py" "\$@"
EOF
chmod 755 "$BIN"

SERVICE="$PREFIX/var/service/home-center-forge"
LOGDIR="$PREFIX/var/log/home-center-forge"
if command -v sv >/dev/null 2>&1 && [ -d "$PREFIX/var/service" ]; then
  mkdir -p "$SERVICE/log" "$LOGDIR"
  cat > "$SERVICE/run" <<EOF
#!/data/data/com.termux/files/usr/bin/bash
exec env HC_REPO_ROOT=$(printf '%q' "$ROOT") python3 $(printf '%q' "$ROOT/tools/home_center_forge_campaign.py") resume 2>&1
EOF
  cat > "$SERVICE/log/run" <<EOF
#!/data/data/com.termux/files/usr/bin/bash
exec svlogd -tt $(printf '%q' "$LOGDIR")
EOF
  chmod 755 "$SERVICE/run" "$SERVICE/log/run"
  sv up home-center-forge || true
else
  PIDFILE="$STATE/supervisor.pid"
  if [ ! -f "$PIDFILE" ] || ! kill -0 "$(cat "$PIDFILE" 2>/dev/null || echo 0)" 2>/dev/null; then
    nohup "$BIN" resume >>"$STATE/supervisor.log" 2>&1 </dev/null &
    echo $! > "$PIDFILE"
  fi
fi

# Stable recovery entry in Termux:Boot when available. Idempotent and harmless when runit owns it.
BOOT="$HOME/.termux/boot"
mkdir -p "$BOOT"
cat > "$BOOT/home-center-forge" <<EOF
#!/data/data/com.termux/files/usr/bin/bash
sleep 8
if command -v sv >/dev/null 2>&1 && [ -d "$PREFIX/var/service/home-center-forge" ]; then
  sv up home-center-forge >/dev/null 2>&1 || true
else
  PIDFILE=$(printf '%q' "$STATE/supervisor.pid")
  if [ ! -f "\$PIDFILE" ] || ! kill -0 "\$(cat \"\$PIDFILE\" 2>/dev/null || echo 0)" 2>/dev/null; then
    nohup $(printf '%q' "$BIN") resume >>$(printf '%q' "$STATE/supervisor.log") 2>&1 </dev/null &
    echo \$! > "\$PIDFILE"
  fi
fi
EOF
chmod 755 "$BOOT/home-center-forge"

python3 "$ROOT/tools/home_center_forge_campaign.py" status
