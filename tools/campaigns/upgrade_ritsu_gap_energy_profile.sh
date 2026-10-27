#!/data/data/com.termux/files/usr/bin/bash
# Upgrade ONLY the private diagnostic campaign, never the voice receiver.
set -Eeuo pipefail
BASE="$HOME/.local/share/ritsu-phone-gap"
ENTRY="$PREFIX/bin/ritsu-gap"
PREVIOUS="00ab7f1f453847c09f88b830f1259edd8b1c1be3"
NEXT="589f2ff13ee030297c12a149a090cc4cdaf396ee"
REPO="https://raw.githubusercontent.com/Valar05/home-center"
FILES=(ritsu_phone_gap_campaign.py test_ritsu_phone_gap_campaign.py ritsu_pcm_silence_guard.py test_ritsu_pcm_silence_guard.py)
TMP=""; STAGE="preflight"
receipt() {
  printf '%s\n' "$1"
  if command -v termux-clipboard-set >/dev/null 2>&1; then
    printf '%s\n' "$1" | termux-clipboard-set >/dev/null 2>&1 || true
  else
    printf 'CLIPBOARD_UNAVAILABLE\n'
  fi
}
onerror() { local status="$?"; trap - ERR; receipt "RITSU_ENERGY_UPGRADE_FAILED stage=$STAGE exit=$status; voice unchanged"; exit "$status"; }
cleanup() { [[ -z "$TMP" || ! -d "$TMP" ]] || rm -rf -- "$TMP"; }
trap onerror ERR
trap cleanup EXIT
for cmd in curl python3 cmp mktemp; do
  command -v "$cmd" >/dev/null 2>&1 || { receipt "RITSU_ENERGY_UPGRADE_FAILED missing=$cmd"; exit 9; }
done
[[ -f "$BASE/ritsu_phone_gap_campaign.py" && -f "$ENTRY" ]] || { receipt 'RITSU_ENERGY_UPGRADE_FAILED campaign not installed'; exit 10; }
if "$ENTRY" status | grep -Fxq 'WORKER_ALIVE=True'; then receipt 'RITSU_ENERGY_UPGRADE_PAUSED worker running'; exit 11; fi
TMP="$(mktemp -d "$BASE/.energy-candidate.XXXXXXXX")"
chmod 700 "$TMP"
STAGE="download-pinned-files"
for f in "${FILES[@]}"; do
  curl -fLsS --retry 2 "$REPO/$NEXT/tools/campaigns/$f" -o "$TMP/$f"
  curl -fLsS --retry 2 "$REPO/$PREVIOUS/tools/campaigns/$f" -o "$TMP/old-$f"
done
STAGE="reconcile-existing"
for f in "${FILES[@]}"; do
  [[ -f "$BASE/$f" ]] || { receipt "RITSU_ENERGY_RECONCILE_REQUIRED missing=$f; no files changed"; exit 12; }
  cmp -s "$BASE/$f" "$TMP/old-$f" || cmp -s "$BASE/$f" "$TMP/$f" || {
    receipt "RITSU_ENERGY_RECONCILE_REQUIRED local edit=$f; no overwrite"; exit 13;
  }
done
STAGE="offline-tests"
python3 -m py_compile "$TMP/"*.py
(cd "$TMP" && python3 test_ritsu_phone_gap_campaign.py && python3 test_ritsu_pcm_silence_guard.py) >"$TMP/tests.log" 2>&1 || {
  tail -n 35 "$TMP/tests.log" >&2
  receipt 'RITSU_ENERGY_UPGRADE_FAILED tests failed; no files changed'
  exit 14
}
STAGE="backup"
BACKUP="$BASE/backups/energy-$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$BACKUP"
for f in "${FILES[@]}"; do cp -p "$BASE/$f" "$BACKUP/$f"; done
STAGE="install-readonly-profile"
for f in "${FILES[@]}"; do
  cp "$TMP/$f" "$BASE/.new-$f.$$"
  chmod 600 "$BASE/.new-$f.$$"
  mv -f "$BASE/.new-$f.$$" "$BASE/$f"
done
printf 'RITSU_ENERGY_PROBE_INSTALLED=1\nBACKUP=%s\n' "$BACKUP"
# Clipboard receives detailed read-only onset report, no audio is played/edited.
exec "$ENTRY" silence
