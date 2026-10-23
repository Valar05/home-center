#!/data/data/com.termux/files/usr/bin/bash
# Canonical Ritsu phone receiver: prefetch up to three files while playing.
# Same existing 19643 Tailscale relay and Termux media player. Staged only.
set -Eeuo pipefail
DIR="${RITSU_RECEIVER_DIR:-$HOME/.ritsu-embodiment}"
HOST="$(cat "$DIR/host")"
TOKEN="$(cat "$DIR/token")"
URL="http://$HOST:19643"
AUTH="Authorization: Bearer $TOKEN"
STATE="$DIR/receiver-v2"
READY="$STATE/ready"
mkdir -p "$READY"
chmod 700 "$STATE" "$READY"
LOCK="$STATE/lock"
if ! mkdir "$LOCK" 2>/dev/null; then
  echo 'RITSU_V2_ALREADY_RUNNING_OR_STALE_LOCK' >&2; exit 3
fi
fetch_pid=''
cleanup() {
  if [ -n "$fetch_pid" ]; then kill "$fetch_pid" 2>/dev/null || true; wait "$fetch_pid" 2>/dev/null || true; fi
  rmdir "$LOCK" 2>/dev/null || true
}
trap cleanup EXIT
trap 'exit 143' TERM INT
if [ -f "$STATE/playing" ]; then
  echo 'RITSU_V2_AMBIGUOUS_INTERRUPTED_PLAYBACK: refusing automatic replay or skip' >&2
  exit 4
fi
if [ ! -f "$STATE/fetch.seq" ]; then printf '1\n' > "$STATE/fetch.seq"; fi
if [ ! -f "$STATE/play.seq" ]; then printf '1\n' > "$STATE/play.seq"; fi

utc() { date -u '+%Y-%m-%dT%H:%M:%S.%3NZ'; }
mono_ms() { awk '{printf "%.0f", $1*1000}' /proc/uptime 2>/dev/null || date +%s%3N; }
trace() {
  local event="$1" sequence="$2" id="$3"
  printf '{"event":"%s","seq":%d,"relayId":"%s","utc":"%s","deviceMonotonicMs":%s}\n' \
    "$event" "$sequence" "$id" "$(utc)" "$(mono_ms)" >> "$STATE/trace.jsonl"
}
atomic_number() {
  local path="$1" number="$2"
  printf '%d\n' "$number" > "$path.tmp.$$"
  mv -f "$path.tmp.$$" "$path"
}
ack_id() {
  local id="$1" response
  response="$(curl -fsS --max-time 8 -H "$AUTH" -H 'Content-Type: application/json' \
      -d "{\"id\":\"$id\"}" "$URL/ack")" || return 1
  printf '%s' "$response" | jq -e '.ok == true' >/dev/null 2>&1
}
recover_pending_ack() {
  [ -f "$STATE/ack.pending" ] || return 0
  local seq id next
  read -r seq id < "$STATE/ack.pending"
  [[ "$seq" =~ ^[0-9]+$ && "$id" =~ ^[a-f0-9]{24}$ ]] || return 1
  [ -f "$READY/$(printf '%08d' "$seq")_${id}.wav" ] || return 1
  next="$(cat "$STATE/fetch.seq")"
  if [ "$next" -le "$seq" ]; then atomic_number "$STATE/fetch.seq" "$((seq+1))"; fi
  ack_id "$id" || return 1
  rm -f "$STATE/ack.pending"
  trace ack_recovered "$seq" "$id"
}
fetch_loop() {
  while :; do
    if ! recover_pending_ack; then sleep 1; continue; fi
    local f p response id filename part bytes
    f="$(cat "$STATE/fetch.seq")"
    p="$(cat "$STATE/play.seq")"
    [[ "$f" =~ ^[0-9]+$ && "$p" =~ ^[0-9]+$ ]] || exit 2
    if (( f-p >= 3 )); then sleep .15; continue; fi
    response="$(curl -fsS --max-time 6 -H "$AUTH" "$URL/next" 2>/dev/null)" || { sleep .5; continue; }
    id="$(printf '%s' "$response" | jq -r '.id // empty' 2>/dev/null || true)"
    if [[ ! "$id" =~ ^[a-f0-9]{24}$ ]]; then sleep .20; continue; fi
    filename="$READY/$(printf '%08d' "$f")_${id}.wav"
    part="$filename.part.$$"
    if ! curl -fsS --max-time 45 -H "$AUTH" "$URL/audio/$id" -o "$part"; then
      rm -f "$part"; sleep .5; continue
    fi
    bytes="$(wc -c < "$part")"
    if (( bytes <= 44 )) || [ "$(head -c 4 "$part")" != RIFF ]; then
      rm -f "$part"; echo "RITSU_V2_INVALID_WAV seq=$f" >&2; sleep .5; continue
    fi
    mv -f "$part" "$filename"
    trace fetched "$f" "$id"
    printf '%d %s\n' "$f" "$id" > "$STATE/ack.pending.tmp.$$"
    mv -f "$STATE/ack.pending.tmp.$$" "$STATE/ack.pending"
    atomic_number "$STATE/fetch.seq" "$((f+1))"
    if ! ack_id "$id"; then sleep .5; continue; fi
    rm -f "$STATE/ack.pending"
    trace acknowledged "$f" "$id"
  done
}

