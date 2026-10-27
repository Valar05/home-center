#!/data/data/com.termux/files/usr/bin/bash
# Stable Ritsu mpv receiver campaign: run/resume/status/receipts. Never force replay.
set -Eeuo pipefail
ROOT="$HOME/.ritsu-embodiment"
STATE="$ROOT/receiver-v2"
READY="$STATE/ready"
LIVE="$ROOT/receiver.sh"
DRIVER="$ROOT/ritsu_phone_mpv_driver_v4.py"
RECEIPTS="$STATE/v4-campaign"
BASE="https://raw.githubusercontent.com/Valar05/home-center/4382496d643e99d179c610819377288c9855eab7/tools/campaigns"
OLD_SHA="55c0fb71168573145de842bf217a3136d942654053f0f785993de8b23abef015"
NEW_SHA="46b98a8604dec9ec751ad19d0711285bb80149b20329cc2f878f7942429f04cf"
DRIVER_SHA="2e64f55ae185d9929cd407ee95c0bc4dccd6e8846094bb4ff461c009deec27ea"
TEST_SHA="92c4d021af168924ace0c58c690739bb772540111aa3320c68b139bcd19aa67f"
ACTION="run"
if [ "$#" -gt 0 ]; then ACTION="$1"; fi
TMP=""
LOCK=""
PHASE="preflight"
mkdir -p "$RECEIPTS"
chmod 700 "$RECEIPTS"
receipt() {
  printf '%s\n' "$1"
  printf '%s\n' "$1" >"$RECEIPTS/latest.tmp.$$"
  mv -f "$RECEIPTS/latest.tmp.$$" "$RECEIPTS/latest.txt"
  { date -u '+%Y-%m-%dT%H:%M:%SZ'; printf '%s\n' "$1"; } >>"$RECEIPTS/history.log"
  if command -v termux-clipboard-set >/dev/null 2>&1; then
    printf '%s\n' "$1" | termux-clipboard-set >/dev/null 2>&1 || true
  fi
}
onerror() {
  ec="$?"
  trap - ERR
  receipt "RITSU_MPV_V4_FAILED=1
PHASE=$PHASE
EXIT=$ec
DO_NOT_FORCE_REPLAY_OR_CLEAR_FIFO=1"
  exit "$ec"
}
cleanup() {
  if [ -n "$TMP" ] && [ -d "$TMP" ]; then rm -rf "$TMP"; fi
  if [ -n "$LOCK" ]; then rmdir "$LOCK" 2>/dev/null || true; fi
}
trap onerror ERR
trap cleanup EXIT
hash() { sha256sum "$1" | cut -d' ' -f1; }
if [ "$ACTION" = status ]; then
  printf 'RITSU_MPV_V4_CAMPAIGN_STATUS\n'
  if [ -f "$LIVE" ]; then printf 'RECEIVER_SHA=%s\n' "$(hash "$LIVE")"; fi
  if [ -S "$STATE/ritsu-mpv.sock" ]; then echo 'PERSISTENT_SOCKET=PRESENT'; else echo 'PERSISTENT_SOCKET=ABSENT'; fi
  if [ -f "$STATE/play.seq" ]; then printf 'PLAY_SEQ=%s\n' "$(cat "$STATE/play.seq")"; fi
  if [ -f "$STATE/fetch.seq" ]; then printf 'FETCH_SEQ=%s\n' "$(cat "$STATE/fetch.seq")"; fi
  if [ -e "$STATE/playing" ]; then echo 'UNRESOLVED_PLAYBACK=YES'; else echo 'UNRESOLVED_PLAYBACK=NO'; fi
  if [ -f "$RECEIPTS/latest.txt" ]; then cat "$RECEIPTS/latest.txt"; fi
  exit 0
fi
if [ "$ACTION" = receipts ]; then cat "$RECEIPTS/history.log" 2>/dev/null || true; exit 0; fi
if [ "$ACTION" != run ] && [ "$ACTION" != resume ]; then
  echo 'USAGE=ritsu-mpv run|resume|status|receipts'; exit 2
fi
for cmd in bash curl python3 mpv termux-media-player sha256sum find; do
  command -v "$cmd" >/dev/null 2>&1 || { receipt "RITSU_MPV_V4_REFUSED missing_command=$cmd"; exit 10; }
done
[ -f "$LIVE" ] && [ -f "$STATE/play.seq" ] && [ -f "$STATE/fetch.seq" ] ||
  { receipt 'RITSU_MPV_V4_REFUSED no_canonical_receiver_state'; exit 11; }
