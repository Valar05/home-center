#!/data/data/com.termux/files/usr/bin/bash
# Ritsu v3: original three-slot prefetch, sample-identical already-ready WAV batching.
# Canonical relay 19643 and termux-media-player unchanged; NO waiting for another WAV. Staged only.
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
if [ -f "$STATE/playing" ] || [ -f "$STATE/stop.request" ]; then
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


trace_batch() {
  local event="$1" first="$2" last="$3" count="$4"
  printf '{"event":"%s","seq":%d,"lastSeq":%d,"count":%d,"utc":"%s","deviceMonotonicMs":%s}\n' \
    "$event" "$first" "$last" "$count" "$(utc)" "$(mono_ms)" >> "$STATE/trace.jsonl"
}
batch_helper="$DIR/ritsu_phone_wav_batch.py"
BATCH_READY="$STATE/combined"
mkdir -p "$BATCH_READY"
chmod 700 "$BATCH_READY"

play_loop() {
  local seq f i id item info result unknown playfile firstid count endseq combined
  local candidates=() group=() ids=() batchlog=""
  while :; do
    seq="$(cat "$STATE/play.seq")"
    [[ "$seq" =~ ^[0-9]+$ ]] || exit 2
    if [ -f "$STATE/stop.request" ]; then echo "RITSU_V3_STOP_REQUESTED" >&2; exit 11; fi
    shopt -s nullglob
    candidates=("$READY/$(printf '%08d' "$seq")_"*.wav)
    shopt -u nullglob
    if [ "\${#candidates[@]}" -eq 0 ]; then
      if ! kill -0 "$fetch_pid" 2>/dev/null; then echo 'RITSU_V3_FETCHER_DIED' >&2; exit 9; fi
      sleep .10; continue
    fi
    if [ "\${#candidates[@]}" -ne 1 ]; then echo 'RITSU_V3_DUPLICATE_FIFO_SLOT' >&2; exit 5; fi
    # All group members MUST already exist; never wait for another clip.
    group=() ids=()
    for ((i=0; i<3; i++)); do
      f=$((seq+i))
      shopt -s nullglob
      candidates=("$READY/$(printf '%08d' "$f")_"*.wav)
      shopt -u nullglob
      [ "\${#candidates[@]}" -eq 0 ] && break
      if [ "\${#candidates[@]}" -ne 1 ]; then echo 'RITSU_V3_DUPLICATE_FIFO_SLOT' >&2; exit 5; fi
      item="\${candidates[0]}"
      id="\${item##*/}"; id="\${id#*_}"; id="\${id%.wav}"
      [[ "$id" =~ ^[a-f0-9]{24}$ ]] || exit 5
      group+=("$item"); ids+=("$id")
    done
    count="\${#group[@]}"
    [ "$count" -gt 0 ] || exit 5
    endseq=$((seq+count-1))
    firstid="\${ids[0]}"
    combined=''
    playfile="\${group[0]}"
    if (( count > 1 )); then
      [ -f "$batch_helper" ] || { echo 'RITSU_V3_BATCH_HELPER_MISSING' >&2; exit 16; }
      combined="$BATCH_READY/$(printf '%08d' "$seq")-$(printf '%08d' "$endseq").wav"
      if [ -e "$combined" ]; then echo 'RITSU_V3_BATCH_ALREADY_EXISTS_AMBIGUOUS' >&2; exit 17; fi
      batchlog="$(python3 "$batch_helper" --output "$combined" "\${group[@]}")" ||
        { echo 'RITSU_V3_BATCH_VERIFY_FAILED' >&2; exit 18; }
      printf '%s' "$batchlog" | jq -e --argjson first "$seq" --argjson last "$endseq" \
        '.status == "verified" and .firstSeq == $first and .lastSeq == $last and .gapInsertedSamples == 0 and .sourceSamplesTrimmed == 0' >/dev/null ||
        { echo 'RITSU_V3_BATCH_RECEIPT_INVALID' >&2; exit 18; }
      playfile="$combined"
    fi
    printf '%d %d %s\n' "$seq" "$endseq" "\${ids[*]}" > "$STATE/playing.tmp.$$"
    mv -f "$STATE/playing.tmp.$$" "$STATE/playing"
    printf '%s' "$playfile" > "$DIR/current"
    result="$(termux-media-player play "$playfile")" ||
      { echo "RITSU_V3_PLAY_FAILED first=$seq last=$endseq" >&2; exit 6; }
    [[ "$result" == Now\ Playing:* ]] ||
      { echo 'RITSU_V3_PLAY_NO_CONFIRMATION' >&2; exit 6; }
    if (( count > 1 )); then
      trace_batch batch_playback_started "$seq" "$endseq" "$count"
    else
      trace playback_started "$seq" "$firstid"
    fi
    unknown=0
    while :; do
      if [ -f "$STATE/stop.request" ]; then echo "RITSU_V3_STOP_REQUESTED" >&2; exit 11; fi
      if ! info="$(termux-media-player info 2>/dev/null)"; then
        unknown=$((unknown+1))
      elif [[ "$info" == *'No track currently!'* ]]; then
        break
      elif [[ "$info" == *'Status: Playing'* || "$info" == *'Status: Paused'* ]]; then
        if [[ "$info" != *"Track: $(basename "$playfile")"* ]]; then
          echo "RITSU_V3_PLAYER_TRACK_MISMATCH first=$seq last=$endseq" >&2; exit 10
        fi
        unknown=0
      else
        unknown=$((unknown+1))
      fi
      if (( unknown > 30 )); then echo 'RITSU_V3_PLAYER_STATE_UNKNOWN' >&2; exit 7; fi
      sleep .12
    done
    if (( count > 1 )); then
      trace_batch batch_playback_finished "$seq" "$endseq" "$count"
    else
      trace playback_finished "$seq" "$firstid"
    fi
    atomic_number "$STATE/play.seq" "$((endseq+1))"
    rm -f "$STATE/playing"
    [ -z "$combined" ] || rm -f -- "$combined"
    for ((f=seq; f<=endseq; f++)); do
      if (( f > 8 )); then rm -f "$READY/$(printf '%08d' "$((f-8))")_"*.wav; fi
    done
  done
}

for c in curl jq termux-media-player awk python3; do command -v "$c" >/dev/null || { echo "MISSING_TOOL $c" >&2; exit 8; }; done
termux-wake-lock >/dev/null 2>&1 || true
trace receiver_started 0 000000000000000000000000
fetch_loop & fetch_pid="$!"
play_loop