play_loop() {
  while :; do
    local seq item id result info unknown
    seq="$(cat "$STATE/play.seq")"
    [[ "$seq" =~ ^[0-9]+$ ]] || exit 2
    shopt -s nullglob
    local candidates=("$READY/$(printf '%08d' "$seq")_"*.wav)
    shopt -u nullglob
    if [ "${#candidates[@]}" -eq 0 ]; then sleep .15; continue; fi
    if [ "${#candidates[@]}" -ne 1 ]; then echo 'RITSU_V2_DUPLICATE_FIFO_SLOT' >&2; exit 5; fi
    item="${candidates[0]}"
    id="${item##*/}"; id="${id#*_}"; id="${id%.wav}"
    [[ "$id" =~ ^[a-f0-9]{24}$ ]] || exit 5
    # Fail closed after interrupted playback instead of replaying or skipping.
    printf '%d %s\n' "$seq" "$id" > "$STATE/playing.tmp.$$"
    mv -f "$STATE/playing.tmp.$$" "$STATE/playing"
    result="$(termux-media-player play "$item")" || { echo "RITSU_V2_PLAY_FAILED $seq" >&2; exit 6; }
    if [[ "$result" != Now\ Playing:* ]]; then echo "RITSU_V2_PLAY_NO_CONFIRMATION $seq" >&2; exit 6; fi
    trace playback_started "$seq" "$id"
    unknown=0
    while :; do
      if ! info="$(termux-media-player info 2>/dev/null)"; then
        unknown=$((unknown+1))
      elif [[ "$info" == *'No track currently!'* ]]; then
        break
      elif [[ "$info" == *'Status: Playing'* || "$info" == *'Status: Paused'* ]]; then
        unknown=0
      else
        unknown=$((unknown+1))
      fi
      if (( unknown > 30 )); then echo "RITSU_V2_PLAYER_STATE_UNKNOWN $seq" >&2; exit 7; fi
      sleep .15
    done
    trace playback_finished "$seq" "$id"
    atomic_number "$STATE/play.seq" "$((seq+1))"
    rm -f "$STATE/playing"
    # WAVs retained locally for debugging, without any additional transport.
  done
}

for c in curl jq termux-media-player awk; do command -v "$c" >/dev/null || { echo "MISSING_TOOL $c" >&2; exit 8; }; done
termux-wake-lock >/dev/null 2>&1 || true
trace receiver_started 0 000000000000000000000000
fetch_loop & fetch_pid="$!"
play_loop