LOCK="$STATE/v4-activation.lock"
if ! mkdir "$LOCK" 2>/dev/null; then
  LOCK=""
  receipt 'RITSU_MPV_V4_REFUSED concurrent_or_stale_activation_lock'
  exit 12
fi
CURRENT="$(hash "$LIVE")"
if [ "$CURRENT" != "$OLD_SHA" ] && [ "$CURRENT" != "$NEW_SHA" ]; then
  receipt "RITSU_MPV_V4_REFUSED unrecognized_receiver_sha=$CURRENT"; exit 13
fi
if [ "$CURRENT" = "$NEW_SHA" ] && [ -S "$STATE/ritsu-mpv.sock" ] && [ -d "$STATE/lock" ]; then
  receipt "RITSU_MPV_V4_ALREADY_ACTIVE=1
SOURCE_SHA=$NEW_SHA
HEARD=unverified"
  exit 0
fi
if [ -e "$STATE/playing" ]; then
  receipt 'RITSU_MPV_V4_DEFERRED=1 uncertain_playback_marker_present'
  exit 0
fi
PHASE=download_test_sources
TMP="$(mktemp -d "$ROOT/.ritsu-v4-stage.XXXXXXXX")"
chmod 700 "$TMP"
for name in ritsu_phone_receiver_v4.sh ritsu_phone_mpv_driver_v4.py test_ritsu_phone_mpv_driver_v4.py; do
  curl -fLsS --retry 2 --max-time 35 "$BASE/$name" -o "$TMP/$name"
done
[ "$(hash "$TMP/ritsu_phone_receiver_v4.sh")" = "$NEW_SHA" ] ||
  { receipt 'RITSU_MPV_V4_REFUSED source_hash_mismatch'; exit 14; }
[ "$(hash "$TMP/ritsu_phone_mpv_driver_v4.py")" = "$DRIVER_SHA" ] ||
  { receipt 'RITSU_MPV_V4_REFUSED driver_hash_mismatch'; exit 15; }
[ "$(hash "$TMP/test_ritsu_phone_mpv_driver_v4.py")" = "$TEST_SHA" ] ||
  { receipt 'RITSU_MPV_V4_REFUSED test_hash_mismatch'; exit 16; }
PHASE=isolated_validation
bash -n "$TMP/ritsu_phone_receiver_v4.sh"
python3 -m py_compile "$TMP/ritsu_phone_mpv_driver_v4.py" "$TMP/test_ritsu_phone_mpv_driver_v4.py"
(cd "$TMP" && python3 test_ritsu_phone_mpv_driver_v4.py) >"$RECEIPTS/logic-tests.log" 2>&1 ||
  { tail -n 30 "$RECEIPTS/logic-tests.log" >&2; receipt 'RITSU_MPV_V4_REFUSED_logic_tests'; exit 17; }
PHASE=physical_mpv_ipc_no_speaker
(cd "$TMP" && python3 test_ritsu_phone_mpv_driver_v4.py --live-ipc-null-test) >"$RECEIPTS/ipc-test.log" 2>&1 ||
  { tail -n 30 "$RECEIPTS/ipc-test.log" >&2; receipt 'RITSU_MPV_V4_REFUSED_virtual_audio_test'; exit 18; }
grep -Fxq 'RITSU_MPV_IPC_REAL_NO_AUDIO=PASS' "$RECEIPTS/ipc-test.log" ||
  { receipt 'RITSU_MPV_V4_REFUSED missing_ipc_success'; exit 19; }
PHASE=backup_and_stage
if [ "$CURRENT" = "$OLD_SHA" ]; then
  BACK="$ROOT/receiver-backups/v4-source-$(date -u +%Y%m%dT%H%M%SZ)"
  mkdir -p "$BACK"
  cp -p "$LIVE" "$BACK/receiver.sh"
  [ "$(hash "$BACK/receiver.sh")" = "$OLD_SHA" ] ||
    { receipt 'RITSU_MPV_V4_REFUSED backup_failed'; exit 20; }
fi
if [ -e "$DRIVER" ] && [ "$(hash "$DRIVER")" != "$DRIVER_SHA" ]; then
  receipt 'RITSU_MPV_V4_REFUSED existing_driver_diverged'; exit 21
fi
cp "$TMP/ritsu_phone_mpv_driver_v4.py" "$ROOT/.v4-driver.$$"
chmod 600 "$ROOT/.v4-driver.$$"
mv -f "$ROOT/.v4-driver.$$" "$DRIVER"
if [ "$CURRENT" = "$OLD_SHA" ]; then
  [ "$(hash "$LIVE")" = "$OLD_SHA" ] ||
    { receipt 'RITSU_MPV_V4_REFUSED concurrent_receiver_edit'; exit 22; }
  cp "$TMP/ritsu_phone_receiver_v4.sh" "$ROOT/.v4-receiver.$$"
  chmod 700 "$ROOT/.v4-receiver.$$"
  mv -f "$ROOT/.v4-receiver.$$" "$LIVE"
