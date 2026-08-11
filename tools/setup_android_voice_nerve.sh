#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
STATE="$HOME/.local/state/home-center"
BIN="$HOME/bin"
mkdir -p "$STATE" "$BIN"
install -m 755 "$ROOT/tools/android_voice_nerve.py" "$BIN/home-center-voice-nerve"
PID="$STATE/voice-nerve.pid"
LOG="$STATE/voice-nerve.log"
if [ -f "$PID" ]; then
  old="$(cat "$PID" 2>/dev/null || true)"
  if [ -n "$old" ]; then kill "$old" 2>/dev/null || true; fi
fi
nohup "$BIN/home-center-voice-nerve" >>"$LOG" 2>&1 &
echo $! > "$PID"
sleep 1
kill -0 "$(cat "$PID")"
echo "Voice nerve running: $(cat "$PID")"
