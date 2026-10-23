#!/data/data/com.termux/files/usr/bin/bash
# Guarded on-phone install of Ritsu v3 code for NEXT receiver launch.
# Does not stop, restart, or trigger voice, relay, media player or Phone Hands.
set -Eeuo pipefail
ROOT="$HOME/.ritsu-embodiment"
OLD="$ROOT/receiver.sh"
HELPER="$ROOT/ritsu_phone_wav_batch.py"
STATE="$ROOT/receiver-v2"
REF="9f94c5c5d10524c3ea8f265dbacd8ad9bc4031fc"
OLD_SHA="8acd84673b91420dddac5705829e17997ca9dfcde87e5f3d3f35b872f219322f"
BASE="https://raw.githubusercontent.com/Valar05/home-center/$REF/tools/campaigns"
SCRATCH=""
PHASE="preflight"
receipt() {
  printf '%s\n' "$1"
  if command -v termux-clipboard-set >/dev/null 2>&1; then
    printf '%s\n' "$1" | termux-clipboard-set >/dev/null 2>&1 || true
  fi
}
fail() { local ec="$?"; trap - ERR; receipt "RITSU_V3_INSTALL_FAILED
PHASE=$PHASE
CODE=$ec
NO_AUDIO_RESTART=1"; exit "$ec"; }
cleanup(){ [[ -z "$SCRATCH" || ! -d "$SCRATCH" ]] || rm -rf -- "$SCRATCH"; }
trap fail ERR
trap cleanup EXIT
for c in curl python3 bash sha256sum cmp mktemp; do
 command -v "$c" >/dev/null 2>&1 || { receipt "RITSU_V3_INSTALL_REFUSED missing_tool=$c"; exit 10; }
done
[ -f "$OLD" ] || { receipt 'RITSU_V3_INSTALL_REFUSED no_canonical_receiver.sh'; exit 11; }
if [ -e "$ROOT/ritsu_phone_wav_batch.py" ]; then
  receipt 'RITSU_V3_INSTALL_RECONCILE existing_batch_helper; no overwrite'
  exit 12
fi
CURRENT="$(sha256sum "$OLD" | awk '{print $1}')"
if [ "$CURRENT" != "$OLD_SHA" ]; then
  receipt "RITSU_V3_INSTALL_REFUSED original_receiver_hash_mismatch
ACTUAL=$CURRENT
EXPECTED=$OLD_SHA
NO_AUDIO_CHANGE=1"
  exit 13
fi
if [ -e "$STATE/playing" ]; then
  # v3 is safe to install at a future restart even with playback,
  # but do not mutate anything while currently emitting a WAV.
  receipt 'RITSU_V3_INSTALL_PAUSED live_playback_marker_present'
  exit 14
fi
PHASE=download
SCRATCH="$(mktemp -d "$ROOT/.ritsu-v3-stage.XXXXXXXX")"
chmod 700 "$SCRATCH"
for name in ritsu_phone_receiver_prefetch_v3.sh ritsu_phone_wav_batch.py test_ritsu_phone_wav_batch.py; do
 curl -fLsS --retry 2 --max-time 30 "$BASE/$name" -o "$SCRATCH/$name"
done
PHASE=tests
bash -n "$SCRATCH/ritsu_phone_receiver_prefetch_v3.sh"
python3 -m py_compile "$SCRATCH/ritsu_phone_wav_batch.py" "$SCRATCH/test_ritsu_phone_wav_batch.py"
(cd "$SCRATCH" && python3 test_ritsu_phone_wav_batch.py) >"$SCRATCH/tests.txt" 2>&1 || {
  tail -n 30 "$SCRATCH/tests.txt" >&2
  receipt 'RITSU_V3_INSTALL_REFUSED tests_failed; no live change'
  exit 15
}
if [ -e "$STATE/playing" ]; then
 receipt 'RITSU_V3_INSTALL_PAUSED playback_started_during_tests; no change'
 exit 16
fi
[ "$(sha256sum "$OLD" | awk '{print $1}')" = "$OLD_SHA" ] ||
  { receipt 'RITSU_V3_INSTALL_REFUSED receiver_changed_during_tests'; exit 17; }
PHASE=backup
BACKUP="$ROOT/receiver-backups/v3-source-$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$BACKUP"
cp -p "$OLD" "$BACKUP/receiver.sh"
[ "$(sha256sum "$BACKUP/receiver.sh" | awk '{print $1}')" = "$OLD_SHA" ] ||
  { receipt 'RITSU_V3_INSTALL_REFUSED backup_mismatch'; exit 18; }
PHASE=install_for_next_restart
cp "$SCRATCH/ritsu_phone_wav_batch.py" "$ROOT/.batch-helper.$$"
chmod 600 "$ROOT/.batch-helper.$$"
mv -f "$ROOT/.batch-helper.$$" "$HELPER"
cp "$SCRATCH/ritsu_phone_receiver_prefetch_v3.sh" "$ROOT/.receiver-v3.$$"
chmod 700 "$ROOT/.receiver-v3.$$"
NEW_SHA="$(sha256sum "$ROOT/.receiver-v3.$$" | awk '{print $1}')"
mv -f "$ROOT/.receiver-v3.$$" "$OLD"
ACTUAL_SHA="$(sha256sum "$OLD" | awk '{print $1}')"
[ "$ACTUAL_SHA" = "$NEW_SHA" ] || {
 receipt 'RITSU_V3_INSTALL_READBACK_FAILED; rollback_from_backup_required'
 exit 19
}
receipt "RITSU_V3_SOURCE_INSTALLED=1
BACKUP=$BACKUP
OLD_SHA256=$OLD_SHA
NEW_SHA256=$NEW_SHA
BASH_SYNTAX_AND_PCM_TESTS=PASS
ACTIVE_RECEIVER=UNCHANGED_UNTIL_RESTART
RELAY=UNCHANGED
MEDIA_PLAYER=UNCHANGED
VOICES=UNCHANGED
NO_AUDIO_RESTART=1
HEARD=unverified"
