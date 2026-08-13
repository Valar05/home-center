#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
SOURCE="$ROOT/tools/spotify_radio.py"
LIB_ROOT="${HC_SPOTIFY_RADIO_LIB:-$HOME/.local/lib/home-center/spotify-radio}"
STATE_ROOT="${HC_SPOTIFY_RADIO_STATE:-$HOME/.local/state/home-center/spotify-radio}"
BIN_DIR="$HOME/bin"
BOOT_DIR="$HOME/.termux/boot"
CONTROLLER="$LIB_ROOT/spotify_radio.py"
WRAPPER="$BIN_DIR/fortress-radio"
BOOT_SCRIPT="$BOOT_DIR/home-center-spotify-radio.sh"
LOG="$STATE_ROOT/monitor.log"
PID_FILE="$STATE_ROOT/monitor.pid"

[ -f "$SOURCE" ] || { echo "BLOCKED: missing $SOURCE" >&2; exit 2; }
python -m py_compile "$SOURCE"
mkdir -p "$LIB_ROOT" "$STATE_ROOT" "$BIN_DIR" "$BOOT_DIR"
install -m 700 "$SOURCE" "$CONTROLLER"

cat > "$WRAPPER" <<EOF
#!/data/data/com.termux/files/usr/bin/bash
exec python '$CONTROLLER' "\$@"
EOF
chmod 700 "$WRAPPER"

cat > "$BOOT_SCRIPT" <<EOF
#!/data/data/com.termux/files/usr/bin/bash
set -u
STATE='$STATE_ROOT'
CONTROLLER='$CONTROLLER'
mkdir -p "\$STATE"
if pgrep -f "python .*spotify_radio.py monitor" >/dev/null 2>&1; then
  exit 0
fi
nohup python "\$CONTROLLER" monitor >>"\$STATE/monitor.log" 2>&1 &
printf '%s\n' "\$!" > "\$STATE/monitor.pid"
EOF
chmod 700 "$BOOT_SCRIPT"

if [ -f "$PID_FILE" ]; then
  old_pid="$(cat "$PID_FILE" 2>/dev/null || true)"
  if [ -n "$old_pid" ] && kill -0 "$old_pid" 2>/dev/null; then
    kill "$old_pid" 2>/dev/null || true
    sleep 1
  fi
fi

nohup python "$CONTROLLER" monitor >>"$LOG" 2>&1 &
monitor_pid=$!
printf '%s\n' "$monitor_pid" > "$PID_FILE"
sleep 1
kill -0 "$monitor_pid" 2>/dev/null || {
  echo "BLOCKED: Spotify radio monitor exited; inspect $LOG" >&2
  tail -80 "$LOG" >&2 || true
  exit 3
}

doctor_json="$("$WRAPPER" doctor)"
controller_sha="$(sha256sum "$CONTROLLER" | awk '{print $1}')"
wrapper_sha="$(sha256sum "$WRAPPER" | awk '{print $1}')"
boot_sha="$(sha256sum "$BOOT_SCRIPT" | awk '{print $1}')"

python - "$doctor_json" "$monitor_pid" "$CONTROLLER" "$controller_sha" "$WRAPPER" "$wrapper_sha" "$BOOT_SCRIPT" "$boot_sha" <<'PY'
import json
import sys

doctor = json.loads(sys.argv[1])
print(json.dumps({
    "schema": "home-center.spotify-radio.install-receipt.v1",
    "ok": doctor.get("ok") is True,
    "controller": {"path": sys.argv[3], "sha256": sys.argv[4]},
    "wrapper": {"path": sys.argv[5], "sha256": sys.argv[6]},
    "bootScript": {"path": sys.argv[7], "sha256": sys.argv[8]},
    "monitorPid": int(sys.argv[2]),
    "doctor": doctor,
    "provider": "spotify-android",
    "spotifyCredentialsStored": False,
    "spotifyWebApiUsed": False,
}, ensure_ascii=False, sort_keys=True))
PY
