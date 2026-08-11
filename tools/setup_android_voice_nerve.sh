#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
STATE="$HOME/.local/state/home-center"
BIN="$HOME/bin"
mkdir -p "$STATE" "$BIN"
cat > "$BIN/home-center-voice-nerve" <<EOF
#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
exec python3 '$ROOT/tools/android_voice_nerve.py' "\$@"
EOF
chmod +x "$BIN/home-center-voice-nerve"
PID="$STATE/voice-nerve.pid"
LOG="$STATE/voice-nerve.log"
if [ -f "$PID" ]; then
  old="$(cat "$PID" 2>/dev/null || true)"
  if [ -n "$old" ]; then kill "$old" 2>/dev/null || true; fi
fi
: > "$LOG"
nohup "$BIN/home-center-voice-nerve" >>"$LOG" 2>&1 &
echo $! > "$PID"
sleep 2
if ! kill -0 "$(cat "$PID")" 2>/dev/null; then
  echo "BLOCKED: voice nerve exited" >&2
  cat "$LOG" >&2
  exit 3
fi
echo "Voice nerve running: $(cat "$PID")"
tail -5 "$LOG"
