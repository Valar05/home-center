#!/data/data/com.termux/files/usr/bin/bash
# Fix escaped v3 source and activate only on demonstrably idle Termux.
# Same relay, same player, existing FIFO counters; never delete ambiguous state.
set -Eeuo pipefail
ROOT="$HOME/.ritsu-embodiment"
STATE="$ROOT/receiver-v2"
READY="$STATE/ready"
LIVE="$ROOT/receiver.sh"
BATCH="$ROOT/ritsu_phone_wav_batch.py"
BAD_SHA="cd71d8d2215ba369aa489aea65b35911fdaf9c7ca59e41e6bcd342a5d02c4e32"
FIX_SHA="55c0fb71168573145de842bf217a3136d942654053f0f785993de8b23abef015"
V2_SHA="8acd84673b91420dddac5705829e17997ca9dfcde87e5f3d3f35b872f219322f"
V2_BACKUP="$ROOT/receiver-backups/v3-source-20261023T221843Z/receiver.sh"
BASE="https://raw.githubusercontent.com/Valar05/home-center/7cbbe2a363afbdf6d6e421d7af4627b19bd42019/tools/campaigns"
COORD_LOCK=""
TMP=""
PHASE="preflight"
receipt() {
  printf '%s\n' "$1"
  if command -v termux-clipboard-set >/dev/null 2>&1; then
    printf '%s\n' "$1" | termux-clipboard-set >/dev/null 2>&1 || true
  fi
}
onerror() {
  local e="$?"
  trap - ERR
  receipt "RITSU_V3_ACTIVATION_FAILED
PHASE=$PHASE
EXIT_CODE=$e
DO_NOT_CLEAR_FIFO_OR_REPLAY=1"
  exit "$e"
}
cleanup() {
  if [ -n "$TMP" ] && [ -d "$TMP" ]; then rm -rf "$TMP"; fi
  if [ -n "$COORD_LOCK" ]; then rmdir "$COORD_LOCK" 2>/dev/null || true; fi
}
trap onerror ERR
trap cleanup EXIT
for name in curl python3 bash sha256sum termux-media-player nohup cmp find; do
  command -v "$name" >/dev/null 2>&1 || { receipt "REFUSED missing_tool=$name"; exit 10; }
done
[ -f "$LIVE" ] && [ -f "$BATCH" ] && [ -f "$V2_BACKUP" ] || {
  receipt "REFUSED missing_receiver_or_verified_backup"; exit 11;
}
[ "$(sha256sum "$V2_BACKUP" | cut -d' ' -f1)" = "$V2_SHA" ] ||
  { receipt "REFUSED old_backup_hash_mismatch"; exit 12; }
COORD_LOCK="$STATE/v3-activation.lock"
if ! mkdir "$COORD_LOCK" 2>/dev/null; then
  COORD_LOCK=""
  receipt "REFUSED another_activation_or_stale_lock"; exit 13
fi
CUR="$(sha256sum "$LIVE" | cut -d' ' -f1)"
if [ "$CUR" != "$BAD_SHA" ] && [ "$CUR" != "$FIX_SHA" ]; then
  receipt "REFUSED unknown_receiver_hash=$CUR"; exit 14
fi
PHASE="source-hotfix"
TMP="$(mktemp -d "$ROOT/.v3-hotfix.XXXXXXXX")"
chmod 700 "$TMP"
for name in ritsu_phone_receiver_prefetch_v3.sh ritsu_phone_wav_batch.py test_ritsu_phone_wav_batch.py; do
  curl -fLsS --retry 2 --max-time 30 "$BASE/$name" -o "$TMP/$name"
done
FIX="$TMP/ritsu_phone_receiver_prefetch_v3.sh"
[ "$(sha256sum "$FIX" | cut -d' ' -f1)" = "$FIX_SHA" ] ||
  { receipt "REFUSED correction_source_hash_mismatch"; exit 15; }
bash -n "$FIX"
# Avoid escaped Bash expansions. Inspect literal parameter syntax.
if grep -Fq '\$''{' "$FIX"; then
  receipt "REFUSED escaped_Bash_variables_still_present"; exit 16
fi
grep -Fq '$''{#candidates[@]}' "$FIX"
grep -Fq '$''{#group[@]}' "$FIX"
python3 -m py_compile "$TMP/ritsu_phone_wav_batch.py" "$TMP/test_ritsu_phone_wav_batch.py"
(cd "$TMP" && python3 test_ritsu_phone_wav_batch.py) > "$TMP/tests.log" 2>&1 ||
  { receipt "REFUSED PCM_tests_failed"; exit 17; }
