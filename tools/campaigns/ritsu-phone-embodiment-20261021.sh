#!/data/data/com.termux/files/usr/bin/bash
set -Eeuo pipefail
trap 'echo "[RITSU CAMPAIGN] FAILED line $LINENO" >&2' ERR
echo '[RITSU CAMPAIGN] Android receiver / notification prototype'
command -v pkg >/dev/null || { echo 'Run inside Termux'; exit 1; }
command -v sha256sum >/dev/null || { echo 'Missing sha256sum'; exit 1; }
pkg install -y curl jq termux-api
for c in curl jq termux-notification termux-media-player; do command -v "$c" >/dev/null || { echo "Missing $c"; exit 1; }; done
DIR="$HOME/.ritsu-embodiment"
mkdir -p "$DIR/audio" "$DIR/receipts"
if [ -f "$DIR/receiver.pid" ]; then
  old="$(cat "$DIR/receiver.pid")"
  if kill -0 "$old" 2>/dev/null; then
    echo "[RITSU CAMPAIGN] Existing receiver PID $old; stop it before reinstall"; exit 1
  fi
fi
printf 'THECAULDRON Tailscale IP [100.68.37.106]: '
read -r HOST
HOST="${HOST:-100.68.37.106}"
case "$HOST" in *[!0-9.]*|'') echo 'Use an IPv4 address'; exit 1;; esac
printf 'Relay token (shown by Windows relay): '
read -rs TOKEN
printf '\n'
[ -n "$TOKEN" ] || { echo 'Token required'; exit 1; }
printf '%s' "$HOST" > "$DIR/host"
printf '%s' "$TOKEN" > "$DIR/token"
chmod 600 "$DIR/host" "$DIR/token"
cat > "$DIR/control.sh" <<'CONTROL'
#!/data/data/com.termux/files/usr/bin/bash
set -u
DIR="$HOME/.ritsu-embodiment"
case "${1:-}" in
 pause) termux-media-player pause ;;
 resume) [ -f "$DIR/current" ] && termux-media-player play "$(cat "$DIR/current")" ;;
 stop) termux-media-player stop ;;
 *) echo 'Unknown control'; exit 2 ;;
esac
CONTROL
cat > "$DIR/receiver.sh" <<'RECEIVER'
#!/data/data/com.termux/files/usr/bin/bash
set -u
DIR="$HOME/.ritsu-embodiment"
HOST="$(cat "$DIR/host")"
TOKEN="$(cat "$DIR/token")"
URL="http://$HOST:19643"
AUTH="Authorization: Bearer $TOKEN"
termux-wake-lock || true
termux-notification --id 19643 --title 'Ritsu | Embodiment' --content 'Phone receiver active' --ongoing --button1 'Pause' --button1-action "bash $DIR/control.sh pause" --button2 'Resume' --button2-action "bash $DIR/control.sh resume" --button3 'Stop' --button3-action "bash $DIR/control.sh stop" || true
trap 'termux-wake-unlock || true' EXIT
while true; do
 RESPONSE="$(curl -fsS --max-time 5 -H "$AUTH" "$URL/next" 2>/dev/null || true)"
 ID="$(printf '%s' "$RESPONSE" | jq -r '.id // empty' 2>/dev/null || true)"
 if [[ "$ID" =~ ^[A-Za-z0-9_-]+$ ]]; then
   FILE="$DIR/audio/$ID.wav"
   if curl -fsS --max-time 45 -H "$AUTH" "$URL/audio/$ID" -o "$FILE"; then
     printf '%s' "$FILE" > "$DIR/current"
     curl -fsS --max-time 5 -H "$AUTH" -H 'Content-Type: application/json' -d "{\"id\":\"$ID\"}" "$URL/ack" >/dev/null || true
     termux-media-player play "$FILE" || true
     sleep 1
     while termux-media-player info 2>/dev/null | grep -Eiq 'playing|isPlaying.*true'; do sleep 1; done
   fi
 else
   sleep 2
 fi
done
RECEIVER
chmod 700 "$DIR/control.sh" "$DIR/receiver.sh"
echo '[RITSU CAMPAIGN] Preflight: checking Windows relay over Tailscale'
curl -fsS --max-time 8 -H "Authorization: Bearer $TOKEN" "http://$HOST:19643/health" | jq .
nohup bash "$DIR/receiver.sh" > "$DIR/receiver.log" 2>&1 </dev/null &
pid=$!
printf '%s' "$pid" > "$DIR/receiver.pid"
sleep 2
kill -0 "$pid" || { tail -30 "$DIR/receiver.log"; exit 1; }
receipt="$DIR/receipts/install-$(date +%Y%m%d-%H%M%S).txt"
{ echo "status=receiver_running"; echo "pid=$pid"; echo "host=$HOST"; echo "script_sha256=$(sha256sum "$0" | cut -d' ' -f1)"; echo "log=$DIR/receiver.log"; } > "$receipt"
echo "[RITSU CAMPAIGN] PASS: receiver PID $pid"
echo "[RITSU CAMPAIGN] RECEIPT: $receipt"
echo '[RITSU CAMPAIGN] Verify notification and send a test clip from THECAULDRON.'