fi
[ "$(hash "$LIVE")" = "$NEW_SHA" ] && [ "$(hash "$DRIVER")" = "$DRIVER_SHA" ] ||
  { receipt 'RITSU_MPV_V4_REFUSED failed_source_readback'; exit 23; }
if [ ! -e "$PREFIX/bin/ritsu-mpv" ] || cmp -s "$0" "$PREFIX/bin/ritsu-mpv"; then
  cp "$0" "$PREFIX/bin/.ritsu-mpv.$$"
  chmod 700 "$PREFIX/bin/.ritsu-mpv.$$"
  mv -f "$PREFIX/bin/.ritsu-mpv.$$" "$PREFIX/bin/ritsu-mpv"
fi
PHASE=idle_gate
idle() {
  [ ! -e "$STATE/playing" ] &&
  [ ! -e "$STATE/ack.pending" ] &&
  [ ! -e "$STATE/stop.request" ] &&
  [ -d "$STATE/lock" ] &&
  [ "$(cat "$STATE/play.seq")" = "$(cat "$STATE/fetch.seq")" ] &&
  [ -z "$(find "$READY" -maxdepth 1 -name '*.part*' -print -quit)" ] &&
  [ -z "$(find "$READY" -maxdepth 1 -name '*.wav' -print | awk -v n="$(cat "$STATE/play.seq")" '{base=$0;sub(/^.*\//,"",base);if(substr(base,1,8)+0>=n+0){print "PENDING";exit}}')" ] &&
  [ ! -e "$STATE/ritsu-mpv.sock" ] &&
  [[ "$(termux-media-player info 2>/dev/null)" == *'No track currently!'* ]]
}
if ! idle; then
  receipt "RITSU_MPV_V4_STAGED=1
LOGIC_AND_REAL_NULL_AUDIO_IPC=PASS
ACTIVATION=DEFERRED_NOT_IDLE
RUN=ritsu-mpv resume"
  exit 0
fi
sleep 2
if ! idle; then
  receipt "RITSU_MPV_V4_STAGED=1
ACTIVATION=DEFERRED_UNSTABLE_IDLE
RUN=ritsu-mpv resume"
  exit 0
fi
PHASE=graceful_old_receiver_stop
touch "$STATE/stop.request"
STOPPED=0
for i in $(seq 1 60); do
  if [ ! -d "$STATE/lock" ]; then STOPPED=1; break; fi
  sleep .25
done
if [ "$STOPPED" != 1 ]; then
  receipt "RITSU_MPV_V4_STAGED=1
ACTIVATION=STOP_NOT_CONFIRMED
DO_NOT_FORCE_RESTART=1"
  exit 24
fi
if [ -e "$STATE/playing" ] || [ -e "$STATE/ack.pending" ]; then
  receipt "RITSU_MPV_V4_STAGED=1
ACTIVATION=POST_STOP_AMBIGUOUS
DO_NOT_REPLAY=1"
  exit 25
fi
PHASE=launch_v4_persistent_mpv
rm -f "$STATE/stop.request"
nohup bash "$LIVE" >>"$ROOT/receiver-v4.log" 2>&1 </dev/null &
pid="$!"
GOOD=0
for i in $(seq 1 48); do
  if [ -S "$STATE/ritsu-mpv.sock" ] && [ -d "$STATE/lock" ] && kill -0 "$pid" 2>/dev/null; then
    GOOD=1
    break
  fi
  sleep .25
done
if [ "$GOOD" != 1 ]; then
  receipt "RITSU_MPV_V4_STAGED=1
ACTIVATION=LAUNCH_UNVERIFIED
LOG=$ROOT/receiver-v4.log
DO_NOT_FORCE_REPLAY=1"
  exit 26
fi
receipt "RITSU_MPV_V4_ACTIVE=1
SOURCE_SHA256=$NEW_SHA
DRIVER_SHA256=$DRIVER_SHA
RECEIVER_PID=$pid
MPV_SOCKET=PRESENT
PLAY_SEQ=$(cat "$STATE/play.seq")
FETCH_SEQ=$(cat "$STATE/fetch.seq")
RELAY=19643
VOICE=UNCHANGED
PCM_TRIM=NONE
NATIVE_MPV_IPC_TEST=PASS
HEARD=unverified"