cmp -s "$BATCH" "$TMP/ritsu_phone_wav_batch.py" ||
  { receipt "REFUSED batch_helper_differs_from_tested"; exit 18; }
if [ "$CUR" = "$BAD_SHA" ]; then
  BACK="$ROOT/receiver-backups/v3-escaped-preactivation-$(date -u +%Y%m%dT%H%M%SZ)"
  mkdir -p "$BACK"
  cp -p "$LIVE" "$BACK/receiver.sh"
  [ "$(sha256sum "$LIVE" | cut -d' ' -f1)" = "$BAD_SHA" ] ||
    { receipt "REFUSED receiver_changed_during_validation"; exit 19; }
  cp "$FIX" "$ROOT/.receiver-v3-patched.$$"
  chmod 700 "$ROOT/.receiver-v3-patched.$$"
  mv -f "$ROOT/.receiver-v3-patched.$$" "$LIVE"
fi
[ "$(sha256sum "$LIVE" | cut -d' ' -f1)" = "$FIX_SHA" ] ||
  { receipt "REFUSED fixed_source_readback_wrong"; exit 20; }
PHASE="idle-verification"
idle() {
  [ ! -e "$STATE/playing" ] &&
  [ ! -e "$STATE/ack.pending" ] &&
  [ ! -e "$STATE/stop.request" ] &&
  [ -d "$STATE/lock" ] &&
  [ -f "$STATE/play.seq" ] &&
  [ -f "$STATE/fetch.seq" ] &&
  [ "$(cat "$STATE/play.seq")" = "$(cat "$STATE/fetch.seq")" ] &&
  [ -z "$(find "$READY" -maxdepth 1 -name '*.part*' -print -quit)" ] &&
  [ ! -f "$READY/$(printf '%08d' "$(cat "$STATE/play.seq")")_"*.wav ] &&
  [[ "$(termux-media-player info 2>/dev/null)" == *"No track currently!"* ]]
}
if ! idle; then
  receipt "RITSU_V3_HOTFIXED=1
SOURCE_SHA256=$FIX_SHA
ACTIVATION=DEFERRED_PHONE_NOT_IDLE
CURRENT_RECEIVER=UNCHANGED
RUN_AGAIN_WHEN_IDLE"
  exit 0
fi
sleep 2
if ! idle; then
  receipt "RITSU_V3_HOTFIXED=1
ACTIVATION=DEFERRED_IDLE_NOT_STABLE
CURRENT_RECEIVER=UNCHANGED"
  exit 0
fi
PHASE="graceful-stop"
touch "$STATE/stop.request"
STOPPED=0
for i in $(seq 1 60); do
  if [ ! -d "$STATE/lock" ]; then STOPPED=1; break; fi
  sleep .25
done
if [ "$STOPPED" != 1 ]; then
  receipt "RITSU_V3_HOTFIXED=1
ACTIVATION=STOP_NOT_ACKNOWLEDGED
DO_NOT_FORCE_RESTART_OR_DELETE_STOP_REQUEST=1"
  exit 21
fi
if [ -e "$STATE/playing" ] ||
   [[ "$(termux-media-player info 2>/dev/null)" != *"No track currently!"* ]]; then
  receipt "RITSU_V3_HOTFIXED=1
ACTIVATION=AMBIGUOUS_AFTER_STOP
DO_NOT_CLEAR_PLAYING_OR_RESTART=1"
  exit 22
fi
PHASE="launch-v3"
rm -f "$STATE/stop.request"
nohup bash "$LIVE" >> "$ROOT/receiver-v3.log" 2>&1 </dev/null &
pid=$!
sleep 2
if ! kill -0 "$pid" 2>/dev/null || [ ! -d "$STATE/lock" ] || [ -e "$STATE/playing" ]; then
  receipt "RITSU_V3_HOTFIXED=1
ACTIVATION=START_UNVERIFIED
PID=$pid
LOG=$ROOT/receiver-v3.log
DO_NOT_REPLAY_OR_FORCE_CLEAR_STATE=1"
  exit 23
fi
receipt "RITSU_V3_RECEIVER_ACTIVE=1
SOURCE_SHA256=$FIX_SHA
PROCESS_PID=$pid
PLAY_SEQ=$(cat "$STATE/play.seq")
FETCH_SEQ=$(cat "$STATE/fetch.seq")
RELAY=19643
PLAYER=termux-media-player
CUT_SAMPLES=0
HEARD=unverified"
